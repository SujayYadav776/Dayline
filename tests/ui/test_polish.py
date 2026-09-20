"""M8 polish: reduced-motion source, window geometry + last-page persistence."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from dayline.core.settings import Settings, load
from dayline.platform.motion import make_motion_source
from dayline.ui.viewmodels.app_vm import AppViewModel
from dayline.ui.viewmodels.settings_vm import SettingsViewModel

TODAY = date.today()


def _vault(tmp_path: Path) -> Path:
    v = tmp_path / "vault"
    (v / "Daily").mkdir(parents=True)
    return v


def test_motion_source_respects_probe() -> None:
    assert make_motion_source(lambda: False)() is False
    assert make_motion_source(lambda: True)() is True


def test_reduce_motion_property(tmp_path: Path) -> None:
    vm = AppViewModel(
        Settings(vault_path=str(_vault(tmp_path))),
        theme_probe=lambda: "light",
        motion_probe=lambda: False,
    )
    anyv: Any = vm
    assert bool(anyv.reduceMotion) is True


def test_geometry_saved_and_restored(tmp_path: Path) -> None:
    cfg = tmp_path / "config.json"
    vm = AppViewModel(
        Settings(vault_path=str(_vault(tmp_path))), config_path=cfg, theme_probe=lambda: "light"
    )
    anyv: Any = vm
    anyv.saveGeometry(120, 80, 500, 800)
    reloaded, _issues = load(cfg)
    assert reloaded.window == {"x": 120, "y": 80, "width": 500, "height": 800}


def test_last_page_persisted(tmp_path: Path) -> None:
    cfg = tmp_path / "config.json"
    vm = AppViewModel(
        Settings(vault_path=str(_vault(tmp_path))), config_path=cfg, theme_probe=lambda: "light"
    )
    anyv: Any = vm
    anyv.start()
    anyv.setPage("week")
    reloaded, _issues = load(cfg)
    assert reloaded.last_page == "week"


def test_last_page_restored_on_start(tmp_path: Path) -> None:
    cfg = tmp_path / "config.json"
    s = Settings(vault_path=str(_vault(tmp_path)), last_page="settings")
    from dayline.core.settings import save

    save(cfg, s)
    vm = AppViewModel(s, config_path=cfg, theme_probe=lambda: "light")
    anyv: Any = vm
    anyv.start()
    assert anyv.page == "settings"


# ---- Mica backdrop ---------------------------------------------------------
def test_mica_defaults_on() -> None:
    assert Settings().mica is True


def test_mica_active_requires_support_and_pref(tmp_path: Path) -> None:
    vm = AppViewModel(
        Settings(vault_path=str(_vault(tmp_path))),
        theme_probe=lambda: "light",
        mica_probe=lambda: True,
    )
    anyv: Any = vm
    assert anyv.micaActive is True
    assert anyv.micaSupported is True
    vm.settings.mica = False
    assert anyv.micaActive is False


def test_mica_inactive_when_unsupported(tmp_path: Path) -> None:
    vm = AppViewModel(
        Settings(vault_path=str(_vault(tmp_path)), mica=True),
        theme_probe=lambda: "light",
        mica_probe=lambda: False,
    )
    anyv: Any = vm
    assert anyv.micaSupported is False
    assert anyv.micaActive is False


def test_mica_toggle_persists(tmp_path: Path) -> None:
    cfg = tmp_path / "config.json"
    vm = SettingsViewModel(Settings(), config_path=cfg)
    anyvm: Any = vm
    assert anyvm.mica is True
    groups: list[str] = []
    anyvm.applied.connect(lambda g: groups.append(g))
    anyvm.setMica(False)
    assert anyvm.mica is False
    assert groups == ["appearance"]
    reloaded, _issues = load(cfg)
    assert reloaded.mica is False
