"""Update discovery (pure, no Qt, no network). The HTTP fetch is injected.

GitHub ``releases/latest`` JSON is parsed into an ``UpdateInfo``; version
comparison and the once-a-day scheduling rule live here so they are fully
unit-testable. Off the happy path we always fail soft (``None``), so a flaky
network or a schema change can never crash the app or nag falsely.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

# A fetcher turns a URL into raw bytes (raises on failure). Injected by the
# platform layer so this module stays network-free and testable.
Fetcher = Callable[[str], bytes]

_DAY = timedelta(days=1)


@dataclass(frozen=True)
class UpdateInfo:
    version: str  # normalized, no leading "v", e.g. "1.2.0"
    page_url: str  # release page (human)
    download_url: str  # installer asset, "" if none found
    notes: str = ""
    published_at: str = ""


def normalize_version(tag: str) -> str:
    """Return the first dotted numeric core, ignoring an optional 'v' prefix/suffix
    label (e.g. 'v1.2.0', 'Dayline v1.2.0-beta' → '1.2.0'); '' if none."""
    m = re.search(r"[vV]?(\d+(?:\.\d+){0,3})", tag or "")
    return m.group(1) if m else ""


def _vtuple(v: str) -> tuple[int, int, int, int]:
    nums = [int(p) for p in normalize_version(v).split(".") if p.isdigit()]
    padded = [*nums, 0, 0, 0, 0][:4]
    return (padded[0], padded[1], padded[2], padded[3])


def needs_update(current: str, latest: str) -> bool:
    """True when ``latest`` is a strictly newer semantic version than ``current``."""
    lv = normalize_version(latest)
    if not lv:
        return False
    cv = normalize_version(current)
    if not cv:
        return True
    return _vtuple(lv) > _vtuple(cv)


def pick_installer_asset(release: dict[str, Any]) -> str:
    """Return the installer asset download URL, preferring '*Setup*.exe'."""
    assets = release.get("assets") or []
    fallback = ""
    if isinstance(assets, list):
        for a in assets:
            if not isinstance(a, dict):
                continue
            url = a.get("browser_download_url")
            name = str(a.get("name") or "").lower()
            if isinstance(url, str) and url.lower().endswith(".exe"):
                if "setup" in name or name.startswith("dayline"):
                    return url
                fallback = fallback or url
    return fallback


def parse_release(payload: object) -> UpdateInfo | None:
    """Parse a GitHub release object; None on anything unexpected."""
    if not isinstance(payload, dict):
        return None
    version = normalize_version(str(payload.get("tag_name") or payload.get("name") or ""))
    if not version:
        return None
    return UpdateInfo(
        version=version,
        page_url=str(payload.get("html_url") or ""),
        download_url=pick_installer_asset(payload),
        notes=str(payload.get("body") or "")[:2000],
        published_at=str(payload.get("published_at") or ""),
    )


def check_for_update(fetcher: Fetcher, url: str, current: str) -> UpdateInfo | None:
    """Fetch + parse + compare.

    Returns an UpdateInfo only when the release is genuinely newer; None when
    up to date or the payload isn't a usable release. Transport/parse failures
    are *raised* so the caller can surface "couldn't check" rather than silently
    claiming up-to-date.
    """
    raw = fetcher(url)
    payload = json.loads(raw.decode("utf-8", "replace"))
    info = parse_release(payload)
    if info is not None and needs_update(current, info.version):
        return info
    return None


def should_check(last_check: str, now: datetime, min_interval: timedelta = _DAY) -> bool:
    """True when there is no recorded check or the interval has elapsed."""
    if not last_check:
        return True
    try:
        last = datetime.fromisoformat(last_check)
    except ValueError:
        return True
    return (now - last) >= min_interval
