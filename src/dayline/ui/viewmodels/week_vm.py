"""WeekViewModel: Mon–Sun (or Sun–Sat) overview backed by cached day stats (FR-W1..W5)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from PySide6.QtCore import Property, QObject, Signal

from dayline.core.clock import logical_date
from dayline.core.stats import DayStats, StatsService
from dayline.core.store import Store

_WEEKDAY = {"mon": 0, "sun": 6}


def _heat_level(done: int) -> int:
    if done == 0:
        return 0
    if done <= 1:
        return 1
    if done <= 2:
        return 2
    if done <= 4:
        return 3
    return 4


class WeekViewModel(QObject):
    changed = Signal()
    dayRequested = Signal(object)  # date → open in Today

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._store: Store | None = None
        self._stats: StatsService | None = None
        self._week_start = "mon"
        self._anchor = date.today()  # any date within the shown week
        self._selected: date | None = None  # day highlighted in the bottom strip
        self._days: list[dict[str, Any]] = []
        self._strip: list[dict[str, Any]] = []
        self._activity: list[dict[str, Any]] = []
        self._activity_months: list[dict[str, Any]] = []
        self._streak = 0
        self._done_today = 0
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
    # Bottom week-strip cells + Progress-panel stats (paper design).
    strip = Property(list, lambda self: self._strip, notify=changed)
    streak = Property(int, lambda self: self._streak, notify=changed)
    doneToday = Property(int, lambda self: self._done_today, notify=changed)
    activity = Property(list, lambda self: self._activity, notify=changed)
    activityMonths = Property(list, lambda self: self._activity_months, notify=changed)

    # -- navigation -----------------------------------------------------------
    def _week_start_date(self, anchor: date) -> date:
        return anchor - timedelta(days=(anchor.weekday() - _WEEKDAY[self._week_start]) % 7)

    def set_anchor(self, d: date) -> None:
        """Follow the day currently open in Today (keeps the strip in sync)."""
        self._anchor = d
        self._selected = d
        self.refresh()

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
        self._strip = self._build_strip(start, today)
        self._done_today = self._stats.day(today).done
        self._streak = self._build_streak(today)
        self._activity, self._activity_months = self._build_activity(today)
        self.changed.emit()

    def _build_strip(self, start: date, today: date) -> list[dict[str, Any]]:
        """Seven cells for the bottom calendar strip (mockup): number, weekday
        letter, today/selected flags, and completion for the column fill."""
        out: list[dict[str, Any]] = []
        for i in range(7):
            d = start + timedelta(days=i)
            st = self._stats.day(d) if self._stats is not None else DayStats(0, 0)
            out.append(
                {
                    "dateStr": d.isoformat(),
                    "dayNum": d.day,
                    "letter": d.strftime("%a")[0].upper(),
                    "isToday": d == today,
                    "isSelected": d == self._selected,
                    "isFuture": d > today,
                    "percent": st.percent,
                }
            )
        return out

    def _build_streak(self, today: date) -> int:
        """Consecutive days (ending today, or yesterday if today is still
        untouched) with at least one completed task."""
        assert self._stats is not None  # guarded by refresh()
        d = today
        if self._stats.day(d).done == 0:
            d -= timedelta(days=1)
        n = 0
        while n < 365 and self._stats.day(d).done > 0:
            n += 1
            d -= timedelta(days=1)
        return n

    def _build_activity(self, today: date) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """GitHub-style heat-map: 13 week-columns × 7 day-rows, column-major
        (QML Grid flow LayoutDown, rows 7), plus month labels per column."""
        assert self._stats is not None
        ws = _WEEKDAY[self._week_start]
        this_week_start = today - timedelta(days=(today.weekday() - ws) % 7)
        first_col = this_week_start - timedelta(weeks=12)
        cells: list[dict[str, Any]] = []
        months: list[dict[str, Any]] = []
        prev_month: int | None = None
        for w in range(13):
            col0 = first_col + timedelta(weeks=w)
            if col0.month != prev_month:
                months.append({"col": w, "label": col0.strftime("%b")})
                prev_month = col0.month
            for i in range(7):
                d = col0 + timedelta(days=i)
                st = self._stats.day(d)
                cells.append(
                    {
                        "dateStr": d.isoformat(),
                        "done": st.done,
                        "total": st.total,
                        "level": _heat_level(st.done),
                        "future": d > today,
                    }
                )
        return cells, months

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
