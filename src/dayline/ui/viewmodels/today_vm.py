"""TodayViewModel: one day's sections + progress, read-only (M2).

Exposes each section as a plain list of row dicts (via task_to_row) so QML
Repeaters get simple, reliably-updating models.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from PySide6.QtCore import Property, QObject, Signal

from dayline.core.model import PRIO_RANK, StatusKind, Task
from dayline.core.stats import DayStats
from dayline.ui.viewmodels.task_model import task_to_row

_DONE_SECTION_KINDS = (StatusKind.DONE, StatusKind.CANCELLED, StatusKind.CUSTOM)


def _sort_key(pair: tuple[int, Task]) -> tuple[int, int]:
    idx, t = pair
    return (PRIO_RANK.get(t.priority, 5), idx)  # stable: ties keep file order (FR-D4)


class TodayViewModel(QObject):
    changed = Signal()
    dateChanged = Signal()
    prevDayRequested = Signal()
    nextDayRequested = Signal()
    goTodayRequested = Signal()
    retryRequested = Signal()

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._day = date.today()
        self._today_flag = True
        self._stats = DayStats(0, 0)
        self._loading = True
        self._error = ""
        self._carried_over = 0
        self._todo: list[dict[str, Any]] = []
        self._done: list[dict[str, Any]] = []
        self._carried: list[dict[str, Any]] = []

    # -- properties ---------------------------------------------------------
    def _progress(self) -> float:
        return self._stats.done / self._stats.total if self._stats.total else 0.0

    def _has_tasks(self) -> bool:
        return bool(self._todo or self._done or self._carried)

    day = Property(str, lambda self: self._day.strftime("%Y-%m-%d"), notify=dateChanged)
    dateLabel = Property(str, lambda self: self._day.strftime("%A, %d %B %Y"), notify=dateChanged)
    isToday = Property(bool, lambda self: self._today_flag, notify=changed)
    progress = Property(float, _progress, notify=changed)
    percent = Property(int, lambda self: self._stats.percent, notify=changed)
    doneCount = Property(int, lambda self: self._stats.done, notify=changed)
    totalCount = Property(int, lambda self: self._stats.total, notify=changed)
    loading = Property(bool, lambda self: self._loading, notify=changed)
    errorText = Property(str, lambda self: self._error, notify=changed)
    carriedOver = Property(int, lambda self: self._carried_over, notify=changed)
    todoList = Property(list, lambda self: self._todo, notify=changed)
    doneList = Property(list, lambda self: self._done, notify=changed)
    carriedList = Property(list, lambda self: self._carried, notify=changed)
    todoCount = Property(int, lambda self: len(self._todo), notify=changed)
    doneSectionCount = Property(int, lambda self: len(self._done), notify=changed)
    carriedSectionCount = Property(int, lambda self: len(self._carried), notify=changed)
    hasTasks = Property(bool, _has_tasks, notify=changed)

    # -- data ---------------------------------------------------------------
    def set_date(self, d: date) -> None:
        self._day = d
        self._loading = True
        self._error = ""
        self.dateChanged.emit()
        self.changed.emit()

    def set_carried_over(self, n: int) -> None:
        if n != self._carried_over:
            self._carried_over = n
            self.changed.emit()

    def apply_doc(self, doc: Any, *, today: date) -> None:
        tasks: list[Task] = doc.tasks if doc is not None else []
        todo = [(i, t) for i, t in enumerate(tasks) if t.kind is StatusKind.OPEN]
        done = [(i, t) for i, t in enumerate(tasks) if t.kind in _DONE_SECTION_KINDS]
        carried = [(i, t) for i, t in enumerate(tasks) if t.kind is StatusKind.MOVED]
        self._todo = [task_to_row(t) for _, t in sorted(todo, key=_sort_key)]
        self._done = [task_to_row(t) for _, t in done]
        self._carried = [task_to_row(t) for _, t in carried]
        self._stats = _stats_from(tasks)
        self._loading = False
        self._error = ""
        self._today_flag = self._day == today
        self.changed.emit()

    def set_error(self, msg: str) -> None:
        self._error = msg
        self._loading = False
        self.changed.emit()

    def set_loading(self, flag: bool) -> None:
        self._loading = flag
        self.changed.emit()

    @property
    def current_date(self) -> date:
        return self._day

    def open_count(self) -> int:
        return self._stats.open_count

    @property
    def is_today(self) -> bool:
        return self._today_flag


def _stats_from(tasks: list[Task]) -> DayStats:
    counted = [t for t in tasks if t.kind in (StatusKind.OPEN, StatusKind.DONE)]
    return DayStats(done=sum(1 for t in counted if t.kind is StatusKind.DONE), total=len(counted))
