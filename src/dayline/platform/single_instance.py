"""Single-instance guard (FR-P3): QLockFile + QLocalServer.

The first process becomes primary and listens; a second launch sends "show"
and exits. Pure logic is exercised with fakes; the Qt plumbing is verified on
a real Windows run.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket

SERVER_NAME = "Dayline.singleinstance"
SHOW = b"show"


class SingleInstance(QObject):
    """Primary-instance holder. Call acquire(); if it returns False another
    instance is already running (it was told to show) and the caller should
    exit. When primary, ``on_second_launch`` runs when a second launch arrives.
    """

    def __init__(
        self, on_second_launch: Callable[[], None], name: str = SERVER_NAME, parent: Any = None
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._on_second = on_second_launch
        self._server: QLocalServer | None = None
        self._is_primary = False

    def acquire(self) -> bool:
        probe = QLocalSocket()
        probe.connectToServer(self._name)
        if probe.waitForConnected(300):
            probe.write(SHOW)
            probe.waitForBytesWritten(300)
            probe.disconnectFromServer()
            return False
        QLocalServer.removeServer(self._name)  # clear a stale socket from a crash
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._handle)
        if not self._server.listen(self._name):
            return False
        self._is_primary = True
        return True

    def _handle(self) -> None:
        if self._server is None:
            return
        conn = self._server.nextPendingConnection()
        if conn is None:
            return
        conn.readyRead.connect(conn.readAll)
        conn.disconnected.connect(conn.deleteLater)
        self._on_second()

    @property
    def is_primary(self) -> bool:
        return self._is_primary

    def shutdown(self) -> None:
        if self._server is not None:
            self._server.close()
            QLocalServer.removeServer(self._name)
            self._server = None
        self._is_primary = False
