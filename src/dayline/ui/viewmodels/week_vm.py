"""WeekViewModel: Mon–Sun (or Sun–Sat) overview backed by cached day stats (FR-W1..W5)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from PySide6.QtCore import Property, QObject, Signal

from dayline.core.clock import logical_date
from dayline.core.stats import StatsService
from dayline.core.store import Store

_WEEKDAY = {"mon": 0, "sun": 6}


class WeekViewModel(QObject):
    changed = Signal()
    dayRequested = Signal(object)  # date → open in Today

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._store: Store | None = None
        self._stats: StatsService | None = None
        self._week_start = "mon"
        self._anchor = date.today()  # any date within the shown week
        self._days: list[dict[str, Any]] = []
        self._week_done = 0
        self._week_total = 0
        self._title = ""
        self._month_heat: list[dict[str, Any]] = []

    def bind(self, store: Store, *, week_start: str, now_provider: Any) -> None:
        self._store = store
        self._stats = StatsService(store)
        self._week_start = week_start if week_start in _WEEKDAY else "mon"
        self._now_provider = now_provider
        self.refresh()

    # -- properties -----------------------------------------------------------
    days = Property(list, lambda self: self._days, notify=changed)
    weekDone = Property(int, lambda self: self._week_done, notify=changed)
    weekTotal = Property(int, lambda self: self._week_total, notify=changed)
    weekPercent = Property(
        int,
        lambda self: round(100 * self._week_done / self._week_total) if self._week_total else 0,
        notify=changed,
    )
    rangeLabel = Property(str, lambda self: self._title, notify=changed)
    monthHeat = Property(list, lambda self: self._month_heat, notify=changed)

    # -- navigation -----------------------------------------------------------
    def _week_start_date(self, anchor: date) -> date:
        return anchor - timedelta(days=(anchor.weekday() - _WEEKDAY[self._week_start]) % 7)

    def refresh(self) -> None:
        if self._store is None or self._stats is None:
            return
        today = logical_date(self._now_provider(), 0)
        start = self._week_start_date(self._anchor)
        days: list[dict[str, Any]] = []
        done = total = 0
        for i in range(7):
            d = start + timedelta(days=i)
            st = self._stats.day(d)
            done += st.done
            total += st.total
            days.append(
                {
                    "dateStr": d.isoformat(),
                    "label": d.strftime("%a"),
                    "dayNum": d.day,
                    "done": st.done,
                    "total": st.total,
                    "percent": st.percent,
                    "isToday": d == today,
                    "isFuture": d > today,
                }
            )
        self._days = days
        self._week_done = done
        self._week_total = total
        self._title = f"{start:%d %b} – {start + timedelta(days=6):%d %b %Y}"
        self._month_heat = self._build_month_heat()
        self.changed.emit()

    def _build_month_heat(self) -> list[dict[str, Any]]:
        """FR-W3: month grid cells for a 7-column heat-map (leading blanks align
        day 1 under its weekday; each real cell carries completion %)."""
        import calendar

        if self._stats is None:
            return []
        y, m = self._anchor.year, self._anchor.month
        first = date(y, m, 1)
        ndays = calendar.monthrange(y, m)[1]
        offset = (first.weekday() - _WEEKDAY[self._week_start]) % 7
        cells: list[dict[str, Any]] = [{"empty": True} for _ in range(offset)]
        for i in range(ndays):
            d = first + timedelta(days=i)
            st = self._stats.day(d)
            cells.append(
                {
                    "empty": False,
                    "dateStr": d.isoformat(),
                    "day": d.day,
                    "percent": st.percent,
                    "hasTasks": st.total > 0,
                }
            )
        return cells

    def invalidate(self) -> None:
        if self._stats is not None:
            self._stats.invalidate()
        self.refresh()

    @staticmethod
    def _shift(anchor: date, weeks: int) -> date:
        return anchor + timedelta(weeks=weeks)

    def prevWeek(self) -> None:
        self._anchor = self._shift(self._anchor, -1)
        self.refresh()

    def nextWeek(self) -> None:
        self._anchor = self._shift(self._anchor, 1)
        self.refresh()

    def thisWeek(self) -> None:
        self._anchor = logical_date(self._now_provider(), 0)
        self.refresh()

    def openDay(self, dateStr: str) -> None:
        self.dayRequested.emit(date.fromisoformat(dateStr))
