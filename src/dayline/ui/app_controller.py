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
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._window = window
        self._vm = vm
        self._tray = tray
        self._hotkey = hotkey
        self._autostart = autostart
        self._quick_add = quick_add
        self._open_obsidian = open_obsidian
        self._quit_app = quit_app
        self._quitting = False
        self._native_filter: Any = None
        self._hotkey_ok = False
        self._notifiers: list[QTimer] = []

    # -- tray / close-to-tray --------------------------------------------------
    def install_tray(self) -> None:
        if self._tray is None or not self._tray.available():
            return
        self._tray.show(
            tooltip="Dayline",
        )

    def toggle_window(self) -> None:
        if self._window.isVisible() and self._window.active:
            self._window.hide()
        else:
            self._show_and_raise()

    def _show_and_raise(self) -> None:
        self._window.show()
        try:
            self._window.raise_()
            self._window.requestActivate()
        except AttributeError:  # pragma: no cover - depends on backend
            pass

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
        self._quit_app()

    # -- dark title bar --------------------------------------------------------
    def apply_titlebar_theme(self) -> None:
        from dayline.platform.dwm import set_dark_titlebar

        try:
            hwnd = int(self._window.winId())
        except (AttributeError, TypeError):
            return
        set_dark_titlebar(hwnd, bool(self._vm.dark))

    # -- global hotkey ---------------------------------------------------------
    def bind_hotkey(self) -> bool:
        if self._hotkey is None:
            return False
        try:
            self._hotkey_ok = self._hotkey.bind(self._vm.settings.hotkey, self._quick_add)
        except HotkeyError as exc:
            log.warning("hotkey bind failed: %s", exc)
            self._hotkey_ok = False
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
        timer.timeout.connect(lambda: self._fire(kind))
        timer.setSingleShot(True)
        timer.start(first_ms)
        # reschedule daily after first fire
        timer.timeout.connect(lambda: timer.start(24 * 3600 * 1000))
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
            self._tray.notify("Dayline", "Good morning — plan your day.")

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
