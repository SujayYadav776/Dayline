"""Natural-language quick-add parsing (pure, no I/O).

Extracts a single due-date phrase from free text typed into the quick-add
field and returns the cleaned text plus the resolved date. Priority bangs
(``!``/``!!``/``!!!``) and ``#tags`` are left untouched for the existing
editor/serializer to handle.

Weekday rules (documented, simple, predictable):
- bare weekday ("friday", "fri") → the next occurrence, today counts;
- "next friday" → the same weekday one week after the bare occurrence.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

# weekday names + abbreviations → ISO weekday (Mon=0)
_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "mon": 0,
    "tue": 1,
    "tues": 1,
    "wed": 2,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

_ISO = r"\d{4}-\d{2}-\d{2}"
_WD_NAMES = "|".join(sorted(_WEEKDAYS, key=len, reverse=True))

# (pattern, kind) — first match wins; `kind` drives resolution below.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"\bnext ({_WD_NAMES})\b", re.IGNORECASE), "next-weekday"),
    (re.compile(rf"\b({_WD_NAMES})\b", re.IGNORECASE), "weekday"),
    (re.compile(r"\btoday\b|\btonight\b", re.IGNORECASE), "today"),
    (re.compile(r"\btomorrow\b", re.IGNORECASE), "tomorrow"),
    (re.compile(r"\bnext week\b", re.IGNORECASE), "next-week"),
    (re.compile(r"\bin (\d{1,3}) days?\b", re.IGNORECASE), "in-days"),
    (re.compile(rf"\b({_ISO})\b"), "iso"),
]


def _weekday_on_or_after(today: date, target: int) -> int:
    """Days ahead until the next occurrence of `target` (0 = today)."""
    return (target - today.weekday()) % 7


# Recurrence phrases typed into quick-add → "🔁 <rule>" (checked BEFORE the
# date patterns so "every monday" isn't half-eaten by the weekday rule).
_REC_ALT = (
    r"every (?:other )?(?:"
    r"day|week|month|year|weekday"
    rf"|{'|'.join(sorted(_WEEKDAYS, key=len, reverse=True))})s?"
    r"|every \d{1,3} (?:day|week|month|year)s?"
    r"|daily|weekly|monthly|yearly"
)
_REC_RE = re.compile(rf"\b({_REC_ALT})\b", re.IGNORECASE)


def extract_recurrence(text: str) -> tuple[str, str | None]:
    """Split a typed recurrence phrase out: ('gym', 'every monday').

    Only the FIRST match is consumed; the rule is lowercased and normalized
    to match what core.recur understands."""
    m = _REC_RE.search(text)
    if not m:
        return text.strip(), None
    rule = " ".join(m.group(1).lower().split())
    cleaned = (text[: m.start()] + " " + text[m.end() :]).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned, rule


def parse(text: str, today: date) -> tuple[str, date | None]:
    """Return (text_without_date_phrase, due_date_or_None).

    Only the FIRST recognised date phrase is consumed; the rest of the text
    is kept verbatim (minus the phrase, whitespace tidied).
    """
    for pattern, kind in _PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        if kind == "next-weekday":
            ahead = _weekday_on_or_after(today, _WEEKDAYS[m.group(1).lower()]) + 7
            due = today + timedelta(days=ahead)
        elif kind == "weekday":
            ahead = _weekday_on_or_after(today, _WEEKDAYS[m.group(1).lower()])
            due = today + timedelta(days=ahead)
        elif kind == "today":
            due = today
        elif kind == "tomorrow":
            due = today + timedelta(days=1)
        elif kind == "next-week":
            due = today + timedelta(days=7)
        elif kind == "in-days":
            due = today + timedelta(days=min(int(m.group(1)), 3650))
        else:  # iso
            try:
                due = date.fromisoformat(m.group(1))
            except ValueError:
                continue
        cleaned = (text[: m.start()] + " " + text[m.end() :]).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned, due
    return text.strip(), None
