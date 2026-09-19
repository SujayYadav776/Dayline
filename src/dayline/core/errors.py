"""Typed exceptions for the core layer (PRD §6.5)."""

from __future__ import annotations


class DaylineError(Exception):
    """Base for all core errors; viewmodels translate to banners."""


class NoteDecodeError(DaylineError):
    """Note bytes are not UTF-8 (or UTF-8+BOM)."""


class LockedFileError(DaylineError):
    """Target file could not be replaced after retries (AV/sync/Obsidian)."""

    def __init__(self, path: str, attempts: int) -> None:
        super().__init__(f"file stayed locked after {attempts} attempts: {path}")
        self.path = path
        self.attempts = attempts


class VaultNotFoundError(DaylineError):
    """Configured vault is missing; UI shows guided recovery (PRD §4.5)."""


class UnsupportedFormatError(DaylineError):
    """Date format contains tokens outside the supported Moment subset."""
