"""Recurrence engine (core/recur.py): rule parsing + next-date math."""

from __future__ import annotations

from datetime import date

import pytest

from dayline.core import recur

MON = date(2026, 9, 21)  # a Monday
TUE = date(2026, 9, 22)


# ---------------------------------------------------------------- rule_of ---
def test_rule_of_extracts_and_normalizes() -> None:
    assert recur.rule_of("gym 🔁 every monday") == "every monday"
    assert recur.rule_of("water 🔁  EVERY   Week ") == "every week"
    assert recur.rule_of("ship 📅 2026-09-20 ⏫") is None


def test_rule_of_stops_at_next_token() -> None:
    assert recur.rule_of("review 🔁 every week 📅 2026-09-27 ⏫") == "every week"
    assert recur.rule_of("standup 🔁 every day #work") == "every day"


# ---------------------------------------------------------------- due_of ---
def test_due_of_parses_or_none() -> None:
    assert recur.due_of("x 📅 2026-09-27") == date(2026, 9, 27)
    assert recur.due_of("x 📅2026-09-27") == date(2026, 9, 27)
    assert recur.due_of("x 📅 not-a-date") is None
    assert recur.due_of("x") is None


# ------------------------------------------------------- next_occurrence ---
@pytest.mark.parametrize(
    ("rule", "after", "want"),
    [
        ("every day", MON, date(2026, 9, 22)),
        ("daily", MON, date(2026, 9, 22)),
        ("every weekday", date(2026, 9, 25), date(2026, 9, 28)),  # Fri→Mon
        ("every weekday", MON, date(2026, 9, 22)),
        ("every week", MON, date(2026, 9, 28)),
        ("weekly", MON, date(2026, 9, 28)),
        ("every other week", MON, date(2026, 10, 5)),
        ("every month", date(2026, 1, 31), date(2026, 2, 28)),  # clamp
        ("monthly", date(2026, 3, 31), date(2026, 4, 30)),
        ("every year", date(2024, 2, 29), date(2025, 2, 28)),  # leap clamp
        ("yearly", MON, date(2027, 9, 21)),
        ("annually", MON, date(2027, 9, 21)),
        ("every 3 days", MON, date(2026, 9, 24)),
        ("every 2 weeks", MON, date(2026, 10, 5)),
        ("every 18 months", date(2026, 9, 30), date(2028, 3, 30)),
        ("every friday", MON, date(2026, 9, 25)),
        ("every mon", MON, date(2026, 9, 28)),  # same weekday → +7
        ("every mondays", MON, date(2026, 9, 28)),
        ("every thurs", TUE, date(2026, 9, 24)),
        ("every other friday", MON, date(2026, 10, 2)),  # skip the nearest
        ("each week", MON, date(2026, 9, 28)),
    ],
)
def test_next_occurrence(rule: str, after: date, want: date) -> None:
    assert recur.next_occurrence(rule, after) == want


def test_next_occurrence_unknown_rules_return_none() -> None:
    assert recur.next_occurrence("whenever", MON) is None
    assert recur.next_occurrence("every hamster", MON) is None
    assert recur.next_occurrence("", MON) is None


# ---------------------------------------------------------------- next_body ---
def test_next_body_rewrites_due_keeps_recurrence() -> None:
    body = "gym 🔁 every monday 📅 2026-09-21 ✅ 2026-09-22 ⏫"
    out = recur.next_body(body, date(2026, 9, 28))
    assert "📅 2026-09-28" in out
    assert "🔁 every monday" in out
    assert "✅" not in out
    assert "⏫" in out
    assert "  " not in out


def test_next_body_inserts_missing_due() -> None:
    out = recur.next_body("standup 🔁 every day", date(2026, 9, 23))
    assert out == "standup 🔁 every day 📅 2026-09-23"
