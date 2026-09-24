"""AppViewModel: shell state, vault wiring, rollover trigger, navigation."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from time import monotonic
from time import time as wall_time
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from dayline.core import quickadd, recur
from dayline.core.clock import detect_wake, logical_date, parse_day_start_minutes
from dayline.core.editor import StaleEditError, TaskEditor
from dayline.core.errors import DaylineError, NoteDecodeError
from dayline.core.model import Priority, StatusKind
from dayline.core.obsidian import (
    DEFAULT_FOLDER,
    DEFAULT_FORMAT,
    DailyNotesSettings,
    find_vaults,
    jump_uri,
    note_path,
    note_rel_no_ext,
    open_uri,
    read_daily_notes,
)
from dayline.core.rollover import rollover
from dayline.core.settings import Settings, save
from dayline.core.store import Store
from dayline.core.updater import UpdateInfo, should_check
from dayline.core.watcher import ChangeDetector
from dayline.platform.dwm import supports_system_backdrop
from dayline.platform.motion import make_motion_source
from dayline.platform.paths import local_appdata_dir, obsidian_json
from dayline.platform.system_theme import make_theme_source
from dayline.platform.update_net import download, github_latest_url, http_get
from dayline.ui.sync import FileSync
from dayline.ui.update_service import UpdateService
from dayline.ui.viewmodels.settings_vm import SettingsViewModel
from dayline.ui.viewmodels.today_vm import TodayViewModel
from dayline.ui.viewmodels.week_vm import WeekViewModel

log = logging.getLogger("dayline.ui.app_vm")

PAGE_TODAY = "today"
_PRIORITY_FROM_LABEL = {"high": Priority.HIGH, "medium": Priority.MEDIUM, "low": Priority.LOW}
# Update discovery source. Public repo → GitHub's releases/latest API needs no
# token; the request is opt-in (Settings toggle) and the https/host guard in
# platform/update_net.py constrains where it can fetch a binary from.
UPDATE_REPO = "SujayYadav776/Dayline"


def _default_uri_open(uri: str) -> None:
    """Hand an obsidian:// URI to the OS (tests inject uri_open instead)."""
    import os
    import subprocess
    import sys

    if sys.platform == "win32":
        os.startfile(uri)
    else:  # pragma: no cover
        subprocess.run(["xdg-open", uri], check=False)


def _default_file_open(path: str) -> None:
    """Open a local file with the OS default handler (folder mode replaces the
    Obsidian jump with this; tests inject file_open instead)."""
    import os
    import subprocess
    import sys

    if sys.platform == "win32":
        os.startfile(path)
    else:  # pragma: no cover
        subprocess.run(["xdg-open", path], check=False)


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
        mica_probe: Callable[[], bool] | None = None,
        update_fetcher: Callable[[str], bytes] | None = None,
        update_downloader: Callable[[str, Path], Path] | None = None,
        sound_play: Callable[[], None] | None = None,
        uri_open: Callable[[str], None] | None = None,
        file_open: Callable[[str], None] | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.store: Store | None = None
        self._config_path = config_path
        self._sound_play = sound_play or (lambda: None)
        self._uri_open = uri_open or _default_uri_open
        self._file_open = file_open or _default_file_open
        self._theme_source = make_theme_source(settings.theme, theme_probe)
        self._motion_source = make_motion_source(motion_probe)
        self._mica_source: Callable[[], bool] = mica_probe or supports_system_backdrop
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
        # ---- updates (opt-in; default off) ----------------------------------
        self._updater = UpdateService(
            current_version=_version_str(),
            url=github_latest_url(UPDATE_REPO),
            fetcher=update_fetcher or http_get,
            downloader=update_downloader or download,
            parent=self,
        )
        self._updater.resultReady.connect(self._on_update_result)
        self._updater.failed.connect(self._on_update_failed)
        self._updater.downloadReady.connect(self._on_update_downloaded)
        self._update_info: UpdateInfo | None = None
        self._update_status = ""
        self._update_user_initiated = False
        # Injected by app.py: tray.notify, installer launch, quit (None = no-op).
        self._update_notify: Callable[[str, str], None] | None = None
        self._installer_launcher: Callable[[str], None] | None = None
        self._quit_app: Callable[[], None] | None = None
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
    # Mica is on only when the user enabled it AND the OS supports it (Win11).
    micaActive = Property(
        bool, lambda self: bool(self.settings.mica and self._mica_source()), notify=changed
    )
    # Pure OS capability (drives whether the Settings toggle is shown).
    micaSupported = Property(bool, lambda self: bool(self._mica_source()), notify=changed)
    # Thin paper: Main.qml drops the opaque window colour and paints the paper
    # at 92% so the Mica blur peeks through — only meaningful while Mica is live.
    thinPaper = Property(bool, lambda self: bool(self.settings.thin_paper), notify=changed)
    # "folder" mode: any plain folder stores the daily notes; Obsidian-specific
    # affordances (deep-link jumps) swap to opening the file with the OS default.
    folderMode = Property(bool, lambda self: self.settings.vault_mode == "folder", notify=changed)
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
        elif group == "updates":
            # Turning the toggle on gives immediate feedback; turning it off
            # clears any shown state.
            if self.settings.update_check_enabled:
                self.checkForUpdates()
            else:
                self._update_info = None
                self._update_status = ""
                self.changed.emit()
        else:
            self.changed.emit()

    # -- updates (opt-in) -----------------------------------------------------
    currentVersion = Property(str, lambda self: _version_str(), notify=changed)
    updateStatus = Property(str, lambda self: self._update_status, notify=changed)
    updateChecking = Property(bool, lambda self: self._updater.busy, notify=changed)
    updateAvailable = Property(bool, lambda self: self._update_info is not None, notify=changed)
    updateLatest = Property(
        str, lambda self: self._update_info.version if self._update_info else "", notify=changed
    )
    updatePageUrl = Property(
        str, lambda self: self._update_info.page_url if self._update_info else "", notify=changed
    )
    updateDownloadUrl = Property(
        str,
        lambda self: self._update_info.download_url if self._update_info else "",
        notify=changed,
    )

    def set_update_hooks(
        self,
        notify: Callable[[str, str], None] | None = None,
        launcher: Callable[[str], None] | None = None,
        quit_app: Callable[[], None] | None = None,
    ) -> None:
        """Inject tray-notify / installer-launch / quit from the platform layer."""
        self._update_notify = notify or self._update_notify
        self._installer_launcher = launcher or self._installer_launcher
        self._quit_app = quit_app or self._quit_app

    @Slot()
    def checkForUpdates(self) -> None:
        self._update_user_initiated = True
        self._update_status = "Checking for updates…"
        self.changed.emit()
        self._updater.check()

    def startup_update_check(self, now: datetime | None = None) -> None:
        """Automatic once-a-day check when the user opted in (silent unless found)."""
        s = self.settings
        if not s.update_check_enabled:
            return
        if not should_check(s.update_last_check, now or datetime.now()):
            return
        s.update_last_check = (now or datetime.now()).isoformat(timespec="seconds")
        self._persist_settings()
        self._update_user_initiated = False
        self._updater.check()

    @Slot()
    def installUpdate(self) -> None:
        info = self._update_info
        if not info or not info.download_url:
            return
        dest = local_appdata_dir() / "Dayline" / "update" / f"Dayline-Setup-{info.version}.exe"
        self._update_status = "Downloading update…"
        self.changed.emit()
        self._updater.download(info.download_url, str(dest))

    def _on_update_result(self, info: UpdateInfo | None) -> None:
        self._update_info = info
        if info is not None:
            self._update_status = f"Dayline {info.version} is available"
            if self._update_notify:
                self._update_notify("Dayline", f"Update {info.version} is available.")
        elif self._update_user_initiated:
            self._update_status = f"You're up to date (v{_version_str()})"
        else:
            self._update_status = ""
        self._update_user_initiated = False
        self.changed.emit()

    def _on_update_failed(self, error: str) -> None:
        if self._update_user_initiated:
            self._update_status = f"Couldn't check for updates ({error[:60]})"
        else:
            self._update_status = ""
        self._update_user_initiated = False
        log.info("update check failed: %s", error)
        self.changed.emit()

    def _on_update_downloaded(self, path: str) -> None:
        self._update_status = "Installing update…"
        self.changed.emit()
        if self._update_notify:
            self._update_notify("Dayline", "Installing update…")
        if self._installer_launcher:
            self._installer_launcher(path)
        if self._quit_app:
            self._quit_app()

    def _persist_settings(self) -> None:
        if self._config_path is None:
            return
        try:
            save(self._config_path, self.settings)
        except OSError:
            log.warning("could not persist update settings", exc_info=True)

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
        self.settings.vault_mode = "obsidian"
        self.settings.vault_path = str(p)
        dn = read_daily_notes(p)
        self.settings.folder = dn.folder
        self.settings.date_format = dn.date_format if not dn.unsupported else "YYYY-MM-DD"
        if self._config_path is not None:
            save(self._config_path, self.settings)
        self.start()

    @Slot(str)
    def selectFolder(self, path: str) -> None:
        """Skip Obsidian entirely: store the daily notes in any plain folder
        with Dayline's own defaults (Daily/YYYY-MM-DD.md)."""
        p = Path(path)
        if not p.is_dir():
            self._error = f"Folder not found: {path}"
            self.changed.emit()
            return
        self.settings.vault_mode = "folder"
        self.settings.vault_path = str(p)
        self.settings.folder = DEFAULT_FOLDER
        self.settings.date_format = DEFAULT_FORMAT
        if self._config_path is not None:
            save(self._config_path, self.settings)
        self.start()

    @Slot()
    def retry(self) -> None:
        self.start()

    # -- loading with skeleton --------------------------------------------------
    def navigate(self, d: date) -> None:
        self.today.set_date(d)
        self.week.set_anchor(d)
        if self.store is None:
            self.today.set_loading(False)
            return
        QTimer.singleShot(0, lambda: self._load_day(d))

    @Slot(str)
    def selectDay(self, date_str: str) -> None:
        """Bottom calendar strip: open the tapped day (stays on Today)."""
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            return
        self.navigate(d)
        self._set_page(PAGE_TODAY)

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
        body, rule = quickadd.extract_recurrence(text)
        body, due = quickadd.parse(body, d)
        if rule and due is None:
            due = recur.next_occurrence(rule, d)  # first instance gets a real date
        if due is not None and body:
            body = _insert_due(body, due)
        if rule and body:
            body = _insert_recurrence(body, rule)
        self._act("add", lambda: self.editor and self.editor.add(d, body))

    @Slot(int)
    def toggleTask(self, key: int) -> None:
        d = self.today.current_date
        was_open = self.today.is_open(key)
        self._act("toggle", lambda: self.editor and self.editor.toggle(d, key))
        if was_open and self.settings.completion_sound:
            self._sound_play()

    @Slot(int, str)
    def rescheduleTask(self, key: int, date_str: str) -> None:
        """Drag-to-reschedule: move a task to another day, then show that day."""
        try:
            target = date.fromisoformat(date_str)
        except ValueError:
            return
        src = self.today.current_date
        if src == target:
            return
        self._act("reschedule", lambda: self.editor and self.editor.move_to_day(src, key, target))
        self.navigate(target)

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

    # panel mode: Main.qml hides the window on focus loss when this is on
    autoHide = Property(bool, lambda self: self.settings.auto_hide, notify=changed)

    def due_summary(self) -> tuple[int, int]:
        """(due today, overdue) counts of OPEN tasks in today's note — the
        text source for the morning reminder toast. Tasks without a 📅 date
        count as due today (they live in today's note)."""
        if self.store is None:
            return 0, 0
        today = self._logical_today()
        try:
            doc = self.store.read_doc(today)
        except (OSError, DaylineError):
            return 0, 0
        due = over = 0
        for t in doc.tasks:
            if t.kind is not StatusKind.OPEN:
                continue
            d = recur.due_of(t.body)
            if d is None or d == today:
                due += 1
            elif d < today:
                over += 1
        return due, over

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
        dn = DailyNotesSettings(self.settings.folder, self.settings.date_format)
        if dn.unsupported or not self.settings.vault_path:
            return ""
        rel = note_rel_no_ext(dn, self._logical_today())
        return open_uri(Path(self.settings.vault_path).name, rel)

    @Slot()
    def openInObsidian(self) -> None:
        if self.settings.vault_mode == "folder" and self.store is not None:
            self._file_open(str(self.store.path_for(self.today.current_date)))
            return
        uri = self.obsidian_uri()
        if uri:
            self._uri_open(uri)

    @Slot(int)
    def openTaskInObsidian(self, key: int) -> None:
        """Click-a-task → jump to its line in Obsidian: block anchor if the
        line has a ^id, else a phrase search restricted to that day's note.
        In folder mode there is no Obsidian, so the day's file opens with the
        OS default handler instead."""
        if self.settings.vault_mode == "folder" and self.store is not None:
            self._file_open(str(self.store.path_for(self.today.current_date)))
            return
        dn = DailyNotesSettings(self.settings.folder, self.settings.date_format)
        if dn.unsupported or not self.settings.vault_path or self.store is None:
            return
        d = self.today.current_date
        try:
            doc = self.store.read_doc(d)
        except (OSError, DaylineError, NoteDecodeError):
            return
        rel = note_rel_no_ext(dn, d)
        vault_name = Path(self.settings.vault_path).name
        task = next((t for t in doc.tasks if t.line_no == key), None)
        if task is None:
            self._uri_open(open_uri(vault_name, rel))
            return
        self._uri_open(jump_uri(vault_name, rel, task.render(), task.description))

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


_BANG_TAIL = re.compile(r"(!{1,3})\s*$")


def _insert_recurrence(body: str, rule: str) -> str:
    """Append '🔁 <rule>' before any trailing priority bangs."""
    token = f"🔁 {rule}"
    m = _BANG_TAIL.search(body)
    if m:
        head = body[: m.start()].rstrip()
        return f"{head} {token} {m.group(1)}"
    return f"{body.rstrip()} {token}" if body.strip() else token


def _insert_due(body: str, due: date) -> str:
    """Append '📅 YYYY-MM-DD' keeping trailing !/!!/!!! bangs last."""
    token = f"📅 {due.isoformat()}"
    m = _BANG_TAIL.search(body)
    if m:
        return f"{body[: m.start()].rstrip()} {token} {m.group(1)}"
    return f"{body} {token}"


def _version_str() -> str:
    from dayline import __version__

    return __version__
