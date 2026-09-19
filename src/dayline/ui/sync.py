"""Qt file watching for live two-way sync (PRD §5.8, FR-O5).

Watches the daily-notes directory with a 200 ms debounce, plus a cheap 5 s
stat-poll fallback (atomic replaces can miss a directory signal). Emits
``dayChanged(date)`` only for genuine external edits — our own writes are
suppressed by the ChangeDetector so we never trigger a reload loop.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from PySide6.QtCore import QFileSystemWatcher, QObject, QTimer, Signal

from dayline.core.watcher import ChangeDetector


class FileSync(QObject):
    dayChanged = Signal(object)  # date

    def __init__(
        self,
        detector: ChangeDetector,
        *,
        debounce_ms: int = 200,
        poll_ms: int = 5000,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._detector = detector
        self._dates: list[date] = []
        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._on_dir)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(debounce_ms)
        self._debounce.timeout.connect(self.check)
        self._poll = QTimer(self)
        self._poll.setInterval(poll_ms)
        self._poll.timeout.connect(self._rearm_and_check)

    def watch(self, folder: Path, dates: list[date]) -> None:
        self._dates = list(dates)
        for d in dates:
            self._detector.prime(d)
        if folder.is_dir() and str(folder) not in self._watcher.directories():
            self._watcher.addPath(str(folder))

    def start(self) -> None:
        self._poll.start()

    def stop(self) -> None:
        self._poll.stop()
        self._debounce.stop()

    def _on_dir(self, _path: str) -> None:
        self._debounce.start()

    def _rearm_and_check(self) -> None:
        # QFileSystemWatcher can drop a directory after rapid replaces; re-add.
        for d in self._watcher.directories():
            if not Path(d).is_dir():
                self._watcher.removePath(d)
        self.check()

    def check(self) -> list[date]:
        """Detect and emit external changes; returns the changed dates."""
        changed = self._detector.changed_days(self._dates)
        for d in changed:
            self.dayChanged.emit(d)
        return changed
