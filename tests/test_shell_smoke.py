"""M0 smoke: the QML shell boots offscreen and the Theme singleton resolves."""

from __future__ import annotations

import pytest


@pytest.mark.usefixtures("qapp_instance")
def test_main_window_boots() -> None:
    from dayline.app import create_engine, qml_dir

    assert qml_dir().is_dir(), f"qml dir missing: {qml_dir()}"
    engine = create_engine()
    roots = engine.rootObjects()
    assert roots, "Main.qml failed to load (check QML import errors above)"
    window = roots[0]
    assert window.objectName() == "rootWindow"
    assert bool(window.property("qmlReady"))
    engine.deleteLater()


@pytest.mark.usefixtures("qapp_instance")
def test_selftest_function_returns_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    from dayline import app as app_mod

    monkeypatch.setattr(sys, "argv", ["Dayline"])
    assert app_mod.main(["--selftest"]) == 0
