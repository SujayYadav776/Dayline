"""Paper-design viewmodel surface: unified Today list, the bottom week-strip,
and the Progress-panel stats (streak / done-today / activity heat-map)."""

from __future__ import annotations

import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from dayline.core.settings import Settings
from dayline.core.store import Store
from dayline.ui.viewmodels.app_vm import AppViewModel
from dayline.ui.viewmodels.today_vm import TodayViewModel
from dayline.ui.viewmodels.week_vm import WeekViewModel, _heat_level

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "vaults"
TODAY = date.today()


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    v = tmp_path / "vault"
    shutil.copytree(FIXTURES / "default", v)
    (v / "Daily" / (TODAY.isoformat() + ".md")).write_text(
        (v / "Daily" / "2026-09-19.md").read_text("utf-8"), "utf-8"
    )
    return v


@pytest.fixture()
def store(vault: Path) -> Store:
    def path_for(d: date) -> Path:
        return vault / "Daily" / f"{d.isoformat()}.md"

    return Store(path_for, sleep=lambda _s: None)


@pytest.fixture()
def appvm(vault: Path, qtbot: Any) -> Any:
    v = AppViewModel(Settings(vault_path=str(vault)), theme_probe=lambda: "light")
    anyv: Any = v
    anyv.start()
    qtbot.waitUntil(lambda: not anyv.today._loading, timeout=2000)
    return anyv


# ---- Today: one flat list, completed inline at the bottom -------------------
def test_taskslist_combines_sections(store: Store) -> None:
    vm: Any = TodayViewModel()
    vm.set_date(TODAY)
    vm.apply_doc(store.read_doc(TODAY), today=TODAY)
    combined = vm.tasksList
    assert len(combined) == len(vm.todoList) + len(vm.carriedList) + len(vm.doneList)
    # every completed/cancelled row sits after every open row
    kinds = [r["statusKind"] for r in combined]
    done_idx = [i for i, k in enumerate(kinds) if k in ("done", "cancelled")]
    open_idx = [i for i, k in enumerate(kinds) if k == "open"]
    assert done_idx and open_idx
    assert min(done_idx) > max(open_idx)


def test_completed_rows_carry_done_statuskind(store: Store) -> None:
    vm: Any = TodayViewModel()
    vm.set_date(TODAY)
    vm.apply_doc(store.read_doc(TODAY), today=TODAY)
    assert any(r["statusKind"] == "done" for r in vm.tasksList)


def test_lowercase_date_block_parts(store: Store) -> None:
    vm: Any = TodayViewModel()
    vm.set_date(date(2026, 9, 19))  # a saturday
    vm.apply_doc(store.read_doc(date(2026, 9, 19)), today=date(2026, 9, 19))
    assert vm.dayName == "saturday"
    assert vm.monthName == "september"
    assert vm.dayNum == "19"


# ---- Week: bottom strip + progress stats ------------------------------------
def test_strip_has_seven_cells_with_today_and_selected(store: Store) -> None:
    vm: Any = WeekViewModel()
    vm.bind(store, week_start="mon", now_provider=lambda: datetime.now())
    vm.set_anchor(TODAY)
    strip = vm.strip
    assert len(strip) == 7
    assert sum(c["isToday"] for c in strip) == 1
    assert sum(c["isSelected"] for c in strip) == 1
    for c in strip:
        assert c["letter"] in "MTWTFSS"
        assert 0 <= c["percent"] <= 100


def test_streak_and_done_today_are_ints(store: Store) -> None:
    vm: Any = WeekViewModel()
    vm.bind(store, week_start="mon", now_provider=lambda: datetime.now())
    vm.set_anchor(TODAY)
    assert isinstance(vm.streak, int) and vm.streak >= 0
    assert isinstance(vm.doneToday, int) and vm.doneToday >= 0


def test_activity_is_13_weeks_of_leveled_cells(store: Store) -> None:
    vm: Any = WeekViewModel()
    vm.bind(store, week_start="mon", now_provider=lambda: datetime.now())
    cells = vm.activity
    assert len(cells) == 13 * 7
    assert all(0 <= c["level"] <= 4 for c in cells)
    assert all(isinstance(c["future"], bool) for c in cells)
    assert date.fromisoformat(cells[-1]["dateStr"]) >= TODAY


@pytest.mark.parametrize(
    ("done", "level"),
    [(0, 0), (1, 1), (2, 2), (3, 3), (4, 3), (5, 4), (99, 4)],
)
def test_heat_level_mapping(done: int, level: int) -> None:
    assert _heat_level(done) == level


# ---- App: tapping a strip day opens it on Today -----------------------------
def test_select_day_navigates_and_shows_today(appvm: Any) -> None:
    target = TODAY + timedelta(days=2)
    appvm.selectDay(target.isoformat())
    assert appvm.today.current_date == target
    assert appvm.page == "today"
    # strip follows the selected day
    assert any(c["isSelected"] and c["dateStr"] == target.isoformat() for c in appvm.week.strip)


def test_select_day_ignores_garbage(appvm: Any) -> None:
    before = appvm.today.current_date
    appvm.selectDay("not-a-date")
    assert appvm.today.current_date == before


# ---- quick-add features: NLP dates, reschedule, completion sound ------------
def test_add_task_parses_natural_date(appvm: Any, vault: Path) -> None:
    from datetime import timedelta

    appvm.addTask("pay rent tomorrow")
    qt_wait(appvm)
    note = (vault / "Daily" / f"{TODAY.isoformat()}.md").read_text("utf-8")
    tomorrow = (TODAY + timedelta(days=1)).isoformat()
    assert f"pay rent 📅 {tomorrow}" in note


def test_add_task_keeps_bangs_last(appvm: Any, vault: Path) -> None:
    # the date lands before the bangs so the editor still maps "!!" → 🔼
    appvm.addTask("ship thing tomorrow !!")
    qt_wait(appvm)
    note = (vault / "Daily" / f"{TODAY.isoformat()}.md").read_text("utf-8")
    assert "ship thing 📅" in note and "🔼" in note


def test_reschedule_moves_task_and_navigates(appvm: Any, vault: Path) -> None:
    target = TODAY + timedelta(days=2)
    key = appvm.today.todoList[0]["taskKey"]
    desc = appvm.today.todoList[0]["description"]
    appvm.rescheduleTask(key, target.isoformat())
    qt_wait(appvm)
    src = (vault / "Daily" / f"{TODAY.isoformat()}.md").read_text("utf-8")
    dst_path = vault / "Daily" / f"{target.isoformat()}.md"
    assert desc not in src
    assert dst_path.is_file() and desc in dst_path.read_text("utf-8")
    assert appvm.today.current_date == target


def test_completion_sound_plays_on_open_to_done(vault: Path, qtbot: Any) -> None:
    from dayline.core.settings import Settings
    from dayline.ui.viewmodels.app_vm import AppViewModel

    plays: list[int] = []
    v: Any = AppViewModel(
        Settings(vault_path=str(vault)),
        theme_probe=lambda: "light",
        sound_play=lambda: plays.append(1),
    )
    v.start()
    qtbot.waitUntil(lambda: not v.today._loading, timeout=2000)
    key = v.today.todoList[0]["taskKey"]
    v.toggleTask(key)  # open → done: plays
    qtbot.wait(50)
    assert plays == [1]
    v.toggleTask(key)  # done → open: silent
    qtbot.wait(50)
    assert plays == [1]


def test_completion_sound_setting_off(vault: Path, qtbot: Any) -> None:
    from dayline.core.settings import Settings
    from dayline.ui.viewmodels.app_vm import AppViewModel

    plays: list[int] = []
    s = Settings(vault_path=str(vault))
    s.completion_sound = False
    v: Any = AppViewModel(s, theme_probe=lambda: "light", sound_play=lambda: plays.append(1))
    v.start()
    qtbot.waitUntil(lambda: not v.today._loading, timeout=2000)
    v.toggleTask(v.today.todoList[0]["taskKey"])
    qtbot.wait(50)
    assert plays == []


def qt_wait(vm: Any, ms: int = 80) -> None:
    """Let the queued singleShot day-reload run."""
    from PySide6.QtTest import QTest

    QTest.qWait(ms)


# ---- click-a-task → jump to its line in Obsidian -----------------------------
def make_uri_vm(vault: Path, qtbot: Any) -> tuple[Any, list[str]]:
    from dayline.core.settings import Settings
    from dayline.ui.viewmodels.app_vm import AppViewModel

    uris: list[str] = []
    v: Any = AppViewModel(
        Settings(vault_path=str(vault)),
        theme_probe=lambda: "light",
        uri_open=uris.append,
    )
    v.start()
    qtbot.waitUntil(lambda: not v.today._loading, timeout=2000)
    return v, uris


def test_task_click_builds_in_note_search_uri(vault: Path, qtbot: Any) -> None:
    from urllib.parse import unquote

    v, uris = make_uri_vm(vault, qtbot)
    row = v.today.todoList[0]
    v.openTaskInObsidian(row["taskKey"])
    assert len(uris) == 1
    assert uris[0].startswith(f"obsidian://search?vault={vault.name}&query=")
    q = unquote(uris[0].split("query=", 1)[1])
    assert q == f'file:"{TODAY.isoformat()}" "{row["description"]}"'


def test_task_click_prefers_block_anchor(vault: Path, qtbot: Any) -> None:
    v, uris = make_uri_vm(vault, qtbot)
    row = v.today.todoList[0]
    note = vault / "Daily" / f"{TODAY.isoformat()}.md"
    text = note.read_text("utf-8")
    # the anchor must sit at end of line (after any emoji tokens), like Obsidian wants it
    anchorable = row["chips"][-1] if row["chips"] else row["description"]
    assert anchorable in text
    note.write_text(text.replace(anchorable, anchorable + " ^tk1", 1), "utf-8")
    v.openTaskInObsidian(row["taskKey"])
    assert uris == [f"obsidian://open?vault={vault.name}&file=Daily%2F{TODAY.isoformat()}%23%5Etk1"]


def test_task_click_unknown_key_opens_note(vault: Path, qtbot: Any) -> None:
    v, uris = make_uri_vm(vault, qtbot)
    v.openTaskInObsidian(99_999)
    assert uris == [f"obsidian://open?vault={vault.name}&file=Daily%2F{TODAY.isoformat()}"]


# ---- recurring quick-add + due summary ---------------------------------------
def test_add_task_recurrence_inserts_token_and_first_due(appvm: Any, vault: Path) -> None:
    from datetime import timedelta

    appvm.addTask("gym every monday")
    qt_wait(appvm)
    note = (vault / "Daily" / f"{TODAY.isoformat()}.md").read_text("utf-8")
    # 📅 resolves to the next Monday (today counts if it is one)
    ahead = (0 - TODAY.weekday()) % 7 or 7
    nxt = (TODAY + timedelta(days=ahead)).isoformat()
    assert "🔁 every monday" in note and f"📅 {nxt}" in note


def test_add_task_recurrence_with_explicit_date(appvm: Any, vault: Path) -> None:
    appvm.addTask("review tomorrow weekly !!")
    qt_wait(appvm)
    note = (vault / "Daily" / f"{TODAY.isoformat()}.md").read_text("utf-8")
    tomorrow = (TODAY + timedelta(days=1)).isoformat()
    assert f"review 📅 {tomorrow} 🔁 weekly 🔼" in note


def test_due_summary_counts_today_and_overdue(vault: Path, qtbot: Any) -> None:
    from datetime import timedelta

    from dayline.core.settings import Settings
    from dayline.ui.viewmodels.app_vm import AppViewModel

    note = vault / "Daily" / f"{TODAY.isoformat()}.md"
    yesterday = (TODAY - timedelta(days=1)).isoformat()
    tomorrow = (TODAY + timedelta(days=1)).isoformat()
    note.write_text(
        "## To-Do\n"
        "- [ ] no date\n"
        f"- [ ] due today \U0001f4c5 {TODAY.isoformat()}\n"
        f"- [ ] overdue \U0001f4c5 {yesterday}\n"
        f"- [ ] future \U0001f4c5 {tomorrow}\n"
        f"- [x] done \U0001f4c5 {yesterday}\n",
        "utf-8",
    )
    s = Settings(vault_path=str(vault))
    s.rollover_enabled = False  # keep the fixture note exactly as written
    v: Any = AppViewModel(s, theme_probe=lambda: "light")
    v.start()
    qtbot.waitUntil(lambda: not v.today._loading, timeout=2000)
    assert v.due_summary() == (2, 1)  # no-date + due-today; one overdue


def test_thin_paper_property_reflects_setting(vault: Path, qtbot: Any) -> None:
    from dayline.core.settings import Settings
    from dayline.ui.viewmodels.app_vm import AppViewModel

    s = Settings(vault_path=str(vault))
    v: Any = AppViewModel(s, theme_probe=lambda: "light", mica_probe=lambda: True)
    assert v.thinPaper is False
    s.thin_paper = True
    v.changed.emit()
    assert v.thinPaper is True


# ---- folder mode (skip Obsidian, store notes in any folder) -------------------
def make_folder_vm(qtbot: Any, tmp_path: Any) -> tuple[Any, list[str], list[str]]:
    from dayline.core.settings import Settings
    from dayline.ui.viewmodels.app_vm import AppViewModel

    uris: list[str] = []
    files: list[str] = []
    notes = tmp_path / "My Notes"
    notes.mkdir()
    cfg = tmp_path / "config.json"
    v: Any = AppViewModel(
        Settings(),
        config_path=cfg,
        theme_probe=lambda: "light",
        uri_open=uris.append,
        file_open=files.append,
    )
    v.selectFolder(str(notes))
    qtbot.waitUntil(lambda: not v.today._loading, timeout=2000)
    return v, uris, files


def test_select_folder_builds_store_and_persists(qtbot: Any, tmp_path: Any) -> None:
    import json

    v, _, _ = make_folder_vm(qtbot, tmp_path)
    assert v.folderMode is True
    assert v.vaultReady is True
    saved = json.loads((tmp_path / "config.json").read_text("utf-8"))
    assert saved["vault_mode"] == "folder"
    assert saved["folder"] == "Daily"
    assert saved["date_format"] == "YYYY-MM-DD"


def test_folder_mode_add_task_writes_plain_markdown(qtbot: Any, tmp_path: Any) -> None:
    v, _, _ = make_folder_vm(qtbot, tmp_path)
    v.addTask("water plants")
    qtbot.waitUntil(lambda: not v.today._loading, timeout=2000)
    note = Path(v.settings.vault_path) / "Daily" / f"{TODAY.isoformat()}.md"
    assert note.is_file()  # Dayline created the note itself
    text = note.read_text("utf-8")
    assert "water plants" in text
    assert "## To-Do" in text


def test_folder_mode_task_jump_opens_file_not_obsidian(qtbot: Any, tmp_path: Any) -> None:
    v, uris, files = make_folder_vm(qtbot, tmp_path)
    v.addTask("ping")
    qtbot.waitUntil(lambda: not v.today._loading, timeout=2000)
    row = v.today.todoList[0]
    v.openTaskInObsidian(row["taskKey"])
    assert uris == []  # no obsidian:// URI in folder mode
    assert files == [str(Path(v.settings.vault_path) / "Daily" / f"{TODAY.isoformat()}.md")]


def test_select_vault_marks_obsidian_mode(qtbot: Any, vault: Any) -> None:
    from dayline.core.settings import Settings
    from dayline.ui.viewmodels.app_vm import AppViewModel

    v: Any = AppViewModel(Settings(), theme_probe=lambda: "light")
    v.selectVault(str(vault))
    qtbot.waitUntil(lambda: not v.today._loading, timeout=2000)
    assert v.folderMode is False
