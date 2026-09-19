"""Day/week statistics with (path, mtime_ns, size) caching (PRD FR-W5)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from dayline.core.model import NoteDoc, StatusKind
from dayline.core.store import stat_state

if TYPE_CHECKING:  # pragma: no cover
    from dayline.core.store import Store


@dataclass(frozen=True)
class DayStats:
    done: int
    total: int  # counts exclude moved/cancelled/custom (PRD §5.2)

    @property
    def percent(self) -> int:
        return round(100 * self.done / self.total) if self.total else 0

    @property
    def open_count(self) -> int:
        return self.total - self.done


def day_stats(doc: NoteDoc) -> DayStats:
    counted = [t for t in doc.tasks if t.kind in (StatusKind.OPEN, StatusKind.DONE)]
    return DayStats(done=sum(1 for t in counted if t.kind is StatusKind.DONE), total=len(counted))


class StatsService:
    """Lazily computes and caches per-day stats; cache keyed by file state."""

    def __init__(self, store: Store) -> None:
        self._store = store
        self._cache: dict[tuple[str, int, int], DayStats] = {}

    def day(self, d: date) -> DayStats:
        path = self._store.path_for(d)
        state = stat_state(path)
        if state is None:
            return DayStats(0, 0)
        key = (str(path).casefold(), state.mtime_ns, state.size)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        stats = day_stats(self._store.read_doc(d))
        if len(self._cache) > 512:
            self._cache.clear()
        self._cache[key] = stats
        return stats

    def days(self, dates: Iterable[date]) -> dict[date, DayStats]:
        return {d: self.day(d) for d in dates}

    def invalidate(self) -> None:
        self._cache.clear()
