"""Settings schema + versioned persistence (PRD §3.7).

`%APPDATA%/Dayline/config.json`, atomic writes, migrated on load.
Validation clamps to safe values and returns human-readable issues.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from dayline.core.clock import parse_day_start_minutes
from dayline.core.obsidian import DEFAULT_FOLDER, DEFAULT_FORMAT

log = logging.getLogger("dayline.core.settings")

SCHEMA_VERSION = 1


@dataclass
class Settings:
    # General
    autostart: bool = False
    close_to_tray: bool = True
    hotkey: str = "ctrl+alt+n"
    quick_add_enabled: bool = True
    # Obsidian
    vault_path: str = ""
    folder: str = DEFAULT_FOLDER
    date_format: str = DEFAULT_FORMAT
    heading: str = "## To-Do"
    # Rollover
    rollover_enabled: bool = True
    lookback: int = 30
    day_start: str = "00:00"  # "HH:MM", 00:00–06:00
    # Notifications (off by default, FR-P7)
    notifications_enabled: bool = False
    morning_summary_at: str = ""  # "HH:MM" or "" = unset
    evening_reminder_at: str = ""
    # Appearance
    theme: str = "system"  # system|light|dark
    accent_custom: str = ""  # "" = follow Windows accent, else "#RRGGBB"
    sort_mode: str = "priority"  # priority|manual
    week_start: str = "mon"  # mon|sun
    reduce_motion: bool = False
    # Data hygiene
    backup_keep_days: int = 7
    # Window memory (FR §4.3)
    window: dict[str, int] = field(default_factory=dict)  # x,y,w,h
    last_page: str = "today"

    schema_version: int = SCHEMA_VERSION


def _coerce(raw: dict[str, Any]) -> Settings:
    """Copy known-typed keys from the stored dict; ignore everything else."""
    s = Settings()
    defaults = asdict(s)
    for name, value in raw.items():
        if name not in defaults:
            continue
        default = defaults[name]
        if isinstance(default, bool):
            ok, stored = isinstance(value, bool), value
        elif isinstance(default, int):
            ok, stored = isinstance(value, int) and not isinstance(value, bool), value
        elif isinstance(default, str):
            ok, stored = isinstance(value, str), value
        else:  # dict[str, int]
            ok, stored = (
                isinstance(value, dict),
                {k: v for k, v in value.items() if isinstance(v, int)}
                if isinstance(value, dict)
                else {},
            )
        if ok:
            setattr(s, name, stored)
    return s


def validate(s: Settings) -> list[str]:
    """Clamp into safe ranges; return list of warnings for anything fixed."""
    issues: list[str] = []

    def fix(name: str, old: Any, new: Any, why: str) -> None:
        setattr(s, name, new)
        issues.append(f"{name}: {old!r} → {new!r} ({why})")

    if not 1 <= s.lookback <= 90:
        fix("lookback", s.lookback, min(90, max(1, s.lookback)), "range 1–90")
    try:
        mins = parse_day_start_minutes(s.day_start)
        if mins > 6 * 60:
            raise ValueError
    except ValueError:
        fix("day_start", s.day_start, "00:00", "must be 00:00–06:00")
    if s.theme not in ("system", "light", "dark"):
        fix("theme", s.theme, "system", "system|light|dark")
    if s.sort_mode not in ("priority", "manual"):
        fix("sort_mode", s.sort_mode, "priority", "priority|manual")
    if s.week_start not in ("mon", "sun"):
        fix("week_start", s.week_start, "mon", "mon|sun")
    if s.accent_custom and not re.fullmatch(r"(?i)#[0-9a-f]{6}", s.accent_custom):
        fix("accent_custom", s.accent_custom, "", "expected #RRGGBB")
    if not s.heading.strip():
        fix("heading", s.heading, "## To-Do", "empty heading")
    if not s.folder.strip():
        fix("folder", s.folder, DEFAULT_FOLDER, "empty folder")
    if not 0 <= s.backup_keep_days <= 90:
        fix("backup_keep_days", s.backup_keep_days, 7, "range 0–90")
    for fname in ("morning_summary_at", "evening_reminder_at"):
        val = getattr(s, fname)
        if val and not re.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d", val):
            fix(fname, val, "", "expected HH:MM")
    return issues


def migrate(raw: dict[str, Any]) -> dict[str, Any]:
    """Chain per-version upgrades; unknown future versions are used as-is."""
    version = int(raw.get("schema_version", 0) or 0)
    while version < SCHEMA_VERSION:
        upgrader = _MIGRATIONS.get(version)
        if upgrader is None:  # pragma: no cover - no migrations in v1
            break
        raw = upgrader(raw)
        version = int(raw.get("schema_version", version + 1))
    return raw


def _migrate_v0(raw: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover
    raw["schema_version"] = 1
    return raw


_MIGRATIONS: dict[int, Any] = {0: _migrate_v0}


def load(path: Path) -> tuple[Settings, list[str]]:
    """Read settings; missing/corrupt file → defaults (+ issue noted)."""
    if not path.is_file():
        return Settings(), []
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict):
            raise ValueError("config is not an object")
    except (OSError, ValueError) as exc:
        log.warning("config unreadable (%s); using defaults", exc)
        return Settings(), [f"config file was unreadable: {exc}"]
    s = _coerce(migrate(raw))
    issues = validate(s)
    return s, issues


def save(path: Path, s: Settings) -> None:
    s.schema_version = SCHEMA_VERSION
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".config.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(asdict(s), fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except OSError:
        Path(tmp).unlink(missing_ok=True)
        raise


def import_legacy_todo_config(path: Path) -> dict[str, Any]:
    """Map the prototype script's todo_config.json (Appendix A) → overrides.

    Returns {} when absent/invalid; the Settings→Import flow (FR-O9) applies it.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    vault = raw.get("vault")
    if isinstance(vault, str) and Path(vault).is_dir():
        out["vault_path"] = vault
    folder = raw.get("folder")
    if isinstance(folder, str) and folder.strip():
        out["folder"] = folder.strip()
    return out
