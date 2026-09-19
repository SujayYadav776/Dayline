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
    assert s.lookback == 30 and s.theme == "system" and s.heading == "## To-Do"


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
    assert s.lookback == 30 and s.theme == "system"


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
