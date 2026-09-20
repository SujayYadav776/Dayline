"""Update flow in AppViewModel with a fake fetcher (runs on the worker thread,
results marshalled back via queued Qt signals → driven by qtbot)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from dayline.core.settings import Settings, load
from dayline.ui.viewmodels.app_vm import AppViewModel
from dayline.ui.viewmodels.settings_vm import SettingsViewModel

NEWER = "99.0.0"  # always newer than the running 1.x dev version
_DL = "https://github.com/a/b/releases/download/x/i.exe"


def _release_payload(tag: str, dl: str = _DL) -> bytes:
    return json.dumps(
        {
            "tag_name": tag,
            "html_url": "https://github.com/a/b/releases/tag/" + tag,
            "body": "notes",
            "assets": [{"name": "Dayline-Setup.exe", "browser_download_url": dl}],
        }
    ).encode("utf-8")


def _vm(settings: Settings, payload: bytes, calls: list[str]) -> AppViewModel:
    def fetcher(url: str) -> bytes:
        calls.append(url)
        return payload

    return AppViewModel(settings, update_fetcher=fetcher, update_downloader=lambda u, d: d)


def test_check_surfaces_a_newer_release(qtbot: Any) -> None:
    anyv: Any = _vm(Settings(), _release_payload(NEWER), [])
    anyv.checkForUpdates()
    qtbot.waitUntil(lambda: bool(anyv.updateAvailable), timeout=3000)
    assert anyv.updateLatest == "99.0.0"  # normalized, no leading 'v'
    assert anyv.updateDownloadUrl.endswith("i.exe")


def test_check_up_to_date_when_not_newer(qtbot: Any) -> None:
    from dayline import __version__

    anyv: Any = _vm(Settings(), _release_payload("v" + __version__), [])
    anyv.checkForUpdates()
    qtbot.waitUntil(lambda: "up to date" in str(anyv.updateStatus).lower(), timeout=3000)
    assert bool(anyv.updateAvailable) is False


def test_no_network_when_disabled(qtbot: Any) -> None:
    calls: list[str] = []
    settings = Settings(update_check_enabled=False)
    anyv: Any = _vm(settings, _release_payload(NEWER), calls)
    anyv.startup_update_check(now=datetime.now())
    assert calls == []  # never fetched


def test_startup_check_when_enabled_and_due(qtbot: Any) -> None:
    calls: list[str] = []
    anyv: Any = _vm(Settings(update_check_enabled=True), _release_payload(NEWER), calls)
    anyv.startup_update_check(now=datetime.now())
    qtbot.waitUntil(lambda: bool(anyv.updateAvailable), timeout=3000)
    assert len(calls) == 1


def test_startup_check_respects_daily_interval(qtbot: Any) -> None:
    calls: list[str] = []
    recent = (datetime.now() - timedelta(minutes=5)).isoformat(timespec="seconds")
    anyv: Any = _vm(
        Settings(update_check_enabled=True, update_last_check=recent),
        _release_payload(NEWER),
        calls,
    )
    anyv.startup_update_check(now=datetime.now())
    assert calls == []  # checked <24h ago → skip


def test_update_toggle_persists(tmp_path: Path) -> None:
    cfg = tmp_path / "config.json"
    svm: Any = SettingsViewModel(Settings(), config_path=cfg)
    assert bool(svm.updateCheckEnabled) is False
    svm.setUpdateCheckEnabled(True)
    reloaded, _issues = load(cfg)
    assert reloaded.update_check_enabled is True
