"""Store: safe read-modify-write with atomic replace + backups (PRD §5.7).

All note mutations go through :meth:`Store.mutate`. Windows-agnostic: the
filesystem, clock and sleeper are plain stdlib and injectable for tests.
"""

from __future__ import annotations

import contextlib
import hashlib
import itertools
import logging
import os
import threading
import time
from collections import defaultdict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TypeVar, cast

from dayline.core.errors import LockedFileError, NoteDecodeError
from dayline.core.model import NoteDoc
from dayline.core.parser import empty_doc, parse_bytes
from dayline.core.serializer import serialize

log = logging.getLogger("dayline.core.store")

_T = TypeVar("_T")

_BACKOFF_S = (0.05, 0.1, 0.2, 0.4, 0.8)
_MAX_LOOPS = 3
_tmp_counter = itertools.count(1)


class _Retry:
    __slots__ = ()


_RETRY = _Retry()


def stat_state(path: Path) -> _FileState | None:
    try:
        return _FileState.of(os.stat(path))
    except FileNotFoundError:
        return None


def _retry_exhausted(path: Path) -> LockedFileError:
    return LockedFileError(str(path), _MAX_LOOPS)


@dataclass(frozen=True)
class _FileState:
    mtime_ns: int
    size: int

    @staticmethod
    def of(path: os.stat_result) -> _FileState:
        return _FileState(path.st_mtime_ns, path.st_size)


class Store:
    """Owns the daily-notes folder layout. `path_for(date)` resolves note files;
    `backups_dir` (optional) receives rolling copies of every modified note."""

    def __init__(
        self,
        path_for: Callable[[date], Path],
        heading: str = "## To-Do",
        *,
        backups_dir: Path | None = None,
        backup_keep_days: int = 7,
        now: Callable[[], datetime] = datetime.now,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.path_for = path_for
        self.heading = heading
        self.backups_dir = backups_dir
        self.backup_keep_days = backup_keep_days
        self._now = now
        self._sleep = sleep
        self._locks: defaultdict[Hashable, threading.Lock] = defaultdict(threading.Lock)
        self._guard = threading.Lock()
        # own-write suppression: (mtime_ns, size, sha1) of our last write per path
        self._own_writes: dict[Path, tuple[_FileState, str]] = {}

    # ---------------------------------------------------------------- read --
    def exists(self, d: date) -> bool:
        return self.path_for(d).is_file()

    def read_doc(self, d: date) -> NoteDoc:
        path = self.path_for(d)
        if not path.is_file():
            return empty_doc(self.heading)
        raw = path.read_bytes()
        try:
            return parse_bytes(raw, self.heading)
        except NoteDecodeError:
            log.warning("skipping non-UTF-8 note at %s", path)
            raise

    def _lock_for(self, d: date) -> threading.Lock:
        key: Hashable = str(os.path.normcase(str(self.path_for(d))))
        with self._guard:
            return self._locks[key]

    # -------------------------------------------------------------- mutate --
    def mutate(self, d: date, fn: Callable[[NoteDoc], _T]) -> _T | None:
        """Fresh read → fn → surgical write. `fn` returning None/False skips the
        write (no-op rollover days etc). Returns fn's result or None."""
        with self._lock_for(d):
            for _loop in range(_MAX_LOOPS):
                outcome = self._mutate_once(d, fn)
                if outcome is _RETRY:
                    continue
                return cast("_T | None", outcome)
            raise _retry_exhausted(self.path_for(d))

    def _mutate_once(self, d: date, fn: Callable[[NoteDoc], _T]) -> object:
        path = self.path_for(d)
        before_state = stat_state(path)
        doc = self.read_doc(d)
        result = fn(doc)
        if result is None or result is False:
            return None
        out = serialize(doc)
        if before_state is not None and path.read_bytes() == out:
            return result  # surgical edit turned out identical — no touch
        self._backup(path)
        tmp = self._write_temp(path, out)
        if stat_state(path) != before_state:
            self._cleanup_temp(path, tmp)  # external write raced us: redo fresh
            return _RETRY
        try:
            self._replace(tmp, path)
        except OSError:
            self._cleanup_temp(path, tmp)
            raise
        self._remember_write(path, out)
        return result

    def _replace(self, tmp: Path, path: Path) -> None:
        for attempt, delay in enumerate((*_BACKOFF_S, 0.0)):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt >= len(_BACKOFF_S):
                    raise LockedFileError(str(path), attempt + 1) from None
                log.info(
                    "replace locked (attempt %d), backing off %.0f ms", attempt + 1, delay * 1000
                )
                self._sleep(delay)

    def _write_temp(self, path: Path, payload: bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.parent / f".{path.name}.{os.getpid()}.{next(_tmp_counter)}.tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
        except OSError:
            tmp.unlink(missing_ok=True)
            raise
        return tmp

    def _cleanup_temp(self, path: Path, tmp: Path | None) -> None:
        candidates = [tmp] if tmp else list(path.parent.glob(f".{path.name}.*.tmp"))
        for c in candidates:
            if c is not None:
                try:
                    c.unlink(missing_ok=True)
                except OSError:  # pragma: no cover - locked temp, GC'd later
                    log.debug("could not remove temp %s", c)

    def _backup(self, path: Path) -> None:
        if self.backups_dir is None or not path.is_file():
            return
        try:
            day = self._now().strftime("%Y-%m-%d")
            target_dir = self.backups_dir / day
            target_dir.mkdir(parents=True, exist_ok=True)
            stamp = self._now().strftime("%H%M%S-%f")
            target = target_dir / f"{path.stem}.{stamp}.md"
            target.write_bytes(path.read_bytes())
            self._prune_backups()
        except OSError:
            log.warning("backup failed for %s (continuing)", path, exc_info=True)

    def _prune_backups(self) -> None:
        assert self.backups_dir is not None
        cutoff = (self._now() - timedelta(days=self.backup_keep_days)).strftime("%Y-%m-%d")
        for entry in self.backups_dir.iterdir():
            if entry.is_dir() and entry.name < cutoff:
                for f in entry.iterdir():
                    f.unlink(missing_ok=True)
                with contextlib.suppress(OSError):  # pragma: no cover
                    entry.rmdir()

    def _remember_write(self, path: Path, payload: bytes) -> None:
        st = os.stat(path)
        self._own_writes[path] = (
            _FileState(st.st_mtime_ns, st.st_size),
            hashlib.sha1(payload).hexdigest(),
        )

    # ------------------------------------------------ own-write suppression --
    def is_own_write(self, path: Path) -> bool:
        """True when the file's current state matches our last recorded write
        (mtime+size, then sha1 of content). Watcher uses this to skip self-writes."""
        recorded = self._own_writes.get(path)
        if recorded is None or not path.is_file():
            return False
        state, digest = recorded
        st = os.stat(path)
        if _FileState(st.st_mtime_ns, st.st_size) != state:
            return False
        return hashlib.sha1(path.read_bytes()).hexdigest() == digest

    def forget_own_write(self, path: Path) -> None:
        self._own_writes.pop(path, None)

    def write_bytes(self, path: Path, payload: bytes) -> None:
        """Atomic raw write (undo/redo). Records the own-write signature so the
        watcher ignores it. No read-modify-write: caller owns the exact bytes."""
        path.parent.mkdir(parents=True, exist_ok=True)
        self._backup(path)
        tmp = self._write_temp(path, payload)
        try:
            self._replace(tmp, path)
        except OSError:
            self._cleanup_temp(path, tmp)
            raise
        self._remember_write(path, payload)
