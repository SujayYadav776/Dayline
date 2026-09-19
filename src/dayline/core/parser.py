"""Byte-faithful note parsing (PRD §5.6). Splits on \\r\\n | \\r | \\n only."""

from __future__ import annotations

import re

from dayline.core.errors import NoteDecodeError
from dayline.core.model import NoteDoc, RawLine

UTF8_BOM = b"\xef\xbb\xbf"
_LINE_RE = re.compile(r"([^\r\n]*)(\r\n|\r|\n)?")


def heading_level(heading: str) -> int:
    """'#' count of the configured managed heading (default 2)."""
    return max(1, len(heading) - len(heading.lstrip("#")))


def split_keep_endings(text: str) -> list[RawLine]:
    lines: list[RawLine] = []
    pos = 0
    n = len(text)
    while pos < n:
        m = _LINE_RE.match(text, pos)
        assert m is not None
        body, ending = m.group(1), m.group(2) or ""
        lines.append(RawLine(body, ending))
        pos += len(body) + len(ending)
        if not body and not ending:  # defensive: avoid zero-width loop
            break
    return lines


def parse_text(text: str, heading: str = "## To-Do") -> NoteDoc:
    lines = split_keep_endings(text)
    eol = next((ln.ending for ln in lines if ln.ending), "\n")
    doc = NoteDoc(lines=lines, eol=eol, heading=heading, heading_level=heading_level(heading))
    doc.rescan()
    return doc


def parse_bytes(raw: bytes, heading: str = "## To-Do") -> NoteDoc:
    bom = raw.startswith(UTF8_BOM)
    try:
        text = raw.decode("utf-8-sig" if bom else "utf-8")
    except UnicodeDecodeError as exc:
        raise NoteDecodeError(f"note is not valid UTF-8: {exc}") from exc
    doc = parse_text(text, heading)
    doc.bom = bom
    return doc


def empty_doc(heading: str = "## To-Do") -> NoteDoc:
    doc = NoteDoc(lines=[], eol="\n", heading=heading, heading_level=heading_level(heading))
    return doc
