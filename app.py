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
import sys
import time
from pathlib import Path

# Add project root to Python search path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging to both console and user log file
LOG_FILE = "/tmp/freeflow.log"
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
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication
except ImportError:
    print("Error: PyQt6 is not installed. Please run './setup.sh' to install all dependencies.")
    sys.exit(1)

from core.config import AppConfig
from core.groq_client import GroqWorker
from core.history import HistoryManager
from core.hotkey import HotkeyListener
from core.injector import TextInjector
from core.recorder import AudioRecorder
from core.single_instance import SingleInstanceGuard
from ui.hud import RecordingHUD
from ui.main_window import MainWindow
from ui.onboarding import OnboardingWizard
from ui.tray import SystemTrayController

APP_VERSION = "1.0.0"


class FreeFlowApplication:
    """
    Main Application Controller.
    Manages the Wispr Flow Hub window, floating HUD capsule, tray icon,
    single-instance IPC, audio recording, Whisper transcription, and text injection.
    """

    def __init__(self, qapp: QApplication, start_minimized: bool = False):
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

        logger.info(f"Initializing FreeFlow Linux v{APP_VERSION}...")

        # 1. Single Instance Guard
        self.guard = SingleInstanceGuard(self.qapp)
        self.guard.activation_requested.connect(self.on_activation_requested)
        if not self.guard.acquire():
            logger.info("Existing instance active. Second instance terminated.")
            sys.exit(0)

        # 2. Load Configuration & History
        self.config = AppConfig.load()
        self.history = HistoryManager()
        self._record_start_time = 0.0

        # 3. Instantiate Core Workers
        self.recorder = AudioRecorder(
            sample_rate=self.config.sample_rate,
            channels=self.config.channels
        )
        self.injector = TextInjector(
            inject_delay=self.config.inject_delay,
            use_clipboard=self.config.use_clipboard_injection,
            restore_clipboard=self.config.restore_clipboard
        )
        self.hotkey_listener = HotkeyListener(self.config)

        # 4. Instantiate UI Components
        self.hud = RecordingHUD()
        self.tray = SystemTrayController(self.config)
        self.main_window = MainWindow(self.config, self.history)
        self._current_groq_worker: GroqWorker = None

        # 5. Wire Signals
        self._connect_signals()

        # 6. Start Global Hotkey Listener
        self.hotkey_listener.start()

        # 7. Show Tray
        self.tray.show()

        # 8. First-Time Setup / Out of the Box Experience (OOBE):
        # If user has not completed setup wizard or has not yet entered their Groq API key,
        # guide them through the onboarding experience immediately.
        if not self.config.first_run_completed or not self.config.groq_api_key:
            logger.info("First run or missing API key detected. Launching Onboarding Wizard...")
            QTimer.singleShot(150, self.open_onboarding_wizard)
        else:
            should_show = not (start_minimized or (self.config.autostart and self.config.start_minimized and "--minimized" in sys.argv))
            if should_show:
                self.main_window.show()
                self.main_window.raise_()
                self.main_window.activateWindow()

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

        # System Tray Actions
        self.tray.open_hub_requested.connect(self.show_main_window)
        self.tray.open_settings_requested.connect(self.open_settings)
        self.tray.toggle_recording_requested.connect(self.hotkey_listener.trigger_toggle_manual)
        self.tray.quit_requested.connect(self.quit)

        # Main Window Hub Actions
        self.main_window.toggle_recording_requested.connect(self.hotkey_listener.trigger_toggle_manual)
        self.main_window.settings_changed.connect(self.on_settings_changed)
        self.main_window.quit_requested.connect(self.quit)

    def on_activation_requested(self, msg: str):
        """Brings existing FreeFlow window to the front when user clicks app launcher."""
        logger.info("Single-instance activation signal received. Presenting window...")
        self.show_main_window()

    def show_main_window(self):
        """Present the main Wispr Flow Hub window."""
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

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
        """Inject text into active window and save to dictation history."""
        logger.info(f"Transcription completed ({len(finalized_text)} chars). Injecting...")

        if not finalized_text.strip():
            self.hud.set_state("hidden")
            self.tray.set_state("ready")
            self.main_window.set_app_state("ready")
            return

        # Save to history
        self.history.add_entry(finalized_text, duration)

        # Visual feedback
        if self.config.show_hud:
            self.hud.set_state("done")
        self.tray.set_state("done")
        self.main_window.set_app_state("ready")

        # Inject into user's cursor position
        success = self.injector.inject(finalized_text)
        if not success:
            logger.warning("Active window injection failed. Text saved to clipboard buffer.")
            self.tray.notify_error("Could not inject text directly. Copied to clipboard.")

    def _on_groq_error(self, error_message: str):
        logger.error(f"Groq API Error: {error_message}")
        if self.config.show_hud:
            self.hud.set_state("error", message="API Error")
        self.tray.notify_error(f"Transcription failed: {error_message}")
        self.main_window.set_app_state("ready")

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
        self.injector.inject_delay = self.config.inject_delay
        self.hotkey_listener.update_config(self.config)
        self.tray.config = self.config
        self.tray.update_tooltip("Ready")
        self.tray._build_menu()
        logger.info("Application preferences reloaded.")

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
        description="FreeFlow Linux — Global Voice-to-Text Transcription Desktop Application"
    )
    parser.add_argument(
        "--minimized",
        action="store_true",
        help="Start FreeFlow minimized to the system tray (used for autostart on boot)"
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
    freeflow = FreeFlowApplication(app, start_minimized=args.minimized)

    if args.setup:
        freeflow.open_onboarding_wizard()
    elif args.settings:
        freeflow.open_settings()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
