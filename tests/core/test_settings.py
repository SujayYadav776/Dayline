"""Settings persistence, migration, validation, legacy import (PRD §3.7, FR-O9)."""

from __future__ import annotations

import json
from pathlib import Path

from dayline.core.settings import (
    SCHEMA_VERSION,
    Settings,
    import_legacy_todo_config,
    load,
    save,
    validate,
)


def test_missing_file_gives_defaults(tmp_path: Path) -> None:
    s, issues = load(tmp_path / "config.json")
    assert issues == []
    assert s.lookback == 30 and s.theme == "light" and s.heading == "## To-Do"
    # tray-first defaults: boot to tray, close hides to tray
    assert s.start_hidden is True and s.close_to_tray is True


def test_save_load_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "Dayline" / "config.json"
    s = Settings(vault_path="C:/vault", window={"x": 10, "y": 20, "w": 440, "h": 720})
    save(p, s)
    loaded, issues = load(p)
    assert issues == []
    assert loaded == s
    assert loaded.schema_version == SCHEMA_VERSION


def test_corrupt_config_falls_back_with_issue(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    p.write_text("{nope", encoding="utf-8")
    s, issues = load(p)
    assert s == Settings() and issues


def test_unknown_keys_ignored_wrong_types_kept_default(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"lookback": "many", "theme": 5, "future_key": True}), encoding="utf-8")
    s, _ = load(p)
    assert s.lookback == 30 and s.theme == "light"


def test_validate_clamps_and_reports() -> None:
    s = Settings(
        lookback=500,
        day_start="09:00",
        theme="neon",
        sort_mode="zen",
        week_start="tue",
        accent_custom="red",
        backup_keep_days=-4,
    )
    issues = validate(s)
    assert s.lookback == 90
    assert s.day_start == "00:00"
    assert s.theme == "system" and s.sort_mode == "priority" and s.week_start == "mon"
    assert s.accent_custom == "" and s.backup_keep_days == 7
    assert len(issues) == 7


def test_migration_bumps_old_version(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"schema_version": 0, "vault_path": "C:/v"}), encoding="utf-8")
    s, issues = load(p)
    assert s.vault_path == "C:/v"
    assert s.schema_version == SCHEMA_VERSION
    assert issues == []


def test_import_legacy(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    p = tmp_path / "todo_config.json"
    p.write_text(json.dumps({"vault": str(vault), "folder": "Daily"}), encoding="utf-8")
    out = import_legacy_todo_config(p)
    assert out == {"vault_path": str(vault), "folder": "Daily"}


def test_import_legacy_guards(tmp_path: Path) -> None:
    assert import_legacy_todo_config(tmp_path / "none.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("[1,2]", encoding="utf-8")
    assert import_legacy_todo_config(bad) == {}
    ghost = tmp_path / "ghost.json"
    ghost.write_text(json.dumps({"vault": str(tmp_path / "gone"), "folder": "  "}), "utf-8")
    assert import_legacy_todo_config(ghost) == {}


def test_time_fields_validated() -> None:
    s = Settings(morning_summary_at="25:99")
    issues = validate(s)
    assert s.morning_summary_at == "" and issues


def test_auto_hide_defaults_off() -> None:
    s = Settings()
    assert s.auto_hide is False


def test_due_reminders_default_on() -> None:
    s = Settings()
    assert s.notifications_enabled is True
    assert s.morning_summary_at == "09:00"


def test_migrate_v1_enables_reminders_for_legacy_configs() -> None:
    from dayline.core.settings import migrate

    legacy = {"schema_version": 1, "notifications_enabled": False, "morning_summary_at": ""}
    out = migrate(legacy)
    assert out["notifications_enabled"] is True
    assert out["morning_summary_at"] == "09:00"
    assert out["schema_version"] == 2


def test_migrate_v1_respects_deliberate_evening_only_setup() -> None:
    from dayline.core.settings import migrate

    raw = {"schema_version": 1, "notifications_enabled": True, "morning_summary_at": ""}
    out = migrate(raw)
    assert out["notifications_enabled"] is True
    assert out["morning_summary_at"] == ""  # untouched: user had chosen times


def test_thin_paper_defaults_off() -> None:
    assert Settings().thin_paper is False


def test_thin_paper_roundtrips_through_coerce(tmp_path: Path) -> None:
    s = Settings(thin_paper=True)
    save(tmp_path / "config.json", s)
    loaded, _ = load(tmp_path / "config.json")
    assert loaded.thin_paper is True


def test_vault_mode_defaults_to_obsidian() -> None:
    assert Settings().vault_mode == "obsidian"


def test_vault_mode_roundtrips_through_coerce(tmp_path: Path) -> None:
    s = Settings(vault_mode="folder")
    save(tmp_path / "config.json", s)
    loaded, _ = load(tmp_path / "config.json")
    assert loaded.vault_mode == "folder"


def test_vault_mode_missing_in_old_config_defaults_obsidian(tmp_path: Path) -> None:
    # configs saved before folder mode existed must load as obsidian
    import json

    p = tmp_path / "config.json"
    data = {"schema_version": 2, "vault_path": "C:/vault"}
    p.write_text(json.dumps(data), encoding="utf-8")
    loaded, _ = load(p)
    assert loaded.vault_mode == "obsidian"


def test_vault_mode_invalid_clamped_by_validate() -> None:
    s = Settings(vault_mode="notion")
    issues = validate(s)
    assert s.vault_mode == "obsidian"
    assert any("vault_mode" in i for i in issues)


def test_summon_hotkey_defaults_and_roundtrip(tmp_path: Path) -> None:
    assert Settings().summon_hotkey == "ctrl+shift+d"
    s = Settings(summon_hotkey="ctrl+alt+space")
    save(tmp_path / "config.json", s)
    loaded, _ = load(tmp_path / "config.json")
    assert loaded.summon_hotkey == "ctrl+alt+space"


def test_summon_hotkey_missing_in_old_config_gets_default(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"schema_version": 2, "hotkey": "ctrl+alt+n"}), encoding="utf-8")
    loaded, _ = load(p)
    assert loaded.summon_hotkey == "ctrl+shift+d"


def test_all_toggle_setters_roundtrip_and_notify() -> None:
    """Every Settings toggle: setter flips the value, the VM property reads it
    back, and the applied(group) signal fires so app-side effects run."""
    from dayline.ui.viewmodels.settings_vm import SettingsViewModel

    s = Settings()
    vm = SettingsViewModel(s)
    seen: list[str] = []
    vm.applied.connect(lambda g: seen.append(g))
    cases = [
        (vm.setMica, "mica", False, "appearance"),
        (vm.setThinPaper, "thin_paper", True, "appearance"),
        (vm.setRolloverEnabled, "rollover_enabled", False, "rollover"),
        (vm.setStartHidden, "start_hidden", False, "general"),
        (vm.setCloseToTray, "close_to_tray", False, "general"),
        (vm.setAutoHide, "auto_hide", True, "general"),
        (vm.setDueReminders, "notifications_enabled", False, "notifications"),
        (vm.setCompletionSound, "completion_sound", False, "general"),
        (vm.setAutostart, "autostart", True, "general"),
        (vm.setUpdateCheckEnabled, "update_check_enabled", True, "updates"),
        (vm.setQuickAddEnabled, "quick_add_enabled", False, "general"),
    ]
    for setter, field, want, group in cases:
        before = getattr(s, field)
        setter(want)
        assert getattr(s, field) == want, field
        assert group in seen, field
        setter(before)  # restore
