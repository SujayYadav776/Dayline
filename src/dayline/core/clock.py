"""Logical day + wake detection (PRD §5.9). DST-safe: pure wall-clock arithmetic.

The app checks a 30 s timer; a jump between wall clock and monotonic clock
larger than 60 s indicates sleep/wake and triggers an immediate re-check.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def parse_day_start_minutes(text: str) -> int:
    """'02:30' → 150. Raises ValueError on malformed input."""
    m = _TIME_RE.match(text.strip())
    if not m:
        raise ValueError(f"invalid HH:MM: {text!r}")
    return int(m.group(1)) * 60 + int(m.group(2))


def logical_date(now: datetime, day_start_minutes: int) -> date:
    """'Day starts at 02:00' → 01:30 belongs to yesterday (FR-R5)."""
    return (now - timedelta(minutes=day_start_minutes)).date()


def detect_wake(
    prev_wall: float, prev_mono: float, wall: float, mono: float, threshold_s: float = 60.0
) -> bool:
    """Wall-clock advanced (or rewound) much more than monotonic → slept/jumped."""
    return abs((wall - prev_wall) - (mono - prev_mono)) > threshold_s
