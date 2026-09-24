"""Natural-language quick-add parsing (pure)."""

from __future__ import annotations

from datetime import date

import pytest

from dayline.core.quickadd import parse

TODAY = date(2026, 9, 21)  # a Monday


@pytest.mark.parametrize(
    ("raw", "expected_text", "expected_date"),
    [
        ("buy milk", "buy milk", None),  # no date phrase → untouched
        ("pay rent tomorrow", "pay rent", date(2026, 9, 22)),
        ("call mom today", "call mom", TODAY),
        ("call mom tonight", "call mom", TODAY),
        ("review TOMORROW", "review", date(2026, 9, 22)),  # case-insensitive
        ("gym next week", "gym", date(2026, 9, 28)),
        ("ship in 3 days", "ship", date(2026, 9, 24)),
        ("deadline  2026-10-05  sync", "deadline sync", date(2026, 10, 5)),
        ("review fri", "review", date(2026, 9, 25)),  # next Friday
        ("review friday", "review", date(2026, 9, 25)),
        ("dance next friday", "dance", date(2026, 10, 2)),  # bare + one week
        ("meet monday", "meet", TODAY),  # today counts
        ("tax in 1 day", "tax", date(2026, 9, 22)),
    ],
)
def test_parse_date_phrases(raw: str, expected_text: str, expected_date: date | None) -> None:
    text, due = parse(raw, TODAY)
    assert text == expected_text
    assert due == expected_date


def test_priority_bangs_survive() -> None:
    text, due = parse("pay rent tomorrow !!", TODAY)
    assert text == "pay rent !!"
    assert due == date(2026, 9, 22)


def test_tags_survive() -> None:
    text, due = parse("fix bug #errands tomorrow", TODAY)
    assert text == "fix bug #errands"
    assert due == date(2026, 9, 22)


def test_newlines_collapsed() -> None:
    text, due = parse("a\nb   tomorrow", TODAY)
    assert text == "a b"
    assert due == date(2026, 9, 22)


def test_multiple_phrases_first_wins() -> None:
    text, due = parse("pay tomorrow and next week", TODAY)
    assert text == "pay and next week"
    assert due == date(2026, 9, 22)


# ---- extract_recurrence -------------------------------------------------------
def test_extract_recurrence_basic() -> None:
    from dayline.core.quickadd import extract_recurrence

    assert extract_recurrence("gym every monday") == ("gym", "every monday")
    assert extract_recurrence("water every day") == ("water", "every day")
    assert extract_recurrence("review weekly") == ("review", "weekly")
    assert extract_recurrence("EAT EVERY 2 WEEKS") == ("EAT", "every 2 weeks")
    assert extract_recurrence("standup every weekday before work") == (
        "standup before work",
        "every weekday",
    )


def test_extract_recurrence_keeps_bangs_and_tags() -> None:
    from dayline.core.quickadd import extract_recurrence

    assert extract_recurrence("gym every monday !!") == ("gym !!", "every monday")
    assert extract_recurrence("gym every monday #health") == (
        "gym #health",
        "every monday",
    )


def test_extract_recurrence_absent() -> None:
    from dayline.core.quickadd import extract_recurrence

    assert extract_recurrence("buy milk") == ("buy milk", None)
    # "every" alone or unknown units are not recurrence phrases
    assert extract_recurrence("every so often") == ("every so often", None)
