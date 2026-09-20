"""Platform adapter logic tests with injected fakes (real Win32 paths are
exercised on a Windows run; here we prove the decision logic)."""

from __future__ import annotations

import pytest

from dayline.platform.autostart import (
    RUN_NAME,
    Autostart,
    FakeReg,
    command_for,
)
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
