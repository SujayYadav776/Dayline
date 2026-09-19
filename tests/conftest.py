"""Shared test fixtures. Offscreen Qt for headless CI/dev machines."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp_instance() -> QApplication:
    """Session-wide QApplication (pytest-qt reuses an existing instance)."""
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    return app
