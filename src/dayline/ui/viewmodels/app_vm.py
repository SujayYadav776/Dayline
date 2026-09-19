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
from dayline.core.errors import DaylineError, NoteDecodeError
from dayline.core.obsidian import (
    DailyNotesSettings,
    find_vaults,
    note_path,
    read_daily_notes,
)
from dayline.core.rollover import rollover
from dayline.core.settings import Settings, save
from dayline.core.store import Store
from dayline.platform.paths import obsidian_json
from dayline.platform.system_theme import make_theme_source
from dayline.ui.viewmodels.today_vm import TodayViewModel

log = logging.getLogger("dayline.ui.app_vm")

PAGE_TODAY = "today"


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
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.store: Store | None = None
        self._config_path = config_path
        self._theme_source = make_theme_source(settings.theme, theme_probe)
        self._page = PAGE_TODAY
        self._error = ""
        self._day_start_min = _safe_day_start(settings.day_start)
        self._last_wall: float | None = None
        self._last_mono: float | None = None
        self.today = TodayViewModel(self)
        self.today.prevDayRequested.connect(self.prevDay)
        self.today.nextDayRequested.connect(self.nextDay)
        self.today.goTodayRequested.connect(self.goToday)
        self.today.retryRequested.connect(self.retry)
        self._tick = QTimer(self)
        self._tick.setInterval(30_000)
        self._tick.timeout.connect(self._on_tick)

    # -- properties -----------------------------------------------------------
    def _page_get(self) -> str:
        return self._page

    page = Property(str, _page_get, notify=pageChanged)
    dark = Property(bool, lambda self: self._theme_source() == "dark", notify=changed)
    errorText = Property(str, lambda self: self._error, notify=changed)
    vaultReady = Property(bool, lambda self: self.store is not None, notify=changed)

    todayVM = Property(QObject, lambda self: self.today, notify=changed)

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
        self._error = ""
        self.store = self._make_store()
        self.changed.emit()
        if self.store is None:
            return
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
        self._tick.start()

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


def _safe_day_start(text: str) -> int:
    try:
        return min(parse_day_start_minutes(text), 6 * 60)
    except ValueError:
        return 0
