"""Stats + cache invalidation tests (FR-W5)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from dayline.core.model import NoteDoc
from dayline.core.parser import parse_text
from dayline.core.stats import DayStats, StatsService, day_stats
from dayline.core.store import Store

D = date(2026, 9, 19)


@pytest.fixture()
def store(tmp_path: Path) -> Store:
    def path_for(d: date) -> Path:
        return tmp_path / f"{d.isoformat()}.md"

    path_for(D).parent.mkdir(parents=True, exist_ok=True)
    return Store(path_for)


def test_day_stats_excludes_moved_cancelled_custom() -> None:
    doc = parse_text("## To-Do\n- [ ] a\n- [x] b\n- [/] c\n- [>] d\n- [-] e\n- [?] f\n")
    assert day_stats(doc) == DayStats(done=1, total=3)


def test_percent_and_open() -> None:
    assert DayStats(13, 19).percent == 68
    assert DayStats(1, 3).percent == 33
    assert DayStats(0, 0).percent == 0
    assert DayStats(2, 5).open_count == 3


def test_stats_service_missing_note(store: Store) -> None:
    assert StatsService(store).day(D) == DayStats(0, 0)


def test_stats_cache_hit_and_invalidate(store: Store, monkeypatch: pytest.MonkeyPatch) -> None:
    store.path_for(D).write_text("## To-Do\n- [x] a\n", encoding="utf-8")
    svc = StatsService(store)
    calls = {"n": 0}
    real = store.read_doc

    def counting(d: date) -> NoteDoc:
        calls["n"] += 1
        return real(d)

    monkeypatch.setattr(store, "read_doc", counting)
    assert svc.day(D) == DayStats(1, 1)
    assert svc.day(D) == DayStats(1, 1)
    assert calls["n"] == 1  # cache hit
    store.path_for(D).write_text("## To-Do\n- [x] a\n- [ ] b\n", encoding="utf-8")
    assert svc.day(D) == DayStats(1, 2)  # state changed → recompute
    assert calls["n"] == 2
