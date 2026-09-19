"""GUI application bootstrap (thin; presentation wiring only)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

APP_NAME = "Dayline"

_QML_DIR_NAME = Path("ui") / "qml"


def qml_dir() -> Path:
    """Location of the QML tree; resolves in the dev tree and in frozen builds."""
    if getattr(sys, "frozen", False):  # pragma: no cover - frozen only
        base = Path(getattr(sys, "_MEIPASS", str(Path(sys.executable).parent)))
        return base / "dayline" / _QML_DIR_NAME
    return Path(__file__).parent / _QML_DIR_NAME


def create_engine() -> QQmlApplicationEngine:
    """Create the QML engine and load the main window. Caller must keep the
    returned engine (and its root objects) alive for the lifetime of the UI."""
    QQuickStyle.setStyle("Basic")
    engine = QQmlApplicationEngine()
    root = qml_dir()
    engine.addImportPath(str(root))
    engine.load(QUrl.fromLocalFile(str(root / "Main.qml")))
    return engine


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

    app = cast("QGuiApplication", QGuiApplication.instance() or QGuiApplication(sys.argv))
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)

    engine = create_engine()
    roots = engine.rootObjects()
    if not roots:
        _report("FATAL: failed to load QML UI")
        return 1

    if args.selftest:
        window = roots[0]
        ok = window.objectName() == "rootWindow" and bool(window.property("qmlReady"))
        _report(f"selftest: qml_loaded={'ok' if ok else 'failed'}")
        return 0 if ok else 1

    # M2+: window/tray/scheduler wiring. M0 ends here with a plain event loop.
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
