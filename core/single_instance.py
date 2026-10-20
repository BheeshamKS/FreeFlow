"""
FreeFlow Single Instance Application Guard
Ensures only one instance of FreeFlow runs at a time.
Brings the existing window to the foreground if launched again from the app menu.
"""

import logging
from typing import Optional

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
except ImportError:
    class QObject:
        pass
    def pyqtSignal(*args):
        return None
    QLocalServer = None
    QLocalSocket = None

logger = logging.getLogger("FreeFlow.SingleInstance")
SOCKET_NAME = "freeflow_desktop_single_instance_ipc"


class SingleInstanceGuard(QObject):
    """
    Guarantees a single running instance of FreeFlow.
    Sends IPC messages to bring existing instance forward when user clicks app launcher.
    """

    activation_requested = pyqtSignal(str) if QObject is not None else None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.server: Optional[QLocalServer] = None

    def acquire(self) -> bool:
        """
        Attempt to acquire single-instance lock.
        Returns True if this is the primary instance.
        Returns False if an instance is already running (and triggers that instance to show).
        """
        if QLocalSocket is None:
            return True

        # Test if an existing server is alive
        socket = QLocalSocket()
        socket.connectToServer(SOCKET_NAME)

        if socket.waitForConnected(500):
            logger.info("Another instance of FreeFlow is already running. Requesting activation...")
            socket.write(b"ACTIVATE")
            socket.flush()
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
            return False

        # Clean up any stale sockets from previous crashes
        QLocalServer.removeServer(SOCKET_NAME)

        # Start primary IPC server
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_new_connection)

        if not self.server.listen(SOCKET_NAME):
            logger.warning(f"Could not listen on local socket {SOCKET_NAME}: {self.server.errorString()}")
            return True

        logger.info("Single-instance IPC server active.")
        return True

    def _on_new_connection(self):
        """Receive activation request from second instance."""
        if not self.server:
            return

        client_socket = self.server.nextPendingConnection()
        if not client_socket:
            return

        if client_socket.waitForReadyRead(500):
            data = client_socket.readAll().data().decode("utf-8").strip()
            logger.info(f"Received IPC command: '{data}'")
            if self.activation_requested:
                self.activation_requested.emit(data)

        client_socket.disconnectFromServer()

    def cleanup(self):
        """Close server and remove socket file."""
        if self.server:
            self.server.close()
            QLocalServer.removeServer(SOCKET_NAME)
