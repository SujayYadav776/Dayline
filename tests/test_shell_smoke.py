"""M2 smoke: shell boots offscreen against a real fixture vault."""

from __future__ import annotations

import shutil
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vaults"
TODAY = date.today()


@pytest.mark.usefixtures("qapp_instance")
def test_main_window_boots(tmp_path: Path) -> None:
    from dayline.app import create_engine, qml_dir

    assert qml_dir().is_dir(), f"qml dir missing: {qml_dir()}"
    engine, vm = create_engine()
    vm_any: Any = vm
    roots = engine.rootObjects()
    assert roots, "Main.qml failed to load (see QML errors above)"
    window = roots[0]
    assert window.objectName() == "rootWindow"
    assert bool(window.property("qmlReady"))
    # the context-property object is alive and wired after load
    assert isinstance(vm_any.vaultReady, bool)
    assert vm_any.settings.heading == "## To-Do"
    engine.deleteLater()


def _make_vault(tmp_path: Path) -> Path:
    dst = tmp_path / "vault"
    shutil.copytree(FIXTURES / "default", dst)
    (dst / "Daily" / f"{date.today():%Y-%m-%d}.md").write_text(
        (dst / "Daily" / "2026-09-19.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return dst


@pytest.mark.usefixtures("qapp_instance")
def test_vm_contract_on_fixture_vault(tmp_path: Path, qtbot: Any) -> None:
    from dayline.core.settings import Settings
    from dayline.ui.viewmodels.app_vm import AppViewModel

    vault = _make_vault(tmp_path)
    settings = Settings(vault_path=str(vault))
    vm = AppViewModel(settings, theme_probe=lambda: "light")
    vm_any: Any = vm
    vm_any.start()
    # navigate()'s QTimer(0) load must run:
    qtbot.waitUntil(lambda: not vm_any.today._loading, timeout=2000)

    assert bool(vm_any.vaultReady) is True
    tvm = vm_any.today
    assert tvm.dateLabel == TODAY.strftime("%A, %d %B %Y")
    # startup rollover carried 'plan the week' + 'grocery run' (+ its child) in
    assert tvm.totalCount == 8 and tvm.doneCount == 1
    assert tvm.percent == 12
    assert tvm.todoCount == 7  # incl. the in-progress task and the open subtasks
    assert tvm.doneSectionCount == 2  # Email (done) + Abandoned (cancelled)
    assert tvm.carriedSectionCount == 1  # '- [>] Renew passport'

    # row dicts expose description/chips for the QML delegate
    first = tvm.todoList[0]
    assert first["description"]
    assert isinstance(first["chips"], list)

    # navigation
    vm_any.nextDay()
    qtbot.waitUntil(lambda: not vm_any.today._loading, timeout=2000)
    assert vm_any.today.dateLabel == (TODAY + timedelta(days=1)).strftime("%A, %d %B %Y")


@pytest.mark.usefixtures("qapp_instance")
def test_vault_missing_state(tmp_path: Path) -> None:
    """No/invalid vault → vaultReady False so the shell shows recovery UI."""
    from dayline.core.settings import Settings
    from dayline.ui.viewmodels.app_vm import AppViewModel

    vm = AppViewModel(Settings(vault_path=str(tmp_path / "nope")), theme_probe=lambda: "light")
    any_vm: Any = vm
    any_vm.start()
    assert bool(any_vm.vaultReady) is False


@pytest.mark.usefixtures("qapp_instance")
def test_empty_day_state(tmp_path: Path, qtbot: Any) -> None:
    """A configured vault but a day with no note → loaded, zero tasks, not loading."""
    from dayline.core.settings import Settings
    from dayline.ui.viewmodels.app_vm import AppViewModel

    vault = tmp_path / "vault"
    (vault / "Daily").mkdir(parents=True)
    vm = AppViewModel(Settings(vault_path=str(vault), rollover_enabled=False),
                      theme_probe=lambda: "light")
    any_vm: Any = vm
    any_vm.start()
    qtbot.waitUntil(lambda: not any_vm.today._loading, timeout=2000)
    tvm = any_vm.today
    assert bool(any_vm.vaultReady) is True
    assert tvm.todoCount == 0 and tvm.totalCount == 0 and tvm.percent == 0
    assert bool(tvm.hasTasks) is False
    assert tvm.progress == 0.0
