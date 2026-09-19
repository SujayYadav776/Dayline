"""Surgical serializer: rebuilds only dirty task lines (PRD §5.6)."""

from __future__ import annotations

from dayline.core.model import NoteDoc


def serialize(doc: NoteDoc) -> bytes:
    doc.flush_dirty()
    text = "".join(line.raw() for line in doc.lines)
    data = text.encode("utf-8")
    if doc.bom:
        data = b"\xef\xbb\xbf" + data
    return data
