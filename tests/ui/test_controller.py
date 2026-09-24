"""AppController window placement: the tray-first widget docks to the
bottom-right of the work area (notification-center style)."""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QIcon

from dayline.platform.tray import Tray
from dayline.ui.app_controller import AppController


class _Rect:
    def __init__(self, x: int, y: int, w: int, h: int) -> None:
        self._x, self._y, self._w, self._h = x, y, w, h

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def width(self) -> int:
        return self._w

    def height(self) -> int:
        return self._h


class _Screen:
    def __init__(self, avail: _Rect) -> None:
        self._avail = avail

    def availableGeometry(self) -> _Rect:
        return self._avail


class _Window:
    def __init__(self, screen: _Screen, w: int, h: int) -> None:
        self._screen = screen
        self._w, self._h = w, h
        self.x, self.y = 0, 0
        self.shown = False

    def screen(self) -> _Screen:
        return self._screen

    def width(self) -> int:
        return self._w

    def height(self) -> int:
        return self._h

    def setX(self, v: int) -> None:
        self.x = v

    def setY(self, v: int) -> None:
        self.y = v

    def show(self) -> None:
        self.shown = True

    def raise_(self) -> None:
        pass

    def requestActivate(self) -> None:
        pass


class _VM:
    class _S:
        close_to_tray = True

    settings = _S()
    dark = False
    micaActive = False


def _controller(window: Any) -> AppController:
    return AppController(
        window=window,
        vm=_VM(),
        tray=None,
        hotkey=None,
        autostart=None,
        quick_add=lambda: None,
        open_obsidian=lambda: None,
        quit_app=lambda: None,
    )


def test_anchor_positions_bottom_right_of_work_area() -> None:
    # work area 1920x1032 (taskbar excluded), window 360x600, margin 12
    screen = _Screen(_Rect(0, 0, 1920, 1032))
    win = _Window(screen, 360, 600)
    _controller(win)._anchor_bottom_right()
    assert win.x == 1920 - 360 - 12
    assert win.y == 1032 - 600 - 12
    assert win.shown is False  # the anchor only positions


def test_anchor_respects_work_area_origin() -> None:
    # secondary monitor offset by (1920, 0)
    screen = _Screen(_Rect(1920, 0, 1280, 1024))
    win = _Window(screen, 360, 600)
    _controller(win)._anchor_bottom_right()
    assert win.x == 1920 + 1280 - 360 - 12
    assert win.y == 1024 - 600 - 12


def test_show_window_positions_then_shows() -> None:
    screen = _Screen(_Rect(0, 0, 1920, 1032))
    win = _Window(screen, 360, 600)
    _controller(win).show_window()
    assert win.shown is True
    assert win.x == 1920 - 360 - 12


def test_anchor_is_safe_without_screen() -> None:
    class _NoScreen:
        def screen(self) -> None:
            return None

        def width(self) -> int:
            return 360

        def height(self) -> int:
            return 600

    # No usable screen (no QApplication, or primaryScreen() is None, or the
    # fake has no setX) → the guard catches AttributeError/TypeError and the
    # anchor skips quietly rather than crashing the show path.
    _controller(_NoScreen())._anchor_bottom_right()


# ---- morning due-reminder toast content --------------------------------------
class _ToastVM:
    class _S:
        close_to_tray = True

    settings = _S()

    class _Today:
        def open_count(self) -> int:
            return 2

    today = _Today()

    def __init__(self, counts: tuple[int, int]) -> None:
        self._counts = counts

    def due_summary(self) -> tuple[int, int]:
        return self._counts


class _ToastTray(Tray):
    """Real Tray subclass so the controller's `Tray | None` annotation checks;
    only notify() is exercised and Tray.__init__ never touches the platform."""

    def __init__(self) -> None:
        super().__init__(
            QIcon(),
            on_activate=lambda: None,
            on_quick_add=lambda: None,
            on_open_obsidian=lambda: None,
            on_quit=lambda: None,
        )
        self.msgs: list[tuple[str, str]] = []

    def notify(self, title: str, msg: str, ms: int = 6000) -> None:
        self.msgs.append((title, msg))


def _toast_controller(counts: tuple[int, int]) -> tuple[AppController, _ToastTray]:
    tray = _ToastTray()
    c = AppController(
        window=_Window(_Screen(_Rect(0, 0, 1920, 1032)), 360, 600),
        vm=_ToastVM(counts),
        tray=tray,
        hotkey=None,
        autostart=None,
        quick_add=lambda: None,
        open_obsidian=lambda: None,
        quit_app=lambda: None,
    )
    return c, tray


def test_morning_fire_composes_due_and_overdue() -> None:
    c, tray = _toast_controller((3, 1))
    c._fire("morning")
    assert tray.msgs == [("Dayline", "3 due today · 1 overdue")]


def test_morning_fire_all_clear() -> None:
    c, tray = _toast_controller((0, 0))
    c._fire("morning")
    assert tray.msgs == [("Dayline", "Nothing due today — all clear.")]


def test_morning_fire_due_only() -> None:
    c, tray = _toast_controller((5, 0))
    c._fire("morning")
    assert tray.msgs == [("Dayline", "5 due today")]
