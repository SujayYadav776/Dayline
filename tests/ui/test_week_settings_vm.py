"""WeekViewModel + SettingsViewModel behaviour (FR-W1..W5, §3.7, FR-O9)."""

from __future__ import annotations

import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

from dayline.core.settings import Settings
from dayline.core.store import Store
from dayline.ui.viewmodels.settings_vm import SettingsViewModel
from dayline.ui.viewmodels.week_vm import WeekViewModel

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "vaults"
TODAY = date.today()


@pytest.fixture()
def store(tmp_path: Path) -> Store:
    vault = tmp_path / "vault"
    shutil.copytree(FIXTURES / "default", vault)
    (vault / "Daily" / (TODAY.isoformat() + ".md")).write_text(
        (vault / "Daily" / "2026-09-19.md").read_text("utf-8"), "utf-8"
    )

    def path_for(d: date) -> Path:
        return vault / "Daily" / f"{d.isoformat()}.md"

    return Store(path_for, sleep=lambda _s: None)


def test_week_has_seven_days_and_totals(store: Store) -> None:
    vm: Any = WeekViewModel()
    vm.bind(store, week_start="mon", now_provider=lambda: datetime.now())
    assert len(vm.days) == 7
    assert vm.days[0]["label"] == "Mon"
    assert vm.weekTotal >= 1
    # today's row is flagged
    assert any(d["isToday"] for d in vm.days)


def test_week_start_sunday_shifts_first_column(store: Store) -> None:
    vm: Any = WeekViewModel()
    vm.bind(store, week_start="sun", now_provider=lambda: datetime.now())
    assert vm.days[0]["label"] == "Sun"


def test_week_navigation_changes_range(store: Store) -> None:
    vm: Any = WeekViewModel()
    vm.bind(store, week_start="mon", now_provider=lambda: datetime.now())
    first = vm.days[0]["dateStr"]
    vm.prevWeek()
    assert vm.days[0]["dateStr"] != first
    vm.thisWeek()
    assert vm.days[0]["dateStr"] == first


def test_week_open_day_emits_date(store: Store, qtbot: Any) -> None:
    vm: Any = WeekViewModel()
    vm.bind(store, week_start="mon", now_provider=lambda: datetime.now())
    with qtbot.waitSignal(vm.dayRequested) as blocker:
        vm.openDay(TODAY.isoformat())
    assert blocker.args == [TODAY]


def test_settings_persists_and_validates(tmp_path: Path) -> None:
    cfg = tmp_path / "config.json"
    s = Settings()
    vm = SettingsViewModel(s, config_path=cfg)
    anyvm: Any = vm
    anyvm.setLookback(500)  # clamps to 90
    assert anyvm.lookback == 90
    assert cfg.is_file()
    anyvm.setTheme("neon")  # invalid → system
    assert anyvm.theme == "system"


def test_settings_import_legacy(tmp_path: Path) -> None:
    import json

    vault = tmp_path / "v"
    vault.mkdir()
    legacy = tmp_path / "todo_config.json"
    legacy.write_text(json.dumps({"vault": str(vault), "folder": "Daily"}), "utf-8")
    vm = SettingsViewModel(Settings(), config_path=tmp_path / "config.json")
    anyvm: Any = vm
    assert anyvm.importLegacy(str(legacy)) is True
    assert anyvm.vaultPath == str(vault)
    assert anyvm.importLegacy(str(tmp_path / "missing.json")) is False


def test_settings_today_preview(tmp_path: Path) -> None:
    vm = SettingsViewModel(Settings(vault_path=str(tmp_path), folder="Daily"))
    anyvm: Any = vm
    preview = anyvm.todayPreview()
    assert preview.endswith("Daily" + __import__("os").sep + TODAY.isoformat() + ".md")
