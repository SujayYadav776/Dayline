"""ChangeDetector + FileSync tests (FR-O5, §5.8): external detection + self-write suppression."""

from __future__ import annotations

import time
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from dayline.core.store import Store
from dayline.core.watcher import ChangeDetector
from dayline.ui.sync import FileSync

D = date(2026, 9, 19)


@pytest.fixture()
def store(tmp_path: Path) -> Store:
    def path_for(d: date) -> Path:
        return tmp_path / f"{d.isoformat()}.md"

    path_for(D).parent.mkdir(exist_ok=True)
    return Store(path_for, sleep=lambda _s: None)


def test_detects_external_change(store: Store) -> None:
    store.mutate(D, lambda doc: doc.add_task("seed") and True)
    det = ChangeDetector(store)
    det.prime(D)
    assert det.changed_days([D]) == []  # nothing changed yet
    # external write (not via store)
    p = store.path_for(D)
    time.sleep(0.01)
    p.write_text("## To-Do\n- [ ] seed\n- [ ] from obsidian\n", encoding="utf-8")
    assert det.changed_days([D]) == [D]
    assert det.changed_days([D]) == []  # reported once


def test_suppresses_own_write(store: Store) -> None:
    det = ChangeDetector(store)
    store.mutate(D, lambda doc: doc.add_task("mine") and True)  # records own-write
    det.prime(D)  # prime AFTER write so last-state matches, but simulate pre-state:
    # Force last-state to the pre-write value to prove is_own_write gates it:
    det._last[store.path_for(D)] = (0, 0)
    assert det.changed_days([D]) == []  # differs from last, but it's our own write → suppressed


def test_missing_file_not_reported(store: Store) -> None:
    det = ChangeDetector(store)
    det.prime(D)  # no file → nothing primed
    assert det.changed_days([D]) == []


def test_filesync_emits_on_external_change(store: Store, tmp_path: Path, qtbot: Any) -> None:
    store.mutate(D, lambda doc: doc.add_task("a") and True)
    det = ChangeDetector(store)
    sync = FileSync(det, debounce_ms=20, poll_ms=50)
    folder = store.path_for(D).parent
    sync.watch(folder, [D])
    with qtbot.waitSignal(sync.dayChanged, timeout=3000) as blocker:
        time.sleep(0.02)
        store.path_for(D).write_text("## To-Do\n- [ ] a\n- [ ] external\n", encoding="utf-8")
    assert blocker.args and blocker.args[0] == D
    sync.stop()
