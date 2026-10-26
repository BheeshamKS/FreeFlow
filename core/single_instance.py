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
DEFAULT_SOCKET_NAME = "freeflow_desktop_single_instance_ipc"


class SingleInstanceGuard(QObject):
    """
    Guarantees a single running instance of FreeFlow.
    Sends IPC messages to bring existing instance forward when user clicks app launcher.
    """

    activation_requested = pyqtSignal(str) if QObject is not None else None

    def __init__(self, app_id: Optional[str] = None, parent=None):
        if isinstance(app_id, QObject):
            super().__init__(app_id)
            self.socket_name = DEFAULT_SOCKET_NAME
        else:
            super().__init__(parent)
            self.socket_name = str(app_id) if app_id else DEFAULT_SOCKET_NAME

        self.server: Optional[QLocalServer] = None

    def acquire(self) -> bool:
        """
        Attempt to acquire single-instance lock.
        Returns True if this is the primary instance.
        Returns False if an instance is already running.
        """
        if QLocalSocket is None:
            return True

        # Test if an existing server is alive
        socket = QLocalSocket()
        socket.connectToServer(self.socket_name)

        if socket.waitForConnected(500):
            logger.info("Another instance of FreeFlow is already running.")
            socket.disconnectFromServer()
            return False

        # Clean up any stale sockets from previous crashes
        QLocalServer.removeServer(self.socket_name)

        # Start primary IPC server
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_new_connection)

        if not self.server.listen(self.socket_name):
            logger.warning(f"Could not listen on local socket {self.socket_name}: {self.server.errorString()}")
            return True

        logger.info(f"Single-instance IPC server active on '{self.socket_name}'.")
        return True

    def send_activation(self, msg: str = "ACTIVATE") -> bool:
        """Send activation message to running instance."""
        if QLocalSocket is None:
            return False
        try:
            socket = QLocalSocket()
            socket.connectToServer(self.socket_name)
            if socket.waitForConnected(1000):
                socket.write(msg.encode("utf-8"))
                socket.flush()
                socket.waitForBytesWritten(1000)
                socket.waitForDisconnected(500)
                logger.info(f"Sent IPC activation signal '{msg}' to running FreeFlow instance.")
                return True
        except Exception as e:
            logger.error(f"Error sending activation IPC: {e}")
        return False

    def _on_new_connection(self):
        """Receive activation request from second instance."""
        if not self.server:
            return

        client_socket = self.server.nextPendingConnection()
        if not client_socket:
            return

        def handle_read():
            try:
                data = client_socket.readAll().data().decode("utf-8", errors="ignore").strip()
                if data:
                    logger.info(f"Received IPC command: '{data}'")
                    if self.activation_requested:
                        self.activation_requested.emit(data)
            except Exception as e:
                logger.error(f"Error reading IPC data: {e}")
            finally:
                client_socket.disconnectFromServer()

        if client_socket.bytesAvailable() > 0:
            handle_read()
        else:
            client_socket.readyRead.connect(handle_read)
            if client_socket.waitForReadyRead(800):
                handle_read()

    def cleanup(self):
        """Close server and remove socket file."""
        if self.server:
            self.server.close()
            QLocalServer.removeServer(self.socket_name)
