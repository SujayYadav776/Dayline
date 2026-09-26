"""Global hotkeys (FR-P5): RegisterHotKey via ctypes + one native event filter.

Several GlobalHotkey instances can coexist: each draws a unique Win32 id from
a counter and stores its callback in a module-level registry, which the
app-wide filter consults to dispatch WM_HOTKEY messages. The modifier/key
parsing is pure and unit-tested; registration sits behind a ``HotkeyBackend``
protocol with a ``FakeBackend`` for tests.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import itertools
import logging
import sys
from collections.abc import Callable
from typing import Protocol

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray

# Win32 modifier flags
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# Virtual-key codes for the letters/digits we allow as the trigger key.
_VK_LETTER = {chr(c): c for c in range(ord("A"), ord("Z") + 1)}  # A..Z == 0x41..0x5A
_VK_DIGIT = {str(d): 0x30 + d for d in range(10)}

_MOD_MAP = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "meta": MOD_WIN,
    "super": MOD_WIN,
}


class HotkeyError(ValueError):
    pass


def parse_hotkey(spec: str) -> tuple[int, int]:
    """'ctrl+alt+n' → (modifiers, vk). Raises HotkeyError on unknown keys."""
    parts = [p.strip().lower() for p in spec.replace(" ", "").split("+") if p.strip()]
    if not parts:
        raise HotkeyError("empty hotkey")
    mods = MOD_NOREPEAT
    key = None
    for p in parts:
        if p in _MOD_MAP:
            mods |= _MOD_MAP[p]
        elif key is None:
            vk = _VK_LETTER.get(p.upper()) or _VK_DIGIT.get(p)
            if vk is None:
                raise HotkeyError(f"unsupported key: {p!r}")
            key = vk
        else:
            raise HotkeyError(f"only one trigger key allowed (got {p!r})")
    if key is None:
        raise HotkeyError("no trigger key")
    if not (mods & (MOD_ALT | MOD_CONTROL | MOD_SHIFT | MOD_WIN)):
        raise HotkeyError("a global hotkey needs at least one modifier")
    return mods, key


class HotkeyBackend(Protocol):
    def register(self, hotkey_id: int, mods: int, vk: int) -> bool: ...
    def unregister(self, hotkey_id: int) -> None: ...


# Qt's event dispatcher hands only WINDOW messages to native event filters;
# a thread hotkey (RegisterHotKey with hwnd=None) posts WM_HOTKEY with
# hwnd==NULL, which Qt dispatches without ever consulting the filter — so
# the callback would never fire. Registering against the app window's HWND
# makes WM_HOTKEY a window message, which the filter does see.
_HWND: int = 0


def set_hotkey_hwnd(hwnd: int) -> None:
    """Point hotkey registration at the app window (call before bind, and
    again whenever the native window is recreated)."""
    global _HWND
    _HWND = hwnd


class WinBackend:
    """RegisterHotKey bound to the app window (see _HWND note)."""

    _user32 = None

    def __init__(self) -> None:
        if sys.platform == "win32":
            self._user32 = ctypes.windll.user32

    def register(self, hotkey_id: int, mods: int, vk: int) -> bool:
        if self._user32 is None:
            return False
        return bool(self._user32.RegisterHotKey(_HWND or None, hotkey_id, mods, vk))

    def unregister(self, hotkey_id: int) -> None:
        if self._user32 is not None:
            self._user32.UnregisterHotKey(_HWND or None, hotkey_id)


class FakeBackend:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.registered: dict[int, tuple[int, int]] = {}

    def register(self, hotkey_id: int, mods: int, vk: int) -> bool:
        if self.ok:
            self.registered[hotkey_id] = (mods, vk)
        return self.ok

    def unregister(self, hotkey_id: int) -> None:
        self.registered.pop(hotkey_id, None)


_WM_HOTKEY = 0x0312
_HOTKEY_ID_BASE = 0xD0DA
_ID_COUNTER = itertools.count(_HOTKEY_ID_BASE)

# Win32 id → callback, filled by GlobalHotkey.bind() and consulted by the
# single app-wide native filter. Module-level because the filter sees only
# raw MSG structs — the id is the only join key.
_CALLBACKS: dict[int, Callable[[], None]] = {}


class HotkeyFilter(QAbstractNativeEventFilter):
    """Routes WM_HOTKEY for every registered id to its callback. Filter
    installed app-wide; one instance serves any number of GlobalHotkeys."""

    def __init__(self) -> None:
        super().__init__()

    def nativeEventFilter(self, eventType: object, message: object) -> tuple[bool, int]:
        if sys.platform != "win32":
            return False, 0
        if eventType != QByteArray(b"windows_generic_MSG"):
            return False, 0
        try:
            ptr = int(message)  # type: ignore[call-overload]
            msg = ctypes.wintypes.MSG.from_address(ptr)
        except (ValueError, OSError):
            return False, 0
        if msg.message == _WM_HOTKEY:
            callback = _CALLBACKS.get(int(msg.wParam))
            if callback is not None:
                callback()
                return True, 0
        return False, 0


class GlobalHotkey:
    """One hotkey slot: unique Win32 id, its own backend registration."""

    def __init__(self, backend: HotkeyBackend | None = None) -> None:
        self._backend = (
            backend
            if backend is not None
            else (WinBackend() if sys.platform == "win32" else FakeBackend(ok=False))
        )
        self._id = next(_ID_COUNTER)
        self.registered = False

    def bind(self, spec: str, callback: Callable[[], None]) -> bool:
        mods, vk = parse_hotkey(spec)
        self.registered = self._backend.register(self._id, mods, vk)
        if self.registered:
            _CALLBACKS[self._id] = callback
        elif sys.platform == "win32":  # pragma: no cover - needs real Win32
            logging.getLogger("dayline.platform.hotkey").warning(
                "RegisterHotKey(%s, id=%s) failed: winerr %s",
                spec,
                hex(self._id),
                ctypes.windll.kernel32.GetLastError(),
            )
        return self.registered

    def unbind(self) -> None:
        if self.registered:
            self._backend.unregister(self._id)
            _CALLBACKS.pop(self._id, None)
            self.registered = False
