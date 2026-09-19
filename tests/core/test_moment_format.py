"""Moment-format subset tests (PRD §5.4)."""

from __future__ import annotations

from datetime import date

import pytest

from dayline.core.moment_format import format_date, unsupported_tokens

D = date(2026, 9, 19)  # a Saturday
assert D.weekday() == 5

CASES = [
    ("YYYY-MM-DD", "2026-09-19"),
    ("YY/M/D", "26/9/19"),
    ("dddd", "Saturday"),
    ("ddd", "Sat"),
    ("MMMM D, YYYY", "September 19, 2026"),
    ("MMM", "Sep"),
    ("[Week of] YYYY-MM-DD", "Week of 2026-09-19"),
    ("YYYY/MM/YYYY-MM-DD", "2026/09/2026-09-19"),  # subfolder support
    ("", ""),
    ("[DD] [literal stays]", "DD literal stays"),
    ("YYYY年MM月DD日", "2026年09月19日"),  # non-ASCII literals pass through
]


@pytest.mark.parametrize(("fmt", "want"), CASES)
def test_format_date(fmt: str, want: str) -> None:
    assert format_date(D, fmt) == want


def test_unsupported_tokens_detected() -> None:
    assert unsupported_tokens("gggg-[W]ww") == ["g", "g", "g", "g", "w", "w"]
    assert unsupported_tokens("YYYY-MM-DD") == []
    assert unsupported_tokens("Do MMMM") == ["o"]
    assert unsupported_tokens("HH:mm") == ["H", "H", "m", "m"]  # time tokens unsupported


def test_format_date_raises_on_unsupported() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        format_date(D, "gggg")


def test_moment_sunday_first_weekday() -> None:
    from datetime import date as dt

    assert format_date(dt(2026, 9, 20), "dddd") == "Sunday"
    assert format_date(dt(2026, 9, 21), "ddd") == "Mon"
