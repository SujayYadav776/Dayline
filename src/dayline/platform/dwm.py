"""Immersive dark title bar via DwmSetWindowAttribute (FR-P8). ctypes; fakeable."""

from __future__ import annotations

import ctypes
import sys

_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19  # early Win10 builds


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
