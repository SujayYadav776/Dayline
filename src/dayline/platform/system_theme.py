"""Windows app-theme probe (FR-P9) behind a tiny fakeable interface."""

from __future__ import annotations

import logging
from collections.abc import Callable

log = logging.getLogger("dayline.platform.system_theme")

GetTheme = Callable[[], str]  # -> "light" | "dark"


def _registry_theme() -> str:
    """HKCU AppsUseLightTheme (0 = dark). Any failure → light."""
    try:
        import winreg

        path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "dark" if int(value) == 0 else "light"
    except OSError:
        return "light"


def make_theme_source(setting: str = "system", probe: GetTheme | None = None) -> GetTheme:
    """Resolve theme setting ('system'|'light'|'dark') to a live bool source.

    'system' uses the registry probe (Windows only); tests inject a fake.
    """
    if setting == "light":
        return lambda: "light"
    if setting == "dark":
        return lambda: "dark"
    use = probe or _registry_theme
    return use
