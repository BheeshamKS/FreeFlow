"""
FreeFlow System Tray Integration
Manages the application's tray icon, context menu, state transitions,
and system-level desktop notifications using native freedesktop icon names (no emojis).
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    from PyQt6.QtGui import QIcon, QAction
    from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox
except ImportError:
    class QObject:
        pass
    def pyqtSignal(*args):
        return None

from core.config import AppConfig

logger = logging.getLogger("FreeFlow.Tray")


class SystemTrayController(QObject):
    """Controls the system tray icon, context menu, and desktop notifications."""

    open_hub_requested = pyqtSignal() if QObject is not None else None
    open_settings_requested = pyqtSignal() if QObject is not None else None
    toggle_recording_requested = pyqtSignal() if QObject is not None else None
    quit_requested = pyqtSignal() if QObject is not None else None

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config

        self.assets_dir = Path(__file__).resolve().parent.parent / "assets"
        self.icon_normal_path = str(self.assets_dir / "icon.png")
        self.icon_recording_path = str(self.assets_dir / "icon_recording.png")
        self.icon_processing_path = str(self.assets_dir / "icon_processing.png")

        self.icon_normal = QIcon(self.icon_normal_path)
        self.icon_recording = QIcon(self.icon_recording_path)
        self.icon_processing = QIcon(self.icon_processing_path)

        self.tray = QSystemTrayIcon(self.icon_normal, parent)
        self.menu = QMenu()

        self._build_menu()
        self.update_tooltip("Ready")

        self.tray.activated.connect(self._on_tray_activated)

    def _build_menu(self):
        """Construct the context menu for the system tray icon."""
        self.menu.clear()

        # Open Main Hub Window
        self.hub_action = QAction("Open FreeFlow Hub...", self.menu)
        font = self.hub_action.font()
        font.setBold(True)
        self.hub_action.setFont(font)
        self.hub_action.triggered.connect(self._on_hub_clicked)
        self.menu.addAction(self.hub_action)

        self.menu.addSeparator()

        # Toggle recording action
        hotkey_str = self.config.get_display_hotkey()
        self.toggle_action = QAction(f"Start Recording ({hotkey_str})", self.menu)
        self.toggle_action.triggered.connect(self._on_toggle_clicked)
        self.menu.addAction(self.toggle_action)

        # Settings
        self.settings_action = QAction("Preferences / Settings...", self.menu)
        self.settings_action.triggered.connect(self._on_settings_clicked)
        self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        # View logs
        self.logs_action = QAction("View Recent Log...", self.menu)
        self.logs_action.triggered.connect(self._on_logs_clicked)
        self.menu.addAction(self.logs_action)

        self.menu.addSeparator()

        # Quit
        self.quit_action = QAction("Quit FreeFlow", self.menu)
        self.quit_action.triggered.connect(self._on_quit_clicked)
        self.menu.addAction(self.quit_action)

        self.tray.setContextMenu(self.menu)

    def _on_hub_clicked(self):
        if self.open_hub_requested:
            self.open_hub_requested.emit()

    def _on_tray_activated(self, reason):
        """Handle single/double clicks on tray icon to open Hub."""
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.open_hub_requested:
                self.open_hub_requested.emit()

    def show(self):
        """Display the system tray icon."""
        self.tray.show()

    def hide(self):
        """Hide the system tray icon."""
        self.tray.hide()

    def update_tooltip(self, state_text: str):
        """Update mouse-over tooltip on the tray icon."""
        hotkey_str = self.config.get_display_hotkey()
        self.tray.setToolTip(f"FreeFlow: {state_text}\nHotkey: {hotkey_str} ({self.config.hotkey_mode.capitalize()})")

    def set_state(self, state: str):
        """Update tray icon and menu text based on current workflow state."""
        hotkey_str = self.config.get_display_hotkey()

        if state == "recording":
            self.tray.setIcon(self.icon_recording)
            self.toggle_action.setText(f"Stop Recording ({hotkey_str})")
            self.update_tooltip("Recording Audio...")
            if self.config.enable_notifications:
                self.send_desktop_notification(
                    title="FreeFlow",
                    message="Recording started",
                    icon="audio-input-microphone",
                    urgency="low",
                    expire_ms=1500
                )

        elif state in ("transcribing", "formatting"):
            self.tray.setIcon(self.icon_processing)
            self.toggle_action.setText("Processing...")
            self.update_tooltip("Transcribing / Polishing...")
            if self.config.enable_notifications:
                self.send_desktop_notification(
                    title="FreeFlow",
                    message="Transcribing audio with Whisper...",
                    icon="hourglass",
                    urgency="low",
                    expire_ms=1500
                )

        elif state == "done":
            self.tray.setIcon(self.icon_normal)
            self.toggle_action.setText(f"Start Recording ({hotkey_str})")
            self.update_tooltip("Ready")
            if self.config.enable_notifications:
                self.send_desktop_notification(
                    title="FreeFlow",
                    message="Transcription injected into active window",
                    icon="emblem-default",
                    urgency="low",
                    expire_ms=2000
                )

        elif state == "error":
            self.tray.setIcon(self.icon_normal)
            self.toggle_action.setText(f"Start Recording ({hotkey_str})")
            self.update_tooltip("Error encountered")

        else:  # 'idle' or 'ready'
            self.tray.setIcon(self.icon_normal)
            self.toggle_action.setText(f"Start Recording ({hotkey_str})")
            self.update_tooltip("Ready")

    def send_desktop_notification(
        self,
        title: str,
        message: str,
        icon: str = "audio-input-microphone",
        urgency: str = "normal",
        expire_ms: int = 3000
    ):
        """
        Send a desktop notification using notify-send via subprocess.
        Uses system icon names without emojis as required.
        """
        if not shutil.which("notify-send"):
            # Fallback to Qt tray notification message
            try:
                self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, expire_ms)
            except Exception:
                pass
            return

        cmd = [
            "notify-send",
            title,
            message,
            "-a", "FreeFlow",
            "-i", icon,
            "-u", urgency,
            "-t", str(expire_ms)
        ]

        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.debug(f"Failed to execute notify-send: {e}")

    def notify_error(self, error_message: str):
        """Show error notification."""
        self.set_state("error")
        self.send_desktop_notification(
            title="FreeFlow Error",
            message=error_message,
            icon="dialog-error",
            urgency="critical",
            expire_ms=6000
        )

    def _on_tray_activated(self, reason):
        """Handle single/double clicks on tray icon."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.open_settings_requested:
                self.open_settings_requested.emit()

    def _on_toggle_clicked(self):
        if self.toggle_recording_requested:
            self.toggle_recording_requested.emit()

    def _on_settings_clicked(self):
        if self.open_settings_requested:
            self.open_settings_requested.emit()

    def _on_logs_clicked(self):
        """Open temporary log file or display message box with latest status."""
        log_path = "/tmp/freeflow.log"
        content = "No log file found at /tmp/freeflow.log"
        if os.path.isfile(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    content = "".join(lines[-40:])
            except Exception as e:
                content = f"Error reading log file: {e}"

        msg_box = QMessageBox()
        msg_box.setWindowTitle("FreeFlow Activity Log")
        msg_box.setText("Recent FreeFlow Log Entries:")
        msg_box.setDetailedText(content)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()

    def _on_quit_clicked(self):
        if self.quit_requested:
            self.quit_requested.emit()
