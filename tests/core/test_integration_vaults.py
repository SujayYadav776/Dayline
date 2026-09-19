"""Integration tests against the committed fixture vaults (PRD §8.1)."""

from __future__ import annotations

import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest

from dayline.core.model import Priority
from dayline.core.obsidian import DailyNotesSettings, note_path
from dayline.core.rollover import rollover
from dayline.core.settings import Settings
from dayline.core.stats import DayStats, day_stats
from dayline.core.store import Store

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "vaults"
TODAY = date(2026, 9, 19)


def make_store(vault: Path, settings: Settings) -> Store:
    def path_for(d: date) -> Path:
        return note_path(vault, DailyNotesSettings(settings.folder, settings.date_format), d)

    return Store(path_for, heading=settings.heading, sleep=lambda _s: None)


@pytest.fixture()
def default_vault(tmp_path: Path) -> Path:
    dst = tmp_path / "vault"
    shutil.copytree(FIXTURES / "default", dst)
    return dst


def test_default_fixture_parses_expected_shapes(default_vault: Path) -> None:
    s = make_store(default_vault, Settings())
    doc = s.read_doc(TODAY)
    assert [t.body.split(" ")[0] for t in doc.tasks] == [
        "Write",
        "collect",
        "Email",
        "Renew",
        "Abandoned",
        "Reading",
        "Buy",
    ]
    st = day_stats(doc)
    # counted (open/done, incl. subtask): Write, collect, Reading(/), Buy, Email(x)
    assert st == DayStats(done=1, total=5)


def test_fixture_bytes_stable_roundtrip(default_vault: Path) -> None:
    s = make_store(default_vault, Settings())
    p = s.path_for(TODAY)
    original = p.read_bytes()
    s.mutate(TODAY, lambda d: True)  # no-op mutation must not touch bytes
    assert p.read_bytes() == original


def test_rollover_over_fixture(tmp_path: Path, default_vault: Path) -> None:
    s = make_store(default_vault, Settings())
    res = rollover(s, TODAY, lookback=30)
    assert res.moved == 2  # 'plan the week' + 'grocery run' were the open 09-18 tasks
    today = s.read_doc(TODAY)
    bodies = [t.description for t in today.tasks]
    assert "plan the week" in bodies  # carried with recurrence + due preserved
    carried = next(t for t in today.tasks if t.description == "plan the week")
    assert "🔁 every monday" in carried.body and "📅 2026-09-21" in carried.body
    yday = s.read_doc(TODAY - timedelta(days=1))
    assert "- [>] plan the week 🔁 every monday 📅 2026-09-21" in "\n".join(
        ln.text for ln in yday.lines
    )
    assert "## Notes" in "\n".join(ln.text for ln in yday.lines)  # section after kept


def test_nested_format_vault(tmp_path: Path) -> None:
    dst = tmp_path / "nested"
    shutil.copytree(FIXTURES / "nested-folder", dst)
    settings = Settings(folder="", date_format="YYYY/MM/YYYY-MM-DD")
    s = make_store(dst, settings)
    doc = s.read_doc(TODAY)
    assert [t.description for t in doc.tasks][:1] == ["triage inbox"]
    assert len(doc.tasks) == 3  # h3 content stays inside the managed section
    s.mutate(TODAY, lambda d: d.add_task("added", Priority.MEDIUM) and True)
    text = s.path_for(TODAY).read_text("utf-8")
    assert "- [ ] added 🔼" in text
    assert "## Log" in text  # later content preserved


def test_add_task_lands_before_next_heading(tmp_path: Path) -> None:
    dst = tmp_path / "nested"
    shutil.copytree(FIXTURES / "nested-folder", dst)
    settings = Settings(folder="", date_format="YYYY/MM/YYYY-MM-DD")
    s = make_store(dst, settings)
    s.mutate(TODAY, lambda d: d.add_task("Z last") and True)
    lines = [ln.text for ln in s.read_doc(TODAY).lines]
    assert lines.index("- [ ] Z last") < lines.index("## Log")
    assert lines[-1] == "all clear"
