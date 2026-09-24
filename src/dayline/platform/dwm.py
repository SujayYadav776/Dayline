"""DWM window tweaks via ctypes (fakeable; degrade gracefully off Win11).

Three effects:
* Immersive dark title bar (FR-P8) — ``set_dark_titlebar``.
* Mica system backdrop (default-on; Windows 11 only) — ``set_mica_backdrop``
  gated by ``supports_system_backdrop`` (build 22000+). Off Win11 or on any
  failure these are no-ops returning False.
* Win11 rounded corners for the frameless window — ``set_rounded_corners``.
"""

from __future__ import annotations

import ctypes
import sys

_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19  # early Win10 builds
_DWMWA_SYSTEMBACKDROP_TYPE = 38  # Win11 22H2+
_DWMSBT_NONE = 1
_DWMSBT_MAINWINDOW = 2  # Mica
_DWMWA_WINDOW_CORNER_PREFERENCE = 33  # Win11 22000+
_DWMWCP_DONOTROUND = 0
_DWMWCP_ROUND = 2  # standard 8 px Win11 radius
_MIN_WIN11_BUILD = 22000


def _current_build() -> int:
    try:
        return int(sys.getwindowsversion().build)
    except (AttributeError, ValueError, OSError):  # pragma: no cover - non-Windows
        return 0


def supports_system_backdrop(build: int | None = None) -> bool:
    """True on Windows 11 (build >= 22000). Non-Windows → build 0 → False."""
    b = _current_build() if build is None else build
    return b >= _MIN_WIN11_BUILD


def set_dark_titlebar(hwnd: int, dark: bool) -> bool:
    """Return True on success. No-op (False) off Windows or on failure."""
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        value = ctypes.c_int(1 if dark else 0)
        dwm = ctypes.windll.dwmapi
        res = dwm.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            ctypes.c_int(_DWMWA_USE_IMMERSIVE_DARK_MODE),
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        if res != 0:  # retry with the pre-20H1 attribute id
            res = dwm.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                ctypes.c_int(_DWMWA_USE_IMMERSIVE_DARK_MODE_OLD),
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
        return int(res) == 0
    except (OSError, AttributeError):
        return False


def set_mica_backdrop(hwnd: int, enabled: bool) -> bool:
    """Apply (or clear) the Mica backdrop. No-op off Win11, without a window, or on failure."""
    if not hwnd or not supports_system_backdrop():
        return False
    try:
        value = ctypes.c_int(_DWMSBT_MAINWINDOW if enabled else _DWMSBT_NONE)
        dwm = ctypes.windll.dwmapi
        res = dwm.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            ctypes.c_int(_DWMWA_SYSTEMBACKDROP_TYPE),
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        return int(res) == 0
    except (OSError, AttributeError):
        return False


def set_rounded_corners(hwnd: int, enabled: bool = True) -> bool:
    """Round (or square) the window corners the Win11 way (DWM clip).

    No-op off Win11, without a window, or on failure — same contract as the
    other tweaks here; the frameless window just keeps its square corners."""
    if not hwnd or not supports_system_backdrop():
        return False
    try:
        value = ctypes.c_int(_DWMWCP_ROUND if enabled else _DWMWCP_DONOTROUND)
        dwm = ctypes.windll.dwmapi
        res = dwm.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            ctypes.c_int(_DWMWA_WINDOW_CORNER_PREFERENCE),
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        return int(res) == 0
    except (OSError, AttributeError):
        return False
