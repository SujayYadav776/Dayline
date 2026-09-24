"""AppController: wires the Windows integrations into the running UI (M5).

Owns tray, global hotkey, single-instance, close-to-tray, dark title bar and
notification timers. Qt/Win32 objects are injected so the decision logic is
unit-testable with fakes; the real plumbing is verified on a Windows run.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from PySide6.QtCore import QObject, QTimer, Slot

from dayline.core.clock import parse_day_start_minutes
from dayline.platform.autostart import Autostart
from dayline.platform.hotkey import GlobalHotkey, HotkeyError
from dayline.platform.tray import Tray

log = logging.getLogger("dayline.ui.controller")


class AppController(QObject):
    def __init__(
        self,
        *,
        window: Any,
        vm: Any,
        tray: Tray | None,
        hotkey: GlobalHotkey | None,
        autostart: Autostart | None,
        quick_add: Callable[[], None],
        open_obsidian: Callable[[], None],
        quit_app: Callable[[], None],
        summon_hotkey: GlobalHotkey | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._window = window
        self._vm = vm
        self._tray = tray
        self._hotkey = hotkey
        # second single-slot RegisterHotKey instance: the universal "summon"
        # key lives beside quick-add instead of replacing it
        self._summon_hk = summon_hotkey
        self._autostart = autostart
        self._quick_add = quick_add
        self._open_obsidian = open_obsidian
        self._quit_app = quit_app
        self._quitting = False
        self._native_filter: Any = None
        self._settings_handler: Any = None
        self._hotkey_ok = False
        self._summon_ok = False
        self._notifiers: list[QTimer] = []

    # -- tray / close-to-tray --------------------------------------------------
    def toggle_window(self) -> None:
        if self._window.isVisible():
            self._window.hide()
        else:
            self._show_and_raise()

    def show_window(self) -> None:
        """Surface the window (used by a second launch while tray-resident)."""
        self._show_and_raise()

    def anchor_bottom_right(self) -> None:
        """Dock the already-visible window to the work-area corner once at
        startup — Dayline always opens bottom-right, never where it was left."""
        self._anchor_bottom_right()

    def _show_and_raise(self) -> None:
        self._anchor_bottom_right()
        self._window.show()
        try:
            self._window.raise_()
            self._window.requestActivate()
        except AttributeError:  # pragma: no cover - depends on backend
            pass

    def _anchor_bottom_right(self, margin: int = 12) -> None:
        """Notification-center style: dock the window to the bottom-right of
        the work area (taskbar excluded) each time it is summoned."""
        try:
            screen = self._window.screen()
            if screen is None:  # pragma: no cover - only pre-show on some platforms
                from PySide6.QtWidgets import QApplication

                screen = QApplication.primaryScreen()
            avail = screen.availableGeometry()
            w = int(self._window.width())
            h = int(self._window.height())
            self._window.setX(avail.x() + max(0, avail.width() - w - margin))
            self._window.setY(avail.y() + max(0, avail.height() - h - margin))
        except (AttributeError, TypeError) as exc:  # headless fakes: skip quietly
            log.debug("bottom-right anchor skipped: %s", exc)

    def should_suppress_close(self) -> bool:
        """Close-to-tray: hide instead of quit, unless we're really quitting."""
        return bool(self._vm.settings.close_to_tray) and not self._quitting

    def on_close_requested(self) -> None:
        if self.should_suppress_close():
            self._window.hide()
        else:
            self.quit()

    def quit(self) -> None:
        self._quitting = True
        if self._tray is not None:
            self._tray.hide()
        if self._hotkey is not None:
            self._hotkey.unbind()
        if self._summon_hk is not None:
            self._summon_hk.unbind()
        self._quit_app()

    # -- dark title bar --------------------------------------------------------
    def apply_titlebar_theme(self) -> None:
        from dayline.platform.dwm import set_dark_titlebar

        try:
            hwnd = int(self._window.winId())
        except (AttributeError, TypeError):
            return
        set_dark_titlebar(hwnd, bool(self._vm.dark))

    # -- Mica system backdrop --------------------------------------------------
    def apply_backdrop(self) -> None:
        from dayline.platform.dwm import set_mica_backdrop

        try:
            hwnd = int(self._window.winId())
        except (AttributeError, TypeError):
            return
        set_mica_backdrop(hwnd, bool(self._vm.micaActive))

    # -- Win11 rounded corners ---------------------------------------------------
    def apply_corner_style(self) -> None:
        from dayline.platform.dwm import set_rounded_corners

        try:
            hwnd = int(self._window.winId())
        except (AttributeError, TypeError):
            return
        set_rounded_corners(hwnd, True)

    # -- global hotkey ---------------------------------------------------------
    def bind_hotkey(self) -> bool:
        if self._hotkey is None:
            return False
        try:
            self._hotkey_ok = self._hotkey.bind(self._vm.settings.hotkey, self._quick_add)
        except HotkeyError as exc:
            log.warning("hotkey bind failed: %s", exc)
            self._hotkey_ok = False
        self._summon_ok = False
        if self._summon_hk is not None:
            try:
                self._summon_ok = self._summon_hk.bind(
                    self._vm.settings.summon_hotkey, self.show_window
                )
            except HotkeyError as exc:
                log.warning("summon hotkey bind failed: %s", exc)
        return self._hotkey_ok

    @property
    def hotkey_ok(self) -> bool:
        return self._hotkey_ok

    # -- autostart -------------------------------------------------------------
    def sync_autostart(self) -> None:
        if self._autostart is None:
            return
        want = bool(self._vm.settings.autostart)
        if self._autostart.enabled() != want:
            try:
                self._autostart.set(want)
            except OSError:
                log.warning("autostart toggle failed", exc_info=True)

    # -- notifications (FR-P7) -------------------------------------------------
    def schedule_notifications(self, now: datetime | None = None) -> None:
        for t in self._notifiers:
            t.stop()
        self._notifiers.clear()
        s = self._vm.settings
        if not s.notifications_enabled:
            return
        now = now or datetime.now()
        for when_str, kind in (
            (s.morning_summary_at, "morning"),
            (s.evening_reminder_at, "evening"),
        ):
            if not when_str:
                continue
            timer = self._make_daily_timer(when_str, kind, now)
            if timer is not None:
                self._notifiers.append(timer)

    def _make_daily_timer(self, hhmm: str, kind: str, now: datetime) -> QTimer | None:
        try:
            minutes = parse_day_start_minutes(hhmm)
        except ValueError:
            return None
        target = (now + timedelta(days=1)).replace(
            hour=minutes // 60, minute=minutes % 60, second=0, microsecond=0
        )
        if now.hour * 60 + now.minute < minutes:
            target = now.replace(hour=minutes // 60, minute=minutes % 60, second=0, microsecond=0)
        first_ms = max(0, int((target - now).total_seconds() * 1000))
        timer = QTimer(self)
        timer.setSingleShot(True)

        def fire() -> None:
            self._fire(kind)
            timer.start(24 * 3600 * 1000)  # next day

        timer.timeout.connect(fire)
        timer.start(first_ms)
        return timer

    def _fire(self, kind: str) -> None:
        if self._tray is None:
            return
        if kind == "evening":
            left = self._vm.today.open_count()
            self._tray.notify(
                "Dayline", f"{left} task(s) still open today." if left else "All done today."
            )
        else:
            due, over = self._vm.due_summary()
            if due == 0 and over == 0:
                self._tray.notify("Dayline", "Nothing due today — all clear.")
            else:
                parts = []
                if due:
                    parts.append(f"{due} due today")
                if over:
                    parts.append(f"{over} overdue")
                self._tray.notify("Dayline", " · ".join(parts))

    # -- slots for QML ---------------------------------------------------------
    @Slot(result=bool)
    def suppressClose(self) -> bool:
        """QML onClosing hook: hide to tray instead of quitting when enabled."""
        if self.should_suppress_close():
            self._window.hide()
            return True
        return False

    @Slot()
    def requestQuit(self) -> None:
        self.quit()

    @Slot()
    def requestQuickAdd(self) -> None:
        self._quick_add()

    @Slot()
    def requestOpenObsidian(self) -> None:
        self._open_obsidian()
