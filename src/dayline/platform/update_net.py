"""HTTPS fetch + installer download for the update check (Windows, stdlib only).

Deliberately narrow: https only, and only to GitHub's own hosts, so the app can
never be pointed (by a tampered feed) at an arbitrary origin to fetch/run a
binary. Kept thin so the pure logic in ``core/updater`` does the thinking.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Final
from urllib.parse import urlparse

_UA: Final = "Dayline/updates (+https://github.com)"
_ALLOWED_HOSTS: Final = frozenset(
    {
        "api.github.com",
        "github.com",
        "codeload.github.com",
        "objects.githubusercontent.com",
        "media.githubusercontent.com",
    }
)


class NetError(Exception):
    """Any fetch/download failure; callers fail soft."""


def _guard(url: str) -> None:
    parts = urlparse(url)
    if parts.scheme != "https":
        raise NetError("https required")
    if parts.hostname not in _ALLOWED_HOSTS:
        raise NetError(f"host not allowed: {parts.hostname}")


def github_latest_url(repo: str) -> str:
    return f"https://api.github.com/repos/{repo}/releases/latest"


def http_get(url: str, timeout: float = 15.0) -> bytes:
    """GET bytes over https to an allowed host, with a UA + API accept header."""
    _guard(url)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _UA, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload: bytes = resp.read()
            return payload
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise NetError(str(exc)) from exc


def download(url: str, dest: Path, timeout: float = 120.0) -> Path:
    """Stream an https asset to ``dest`` on an allowed host; return the path."""
    _guard(url)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as fh:
            for chunk in iter(lambda: resp.read(65536), b""):
                fh.write(chunk)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        dest.unlink(missing_ok=True)
        raise NetError(str(exc)) from exc
    return dest


def make_fetcher() -> Callable[[str], bytes]:
    return http_get
