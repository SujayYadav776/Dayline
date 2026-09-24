"""Render key UI states offscreen for design QA (PRD §5 'verify both themes').

Usage: uv run python scripts/screenshot_pages.py [outdir]
Writes light/dark/empty/setup PNGs; non-zero exit if a render fails.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

from dayline import app as dayline_app  # noqa: E402
from dayline.core.settings import Settings  # noqa: E402
from dayline.ui.viewmodels.app_vm import AppViewModel  # noqa: E402


def build_vault(tmp: Path) -> Path:
    vault = tmp / "vault"
    shutil.copytree(ROOT / "tests" / "fixtures" / "vaults" / "default", vault)
    today = date.today()
    src = vault / "Daily" / "2026-09-19.md"
    (vault / "Daily" / f"{today.isoformat()}.md").write_text(src.read_text("utf-8"), "utf-8")
    return vault


def spin(app: QGuiApplication, seconds: float = 0.5) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


def capture(
    app: QGuiApplication,
    settings: Settings,
    out: Path,
    prepare: Callable[[AppViewModel], None] | None = None,
    post: Callable[[object], None] | None = None,
) -> bool:
    theme = settings.theme if settings.theme in ("light", "dark") else "light"
    vm = AppViewModel(settings, theme_probe=lambda: theme)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("App", vm)
    root = dayline_app.qml_dir()
    engine.addImportPath(str(root))
    engine.load(QUrl.fromLocalFile(str(root / "Main.qml")))
    ok = False
    try:
        roots = engine.rootObjects()
        if not roots:
            return False
        win = roots[0]
        vm.start()
        spin(app)
        if prepare:
            prepare(vm)
            spin(app)
        if post:
            post(win)
            spin(app)
        out.parent.mkdir(parents=True, exist_ok=True)
        pix = win.grabWindow()
        ok = (not pix.isNull()) and pix.save(str(out))
    finally:
        engine.deleteLater()
        vm.deleteLater()
    return ok and out.exists() and out.stat().st_size > 1000


def main() -> int:
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    dayline_app.load_bundled_fonts()
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "screenshots"
    results: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as td:
        vault = build_vault(Path(td))

        def vs(**kw: object) -> Settings:
            return Settings(vault_path=str(vault), **kw)  # type: ignore[arg-type]

        results.append(("today-light", capture(app, vs(theme="light"), outdir / "today-light.png")))
        results.append(("today-dark", capture(app, vs(theme="dark"), outdir / "today-dark.png")))
        results.append(
            (
                "today-empty",
                capture(
                    app,
                    vs(theme="light"),
                    outdir / "today-empty.png",
                    prepare=lambda vm: vm.navigate(date.today() + timedelta(days=5)),
                ),
            )
        )
        results.append(("onboarding", capture(app, Settings(), outdir / "onboarding.png")))
        results.append(
            (
                "recovery",
                capture(
                    app,
                    Settings(vault_path=str(Path(td) / "gone")),
                    outdir / "recovery.png",
                ),
            )
        )
        results.append(
            (
                "week",
                capture(
                    app,
                    vs(theme="light"),
                    outdir / "week.png",
                    prepare=lambda vm: vm.setPage("week"),
                ),
            )
        )
        results.append(
            (
                "settings",
                capture(
                    app,
                    vs(theme="light"),
                    outdir / "settings.png",
                    prepare=lambda vm: vm.setPage("settings"),
                ),
            )
        )
        results.append(
            (
                "progress",
                capture(
                    app,
                    vs(theme="light"),
                    outdir / "progress.png",
                    post=lambda win: win.setProperty("progressOpen", True),
                ),
            )
        )
    bad = [n for n, ok in results if not ok]
    for name, ok in results:
        print(f"{'OK  ' if ok else 'FAIL'} {name}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
