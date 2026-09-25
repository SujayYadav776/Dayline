"""GUI application bootstrap (thin; presentation wiring only)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QUrl
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


def load_bundled_fonts() -> None:
    """Register the design fonts (Varela Round / Wallpoet / LEMON MILK) with Qt.

    The paper design system binds to these families by name (Theme.qml);
    Segoe UI stays as the fallback if a file is missing."""
    from PySide6.QtGui import QFontDatabase

    fonts_dir = qml_dir().parent / "assets" / "fonts"
    if not fonts_dir.is_dir():  # pragma: no cover - dev tree always has them
        return
    log = logging.getLogger("dayline.app")
    files = sorted(fonts_dir.glob("*.ttf")) + sorted(fonts_dir.glob("*.otf"))
    for f in files:
        if QFontDatabase.addApplicationFont(str(f)) == -1:
            log.warning("could not load bundled font %s", f.name)


def create_engine() -> tuple[QQmlApplicationEngine, AppViewModel]:
    """Create the QML engine with the App context property set. The caller
    must keep the returned engine and viewmodel alive for the UI lifetime."""
    QQuickStyle.setStyle("Basic")
    load_bundled_fonts()

    cfg_path = config_file()
    settings, _issues = load_settings(cfg_path)

    from dayline.platform.sound import play_wav

    snap_wav = qml_dir().parent / "assets" / "snap.wav"
    vm = AppViewModel(settings, config_path=cfg_path, sound_play=lambda: play_wav(snap_wav))

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("App", vm)
    # Tray-first: skip the window from the very first frame when the user
    # opted in AND a vault is configured AND a tray exists to return to.
    from PySide6.QtWidgets import QSystemTrayIcon

    start_hidden = bool(
        settings.start_hidden and settings.vault_path and QSystemTrayIcon.isSystemTrayAvailable()
    )
    engine.rootContext().setContextProperty("StartHidden", start_hidden)
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
    from dayline.platform.paths import logs_dir
    from dayline.ui import crash

    crash.install(logs_dir())
    # QApplication (not QGuiApplication) is required because the system tray +
    # its context menu are QtWidgets (QSystemTrayIcon/QMenu); showing a widget
    # under a bare QGuiApplication makes Qt abort() on a real desktop.
    from PySide6.QtWidgets import QApplication

    app = cast("QApplication", QApplication.instance() or QApplication(sys.argv))
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(_version())

    # On Win11, request an alpha surface so the Mica backdrop can show through.
    from dayline.platform.dwm import supports_system_backdrop

    if supports_system_backdrop():  # pragma: no cover - platform capability
        from PySide6.QtGui import QSurfaceFormat

        fmt = QSurfaceFormat.defaultFormat()
        fmt.setAlphaBufferSize(8)
        QSurfaceFormat.setDefaultFormat(fmt)

    # single instance: a second launch asks the running one to show, then exits
    from dayline.platform.single_instance import SingleInstance

    pending_show = {"v": False}
    controller_ref: dict[str, Any] = {"c": None}

    def _second_launch() -> None:
        ctrl = controller_ref["c"]
        if ctrl is not None:
            ctrl.show_window()  # already running (often tray-hidden) → surface it
        else:
            pending_show["v"] = True  # raced ahead of startup; handled below

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

    # window/taskbar icon = the exact brand logo
    from PySide6.QtGui import QIcon

    window.setIcon(QIcon(str(qml_dir().parent / "assets" / "app.png")))

    if args.selftest:
        ok = window.objectName() == "rootWindow" and bool(window.property("qmlReady"))
        _report(f"selftest: qml_loaded={'ok' if ok else 'failed'}")
        return 0 if ok else 1

    controller = _integrate_windows(app, engine, vm, window)
    controller_ref["c"] = controller
    if args.minimized:
        window.hide()
    elif pending_show["v"]:
        controller.show_window()
    elif window.isVisible():
        # always open notification-centre style: bottom-right, default small
        # size — the last geometry is intentionally not restored
        controller.anchor_bottom_right()
    if not window.isVisible() and getattr(controller, "_tray", None) is not None:
        # tray-first boot: tell the user where the app went (once per run)
        controller._tray.notify("Dayline", "Running in the tray — click the icon to open.")

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
    summon_hk = GlobalHotkey()  # second slot: universal "bring Dayline up" key
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
        summon_hotkey=summon_hk,
    )
    engine.rootContext().setContextProperty("Controller", controller)

    if tray.available():
        tray.show()
    else:
        controller._tray = None  # no tray → notify() no-ops, menu unavailable
    # global hotkey via native event filter (Windows only; needs a message loop)
    if sys.platform == "win32":
        qf = HotkeyFilter()
        app.installNativeEventFilter(qf)
        controller.bind_hotkey()
        controller._native_filter = qf  # keep alive

    def _on_settings(group: str) -> None:
        if group == "notifications":
            controller.schedule_notifications()

    controller.apply_titlebar_theme()
    controller.apply_backdrop()
    controller.apply_corner_style()  # static Win11 preference
    vm.changed.connect(controller.apply_titlebar_theme)
    vm.changed.connect(controller.apply_backdrop)
    vm.settingsVM.applied.connect(_on_settings)
    controller.schedule_notifications()
    controller.sync_autostart()
    controller._settings_handler = _on_settings  # keep closure alive

    # Updates: tray toast, silent installer launch, quit — wired to the VM.
    from PySide6.QtCore import QTimer

    from dayline.platform.installer import launch_setup_exe

    def _update_notify(title: str, msg: str) -> None:
        if controller._tray is not None:
            controller._tray.notify(title, msg)

    vm.set_update_hooks(notify=_update_notify, launcher=launch_setup_exe, quit_app=app.quit)
    QTimer.singleShot(4000, vm.startup_update_check)  # after first paint; opt-in guarded
    return controller


def _trigger_quick_add(vm: Any) -> None:
    vm.showQuickAdd()


def _version() -> str:
    from dayline import __version__

    return __version__


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
