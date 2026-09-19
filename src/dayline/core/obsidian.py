"""Obsidian vault + daily-notes plugin discovery (PRD FR-O1/O2/O6).

Tolerant by design: any missing or malformed config degrades to defaults,
never raises (the wizard surfaces a friendly state instead).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote

from dayline.core.errors import UnsupportedFormatError
from dayline.core.moment_format import format_date, unsupported_tokens

log = logging.getLogger("dayline.core.obsidian")

DEFAULT_FOLDER = "Daily"
DEFAULT_FORMAT = "YYYY-MM-DD"


@dataclass(frozen=True)
class VaultInfo:
    name: str
    path: Path
    is_open: bool = False
    ts: int = 0


@dataclass(frozen=True)
class DailyNotesSettings:
    folder: str = DEFAULT_FOLDER
    date_format: str = DEFAULT_FORMAT
    template: str | None = None

    @property
    def unsupported(self) -> list[str]:
        return unsupported_tokens(self.date_format)


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def find_vaults(obsidian_json: Path) -> list[VaultInfo]:
    """Parse %APPDATA%/obsidian/obsidian.json into candidate vaults, best first."""
    data = _load_json(obsidian_json)
    if not data:
        return []
    vaults = data.get("vaults")
    if not isinstance(vaults, dict):
        return []
    out: list[VaultInfo] = []
    for entry in vaults.values():
        if not isinstance(entry, dict):
            continue
        raw = entry.get("path")
        if not isinstance(raw, str) or not raw.strip():
            continue
        p = Path(raw)
        out.append(
            VaultInfo(
                name=p.name,
                path=p,
                is_open=bool(entry.get("open", False)),
                ts=int(entry.get("ts", 0) or 0),
            )
        )
    out.sort(key=lambda v: (not v.is_open, -v.ts, v.name.lower()))
    return out


def read_daily_notes(vault_dir: Path) -> DailyNotesSettings:
    """Read <vault>/.obsidian/daily-notes.json with fallbacks (FR-O2)."""
    data = _load_json(vault_dir / ".obsidian" / "daily-notes.json") or {}
    folder = data.get("folder")
    fmt = data.get("format")
    template = data.get("template")
    return DailyNotesSettings(
        folder=folder if isinstance(folder, str) and folder.strip() else DEFAULT_FOLDER,
        date_format=fmt if isinstance(fmt, str) and fmt.strip() else DEFAULT_FORMAT,
        template=template if isinstance(template, str) and template.strip() else None,
    )


def note_path(vault: Path, settings: DailyNotesSettings, d: date) -> Path:
    """vault / folder / formatted(date).md — format may include '/' subfolders."""
    fmt = settings.date_format
    if unsupported_tokens(fmt):
        raise UnsupportedFormatError(f"unsupported date format: {fmt}")
    stem = format_date(d, fmt)
    parts = [settings.folder] + [seg for seg in stem.split("/") if seg]
    p = vault
    for part in parts:
        p = p / part
    return p.with_suffix(".md")


def note_rel_no_ext(settings: DailyNotesSettings, d: date) -> str:
    stem = format_date(d, settings.date_format)
    return "/".join(x for x in [settings.folder, *stem.split("/")] if x)


def open_uri(vault_name: str, rel_no_ext: str) -> str:
    """obsidian://open URI, strictly percent-encoded (FR-O6)."""
    return f"obsidian://open?vault={quote(vault_name, safe='')}&file={quote(rel_no_ext, safe='')}"


def is_conflict_copy(name: str) -> bool:
    """Sync-client conflict copies must be ignored (FR-O10). Covers
    '… (conflicted copy) …', '…'s conflicted copy', 'conflict-…' variants."""
    return "conflict" in name.lower()
