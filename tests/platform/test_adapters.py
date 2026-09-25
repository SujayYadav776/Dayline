"""Platform adapter logic tests with injected fakes (real Win32 paths are
exercised on a Windows run; here we prove the decision logic)."""

from __future__ import annotations

import pytest

from dayline.platform import dwm
from dayline.platform.autostart import (
    RUN_NAME,
    Autostart,
    FakeReg,
    command_for,
)
from dayline.platform.dwm import set_mica_backdrop, set_rounded_corners, supports_system_backdrop
from dayline.platform.hotkey import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_NOREPEAT,
    FakeBackend,
    GlobalHotkey,
    HotkeyError,
    parse_hotkey,
)


# ---- autostart -------------------------------------------------------------
def test_command_for_quotes_exe() -> None:
    assert command_for("C:\\a b\\Dayline.exe") == '"C:\\a b\\Dayline.exe" --minimized'


def test_command_for_dev_args() -> None:
    assert command_for("pythonw.exe", "-m dayline") == '"pythonw.exe" -m dayline --minimized'


def test_autostart_set_and_clear() -> None:
    reg = FakeReg()
    a = Autostart(reg=reg, command='"X" --minimized')
    assert a.enabled() is False
    a.set(True)
    assert reg.store[RUN_NAME] == '"X" --minimized'
    assert a.enabled() is True
    a.set(False)
    assert a.enabled() is False


# ---- hotkey parsing --------------------------------------------------------
def test_parse_ctrl_alt_n() -> None:
    mods, vk = parse_hotkey("ctrl+alt+n")
    assert vk == ord("N")
    assert mods & MOD_CONTROL and mods & MOD_ALT and mods & MOD_NOREPEAT


def test_parse_case_and_spaces_insensitive() -> None:
    assert parse_hotkey("Ctrl + Alt + N") == parse_hotkey("ctrl+alt+n")


def test_parse_digit_key() -> None:
    _mods, vk = parse_hotkey("ctrl+alt+1")
    assert vk == 0x31


@pytest.mark.parametrize("bad", ["", "ctrl+", "ctrl+shift", "ctrl+f1", "n"])
def test_parse_rejects(bad: str) -> None:
    with pytest.raises(HotkeyError):
        parse_hotkey(bad)


def test_global_hotkey_bind_fake_backend() -> None:
    backend = FakeBackend(ok=True)
    hk = GlobalHotkey(backend)
    assert hk.bind("ctrl+alt+n", lambda: None) is True
    assert backend.registered  # registered an id
    hk.unbind()
    assert backend.registered == {}


def test_global_hotkey_conflict_returns_false() -> None:
    hk = GlobalHotkey(FakeBackend(ok=False))
    assert hk.bind("ctrl+alt+n", lambda: None) is False


def test_two_hotkeys_get_distinct_ids_and_route_independently() -> None:
    """Regression: quick-add and summon both used id 0xD0DA, so the second
    RegisterHotKey failed and the summon key never fired. Each instance must
    now draw its own id and register its own callback in the dispatch map."""
    from dayline.platform.hotkey import _CALLBACKS

    backend = FakeBackend(ok=True)
    quick: list[str] = []
    summon: list[str] = []
    hk1 = GlobalHotkey(backend)
    hk2 = GlobalHotkey(backend)
    assert hk1.bind("ctrl+alt+n", lambda: quick.append("q")) is True
    assert hk2.bind("ctrl+shift+d", lambda: summon.append("s")) is True
    assert hk1._id != hk2._id
    assert set(backend.registered) == {hk1._id, hk2._id}
    # the native filter dispatches on the id carried in WM_HOTKEY's wParam
    _CALLBACKS[hk1._id]()
    _CALLBACKS[hk2._id]()
    assert quick == ["q"] and summon == ["s"]
    hk1.unbind()
    hk2.unbind()
    assert hk1._id not in _CALLBACKS and hk2._id not in _CALLBACKS
    assert backend.registered == {}


# ---- Mica backdrop ---------------------------------------------------------
@pytest.mark.parametrize("build", [22000, 22621, 26200])
def test_supports_system_backdrop_on_win11(build: int) -> None:
    assert supports_system_backdrop(build) is True


@pytest.mark.parametrize("build", [0, 19041, 19045, 21999])
def test_supports_system_backdrop_off_win11(build: int) -> None:
    assert supports_system_backdrop(build) is False


def test_mica_backdrop_noop_without_hwnd() -> None:
    assert set_mica_backdrop(0, True) is False
    assert set_mica_backdrop(0, False) is False


# ---- rounded corners (Win11 DWM clip) ---------------------------------------
def test_rounded_corners_noop_without_hwnd() -> None:
    assert set_rounded_corners(0) is False
    assert set_rounded_corners(0, False) is False


def test_rounded_corners_degrades_off_win11(monkeypatch: pytest.MonkeyPatch) -> None:
    # even with a fake hwnd, a non-Win11 build must not touch DWM
    monkeypatch.setattr(dwm, "supports_system_backdrop", lambda build=None: False)
    assert set_rounded_corners(1234) is False
