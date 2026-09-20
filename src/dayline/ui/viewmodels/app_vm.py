"""AppViewModel: shell state, vault wiring, rollover trigger, navigation."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from time import monotonic
from time import time as wall_time
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from dayline.core.clock import detect_wake, logical_date, parse_day_start_minutes
from dayline.core.editor import StaleEditError, TaskEditor
from dayline.core.errors import DaylineError, NoteDecodeError
from dayline.core.model import Priority
from dayline.core.obsidian import (
    DailyNotesSettings,
    find_vaults,
    note_path,
    read_daily_notes,
)
from dayline.core.rollover import rollover
from dayline.core.settings import Settings, save
from dayline.core.store import Store
from dayline.core.watcher import ChangeDetector
from dayline.platform.motion import make_motion_source
from dayline.platform.paths import obsidian_json
from dayline.platform.system_theme import make_theme_source
from dayline.ui.sync import FileSync
from dayline.ui.viewmodels.settings_vm import SettingsViewModel
from dayline.ui.viewmodels.today_vm import TodayViewModel
from dayline.ui.viewmodels.week_vm import WeekViewModel

log = logging.getLogger("dayline.ui.app_vm")

PAGE_TODAY = "today"
_PRIORITY_FROM_LABEL = {"high": Priority.HIGH, "medium": Priority.MEDIUM, "low": Priority.LOW}


class AppViewModel(QObject):
    """Owns settings + store + navigation; exposes only display data to QML."""

    changed = Signal()
    pageChanged = Signal()

    def __init__(
        self,
        settings: Settings,
        *,
        config_path: Path | None = None,
        theme_probe: Callable[[], str] | None = None,
        motion_probe: Callable[[], bool] | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.store: Store | None = None
        self._config_path = config_path
        self._theme_source = make_theme_source(settings.theme, theme_probe)
        self._motion_source = make_motion_source(motion_probe)
        self._page = PAGE_TODAY
        self._error = ""
        self._force_setup = False
        self._quick_add = False
        self._day_start_min = _safe_day_start(settings.day_start)
        self._last_wall: float | None = None
        self._last_mono: float | None = None
        self.today = TodayViewModel(self)
        self.today.prevDayRequested.connect(self.prevDay)
        self.today.nextDayRequested.connect(self.nextDay)
        self.today.goTodayRequested.connect(self.goToday)
        self.today.retryRequested.connect(self.retry)
        self.week = WeekViewModel(self)
        self.week.dayRequested.connect(self._openDayFromWeek)
        self._settings_vm = SettingsViewModel(
            settings, config_path, on_reload=self.start, parent=self
        )
        self._settings_vm.applied.connect(self._on_settings_applied)
        self.editor: TaskEditor | None = None
        self._detector: ChangeDetector | None = None
        self._sync: FileSync | None = None
        self._tick = QTimer(self)
        self._tick.setInterval(30_000)
        self._tick.timeout.connect(self._on_tick)

    # -- properties -----------------------------------------------------------
    def _page_get(self) -> str:
        return self._page

    page = Property(str, _page_get, notify=pageChanged)
    dark = Property(bool, lambda self: self._theme_source() == "dark", notify=changed)
    reduceMotion = Property(bool, lambda self: not self._motion_source(), notify=changed)
    errorText = Property(str, lambda self: self._error, notify=changed)
    vaultReady = Property(
        bool, lambda self: self.store is not None and not self._force_setup, notify=changed
    )
    firstRun = Property(
        bool,
        lambda self: self.store is None and not self.settings.vault_path,
        notify=changed,
    )

    todayVM = Property(QObject, lambda self: self.today, notify=changed)
    weekVM = Property(QObject, lambda self: self.week, notify=changed)
    settingsVM = Property(QObject, lambda self: self._settings_vm, notify=changed)

    @Slot()
    def goWeek(self) -> None:
        self._set_page("week")

    @Slot()
    def goSettings(self) -> None:
        self._set_page("settings")

    @Slot(str)
    def setPage(self, name: str) -> None:
        self._set_page(name)

    @Slot()
    def goSetup(self) -> None:
        """Force the vault chooser (Change vault…) even when a vault is set."""
        self._force_setup = True
        self.changed.emit()

    @Slot()
    def runRolloverNow(self) -> None:
        if self.store is None:
            return
        try:
            res = rollover(self.store, self._logical_today(), self.settings.lookback)
            self.today.set_carried_over(res.moved)
            self._reload()
        except DaylineError as exc:
            self._error = str(exc)
        self.changed.emit()

    # -- window geometry + last page (PRD §4.3) --------------------------------
    geometry = Property(dict, lambda self: self.settings.window, notify=changed)

    @Slot(int, int, int, int)
    def saveGeometry(self, x: int, y: int, w: int, h: int) -> None:
        self.settings.window = {"x": x, "y": y, "width": w, "height": h}
        if self._config_path is not None:
            save(self._config_path, self.settings)

    def _set_page(self, name: str) -> None:
        self._page = name
        self.settings.last_page = name
        if self._config_path is not None:
            save(self._config_path, self.settings)
        if name == "week" and self.store is not None:
            self.week.invalidate()
        self.pageChanged.emit()

    def _openDayFromWeek(self, d: date) -> None:
        self.navigate(d)
        self._set_page(PAGE_TODAY)

    def _on_settings_applied(self, group: str) -> None:
        if group == "appearance":
            self.changed.emit()  # theme/sort/week-start live
            if self.store is not None:
                self.week.bind(
                    self.store,
                    week_start=self.settings.week_start,
                    now_provider=datetime.now,
                )
                self._reload()
        elif group == "rollover":
            self._day_start_min = _safe_day_start(self.settings.day_start)
            if self.settings.rollover_enabled and self.store is not None:
                try:
                    res = rollover(self.store, self._logical_today(), self.settings.lookback)
                    self.today.set_carried_over(res.moved)
                    self._reload()
                except DaylineError as exc:
                    self._error = str(exc)
            self.changed.emit()
        else:
            self.changed.emit()

    @Property(list, notify=changed)
    def detectedVaults(self) -> list[dict[str, Any]]:
        return [
            {"name": v.name, "path": str(v.path), "isDefault": v.is_open}
            for v in find_vaults(obsidian_json())
        ]

    # -- lifecycle -------------------------------------------------------------
    def start(self) -> None:
        """Build the store from settings, run startup rollover, load logical today."""
        self._tick.stop()
        self._teardown_sync()
        self._error = ""
        self.store = self._make_store()
        if self.store is not None:
            self._force_setup = False
            self._page = PAGE_TODAY
            self.pageChanged.emit()
        self.changed.emit()
        if self.store is None:
            return
        self.editor = TaskEditor(self.store)
        self._detector = ChangeDetector(self.store)
        self._sync = FileSync(self._detector)
        self._sync.dayChanged.connect(self._on_external_change)
        s = self.settings
        today = self._logical_today()
        if s.rollover_enabled:
            try:
                res = rollover(self.store, today, s.lookback)
                self.today.set_carried_over(res.moved)
            except DaylineError as exc:
                log.warning("startup rollover failed: %s", exc)
                self._error = str(exc)
                self.changed.emit()
        self.navigate(today)
        self._start_sync(today)
        self.week.bind(self.store, week_start=s.week_start, now_provider=datetime.now)
        if s.last_page in (PAGE_TODAY, "week", "settings"):
            self._page = s.last_page
        self._tick.start()

    def _teardown_sync(self) -> None:
        if self._sync is not None:
            self._sync.stop()
            self._sync.deleteLater()
            self._sync = None
        self._detector = None
        self.editor = None

    def _start_sync(self, today: date) -> None:
        if self.store is None or self._sync is None:
            return
        folder = self.store.path_for(today).parent
        self._sync.watch(folder, self._watched_dates(today))
        self._sync.start()

    def _watched_dates(self, today: date) -> list[date]:
        """Notes we care about: the viewed day + the rollover lookback window."""
        span = range(-1, min(self.settings.lookback, 90) + 1)
        return [today - timedelta(days=n) for n in span]

    def _make_store(self) -> Store | None:
        s = self.settings
        dn = DailyNotesSettings(s.folder, s.date_format)
        base = Path(s.vault_path) if s.vault_path else None
        if base is None or dn.unsupported or not base.is_dir():
            return None
        heading = s.heading

        def path_for(d: date) -> Path:
            return note_path(base, dn, d)

        return Store(path_for, heading=heading)

    def _logical_today(self) -> date:
        return logical_date(datetime.now(), self._day_start_min)

    # -- slots (QML) ------------------------------------------------------------
    @Slot()
    def nextDay(self) -> None:
        self.navigate(self.today.current_date + timedelta(days=1))

    @Slot()
    def prevDay(self) -> None:
        self.navigate(self.today.current_date - timedelta(days=1))

    @Slot()
    def goToday(self) -> None:
        self.navigate(self._logical_today())

    @Slot(str)
    def selectVault(self, path: str) -> None:
        """Apply a vault choice from the setup/recovery panel and start."""
        p = Path(path)
        if not p.is_dir():
            self._error = f"Folder not found: {path}"
            self.changed.emit()
            return
        self.settings.vault_path = str(p)
        dn = read_daily_notes(p)
        self.settings.folder = dn.folder
        self.settings.date_format = dn.date_format if not dn.unsupported else "YYYY-MM-DD"
        if self._config_path is not None:
            save(self._config_path, self.settings)
        self.start()

    @Slot()
    def retry(self) -> None:
        self.start()

    # -- loading with skeleton --------------------------------------------------
    def navigate(self, d: date) -> None:
        self.today.set_date(d)
        if self.store is None:
            self.today.set_loading(False)
            return
        QTimer.singleShot(0, lambda: self._load_day(d))

    def _load_day(self, d: date) -> None:
        if self.store is None or d != self.today.current_date:
            return
        try:
            doc = self.store.read_doc(d)
        except NoteDecodeError:
            self.today.set_error("This note is not valid UTF-8 text — open it in Obsidian.")
            return
        except OSError as exc:
            self.today.set_error(f"Could not read the note: {exc}")
            return
        self.today.apply_doc(doc, today=self._logical_today())

    # -- clock: midnight rollover + wake detection (§5.9) --------------------------
    def _on_tick(self) -> None:
        wall, mono = wall_time(), monotonic()
        woke = (
            self._last_wall is not None
            and self._last_mono is not None
            and detect_wake(self._last_wall, self._last_mono, wall, mono)
        )
        self._last_wall, self._last_mono = wall, mono
        today = self._logical_today()
        if not (woke or today != self.today.current_date):
            return
        if woke and self.settings.rollover_enabled and self.store is not None:
            try:
                res = rollover(self.store, today, self.settings.lookback)
                self.today.set_carried_over(res.moved)
            except DaylineError as exc:
                log.warning("wake rollover failed: %s", exc)
        if self.today.is_today or woke:
            self.navigate(today)

    # -- mutation actions (QML) -------------------------------------------------
    canUndo = Property(
        bool, lambda self: bool(self.editor and self.editor.undo_stack.can_undo), notify=changed
    )
    canRedo = Property(
        bool, lambda self: bool(self.editor and self.editor.undo_stack.can_redo), notify=changed
    )

    def _act(self, label: str, run: Callable[[], object]) -> None:
        if self.editor is None:
            return
        try:
            run()
        except StaleEditError:
            log.info("%s hit a stale task; reloading", label)
        except DaylineError as exc:
            self._error = str(exc)
        self._reload()
        self.changed.emit()

    @Slot(str)
    def addTask(self, text: str) -> None:
        d = self.today.current_date
        self._act("add", lambda: self.editor and self.editor.add(d, text))

    @Slot(int)
    def toggleTask(self, key: int) -> None:
        d = self.today.current_date
        self._act("toggle", lambda: self.editor and self.editor.toggle(d, key))

    @Slot(int, str)
    def editTask(self, key: int, text: str) -> None:
        d = self.today.current_date
        self._act("edit", lambda: self.editor and self.editor.edit_text(d, key, text))

    @Slot(int, str)
    def setPriority(self, key: int, level: str) -> None:
        d = self.today.current_date
        prio = _PRIORITY_FROM_LABEL.get(level.lower())
        self._act("priority", lambda: self.editor and self.editor.set_priority(d, key, prio))

    @Slot(int)
    def deleteTask(self, key: int) -> None:
        d = self.today.current_date
        self._act("delete", lambda: self.editor and self.editor.delete(d, key))

    @Slot(int, int)
    def moveTask(self, key: int, before_key: int) -> None:
        d = self.today.current_date
        before = None if before_key < 0 else before_key
        self._act("move", lambda: self.editor and self.editor.move(d, key, before))

    @Slot()
    def undo(self) -> None:
        if self.editor:
            self.editor.undo()
            self._reload()
            self.changed.emit()

    @Slot()
    def redo(self) -> None:
        if self.editor:
            self.editor.redo()
            self._reload()
            self.changed.emit()

    # -- quick-add popup (FR-P6) ------------------------------------------------
    quickAddVisible = Property(bool, lambda self: self._quick_add, notify=changed)

    @Slot()
    def showQuickAdd(self) -> None:
        self._quick_add = True
        self.changed.emit()

    @Slot()
    def hideQuickAdd(self) -> None:
        self._quick_add = False
        self.changed.emit()

    def obsidian_uri(self) -> str:
        """obsidian://open URI for the logical-today note (FR-O6)."""
        from dayline.core.obsidian import note_rel_no_ext, open_uri

        dn = DailyNotesSettings(self.settings.folder, self.settings.date_format)
        if dn.unsupported or not self.settings.vault_path:
            return ""
        rel = note_rel_no_ext(dn, self._logical_today())
        return open_uri(Path(self.settings.vault_path).name, rel)

    @Slot()
    def openInObsidian(self) -> None:
        uri = self.obsidian_uri()
        if not uri:
            return
        import sys

        if sys.platform == "win32":
            import os

            os.startfile(uri)
        else:  # pragma: no cover
            import subprocess

            subprocess.run(["xdg-open", uri], check=False)

    def _reload(self) -> None:
        self._load_day(self.today.current_date)
        if self.store is not None:
            self.week.invalidate()

    def _on_external_change(self, d: date) -> None:
        if d == self.today.current_date:
            self._reload()


def _safe_day_start(text: str) -> int:
    try:
        return min(parse_day_start_minutes(text), 6 * 60)
    except ValueError:
        return 0
