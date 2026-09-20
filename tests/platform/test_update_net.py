"""platform/update_net: the https+host guard (no real network here)."""

from __future__ import annotations

import pytest

from dayline.platform.update_net import NetError, _guard, github_latest_url


def test_github_latest_url() -> None:
    assert github_latest_url("a/b") == "https://api.github.com/repos/a/b/releases/latest"


@pytest.mark.parametrize(
    "url",
    [
        "http://api.github.com/x",  # not https
        "https://evil.example.com/x",  # host not allowlisted
        "https://api.github.com.evil.com/x",  # suffix trick
        "file:///c:/windows/x.exe",  # non-http scheme
    ],
)
def test_guard_rejects(url: str) -> None:
    with pytest.raises(NetError):
        _guard(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://api.github.com/repos/a/b/releases/latest",
        "https://github.com/a/b/releases/download/v1/Dayline-Setup-1.0.0.exe",
        "https://objects.githubusercontent.com/x",
    ],
)
def test_guard_allows(url: str) -> None:
    _guard(url)  # must not raise
