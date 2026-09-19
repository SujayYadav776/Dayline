"""Rollover tests: normative algorithm checks + hypothesis properties (PRD §5.5)."""

from __future__ import annotations

import re
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dayline.core.model import normalize
from dayline.core.rollover import rollover
from dayline.core.store import Store

TODAY = date(2026, 9, 19)


@pytest.fixture()
def store(tmp_path: Path) -> Store:
    def path_for(d: date) -> Path:
        return tmp_path / f"{d.isoformat()}.md"

    return Store(path_for, sleep=lambda _s: None)


def write(store: Store, d: date, body: str) -> None:
    store.path_for(d).write_text(body, encoding="utf-8")


def read(store: Store, d: date) -> str:
    p = store.path_for(d)
    return p.read_text("utf-8") if p.exists() else ""


def test_basic_carry_and_mark(store: Store) -> None:
    write(store, TODAY - timedelta(days=2), "## To-Do\n- [ ] old open ⏫\n- [x] old done\n")
    write(store, TODAY - timedelta(days=1), "## To-Do\n- [ ] yesterday\n")
    res = rollover(store, TODAY, lookback=30)
    assert res.moved == 2
    today = read(store, TODAY)
    assert "- [ ] old open ⏫" in today  # priority preserved (FR-R7)
    assert "- [ ] yesterday" in today
    assert "- [x] old done" not in today
    src = read(store, TODAY - timedelta(days=2))
    assert "- [>] old open ⏫" in src  # source marked (FR-R2)
    assert "- [x] old done" in src  # untouched


def test_idempotent(store: Store) -> None:
    write(store, TODAY - timedelta(days=1), "## To-Do\n- [ ] one\n    - [ ] sub\n")
    rollover(store, TODAY, 30)
    snap_day = read(store, TODAY - timedelta(days=1))
    snap_today = read(store, TODAY)
    again = rollover(store, TODAY, 30)
    assert again.moved == 0 and again.marked_days == 0
    assert read(store, TODAY - timedelta(days=1)) == snap_day
    assert read(store, TODAY) == snap_today


def test_dedupe_against_today_but_still_marks(store: Store) -> None:
    write(store, TODAY, "## To-Do\n- [ ] Buy milk\n")
    write(store, TODAY - timedelta(days=3), "## To-Do\n- [ ] Buy milk\n")
    write(store, TODAY - timedelta(days=2), "## To-Do\n- [ ]   buy   MILK ⏫\n")
    res = rollover(store, TODAY, 30)
    today = read(store, TODAY)
    assert today.count("- [ ] Buy milk") == 1  # no duplicates (FR-R3)
    assert res.moved == 0
    assert "- [>] Buy milk" in read(store, TODAY - timedelta(days=3))
    assert "- [>]   buy   MILK ⏫" in read(store, TODAY - timedelta(days=2))


def test_order_oldest_first(store: Store) -> None:
    write(store, TODAY - timedelta(days=3), "## To-Do\n- [ ] A\n")
    write(store, TODAY - timedelta(days=1), "## To-Do\n- [ ] B\n")
    rollover(store, TODAY, 30)
    today = read(store, TODAY)
    assert today.index("- [ ] A") < today.index("- [ ] B")


def test_never_carries_cancelled_custom_done_moved(store: Store) -> None:
    src = "## To-Do\n- [-] cancel\n- [?] custom\n- [x] fin\n- [>] already\n- [/] progress\n"
    write(store, TODAY - timedelta(days=1), src)
    rollover(store, TODAY, 30)
    today = read(store, TODAY)
    assert "- [ ] progress" in today
    for gone in ("cancel", "custom", "fin", "already"):
        assert gone not in today
    after = read(store, TODAY - timedelta(days=1))
    assert "- [-] cancel" in after and "- [?] custom" in after  # FR-R8 untouched
    assert "- [>] progress" in after  # carried in-progress marked '>'


def test_subtasks_travel_with_parent_reset_open(store: Store) -> None:
    write(
        store,
        TODAY - timedelta(days=1),
        "## To-Do\n- [ ] parent 🔼\n    - [x] done child\n    - [ ] open child\n",
    )
    rollover(store, TODAY, 30)
    today = read(store, TODAY)
    assert "- [ ] parent 🔼" in today
    assert "    - [ ] done child" in today  # reset to open per FR-R4
    assert "    - [ ] open child" in today
    src = read(store, TODAY - timedelta(days=1))
    assert "- [>] parent 🔼" in src
    assert "    - [x] done child" in src  # children untouched in source


def test_missing_today_note_created_only_when_gaining(store: Store) -> None:
    rollover(store, TODAY, 30)
    assert not store.path_for(TODAY).exists()
    write(store, TODAY - timedelta(days=1), "## To-Do\n- [ ] x\n")
    rollover(store, TODAY, 30)
    assert store.path_for(TODAY).is_file()


def test_lookback_window_boundary(store: Store) -> None:
    write(store, TODAY - timedelta(days=31), "## To-Do\n- [ ] too old\n")
    write(store, TODAY - timedelta(days=30), "## To-Do\n- [ ] boundary\n")
    rollover(store, TODAY, 30)
    today = read(store, TODAY)
    assert "boundary" in today and "too old" not in today


def test_rollover_survives_no_heading_note(store: Store) -> None:
    write(store, TODAY - timedelta(days=1), "just a diary, no heading\n")
    write(store, TODAY, "## To-Do\n- [ ] keep\n")
    rollover(store, TODAY, 30)
    assert "just a diary" in read(store, TODAY - timedelta(days=1))  # nothing invented


# --------------------------------------------------------- hypothesis ------

_STATUS = st.sampled_from([" ", "x", "/", ">", "-", "?", "X"])
_BODY = st.text(alphabet="abcXYZ ", min_size=1, max_size=8).map(str.strip).filter(bool)


@st.composite
def window(draw: st.DrawFn) -> tuple[dict[int, list[tuple[str, str]]], int]:
    days: dict[int, list[tuple[str, str]]] = {}
    for off in range(1, 8):
        if draw(st.booleans(), label=f"day-{off}"):
            tasks = []
            for _ in range(draw(st.integers(0, 3))):
                prio = draw(st.sampled_from(["", " ⏫", " 📅 2026-09-20"]))
                tasks.append((draw(_STATUS), draw(_BODY) + prio))
            days[off] = tasks
    return days, draw(st.integers(1, 10))


_OPEN_LINE = re.compile(r"^- \[( |/)\] (.*)$")


@settings(max_examples=320, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(window())
def test_rollover_properties(case: tuple[dict[int, list[tuple[str, str]]], int]) -> None:
    days, lookback = case
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        def path_for(d: date) -> Path:
            return tmp / f"{d.isoformat()}.md"

        store = Store(path_for, sleep=lambda _x: None)
        original: dict[Path, str] = {}
        for off, tasks in days.items():
            d = TODAY - timedelta(days=off)
            text = "## To-Do\n" + "".join(f"- [{s}] {b}\n" for s, b in tasks)
            path = path_for(d)
            path.write_text(text, encoding="utf-8")
            original[path] = text
        today_path = path_for(TODAY)
        if today_path.exists():
            original[today_path] = today_path.read_text("utf-8")

        rollover(store, TODAY, lookback)

        after = {p: p.read_text("utf-8") for p in tmp.glob("*.md")}
        today_text = after.get(today_path, "")

        # --- idempotent: re-run changes nothing ------------------------------
        snap = dict(after)
        res2 = rollover(store, TODAY, lookback)
        assert res2.moved == 0
        assert {p: p.read_text("utf-8") for p in tmp.glob("*.md")} == snap

        # --- no loss: window-open norms appear in today as open/done ---------
        today_norms: set[str] = set()
        for line in today_text.splitlines():
            m = re.match(r"^- \[( |x|X|/)\] (.*)$", line)
            if m:
                today_norms.add(normalize(m.group(2)))
        for path, text in original.items():
            if path == today_path:
                continue
            d = date.fromisoformat(path.stem)
            if d < TODAY - timedelta(days=lookback):
                continue
            for line in text.splitlines():
                m = _OPEN_LINE.match(line)
                if m:
                    assert normalize(m.group(2)) in today_norms, (path, line)

        # --- untouched content: source lines differ only status → '>' --------
        for path, text in original.items():
            if path == today_path:
                continue
            new_lines = after[path].splitlines()
            for old_line in text.splitlines():
                marked = old_line[:3] + ">" + old_line[4:]
                assert old_line in new_lines or (
                    old_line.startswith(("- [ ] ", "- [/] ")) and marked in new_lines
                ), (path, old_line)
