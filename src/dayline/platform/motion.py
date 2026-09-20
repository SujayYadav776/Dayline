"""Reduced-motion detection (PRD §4.2: motion off when the OS animation setting is off).

Reads HKCU\\Control Panel\\Desktop\\MinAnimate ("0" ⇒ animations disabled).
Fakeable; defaults to "animations on" off Windows or on any error.
"""

from __future__ import annotations

import sys
from collections.abc import Callable


def _registry_animations_enabled() -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as k:
            val, _ = winreg.QueryValueEx(k, "MinAnimate")
            return str(val).strip() != "0"
    except (OSError, ImportError):
        return True


def make_motion_source(probe: Callable[[], bool] | None = None) -> Callable[[], bool]:
    use = probe or (_registry_animations_enabled if sys.platform == "win32" else (lambda: True))
    return use


class AnimationsEnabled:
    def __init__(self, probe: Callable[[], bool] | None = None) -> None:
        self._probe = make_motion_source(probe)

    def __call__(self) -> bool:
        return self._probe()
