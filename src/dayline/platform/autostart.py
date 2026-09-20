"""Autostart via HKCU\\...\\Run (FR-P4). Registry access is injected for tests."""

from __future__ import annotations

import contextlib
import sys
from typing import Protocol

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "Dayline"


class Reg(Protocol):
    def get(self, name: str) -> str | None: ...
    def set(self, name: str, value: str) -> None: ...
    def delete(self, name: str) -> None: ...


class WinReg:
    """Real HKCU Run adapter (Windows only)."""

    def __init__(self) -> None:
        import winreg

        self._winreg = winreg

    def get(self, name: str) -> str | None:
        with self._winreg.OpenKey(self._winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            try:
                val, _ = self._winreg.QueryValueEx(k, name)
                return str(val)
            except FileNotFoundError:
                return None

    def set(self, name: str, value: str) -> None:
        with self._winreg.OpenKey(
            self._winreg.HKEY_CURRENT_USER, RUN_KEY, 0, self._winreg.KEY_SET_VALUE
        ) as k:
            self._winreg.SetValueEx(k, name, 0, self._winreg.REG_SZ, value)

    def delete(self, name: str) -> None:
        with (
            self._winreg.OpenKey(
                self._winreg.HKEY_CURRENT_USER, RUN_KEY, 0, self._winreg.KEY_SET_VALUE
            ) as k,
            contextlib.suppress(FileNotFoundError),
        ):
            self._winreg.DeleteValue(k, name)


class FakeReg:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, name: str) -> str | None:
        return self.store.get(name)

    def set(self, name: str, value: str) -> None:
        self.store[name] = value

    def delete(self, name: str) -> None:
        self.store.pop(name, None)


def command_for(exe_path: str, extra_args: str = "") -> str:
    """Quoted launch command with --minimized (autostart starts hidden to tray)."""
    parts = [f'"{exe_path}"']
    if extra_args:
        parts.append(extra_args)
    parts.append("--minimized")
    return " ".join(parts)


def launch_command(exe_path: str | None = None) -> str:
    """Full Run-key command for the current environment (frozen vs dev)."""
    if exe_path is not None:
        return command_for(exe_path)
    if getattr(sys, "frozen", False):  # pragma: no cover - frozen only
        return command_for(sys.executable)
    import os

    exe = sys.executable
    pyw = exe.replace("python.exe", "pythonw.exe")
    return command_for(pyw if os.path.exists(pyw) else exe, "-m dayline")


class Autostart:
    def __init__(self, reg: Reg | None = None, command: str | None = None) -> None:
        self._reg = reg if reg is not None else _default_reg()
        self._command = command or launch_command()

    def enabled(self) -> bool:
        try:
            return self._reg.get(RUN_NAME) is not None
        except OSError:
            return False

    def set(self, on: bool) -> None:
        if on:
            self._reg.set(RUN_NAME, self._command)
        else:
            with contextlib.suppress(OSError):
                self._reg.delete(RUN_NAME)


def _default_reg() -> Reg:
    return WinReg() if sys.platform == "win32" else FakeReg()
