"""SettingsViewModel: exposes persisted Settings to QML with live-apply setters.

Every setter validates/clamps, saves to disk, and emits changed; the App reacts
to ``applied`` to rebuild the store / theme / rollover where relevant.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from dayline.core.clock import logical_date
from dayline.core.obsidian import DailyNotesSettings
from dayline.core.settings import Settings, save, validate


class SettingsViewModel(QObject):
    changed = Signal()
    applied = Signal(str)  # which group changed: vault|rollover|appearance|general|notifications

    def __init__(
        self,
        settings: Settings,
        config_path: Path | None = None,
        on_reload: Callable[[], None] | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._s = settings
        self._config = config_path
        self._on_reload = on_reload
        self._issues: list[str] = []

    # -- generic helpers ------------------------------------------------------
    def _set(self, name: str, value: Any, group: str) -> None:
        setattr(self._s, name, value)
        self._issues = validate(self._s)
        self._persist()
        self.changed.emit()
        self.applied.emit(group)
        if group == "vault" and self._on_reload:
            self._on_reload()

    def _persist(self) -> None:
        if self._config is not None:
            try:
                save(self._config, self._s)
            except OSError:
                self._issues.append("could not write config")

    # -- read properties ------------------------------------------------------
    vaultPath = Property(str, lambda self: self._s.vault_path, notify=changed)
    folder = Property(str, lambda self: self._s.folder, notify=changed)
    dateFormat = Property(str, lambda self: self._s.date_format, notify=changed)
    heading = Property(str, lambda self: self._s.heading, notify=changed)
    lookback = Property(int, lambda self: self._s.lookback, notify=changed)
    dayStart = Property(str, lambda self: self._s.day_start, notify=changed)
    rolloverEnabled = Property(bool, lambda self: self._s.rollover_enabled, notify=changed)
    theme = Property(str, lambda self: self._s.theme, notify=changed)
    sortMode = Property(str, lambda self: self._s.sort_mode, notify=changed)
    weekStart = Property(str, lambda self: self._s.week_start, notify=changed)
    mica = Property(bool, lambda self: self._s.mica, notify=changed)
    thinPaper = Property(bool, lambda self: self._s.thin_paper, notify=changed)
    closeToTray = Property(bool, lambda self: self._s.close_to_tray, notify=changed)
    startHidden = Property(bool, lambda self: self._s.start_hidden, notify=changed)
    autoHide = Property(bool, lambda self: self._s.auto_hide, notify=changed)
    completionSound = Property(bool, lambda self: self._s.completion_sound, notify=changed)
    autostart = Property(bool, lambda self: self._s.autostart, notify=changed)
    hotkey = Property(str, lambda self: self._s.hotkey, notify=changed)
    summonHotkey = Property(str, lambda self: self._s.summon_hotkey, notify=changed)
    quickAddEnabled = Property(bool, lambda self: self._s.quick_add_enabled, notify=changed)
    updateCheckEnabled = Property(bool, lambda self: self._s.update_check_enabled, notify=changed)
    notificationsEnabled = Property(
        bool, lambda self: self._s.notifications_enabled, notify=changed
    )
    morningAt = Property(str, lambda self: self._s.morning_summary_at, notify=changed)
    eveningAt = Property(str, lambda self: self._s.evening_reminder_at, notify=changed)
    issues = Property(list, lambda self: self._issues, notify=changed)
    version = Property(str, lambda self: _version(), notify=changed)

    def dateFormatUnsupported(self) -> bool:
        return bool(DailyNotesSettings(self._s.folder, self._s.date_format).unsupported)

    unsupportedFormat = Property(bool, dateFormatUnsupported, notify=changed)

    # -- write slots ----------------------------------------------------------
    @Slot(str)
    def setVault(self, path: str) -> None:
        self._set("vault_path", path, "vault")

    @Slot(str)
    def setFolder(self, value: str) -> None:
        self._set("folder", value, "vault")

    @Slot(str)
    def setDateFormat(self, value: str) -> None:
        self._set("date_format", value, "vault")

    @Slot(str)
    def setHeading(self, value: str) -> None:
        self._set("heading", value, "vault")

    @Slot(int)
    def setLookback(self, value: int) -> None:
        self._set("lookback", value, "rollover")

    @Slot(str)
    def setDayStart(self, value: str) -> None:
        self._set("day_start", value, "rollover")

    @Slot(bool)
    def setRolloverEnabled(self, value: bool) -> None:
        self._set("rollover_enabled", value, "rollover")

    @Slot(str)
    def setTheme(self, value: str) -> None:
        self._set("theme", value, "appearance")

    @Slot(str)
    def setSortMode(self, value: str) -> None:
        self._set("sort_mode", value, "appearance")

    @Slot(str)
    def setWeekStart(self, value: str) -> None:
        self._set("week_start", value, "appearance")

    @Slot(bool)
    def setMica(self, value: bool) -> None:
        self._set("mica", value, "appearance")

    @Slot(bool)
    def setThinPaper(self, value: bool) -> None:
        self._set("thin_paper", value, "appearance")

    @Slot(bool)
    def setCloseToTray(self, value: bool) -> None:
        self._set("close_to_tray", value, "general")

    @Slot(bool)
    def setStartHidden(self, value: bool) -> None:
        self._set("start_hidden", value, "general")

    @Slot(bool)
    def setCompletionSound(self, value: bool) -> None:
        self._set("completion_sound", value, "general")

    @Slot(bool)
    def setAutostart(self, value: bool) -> None:
        self._set("autostart", value, "general")

    @Slot(str)
    def setHotkey(self, value: str) -> None:
        self._set("hotkey", value, "general")

    @Slot(bool)
    def setQuickAddEnabled(self, value: bool) -> None:
        self._set("quick_add_enabled", value, "general")

    @Slot(bool)
    def setUpdateCheckEnabled(self, value: bool) -> None:
        self._set("update_check_enabled", value, "updates")

    @Slot(bool)
    def setNotificationsEnabled(self, value: bool) -> None:
        self._set("notifications_enabled", value, "notifications")

    # "Daily due reminder" switch in Settings → General: drives the morning
    # scheduler and guarantees a time when switched back on.
    dueReminders = Property(bool, lambda self: self._s.notifications_enabled, notify=changed)

    @Slot(bool)
    def setDueReminders(self, value: bool) -> None:
        if value and not self._s.morning_summary_at:
            self._s.morning_summary_at = "09:00"
        self._set("notifications_enabled", value, "notifications")

    @Slot(bool)
    def setAutoHide(self, value: bool) -> None:
        self._set("auto_hide", value, "general")

    @Slot(str)
    def setMorningAt(self, value: str) -> None:
        self._set("morning_summary_at", value, "notifications")

    @Slot(str)
    def setEveningAt(self, value: str) -> None:
        self._set("evening_reminder_at", value, "notifications")

    @Slot(result=str)
    def todayPreview(self) -> str:
        """Live preview of the resolved note path for the current settings."""
        from datetime import datetime

        from dayline.core.obsidian import note_path

        if not self._s.vault_path:
            return "(no vault selected)"
        dn = DailyNotesSettings(self._s.folder, self._s.date_format)
        if dn.unsupported:
            return "unsupported date format"
        try:
            p = note_path(Path(self._s.vault_path), dn, logical_date(datetime.now(), 0))
            return str(p)
        except Exception as exc:
            return f"error: {exc}"

    @Slot(str, result=bool)
    def importLegacy(self, path: str) -> bool:
        from dayline.core.settings import import_legacy_todo_config

        overrides = import_legacy_todo_config(Path(path))
        if not overrides:
            return False
        for k, v in overrides.items():
            setattr(self._s, k, v)
        self._issues = validate(self._s)
        self._persist()
        self.changed.emit()
        self.applied.emit("vault")
        if self._on_reload:
            self._on_reload()
        return True


def _version() -> str:
    from dayline import __version__

    return __version__
