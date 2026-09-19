"""App-data locations (PRD §5.10) — env-var driven, fakeable in tests."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Dayline"


def _env_dir(var: str, fallback: Path) -> Path:
    val = os.environ.get(var)
    return Path(val) if val else fallback


def appdata_dir() -> Path:
    return _env_dir("APPDATA", Path.home() / "AppData" / "Roaming")


def local_appdata_dir() -> Path:
    return _env_dir("LOCALAPPDATA", Path.home() / "AppData" / "Local")


def config_file() -> Path:
    return appdata_dir() / APP_NAME / "config.json"


def logs_dir() -> Path:
    return local_appdata_dir() / APP_NAME / "logs"


def backups_dir() -> Path:
    return local_appdata_dir() / APP_NAME / "backups"


def obsidian_json() -> Path:
    return appdata_dir() / "obsidian" / "obsidian.json"
