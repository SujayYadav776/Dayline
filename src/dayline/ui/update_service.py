"""Async update worker. Network I/O runs on a short-lived QThread so the UI
never blocks; results are marshalled back via Qt signals (auto-queued to the
GUI thread). No settings/state mutation ever happens off the main thread."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot

from dayline.core.updater import Fetcher, UpdateInfo, check_for_update

Downloader = Callable[[str, Path], Path]


class UpdateService(QObject):
    resultReady = Signal(object)  # UpdateInfo | None (None = up-to-date or error)
    downloadReady = Signal(str)  # absolute installer path
    failed = Signal(str)  # human-readable message

    def __init__(
        self,
        current_version: str,
        url: str,
        fetcher: Fetcher,
        downloader: Downloader,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._current = current_version
        self._url = url
        self._fetcher = fetcher
        self._downloader = downloader
        self._threads: list[QThread] = []
        self._info: UpdateInfo | None = None
        self._busy = False

    @property
    def busy(self) -> bool:
        return self._busy

    @property
    def latest(self) -> UpdateInfo | None:
        return self._info

    # -- check --------------------------------------------------------------
    @Slot()
    def check(self) -> None:
        if self._busy:
            return
        self._busy = True
        t = _Task(self._spawn_check)
        t.done.connect(self._on_checked)
        self._track(t)
        t.start()

    def _spawn_check(self) -> tuple[UpdateInfo | None, str]:
        try:
            return check_for_update(self._fetcher, self._url, self._current), ""
        except Exception as exc:
            return None, str(exc)

    def _on_checked(self, info: UpdateInfo | None, error: str) -> None:
        self._busy = False
        if error:
            self.failed.emit(error)
            return
        self._info = info
        self.resultReady.emit(info)

    # -- install ------------------------------------------------------------
    @Slot(str, str)
    def download(self, url: str, dest: str) -> None:
        if self._busy or not url:
            return
        self._busy = True
        target = Path(dest)
        t = _Task(lambda: self._spawn_download(url, target))
        t.done.connect(self._on_downloaded)
        self._track(t)
        t.start()

    def _spawn_download(self, url: str, dest: Path) -> tuple[str, str]:
        try:
            return str(self._downloader(url, dest)), ""
        except Exception as exc:
            return "", str(exc)

    def _on_downloaded(self, path: str, error: str) -> None:
        self._busy = False
        if error:
            self.failed.emit(error)
        else:
            self.downloadReady.emit(path)

    def _track(self, t: QThread) -> None:
        self._threads.append(t)
        t.finished.connect(lambda: self._retire(t))

    def _retire(self, t: QThread) -> None:
        if t in self._threads:
            self._threads.remove(t)
        t.deleteLater()


class _Task(QThread):
    """Runs ``work()`` off the GUI thread and emits (value_a, value_b)."""

    done = Signal(object, str)

    def __init__(self, work: Callable[[], tuple[Any, str]]) -> None:
        super().__init__()
        self._work = work

    def run(self) -> None:
        a, b = self._work()
        self.done.emit(a, b)
