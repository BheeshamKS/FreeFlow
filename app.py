#!/usr/bin/env python3
"""
FreeFlow Linux — High-Speed Push-to-Talk Voice Transcription Desktop Application
================================================================================
A production-ready Linux alternative to macOS FreeFlow and Wispr Flow.
Runs as a desktop application with a Wispr Flow Hub window, system tray,
animated floating waveform HUD overlay, and single-instance IPC enforcement.
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

# Add project root to Python search path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging to both console and user log file
LOG_FILE = str(Path(tempfile.gettempdir()) / "freeflow.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    ]
)
logger = logging.getLogger("FreeFlow.App")

# Ensure PyQt6 is available
try:
    from PyQt6.QtCore import Qt, QTimer, QObject
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication, QMessageBox
except ImportError:
    print("Error: PyQt6 is not installed. Please run './setup.sh' to install all dependencies.")
    sys.exit(1)

from core.autostart import ensure_desktop_launcher
from core.config import AppConfig
from core.groq_client import GroqWorker
from core.history import HistoryManager
from core.hotkey import HotkeyListener
from core.injector import TextInjector
from core.platform import get_recovery_audio_path, is_linux
from core.recorder import AudioRecorder
from core.single_instance import SingleInstanceGuard
from core.troubleshooting import diagnose_error, get_common_diagnostic, ErrorDiagnostic
from core.updater import UpdateManager
from core.version import APP_VERSION
from ui.hud import RecordingHUD
from ui.main_window import MainWindow
from ui.onboarding import OnboardingWizard
from ui.tray import SystemTrayController
from ui.troubleshooting_dialog import TroubleshootingDialog


class FreeFlowApplication(QObject):
    """
    Main Application Controller.
    Manages the Wispr Flow Hub window, floating HUD capsule, tray icon,
    single-instance IPC, audio recording, Whisper transcription, and text injection.
    """

    def __init__(self, qapp: QApplication, start_minimized: bool = False, is_autostart: bool = False):
        super().__init__()
        self.qapp = qapp
        self.qapp.setApplicationName("FreeFlow")
        self.qapp.setApplicationDisplayName("FreeFlow")
        self.qapp.setApplicationVersion(APP_VERSION)
        self.qapp.setQuitOnLastWindowClosed(False)

        # Set Application Icon
        icon_path = str(PROJECT_ROOT / "assets" / "icon.png")
        if os.path.isfile(icon_path):
            self.app_icon = QIcon(icon_path)
            self.qapp.setWindowIcon(self.app_icon)

        logger.info(f"Initializing FreeFlow v{APP_VERSION}...")

        # 1. Single Instance Guard & Launcher Inter-Process Communication
        self.guard = SingleInstanceGuard(self.qapp)
        self.guard.activation_requested.connect(self.on_activation_requested)
        if not self.guard.acquire():
            # If launched during boot/login or with explicit autostart/minimized flags, DO NOT send activation!
            is_boot_autostart = is_autostart or ("--autostart" in sys.argv) or ("--minimized" in sys.argv) or start_minimized
            if is_boot_autostart:
                logger.info("FreeFlow background/autostart instance detected already running daemon. Exiting silently.")
                sys.exit(0)
            logger.info("Another instance of FreeFlow is already running. Forwarding activation to foreground window.")
            self.guard.send_activation("ACTIVATE")
            sys.exit(0)

        # 2. Ensure standard desktop application launcher entry is present in app menu
        ensure_desktop_launcher()

        # 3. Load Configuration & History
        self.config = AppConfig.load()
        self.history = HistoryManager()
        self._record_start_time = 0.0

        # Audio Recovery Buffer State (Protects against network/API failures on long recordings)
        self._recovery_audio_path: Optional[str] = None
        self._recovery_audio_duration: float = 0.0
        self._recovery_audio_available: bool = False

        # 4. Instantiate Core Workers
        self.recorder = AudioRecorder(
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            device=self.config.audio_device
        )
        self.injector = TextInjector(
            inject_delay=self.config.inject_delay,
            use_clipboard=self.config.use_clipboard_injection,
            restore_clipboard=self.config.restore_clipboard
        )
        self.hotkey_listener = HotkeyListener(self.config)

        # 5. Instantiate UI Components
        self.hud = RecordingHUD()
        self.tray = SystemTrayController(self.config)
        self.main_window = MainWindow(self.config, self.history)
        self._current_groq_worker: Optional[GroqWorker] = None

        # 6. Wire Signals
        self._connect_signals()

        # 7. Start Global Hotkey Listener
        self.hotkey_listener.start()

        # 8. Show Tray
        self.tray.show()

        # 9. First-Time Setup / Out of the Box Experience (OOBE):
        # If user has not completed setup wizard or has not yet entered their Groq API key,
        # guide them through the onboarding experience immediately.
        if not self.config.first_run_completed or not self.config.groq_api_key:
            logger.info("First run or missing API key detected. Launching Onboarding Wizard...")
            QTimer.singleShot(150, self.open_onboarding_wizard)
        else:
            # Check if launched automatically on graphical system login / boot
            is_boot_startup = is_autostart or ("--autostart" in sys.argv) or ("--minimized" in sys.argv) or start_minimized
            if is_boot_startup:
                # If started automatically on boot or with minimized flag, respect start_minimized setting!
                should_show = not self.config.start_minimized and not start_minimized
                logger.info(f"Launched on boot/login. start_minimized={self.config.start_minimized} -> should_show={should_show}")
            else:
                # Normal manual launch by user clicking app in menu or running in terminal
                should_show = True

            if should_show:
                self.show_main_window()

        # 10. Startup Update Check
        if self.config.check_updates_on_startup:
            QTimer.singleShot(3000, self._check_startup_updates)

        logger.info("FreeFlow desktop application initialized successfully.")

    def _connect_signals(self):
        """Connect Qt signals across threads and UI widgets."""
        # Global Hotkey Triggers
        self.hotkey_listener.start_recording.connect(self.on_start_recording)
        self.hotkey_listener.stop_recording.connect(self.on_stop_recording)
        self.hotkey_listener.error_occurred.connect(self.on_hotkey_error)

        # Live Audio Waveform Updates
        self.recorder.audio_level.connect(self.hud.update_audio_level)
        self.recorder.audio_level.connect(self.main_window.update_audio_level)
        self.recorder.error_occurred.connect(self.on_recorder_error)

        # HUD Capsule Actions
        self.hud.solutions_requested.connect(self.show_troubleshooting_dialog)
        self.hud.retry_requested.connect(self.retry_transcription)

        # System Tray Actions
        self.tray.open_hub_requested.connect(self.show_main_window)
        self.tray.open_settings_requested.connect(self.open_settings)
        self.tray.check_updates_requested.connect(self._manual_check_updates)
        self.tray.troubleshoot_requested.connect(self.show_troubleshooting_dialog)
        self.tray.toggle_recording_requested.connect(self.hotkey_listener.trigger_toggle_manual)
        self.tray.retry_transcription_requested.connect(self.retry_transcription)
        self.tray.quit_requested.connect(self.quit)

        # Main Window Hub Actions
        self.main_window.toggle_recording_requested.connect(self.hotkey_listener.trigger_toggle_manual)
        self.main_window.retry_transcription_requested.connect(self.retry_transcription)
        self.main_window.settings_changed.connect(self.on_settings_changed)
        self.main_window.simulate_error_requested.connect(self.simulate_error)
        self.main_window.quit_requested.connect(self.quit)

    def on_activation_requested(self, msg: str):
        """Brings existing FreeFlow window to the front when user clicks app launcher."""
        logger.info("Single-instance activation signal received. Presenting window...")
        self.show_main_window()

    def show_main_window(self):
        """Present the main Wispr Flow Hub window, restoring from minimized if needed."""
        if self.main_window.isMinimized():
            self.main_window.showNormal()
        else:
            self.main_window.show()

        # Clear minimized state and mark active
        self.main_window.setWindowState(
            (self.main_window.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive
        )
        self.main_window.raise_()
        self.main_window.activateWindow()

        # On Linux X11, helper to overcome window manager focus-stealing prevention
        if is_linux():
            try:
                if os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
                    subprocess.run(
                        ["xdotool", "search", "--onlyvisible", "--name", "FreeFlow", "windowactivate"],
                        capture_output=True,
                        timeout=0.3
                    )
            except Exception:
                pass

    def open_settings(self):
        """Navigate to the settings tab in the Hub window."""
        self.main_window._switch_tab(2)
        self.show_main_window()

    def open_onboarding_wizard(self):
        """Open the first-time startup onboarding setup wizard."""
        wiz = OnboardingWizard(self.config, self.main_window)
        wiz.wizard_completed.connect(self.on_settings_changed)
        wiz.exec()
        self.show_main_window()

    def on_start_recording(self):
        """Triggered when hotkey or Voice Orb is toggled on."""
        logger.info("Event: on_start_recording triggered.")

        if not self.config.groq_api_key:
            self.tray.notify_error("Groq API key not configured. Please open Preferences.")
            self.open_settings()
            return

        if self.recorder.is_recording:
            return

        self._record_start_time = time.time()
        success = self.recorder.start()
        if success:
            if self.config.show_hud:
                self.hud.set_state("recording")
            self.tray.set_state("recording")
            self.main_window.set_app_state("recording")

    def on_stop_recording(self):
        """Triggered when hotkey or Voice Orb is toggled off."""
        logger.info("Event: on_stop_recording triggered.")
        if not self.recorder.is_recording:
            return

        duration = time.time() - self._record_start_time
        audio_file_path = self.recorder.stop()

        if not audio_file_path:
            self.hud.set_state("hidden")
            self.tray.set_state("ready")
            self.main_window.set_app_state("ready")
            return

        # Back up recorded audio to recovery path so it is never lost on network or API failure
        try:
            recovery_path = str(get_recovery_audio_path())
            if os.path.abspath(audio_file_path) != os.path.abspath(recovery_path):
                shutil.copy2(audio_file_path, recovery_path)
            self._recovery_audio_path = recovery_path
        except Exception as e:
            logger.warning(f"Could not copy audio to recovery buffer: {e}")
            self._recovery_audio_path = audio_file_path

        self._recovery_audio_duration = duration
        self._recovery_audio_available = True

        # Visual state transition
        if self.config.show_hud:
            self.hud.set_state("transcribing")
        self.tray.set_state("transcribing")
        self.main_window.set_app_state("transcribing")

        # Spawn background transcription worker
        self._current_groq_worker = GroqWorker(self.config, audio_file_path)
        self._current_groq_worker.status_changed.connect(self._on_groq_status_changed)
        self._current_groq_worker.completed.connect(lambda text: self._on_transcription_completed(text, duration))
        self._current_groq_worker.error.connect(self._on_groq_error)
        self._current_groq_worker.start()

    def _on_groq_status_changed(self, status: str):
        if self.config.show_hud:
            self.hud.set_state(status)
        self.tray.set_state(status)
        self.main_window.set_app_state(status)

    def _on_transcription_completed(self, finalized_text: str, duration: float):
        """Inject text into active window or copy to clipboard if no text box is focused."""
        logger.info(f"Transcription completed ({len(finalized_text)} chars). Dispatching...")

        if not finalized_text.strip():
            self.hud.set_state("hidden")
            self.tray.set_state("ready")
            self.main_window.set_app_state("ready")
            return

        # Mark recovery audio as successfully transcribed
        self._set_recovery_state(False)

        # Save to history
        self.history.add_entry(finalized_text, duration)
        self.tray.set_state("done")
        self.main_window.set_app_state("ready")

        # Smart injection: if active text box is focused -> inject and restore clipboard.
        # If no active text box is focused -> copy directly to clipboard and notify.
        success, action = self.injector.inject_or_clipboard(finalized_text)

        if action == "copied_to_clipboard":
            logger.info("Transcribed text copied to clipboard (no active text box).")
            if self.config.show_hud:
                self.hud.set_state("done", message="Copied to clipboard (no text box active)")
            self.tray.notify_info("Transcribed text copied to clipboard (no active text box).")
        elif action == "injected":
            logger.info("Transcribed text injected directly into active text box.")
            if self.config.show_hud:
                self.hud.set_state("done", message="Injected!")
        elif action == "fallback_copied":
            logger.warning("Keystroke injection into active text box failed; fallback to clipboard.")
            if self.config.show_hud:
                self.hud.set_state("done", message="Copied to clipboard")
            self.tray.notify_warning("Could not inject text directly. Copied to clipboard.")
        else:
            if self.config.show_hud:
                self.hud.set_state("done", message="Done")

    def _on_groq_error(self, error_message: str):
        logger.error(f"Groq API Error: {error_message}")
        self._last_error = error_message
        diagnostic = diagnose_error(error_message)

        # Mark recovery audio available so user can retry without speaking again
        has_recovery = bool(self._recovery_audio_path and os.path.isfile(self._recovery_audio_path))
        self._set_recovery_state(has_recovery, self._recovery_audio_duration)

        if self.config.show_hud:
            self.hud.set_error(
                message=diagnostic.title,
                error_details=error_message,
                recovery_available=has_recovery
            )
        self.tray.notify_error(f"{diagnostic.title}. Click HUD to retry or view solutions.")
        self.main_window.set_app_state("ready")

    def retry_transcription(self):
        """Re-run transcription using the temporarily preserved audio buffer without re-recording."""
        if not self._recovery_audio_path or not os.path.isfile(self._recovery_audio_path):
            logger.warning("No recovery audio available to retry.")
            self.tray.notify_warning("No saved audio available to retry.")
            return

        logger.info(f"Retrying transcription with saved recovery audio ({self._recovery_audio_duration:.2f}s): {self._recovery_audio_path}")

        if self.config.show_hud:
            self.hud.set_state("transcribing", message="Retrying transcription...")
        self.tray.set_state("transcribing")
        self.main_window.set_app_state("transcribing")

        # Spawn background transcription worker with saved audio file
        self._current_groq_worker = GroqWorker(self.config, self._recovery_audio_path)
        self._current_groq_worker.status_changed.connect(self._on_groq_status_changed)
        self._current_groq_worker.completed.connect(
            lambda text: self._on_transcription_completed(text, self._recovery_audio_duration)
        )
        self._current_groq_worker.error.connect(self._on_groq_error)
        self._current_groq_worker.start()

    def _set_recovery_state(self, available: bool, duration: float = 0.0):
        """Update UI affordances across Tray, MainWindow, and HUD when recovery audio state changes."""
        self._recovery_audio_available = available
        self.tray.set_recovery_audio_available(available, duration)
        self.main_window.set_recovery_audio_available(available, duration)

    def show_troubleshooting_dialog(self, error_details: Optional[str] = None):
        """Display the interactive troubleshooting and solutions dialog."""
        if error_details and str(error_details).strip():
            diagnostic = diagnose_error(str(error_details).strip())
        else:
            # When opened from tray or settings menu without an active error, show common troubleshooting
            diagnostic = get_common_diagnostic("api_key")

        has_recovery = bool(
            self._recovery_audio_path and
            os.path.isfile(self._recovery_audio_path) and
            self._recovery_audio_available
        )

        dialog = TroubleshootingDialog(
            self.main_window,
            diagnostic=diagnostic,
            config=self.config,
            recovery_audio_path=self._recovery_audio_path if has_recovery else None,
            recovery_audio_duration=self._recovery_audio_duration
        )
        dialog.open_settings_requested.connect(self._on_solutions_open_settings)
        dialog.simulate_error_requested.connect(self.simulate_error)
        dialog.retry_transcription_requested.connect(self.retry_transcription)
        dialog.exec()

    def simulate_error(self, error_msg: str):
        """Simulate an error scenario on the HUD and tray to test error handling."""
        logger.info(f"Triggering simulated error for user testing: {error_msg}")
        self._on_groq_error(error_msg)

    def _on_solutions_open_settings(self, tab_index: int = 2):
        self.main_window._switch_tab(tab_index)
        self.show_main_window()

    def on_hotkey_error(self, error_message: str):
        logger.error(f"Hotkey Error: {error_message}")
        self.tray.notify_error(error_message)

    def on_recorder_error(self, error_message: str):
        logger.error(f"Recorder Error: {error_message}")
        self.tray.notify_error(error_message)
        self.main_window.set_app_state("ready")

    def on_settings_changed(self, new_config: AppConfig):
        """Update runtime components when preferences change."""
        self.config = new_config
        self.recorder.sample_rate = self.config.sample_rate
        self.recorder.set_device(self.config.audio_device)
        self.injector.inject_delay = self.config.inject_delay
        self.hotkey_listener.update_config(self.config)
        self.tray.config = self.config
        self.tray.update_tooltip("Ready")
        self.tray._build_menu()
        logger.info("Application preferences reloaded.")

    def _check_startup_updates(self):
        """Asynchronously query GitHub Releases on startup in background."""
        logger.info("Checking for FreeFlow updates on startup...")
        self.updater = UpdateManager(APP_VERSION, self)
        self.updater.update_available.connect(self._on_startup_update_available)
        self.updater.check_for_updates()

    def _manual_check_updates(self):
        """Trigger update check from system tray menu."""
        logger.info("Manual update check requested from tray.")
        self.updater = UpdateManager(APP_VERSION, self)
        self.updater.update_available.connect(self._on_startup_update_available)
        self.updater.up_to_date.connect(
            lambda: self.tray.send_desktop_notification(
                "FreeFlow Updates", "FreeFlow is up to date!", icon="dialog-information"
            )
        )
        self.updater.check_error.connect(
            lambda err: self.tray.notify_error("Could not check for updates.")
        )
        self.updater.check_for_updates()

    def _on_startup_update_available(self, tag: str, notes: str, asset: dict):
        logger.info(f"Update available: {tag} (auto_update_mode={self.config.auto_update_mode})")
        self.main_window.show_update_banner(tag, notes, self.updater)

        if self.config.auto_update_mode == "auto":
            # Auto-update: download asset quietly in background, then prompt to restart
            logger.info(f"Auto-update enabled: downloading {tag} in background...")
            self.updater.download_finished.connect(
                lambda path: self._prompt_restart_after_download(tag)
            )
            self.updater.start_download()
        else:
            # Ask before updating: notify user
            self.tray.send_desktop_notification(
                title="FreeFlow Update Available",
                message=f"FreeFlow {tag} is available! Open FreeFlow to update.",
                icon="system-software-update",
                urgency="normal",
                expire_ms=6000
            )

    def _prompt_restart_after_download(self, tag: str):
        """Prompt user with restart dialog once background download finishes."""
        ans = QMessageBox.question(
            self.main_window if self.main_window.isVisible() else None,
            "FreeFlow Update Ready",
            f"FreeFlow {tag} has been downloaded and is ready to apply!\n\n"
            f"Restart the FreeFlow app now to complete the update?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.updater.apply_update_and_restart()

    def quit(self):
        """Clean application shutdown."""
        logger.info("Quitting FreeFlow...")
        self.guard.cleanup()
        self.hotkey_listener.stop()
        if self.recorder.is_recording:
            self.recorder.stop()
        self.hud.hide_hud()
        self.tray.hide()
        self.main_window.hide()
        self.qapp.quit()


def parse_arguments():
    """Parse command line flags."""
    parser = argparse.ArgumentParser(
        description="FreeFlow — Global Voice-to-Text Transcription Desktop Application"
    )
    parser.add_argument(
        "--minimized",
        action="store_true",
        help="Start FreeFlow minimized to the system tray (used for autostart on boot)"
    )
    parser.add_argument(
        "--autostart",
        action="store_true",
        help="Indicates FreeFlow was launched automatically on system login/boot"
    )
    parser.add_argument(
        "--settings",
        action="store_true",
        help="Open directly to the Settings preferences tab"
    )
    parser.add_argument(
        "--setup", "--wizard",
        action="store_true",
        dest="setup",
        help="Launch the first-time setup onboarding wizard directly"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"FreeFlow {APP_VERSION}"
    )
    return parser.parse_args()


def main():
    """Application entry point."""
    args = parse_arguments()

    app = QApplication(sys.argv)
    freeflow = FreeFlowApplication(
        app,
        start_minimized=args.minimized,
        is_autostart=args.autostart
    )

    if args.setup:
        freeflow.open_onboarding_wizard()
    elif args.settings:
        freeflow.open_settings()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
