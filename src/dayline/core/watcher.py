"""External-change detection for two-way sync (PRD §5.8, FR-O5).

Pure and testable: tracks each note's (mtime_ns, size); a change is reported
only when the file differs from the last seen state AND is not one of our own
recorded writes (``Store.is_own_write``), which prevents self-reload loops.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from dayline.core.store import stat_state

if TYPE_CHECKING:  # pragma: no cover
    from dayline.core.store import Store


class ChangeDetector:
    def __init__(self, store: Store) -> None:
        self._store = store
        self._last: dict[Path, tuple[int, int]] = {}

    def prime(self, d: date) -> None:
        path = self._store.path_for(d)
        st = stat_state(path)
        if st is not None:
            self._last[path] = (st.mtime_ns, st.size)

    def changed_days(self, dates: list[date]) -> list[date]:
        """Return dates whose note changed externally since last seen."""
        out: list[date] = []
        for d in dates:
            path = self._store.path_for(d)
            st = stat_state(path)
            cur = (st.mtime_ns, st.size) if st else None
            prev = self._last.get(path)
            if cur is None:
                if prev is not None:
                    del self._last[path]
                continue
            if prev != cur:
                self._last[path] = cur
                if self._store.is_own_write(path):
                    continue  # our own write → suppress
                out.append(d)
        return out

    def forget(self, path: Path) -> None:
        self._last.pop(path, None)
