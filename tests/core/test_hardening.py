"""M6 hardening: performance targets (§1.6), log privacy (§4.4), crash hook (§6.5)."""

from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from dayline.core.model import NoteDoc
from dayline.core.stats import StatsService
from dayline.core.store import Store
from dayline.ui import crash

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "vaults"
TODAY = date.today()


def _vault(tmp_path: Path) -> Store:
    src = FIXTURES / "default" / "Daily" / "2026-09-19.md"
    body = src.read_text("utf-8")

    def path_for(d: date) -> Path:
        return tmp_path / f"{d.isoformat()}.md"

    for i in range(30):
        path_for(TODAY - timedelta(days=i)).write_text(body, "utf-8")
    return Store(path_for, sleep=lambda _s: None)


def test_week_stats_under_200ms_for_30_notes(tmp_path: Path) -> None:
    store = _vault(tmp_path)
    svc = StatsService(store)
    dates = [TODAY - timedelta(days=i) for i in range(7)]
    start = time.perf_counter()
    for d in dates:
        svc.day(d)
    first_ms = (time.perf_counter() - start) * 1000
    # warm cache second pass must be fast
    start = time.perf_counter()
    for d in dates:
        svc.day(d)
    warm_ms = (time.perf_counter() - start) * 1000
    assert first_ms < 200, f"cold week stats {first_ms:.1f}ms"
    assert warm_ms < 20, f"warm week stats {warm_ms:.1f}ms"


def test_500_task_day_add_and_parse(tmp_path: Path) -> None:
    def path_for(d: date) -> Path:
        return tmp_path / f"{d.isoformat()}.md"

    store = Store(path_for, sleep=lambda _s: None)
    start = time.perf_counter()

    def fill(doc: NoteDoc) -> bool:
        for i in range(500):
            doc.add_task(f"task number {i}")
        return True

    store.mutate(TODAY, fill)
    add_ms = (time.perf_counter() - start) * 1000
    doc = store.read_doc(TODAY)
    assert len(doc.tasks) == 500
    assert add_ms < 2000, f"500-task write {add_ms:.0f}ms"


def test_info_logs_never_contain_task_text(tmp_path: Path, caplog: Any) -> None:
    secret = "buy milk ⏫ personal-secret-task"

    def path_for(d: date) -> Path:
        return tmp_path / f"{d.isoformat()}.md"

    store = Store(path_for, sleep=lambda _s: None)
    with caplog.at_level(logging.INFO, logger="dayline"):
        store.mutate(TODAY, lambda doc: doc.add_task(secret) and True)
        store.read_doc(TODAY)
    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "personal-secret-task" not in joined
    assert "buy milk" not in joined


def test_crash_hook_installed_and_logs(tmp_path: Path, caplog: Any) -> None:
    import sys

    prev = sys.excepthook
    try:
        crash.install(tmp_path / "logs")
        assert sys.excepthook is not prev
        # a raised exception routed through the hook must be logged, not printed
        try:
            raise ValueError("boom")
        except ValueError:
            exc_type, exc, tb = sys.exc_info()
            assert exc_type is not None and exc is not None
            with caplog.at_level(logging.CRITICAL, logger="dayline.crash"):
                sys.excepthook(exc_type, exc, tb)
        assert any("boom" in r.getMessage() or "uncaught" in r.getMessage() for r in caplog.records)
    finally:
        sys.excepthook = prev


def test_interactive_components_declare_accessibility() -> None:
    """§4.7: every interactive QML component exposes Accessible.name/role."""
    qml = Path(__file__).resolve().parent.parent.parent / "src" / "dayline" / "ui" / "qml"
    interactive = [
        "TaskRow.qml",
        "SectionHeader.qml",
        "WeekPage.qml",
        "TodayPage.qml",
        "SettingsPage.qml",
        "Onboarding.qml",
        "ActionButton.qml",
    ]
    for name in interactive:
        text = (qml / "Dayline" / name).read_text("utf-8")
        assert "Accessible." in text, f"{name} missing Accessible.*"
