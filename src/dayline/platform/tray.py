"""System tray + notifications (FR-P1, FR-P2, FR-P7) via QSystemTrayIcon.

Left-click toggles the window; the menu offers Quick add · Open today in
Obsidian · Show · Quit. Notifications use showMessage (native toasts are a
post-v1 upgrade). All UI callbacks are injected so the wiring is testable.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class Tray:
    def __init__(
        self,
        icon: QIcon,
        *,
        on_activate: Callable[[], None],
        on_quick_add: Callable[[], None],
        on_open_obsidian: Callable[[], None],
        on_quit: Callable[[], None],
        parent: Any = None,
    ) -> None:
        self._icon = icon
        self._on_activate = on_activate
        self._on_quick_add = on_quick_add
        self._on_open_obsidian = on_open_obsidian
        self._on_quit = on_quit
        self._tray: QSystemTrayIcon | None = None
        self._parent = parent

    def available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show(self, tooltip: str = "Dayline") -> bool:
        self._tray = QSystemTrayIcon(self._icon, self._parent)
        self._tray.setToolTip(tooltip)
        menu = QMenu()
        menu.addAction("Quick add", self._on_quick_add)
        menu.addAction("Open today in Obsidian", self._on_open_obsidian)
        menu.addSeparator()
        menu.addAction("Show Dayline", self._on_activate)
        menu.addAction("Quit", self._on_quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.show()
        return True

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # left click
            self._on_activate()

    def hide(self) -> None:
        if self._tray is not None:
            self._tray.hide()
            self._tray = None

    def notify(self, title: str, message: str, ms: int = 6000) -> None:
        if self._tray is not None:
            self._tray.showMessage(title, message, self._icon, ms)
