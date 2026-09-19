"""Moment.js date-format subset (PRD §5.4): YYYY YY MMMM MMM MM M DD D dddd ddd,
bracket-escaped literals, '/' for subfolders. Unsupported tokens are reported
so the UI can warn and fall back to YYYY-MM-DD (FR-O3)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

MONTHS_FULL = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
MONTHS_SHORT = [m[:3] for m in MONTHS_FULL]
DAYS_FULL = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]
DAYS_SHORT = [d[:3] for d in DAYS_FULL]

# longest-first so MMMM beats MM etc.
_SUPPORTED_FIXED: dict[str, Callable[[date], str]] = {
    "YYYY": lambda d: f"{d.year:04d}",
    "YY": lambda d: f"{d.year % 100:02d}",
    "MMMM": lambda d: MONTHS_FULL[d.month - 1],
    "MMM": lambda d: MONTHS_SHORT[d.month - 1],
    "MM": lambda d: f"{d.month:02d}",
    "M": lambda d: str(d.month),
    "DD": lambda d: f"{d.day:02d}",
    "D": lambda d: str(d.day),
}

# Moment weekday order: Sunday=0 — DAYS_FULL/DAYS_SHORT already follow it.


def _dow(d: date) -> int:
    """Moment get('day'): 0=Sunday..6=Saturday."""
    return (d.weekday() + 1) % 7


def _sub(d: date, token: str) -> str:
    if token == "dddd":
        return DAYS_FULL[_dow(d)]
    if token == "ddd":
        return DAYS_SHORT[_dow(d)]
    return _SUPPORTED_FIXED[token](d)


# Moment format-token letters we do NOT implement — a bare occurrence should
# warn (week numbers gggg/[W]ww, time HH:mm, epoch, …). Ordinary letters are
# literals in Moment too and must pass through untouched.
_UNSUPPORTED_TOKEN_CHARS = set("GgQqYwWEaAHkKmsSXZod")


def unsupported_tokens(fmt: str) -> list[str]:
    """Bare token letters outside []-escapes that we do not support."""
    out: list[str] = []
    pos = 0
    while pos < len(fmt):
        if fmt[pos] == "[":
            close = fmt.find("]", pos)
            pos = (close + 1) if close != -1 else pos + 1
            continue
        matched = False
        for token in ("YYYY", "MMMM", "dddd", "MMM", "ddd", "YY", "MM", "DD", "M", "D"):
            if fmt.startswith(token, pos):
                pos += len(token)
                matched = True
                break
        if not matched:
            ch = fmt[pos]
            if ch in _UNSUPPORTED_TOKEN_CHARS:
                out.append(ch)
            pos += 1
    return out


def format_date(d: date, fmt: str) -> str:
    """Render `d` with the supported subset. Raises ValueError on stray
    unsupported letters — call unsupported_tokens() first and fall back."""
    bad = unsupported_tokens(fmt)
    if bad:
        raise ValueError(f"unsupported date-format tokens: {''.join(sorted(set(bad)))}")
    out: list[str] = []
    pos = 0
    while pos < len(fmt):
        ch = fmt[pos]
        if ch == "[":
            close = fmt.find("]", pos)
            if close == -1:
                out.append(fmt[pos:])
                break
            out.append(fmt[pos + 1 : close])
            pos = close + 1
            continue
        for token in ("YYYY", "MMMM", "dddd", "MMM", "ddd", "YY", "MM", "DD", "M", "D"):
            if fmt.startswith(token, pos):
                out.append(_sub(d, token))
                pos += len(token)
                break
        else:
            out.append(ch)
            pos += 1
    return "".join(out)
