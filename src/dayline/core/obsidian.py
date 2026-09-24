"""Obsidian vault + daily-notes plugin discovery (PRD FR-O1/O2/O6).

Tolerant by design: any missing or malformed config degrades to defaults,
never raises (the wizard surfaces a friendly state instead).
"""

from __future__ import annotations

import json
import logging
import re
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


def open_uri(vault_name: str, rel_no_ext: str, block: str | None = None) -> str:
    """obsidian://open URI, strictly percent-encoded (FR-O6). With `block`,
    the file value carries an encoded #^anchor so Obsidian scrolls to it."""
    file_part = quote(rel_no_ext, safe="")
    if block:
        file_part += "%23%5E" + quote(block, safe="")
    return f"obsidian://open?vault={quote(vault_name, safe='')}&file={file_part}"


def search_uri(vault_name: str, query: str) -> str:
    """obsidian://search URI (core search action)."""
    return f"obsidian://search?vault={quote(vault_name, safe='')}&query={quote(query, safe='')}"


# Obsidian block references: ^id (alphanumeric, hyphens allowed), trailing on a line
_BLOCK_REF_RE = re.compile(r"[ \t]\^([A-Za-z0-9][A-Za-z0-9-]{0,63})[ \t]*$")


def block_ref_of(line: str) -> str | None:
    """The ^anchor at the end of a rendered line, if the user wrote one."""
    m = _BLOCK_REF_RE.search(line.rstrip("\r\n"))
    return m.group(1) if m else None


_JUMP_PHRASE_CHARS = 80


def jump_uri(vault_name: str, rel_no_ext: str, rendered_line: str, description: str) -> str:
    """Deep link to one task line (click-a-task → jump in Obsidian).

    Strategy: a literal line number isn't addressable in Obsidian, so prefer a
    block anchor the user already wrote (`^id` → open note#^id); otherwise run
    a search for the task's text restricted to that day's note, which lands on
    the exact line and highlights it. Empty/whitespace-only descriptions fall
    back to opening the note itself."""
    block = block_ref_of(rendered_line)
    if block:
        return open_uri(vault_name, rel_no_ext, block=block)
    phrase = re.sub(r"\s+", " ", description.replace('"', " ")).strip()[:_JUMP_PHRASE_CHARS]
    if phrase:
        stem = rel_no_ext.rsplit("/", 1)[-1]
        return search_uri(vault_name, f'file:"{stem}" "{phrase}"')
    return open_uri(vault_name, rel_no_ext)


def is_conflict_copy(name: str) -> bool:
    """Sync-client conflict copies must be ignored (FR-O10). Covers
    '… (conflicted copy) …', '…'s conflicted copy', 'conflict-…' variants."""
    return "conflict" in name.lower()
