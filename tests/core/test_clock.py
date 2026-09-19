"""Logical day + wake detection (PRD §5.9)."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from dayline.core.clock import detect_wake, logical_date, parse_day_start_minutes


def test_parse_day_start() -> None:
    assert parse_day_start_minutes("00:00") == 0
    assert parse_day_start_minutes("2:30") == 150
    assert parse_day_start_minutes("06:00") == 360
    with pytest.raises(ValueError):
        parse_day_start_minutes("7:00 pm")
    with pytest.raises(ValueError):
        parse_day_start_minutes("24:00")


def test_logical_day_boundary() -> None:
    # day starts 02:00 → 01:30 belongs to yesterday; 02:00 sharp is today
    assert logical_date(datetime(2026, 1, 5, 1, 30), 120) == date(2026, 1, 4)
    assert logical_date(datetime(2026, 1, 5, 2, 0), 120) == date(2026, 1, 5)
    assert logical_date(datetime(2026, 1, 1, 0, 30), 120) == date(2025, 12, 31)
    assert logical_date(datetime(2026, 3, 9, 0, 30), 0) == date(2026, 3, 9)


def test_wake_detection_wall_vs_monotonic() -> None:
    # normal 30 s tick
    assert not detect_wake(1000.0, 500.0, 1030.0, 530.0)
    # slept 8 h: wall advanced 8h01m, monotonic ~30 s
    assert detect_wake(1000.0, 500.0, 1000.0 + 8 * 3600 + 30, 530.0)
    # clock rolled back (DST end): negative wall delta
    assert detect_wake(1000.0, 500.0, 1000.0 - 3600 + 30, 530.0)
    # small drift tolerated
    assert not detect_wake(0.0, 0.0, 30.5, 30.0)
