"""Recurrence (Obsidian Tasks 🔁 syntax): rule parsing + next-date math.

Pure and deterministic (no clock reads) so the editor passes an explicit
base date. Supported rules (case-insensitive, whitespace-tolerant):
every day/daily · every weekday · every week/weekly · every other week ·
every month/monthly · every year/yearly/annually · every N days|weeks|
months|years · every <weekday> (names + abbreviations) · every other
<weekday>. Anything else returns None (the task simply doesn't repeat).

Semantics: the next occurrence is STRICTLY AFTER the base date, where the
caller passes base = max(📅 due, completion day) so completing an overdue
recurring task never spawns an instance in the past. Month/year steps clamp
to the last valid day (Jan 31 → Feb 28; Feb 29 → Feb 28).
"""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

# 🔁 + rule text up to the next Tasks token / tag (mirrors model._RECURRENCE_TOKEN_RE)
_RULE_RE = re.compile(r"🔁\s*([^📅⏳🛫➕✅🔁🔺🔼⏬#]+)")
_DUE_RE = re.compile(r"📅\s*(\d{4}-\d{2}-\d{2})")
_DONE_RE = re.compile(r"\s*✅\s*\d{4}-\d{2}-\d{2}")

_WEEKDAYS = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}
_WD_ALT = "|".join(sorted(_WEEKDAYS, key=len, reverse=True))


def rule_of(body: str) -> str | None:
    """The normalized 🔁 rule text ("every monday"), or None if absent."""
    m = _RULE_RE.search(body)
    if not m:
        return None
    rule = " ".join(m.group(1).lower().split())
    return rule or None


def due_of(body: str) -> date | None:
    """The 📅 due date in a task body, if any and valid."""
    m = _DUE_RE.search(body)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def add_months(d: date, n: int) -> date:
    total = d.year * 12 + (d.month - 1) + n
    y, m = divmod(total, 12)
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def add_years(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:  # Feb 29 → Feb 28
        return d.replace(month=2, day=28, year=d.year + n)


def next_occurrence(rule: str, after: date) -> date | None:
    """First occurrence STRICTLY AFTER `after`, or None for unknown rules."""
    r = " ".join(rule.lower().split())
    r = re.sub(r"^each\b", "every", r)
    if not r:
        return None
    if r in ("every day", "daily"):
        return after + timedelta(days=1)
    if r in ("every weekday", "weekdays"):
        nxt = after + timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += timedelta(days=1)
        return nxt
    if r in ("every week", "weekly"):
        return after + timedelta(days=7)
    if r in ("every other week",):
        return after + timedelta(days=14)
    if r in ("every month", "monthly"):
        return add_months(after, 1)
    if r in ("every year", "yearly", "annually"):
        return add_years(after, 1)
    m = re.fullmatch(r"(?:every|each) (\d{1,3}) (day|days|week|weeks|month|months|year|years)", r)
    if m:
        n = min(int(m.group(1)), 3650)
        unit = m.group(2).rstrip("s")
        if unit == "day":
            return after + timedelta(days=n)
        if unit == "week":
            return after + timedelta(weeks=n)
        if unit == "month":
            return add_months(after, n)
        return add_years(after, n)
    m = re.fullmatch(rf"(?:every|each) (other )?({_WD_ALT})s?", r)
    if m:
        ahead = (_WEEKDAYS[m.group(2)] - after.weekday()) % 7 or 7
        if m.group(1):  # "every other monday": skip the nearest occurrence
            ahead += 7
        return after + timedelta(days=ahead)
    return None


def next_body(body: str, nxt: date) -> str:
    """Body for the next instance: new 📅 (inserted if absent), 🔁 kept,
    completion ✅ dropped."""
    text = _DONE_RE.sub("", body)
    if _DUE_RE.search(text):
        text = _DUE_RE.sub(f"📅 {nxt.isoformat()}", text)
    else:
        text = f"{text.rstrip()} 📅 {nxt.isoformat()}"
    return re.sub(r"\s{2,}", " ", text).strip()
