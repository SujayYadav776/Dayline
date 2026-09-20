"""core/updater: version compare, GitHub-release parsing, scheduling (pure)."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timedelta

import pytest

from dayline.core.updater import (
    UpdateInfo,
    check_for_update,
    needs_update,
    normalize_version,
    parse_release,
    pick_installer_asset,
    should_check,
)


# ---- version normalisation + comparison -----------------------------------
def test_normalize_version() -> None:
    assert normalize_version("v1.2.0") == "1.2.0"
    assert normalize_version("1.2") == "1.2"
    assert normalize_version("release-v1.2.3-beta") == "1.2.3"
    assert normalize_version("nonsense") == ""
    assert normalize_version("") == ""


def test_needs_update_only_when_strictly_newer() -> None:
    assert needs_update("1.1.1", "1.2.0") is True
    assert needs_update("1.1.1", "1.1.2") is True
    assert needs_update("1.9.0", "1.10.0") is True  # numeric, not lexical
    assert needs_update("1.2.0", "1.2.0") is False
    assert needs_update("1.2.0", "1.1.9") is False
    assert needs_update("1.2", "1.2.0") is False  # padded equal
    assert needs_update("1.2.0", "garbage") is False
    assert needs_update("garbage", "1.2.0") is True


# ---- asset pick ------------------------------------------------------------
def test_pick_installer_prefers_setup() -> None:
    rel = {
        "assets": [
            {"name": "app.zip", "browser_download_url": "https://x/app.zip"},
            {"name": "Dayline-Setup-1.2.0.exe", "browser_download_url": "https://x/s.exe"},
            {"name": "portable.exe", "browser_download_url": "https://x/p.exe"},
        ]
    }
    assert pick_installer_asset(rel) == "https://x/s.exe"


def test_pick_installer_falls_back_to_any_exe() -> None:
    rel = {"assets": [{"name": "thing.exe", "browser_download_url": "https://x/t.exe"}]}
    assert pick_installer_asset(rel) == "https://x/t.exe"


def test_pick_installer_none() -> None:
    assert pick_installer_asset({}) == ""
    assert pick_installer_asset({"assets": [{"name": "notes.txt"}]}) == ""


# ---- parse_release ---------------------------------------------------------
def test_parse_release_ok() -> None:
    info = parse_release(
        {
            "tag_name": "v1.2.0",
            "html_url": "https://gh/releases/tag/v1.2.0",
            "body": "notes",
            "published_at": "2026-09-20T10:00:00Z",
            "assets": [
                {"name": "Dayline-Setup-1.2.0.exe", "browser_download_url": "https://d/s.exe"}
            ],
        }
    )
    assert info == UpdateInfo(
        "1.2.0",
        "https://gh/releases/tag/v1.2.0",
        "https://d/s.exe",
        "notes",
        "2026-09-20T10:00:00Z",
    )


def test_parse_release_bad_payloads() -> None:
    assert parse_release([]) is None
    assert parse_release({}) is None
    assert parse_release({"tag_name": "not-a-version"}) is None


# ---- check_for_update (injected fetcher) ---------------------------------
def _fetcher(payload: object) -> Callable[[str], bytes]:
    data = json.dumps(payload).encode("utf-8")
    return lambda _url: data


def test_check_for_update_returns_newer() -> None:
    payload = {
        "tag_name": "v9.9.9",
        "html_url": "u",
        "assets": [{"name": "Dayline-Setup-9.9.9.exe", "browser_download_url": "d.exe"}],
    }
    info = check_for_update(_fetcher(payload), "api", "1.0.0")
    assert info is not None and info.version == "9.9.9" and info.download_url == "d.exe"


def test_check_for_update_none_when_up_to_date() -> None:
    payload = {"tag_name": "v1.0.0", "html_url": "u", "assets": []}
    assert check_for_update(_fetcher(payload), "api", "1.0.0") is None


def test_check_for_update_propagates_errors() -> None:
    def boom(_url: str) -> bytes:
        raise RuntimeError("offline")

    with pytest.raises(RuntimeError):
        check_for_update(boom, "api", "1.0.0")
    with pytest.raises(ValueError):  # json.loads on garbage → JSONDecodeError
        check_for_update(lambda _u: b"not json", "api", "1.0.0")


def test_check_for_update_none_when_unusable_payload() -> None:
    # valid JSON but not a usable release → None, no raise
    assert check_for_update(_fetcher({"message": "not found"}), "api", "1.0.0") is None


# ---- scheduling ------------------------------------------------------------
def test_should_check() -> None:
    now = datetime(2026, 9, 20, 12, 0, 0)
    assert should_check("", now) is True
    assert should_check(now.isoformat(timespec="seconds"), now) is False  # just checked
    older = (now - timedelta(days=1, seconds=5)).isoformat(timespec="seconds")
    assert should_check(older, now) is True
    assert should_check("not-a-date", now) is True
