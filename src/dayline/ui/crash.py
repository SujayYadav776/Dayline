"""Crash resilience (PRD §6.5): a global hook that logs a traceback and shows a
non-blocking dialog offering to open the logs folder. Never silently swallows."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from pathlib import Path
from types import TracebackType

log = logging.getLogger("dayline.crash")

_shown = False


def install(logs_dir: Path, *, open_folder: Callable[[str], None] | None = None) -> None:
    """Route uncaught Python exceptions and Qt warnings to the log + a dialog."""
    logs_dir.mkdir(parents=True, exist_ok=True)

    def hook(exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None) -> None:
        global _shown
        log.critical("uncaught exception", exc_info=(exc_type, exc, tb))
        # keep default behaviour for KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        if not _shown:
            _shown = True
            _show_dialog(logs_dir, exc, open_folder)

    sys.excepthook = hook


def _show_dialog(
    logs_dir: Path, exc: BaseException, open_folder: Callable[[str], None] | None
) -> None:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        if QApplication.instance() is None:
            return
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Dayline hit a problem")
        box.setText("Something went wrong and was logged.")
        box.setInformativeText(f"{type(exc).__name__}: {exc}")
        open_btn = box.addButton("Open logs folder", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Close)
        box.exec()
        if box.clickedButton() is open_btn:
            (open_folder or _default_open)(str(logs_dir))
    except Exception:
        log.exception("failed to show crash dialog")


def _default_open(path: str) -> None:
    import os
    import subprocess
    import sys

    if sys.platform == "win32":
        os.startfile(path)
    else:  # pragma: no cover
        subprocess.run(["xdg-open", path], check=False)
