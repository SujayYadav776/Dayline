"""GUI application bootstrap (thin; presentation wiring only)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from dayline.core.settings import load as load_settings
from dayline.platform.paths import config_file
from dayline.ui.viewmodels.app_vm import AppViewModel

APP_NAME = "Dayline"

_QML_DIR_NAME = Path("ui") / "qml"


def qml_dir() -> Path:
    """Location of the QML tree; resolves in the dev tree and in frozen builds."""
    if getattr(sys, "frozen", False):  # pragma: no cover - frozen only
        base = Path(getattr(sys, "_MEIPASS", str(Path(sys.executable).parent)))
        return base / "dayline" / _QML_DIR_NAME
    return Path(__file__).parent / _QML_DIR_NAME


def configure_logging() -> None:
    from dayline.platform.paths import logs_dir

    logs_dir().mkdir(parents=True, exist_ok=True)
    from logging.handlers import RotatingFileHandler

    handlers: list[logging.Handler] = [
        RotatingFileHandler(
            logs_dir() / "dayline.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
    ]
    if sys.stderr is not None:  # windowed frozen builds have no console
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def create_engine() -> tuple[QQmlApplicationEngine, AppViewModel]:
    """Create the QML engine with the App context property set. The caller
    must keep the returned engine and viewmodel alive for the UI lifetime."""
    QQuickStyle.setStyle("Basic")

    cfg_path = config_file()
    settings, _issues = load_settings(cfg_path)
    vm = AppViewModel(settings, config_path=cfg_path)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("App", vm)
    root = qml_dir()
    engine.addImportPath(str(root))
    engine.load(QUrl.fromLocalFile(str(root / "Main.qml")))
    return engine, vm


def _report(msg: str) -> None:
    """stdout/stderr are None in a windowed frozen build; never print blindly."""
    if sys.stdout is not None:
        print(msg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=APP_NAME)
    parser.add_argument(
        "--selftest", action="store_true", help="boot the UI, verify the QML window loads, exit 0/1"
    )
    parser.add_argument(
        "--minimized", action="store_true", help="start hidden to tray (used with autostart)"
    )
    args = parser.parse_args(argv)

    configure_logging()
    app = cast("QGuiApplication", QGuiApplication.instance() or QGuiApplication(sys.argv))
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(_version())

    # single instance: a second launch asks the running one to show, then exits
    from dayline.platform.single_instance import SingleInstance

    pending_show = {"v": False}

    def _second_launch() -> None:
        pending_show["v"] = True

    si = SingleInstance(_second_launch)
    if not args.selftest and not si.acquire():
        _report("another Dayline instance is already running; signaled it to show")
        return 0

    engine, vm = create_engine()
    roots = engine.rootObjects()
    if not roots:
        _report("FATAL: failed to load QML UI")
        return 1
    vm.start()
    window: Any = roots[0]

    if args.selftest:
        ok = window.objectName() == "rootWindow" and bool(window.property("qmlReady"))
        _report(f"selftest: qml_loaded={'ok' if ok else 'failed'}")
        return 0 if ok else 1

    controller = _integrate_windows(app, engine, vm, window)
    if args.minimized:
        window.hide()
    elif pending_show["v"]:
        controller.toggle_window()

    rc = app.exec()
    si.shutdown()
    return rc


def _integrate_windows(app: Any, engine: Any, vm: Any, window: Any) -> Any:
    """Construct and wire the Windows integrations. Returns the controller."""
    from PySide6.QtGui import QIcon

    from dayline.platform.autostart import Autostart
    from dayline.platform.hotkey import GlobalHotkey, HotkeyFilter
    from dayline.platform.tray import Tray
    from dayline.ui.app_controller import AppController

    icon = QIcon(str(qml_dir().parent / "assets" / "app.png"))

    def open_obsidian() -> None:
        vm.openInObsidian()

    tray = Tray(
        icon,
        on_activate=lambda: controller.toggle_window(),
        on_quick_add=lambda: _trigger_quick_add(vm),
        on_open_obsidian=open_obsidian,
        on_quit=lambda: controller.quit(),
    )
    hotkey = GlobalHotkey()
    autostart = Autostart()
    controller = AppController(
        window=window,
        vm=vm,
        tray=tray,
        hotkey=hotkey,
        autostart=autostart,
        quick_add=lambda: _trigger_quick_add(vm),
        open_obsidian=open_obsidian,
        quit_app=app.quit,
    )
    engine.rootContext().setContextProperty("Controller", controller)

    if tray.available():
        tray.show()
    else:
        controller._tray = None  # no tray → notify() no-ops, menu unavailable
    # global hotkey via native event filter (Windows only; needs a message loop)
    if sys.platform == "win32":
        qf = HotkeyFilter(lambda: _trigger_quick_add(vm))
        app.installNativeEventFilter(qf)
        controller.bind_hotkey()
        controller._native_filter = qf  # keep alive
    controller.apply_titlebar_theme()
    vm.changed.connect(controller.apply_titlebar_theme)
    vm.changed.connect(controller.schedule_notifications)
    controller.schedule_notifications()
    controller.sync_autostart()
    return controller


def _trigger_quick_add(vm: Any) -> None:
    vm.showQuickAdd()


def _version() -> str:
    from dayline import __version__

    return __version__


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
