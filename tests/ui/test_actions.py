"""M3 end-to-end VM actions: mutate the vault through the viewmodel, verify the
note on disk updates and the model reloads — and that our own writes do not
trigger a spurious external-change reload (self-write suppression)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "vaults"
TODAY = date.today()


@pytest.fixture()
def vm(tmp_path: Path, qtbot: Any) -> tuple[Any, Any, Path]:
    import shutil

    from dayline.core.settings import Settings
    from dayline.ui.viewmodels.app_vm import AppViewModel

    vault = tmp_path / "vault"
    shutil.copytree(FIXTURES / "default", vault)
    (vault / "Daily" / (TODAY.isoformat() + ".md")).write_text(
        (vault / "Daily" / "2026-09-19.md").read_text("utf-8"), "utf-8"
    )
    v = AppViewModel(Settings(vault_path=str(vault)), theme_probe=lambda: "light")
    anyv: Any = v
    anyv.start()
    qtbot.waitUntil(lambda: not anyv.today._loading, timeout=2000)
    return v, anyv, vault


def _note(vault: Path) -> str:
    return (vault / "Daily" / (TODAY.isoformat() + ".md")).read_text("utf-8")


def test_add_task_updates_disk_and_model(vm: Any, qtbot: Any) -> None:
    _v, anyv, vault = vm
    before = anyv.today.todoCount
    anyv.addTask("Buy stamps !!")
    qtbot.wait(50)
    assert "Buy stamps 🔼" in _note(vault)
    assert anyv.today.todoCount == before + 1


def test_toggle_and_undo(vm: Any, qtbot: Any) -> None:
    _v, anyv, _vault = vm
    key = anyv.today.todoList[0]["taskKey"]
    anyv.toggleTask(key)
    qtbot.wait(50)
    assert anyv.today.doneCount == 2  # Email was done; toggled one more
    anyv.undo()
    qtbot.wait(50)
    assert anyv.today.doneCount == 1
    anyv.redo()
    qtbot.wait(50)
    assert anyv.today.doneCount == 2


def test_priority_and_edit(vm: Any, qtbot: Any) -> None:
    _v, anyv, vault = vm
    anyv.addTask("Plain thing")
    qtbot.wait(50)
    key = next(t["taskKey"] for t in anyv.today.todoList if t["description"] == "Plain thing")
    anyv.setPriority(key, "high")
    qtbot.wait(50)
    assert "Plain thing ⏫" in _note(vault)
    anyv.editTask(key, "Renamed thing")
    qtbot.wait(50)
    assert "Renamed thing ⏫" in _note(vault)  # priority preserved on edit


def test_delete_and_no_self_reload_loop(vm: Any, qtbot: Any) -> None:
    """After our own mutation, the watcher must NOT report an external change."""
    _v, anyv, vault = vm
    key = anyv.today.todoList[0]["taskKey"]
    desc = anyv.today.todoList[0]["description"]
    anyv.deleteTask(key)
    qtbot.wait(50)
    assert desc not in _note(vault)
    # the sync detector sees our write but suppresses it (own-write)
    changed = anyv._sync.check()
    assert changed == []


def test_external_edit_reflected(vm: Any, qtbot: Any) -> None:
    _v, anyv, vault = vm
    note = vault / "Daily" / (TODAY.isoformat() + ".md")
    note.write_text("## To-Do\n- [ ] added in obsidian\n- [x] done in obsidian\n", encoding="utf-8")
    # the poll/debounce should notice the external write and reload the day
    qtbot.waitUntil(lambda: anyv._sync.check() != [], timeout=2000)
    qtbot.waitUntil(
        lambda: "added in obsidian" in [t["description"] for t in anyv.today.todoList],
        timeout=2000,
    )
    assert "done in obsidian" in [t["description"] for t in anyv.today.doneList]
