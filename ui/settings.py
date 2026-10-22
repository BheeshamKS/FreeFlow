"""
FreeFlow Settings Dialog
Provides a tabbed preferences window for API keys, global hotkey binding,
model selection, audio parameters, and system startup behavior.
"""

import logging
import os
import subprocess
from pathlib import Path

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import (
        QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
        QFormLayout, QLabel, QLineEdit, QPushButton, QComboBox,
        QRadioButton, QButtonGroup, QCheckBox, QTextEdit,
        QDoubleSpinBox, QMessageBox, QGroupBox
    )
except ImportError:
    class QDialog:
        pass
    def pyqtSignal(*args):
        return None

from core.config import AppConfig
from core.groq_client import GroqService
from core.recorder import list_input_devices
from core.autostart import set_autostart
from core.updater import UpdateManager
from core.version import APP_VERSION
from ui.shortcut_recorder import ShortcutRecorderWidget

logger = logging.getLogger("FreeFlow.Settings")


class NoScrollComboBox(QComboBox):
    """
    QComboBox that ignores mouse wheel scrolling when closed.
    Prevents unintended setting changes when scrolling through preferences pages.
    """
    def wheelEvent(self, event):
        view = self.view()
        if view and view.isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()


class SettingsDialog(QDialog):
    """Tabbed Preferences Dialog for FreeFlow."""

    settings_saved = pyqtSignal(object) if QDialog is not None else None

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config

        self.setWindowTitle("FreeFlow Preferences")
        self.resize(540, 520)

        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget(self)
        main_layout.addWidget(self.tabs)

        # Tab 1: General & Hotkey
        self.tab_general = QWidget()
        self._setup_general_tab()
        self.tabs.addTab(self.tab_general, "General & Hotkeys")

        # Tab 2: Speech & AI Models
        self.tab_ai = QWidget()
        self._setup_ai_tab()
        self.tabs.addTab(self.tab_ai, "AI & Audio")

        # Tab 3: About
        self.tab_about = QWidget()
        self._setup_about_tab()
        self.tabs.addTab(self.tab_about, "About & Help")

        # Bottom Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save & Apply")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.btn_save)

        main_layout.addLayout(btn_layout)

    def _setup_general_tab(self):
        layout = QVBoxLayout(self.tab_general)

        # 1. Groq API Key Group
        api_group = QGroupBox("Groq Cloud API Key")
        api_layout = QVBoxLayout(api_group)

        key_row = QHBoxLayout()
        self.input_api_key = QLineEdit()
        self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_api_key.setText(self.config.groq_api_key)
        self.input_api_key.setPlaceholderText("gsk_...")
        key_row.addWidget(self.input_api_key)

        self.btn_show_key = QPushButton("Show")
        self.btn_show_key.setFixedWidth(65)
        self.btn_show_key.clicked.connect(self._toggle_show_api_key)
        key_row.addWidget(self.btn_show_key)

        self.btn_test_key = QPushButton("Test Connection")
        self.btn_test_key.clicked.connect(self._test_groq_connection)
        key_row.addWidget(self.btn_test_key)

        api_layout.addLayout(key_row)
        hint_label = QLabel("<small>Free API keys can be obtained instantly from <a href='https://console.groq.com'>console.groq.com</a></small>")
        hint_label.setOpenExternalLinks(True)
        api_layout.addWidget(hint_label)
        layout.addWidget(api_group)

        # 2. Hotkey Configuration Group
        hotkey_group = QGroupBox("Global Hotkey Configuration")
        form = QFormLayout(hotkey_group)

        self.shortcut_recorder = ShortcutRecorderWidget(
            modifier=self.config.hotkey_modifier,
            key=self.config.hotkey_key,
            parent=self
        )
        form.addRow("Shortcut:", self.shortcut_recorder)

        # Mode Selection
        mode_layout = QVBoxLayout()
        self.radio_toggle = QRadioButton("Toggle Mode (Press once to start, press again to stop)")
        self.radio_hold = QRadioButton("Hold-to-Talk (Hold key while speaking, release to transcribe)")

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_toggle)
        self.mode_group.addButton(self.radio_hold)

        if self.config.hotkey_mode == "hold":
            self.radio_hold.setChecked(True)
        else:
            self.radio_toggle.setChecked(True)

        mode_layout.addWidget(self.radio_toggle)
        mode_layout.addWidget(self.radio_hold)
        form.addRow("Recording Mode:", mode_layout)

        layout.addWidget(hotkey_group)

        # 3. System Feedback & Autostart
        sys_group = QGroupBox("System & Interface")
        sys_layout = QVBoxLayout(sys_group)

        self.chk_hud = QCheckBox("Show floating waveform HUD overlay during recording")
        self.chk_hud.setChecked(self.config.show_hud)
        sys_layout.addWidget(self.chk_hud)

        self.chk_notify = QCheckBox("Show desktop notifications (notify-send)")
        self.chk_notify.setChecked(self.config.enable_notifications)
        sys_layout.addWidget(self.chk_notify)

        self.chk_autostart = QCheckBox("Start FreeFlow automatically on system login")
        self.chk_autostart.setChecked(self.config.autostart)
        sys_layout.addWidget(self.chk_autostart)

        self.chk_start_minimized = QCheckBox("Start minimized to system tray on boot")
        self.chk_start_minimized.setChecked(self.config.start_minimized)
        sys_layout.addWidget(self.chk_start_minimized)

        self.chk_close_to_tray = QCheckBox("Closing window hides to tray instead of quitting")
        self.chk_close_to_tray.setChecked(self.config.close_to_tray)
        sys_layout.addWidget(self.chk_close_to_tray)

        layout.addWidget(sys_group)

        # 4. Software Updates
        update_group = QGroupBox("Software Updates")
        update_layout = QVBoxLayout(update_group)

        self.chk_updates = QCheckBox("Automatically check for updates on startup")
        self.chk_updates.setChecked(self.config.check_updates_on_startup)
        update_layout.addWidget(self.chk_updates)

        mode_box = QVBoxLayout()
        mode_box.setContentsMargins(16, 2, 0, 4)
        mode_box.setSpacing(4)
        self.radio_update_auto = QRadioButton("Auto-update: Download in background and prompt to restart the app")
        self.radio_update_ask = QRadioButton("Ask before updating: Show notification when update is available")

        self.update_mode_group = QButtonGroup(self)
        self.update_mode_group.addButton(self.radio_update_auto)
        self.update_mode_group.addButton(self.radio_update_ask)

        if self.config.auto_update_mode == "auto":
            self.radio_update_auto.setChecked(True)
        else:
            self.radio_update_ask.setChecked(True)

        mode_box.addWidget(self.radio_update_auto)
        mode_box.addWidget(self.radio_update_ask)
        update_layout.addLayout(mode_box)

        # Update check action row
        check_row = QHBoxLayout()
        lbl_version = QLabel(f"Installed: <b>v{APP_VERSION}</b>")
        check_row.addWidget(lbl_version)
        check_row.addSpacing(10)

        self.lbl_update_status = QLabel("")
        self.lbl_update_status.setStyleSheet("color: #8a8f98; font-size: 12px;")
        check_row.addWidget(self.lbl_update_status, 1)

        self.btn_check_updates = QPushButton("Check for Updates")
        self.btn_check_updates.clicked.connect(self._check_for_updates)
        check_row.addWidget(self.btn_check_updates)
        update_layout.addLayout(check_row)

        layout.addWidget(update_group)
        layout.addStretch()

    def _setup_ai_tab(self):
        layout = QVBoxLayout(self.tab_ai)
        form = QFormLayout()

        # Microphone Device Selection
        mic_layout = QHBoxLayout()
        self.combo_device = NoScrollComboBox()
        self.btn_refresh_mics = QPushButton("Refresh")
        self.btn_refresh_mics.setFixedWidth(75)
        self.btn_refresh_mics.clicked.connect(self._populate_audio_devices)
        mic_layout.addWidget(self.combo_device, 1)
        mic_layout.addWidget(self.btn_refresh_mics)
        form.addRow("Microphone:", mic_layout)
        self._populate_audio_devices()

        # Whisper Model
        self.combo_whisper = NoScrollComboBox()
        self.combo_whisper.addItem("whisper-large-v3 (Highest Accuracy, Multilingual)", "whisper-large-v3")
        self.combo_whisper.addItem("whisper-large-v3-turbo (Fast & Accurate)", "whisper-large-v3-turbo")
        self.combo_whisper.addItem("distil-whisper-large-v3-en (Ultra-fast English)", "distil-whisper-large-v3-en")
        w_idx = self.combo_whisper.findData(self.config.transcription_model)
        if w_idx >= 0:
            self.combo_whisper.setCurrentIndex(w_idx)
        form.addRow("Speech Model:", self.combo_whisper)

        # Sample Rate
        self.combo_rate = NoScrollComboBox()
        self.combo_rate.addItem("16000 Hz (Optimal for Whisper)", 16000)
        self.combo_rate.addItem("44100 Hz (CD Quality)", 44100)
        r_idx = self.combo_rate.findData(self.config.sample_rate)
        if r_idx >= 0:
            self.combo_rate.setCurrentIndex(r_idx)
        form.addRow("Audio Sample Rate:", self.combo_rate)

        # Injection Delay
        self.spin_delay = QDoubleSpinBox()
        self.spin_delay.setRange(0.05, 1.0)
        self.spin_delay.setSingleStep(0.05)
        self.spin_delay.setValue(self.config.inject_delay)
        self.spin_delay.setSuffix(" sec")
        form.addRow("Text Injection Delay:", self.spin_delay)

        layout.addLayout(form)

        # LLM Formatting Box
        llm_group = QGroupBox("LLM Post-Processing (Grammar & Filler-Word Removal)")
        llm_layout = QVBoxLayout(llm_group)

        self.chk_format = QCheckBox("Enable Llama 3 formatting")
        self.chk_format.setChecked(self.config.format_text)
        self.chk_format.toggled.connect(self._on_format_toggled)
        llm_layout.addWidget(self.chk_format)

        form_llm = QFormLayout()
        self.combo_llm = NoScrollComboBox()
        self.combo_llm.addItem("openai/gpt-oss-20b (Recommended, Ultra-Fast)", "openai/gpt-oss-20b")
        self.combo_llm.addItem("qwen/qwen3.8-27b (Fast & Precise)", "qwen/qwen3.8-27b")
        self.combo_llm.addItem("openai/gpt-oss-120b (Comprehensive)", "openai/gpt-oss-120b")
        self.combo_llm.addItem("llama-3.1-8b-instant (Meta Llama 3.1)", "llama-3.1-8b-instant")
        self.combo_llm.addItem("llama3-8b-8192 (Legacy)", "llama3-8b-8192")
        l_idx = self.combo_llm.findData(self.config.format_model)
        if l_idx >= 0:
            self.combo_llm.setCurrentIndex(l_idx)
        else:
            self.combo_llm.addItem(self.config.format_model, self.config.format_model)
            self.combo_llm.setCurrentIndex(self.combo_llm.count() - 1)
        form_llm.addRow("Formatting Model:", self.combo_llm)

        self.btn_fetch_models = QPushButton("Fetch Available Models from Account")
        self.btn_fetch_models.clicked.connect(self._fetch_account_models)
        form_llm.addRow("", self.btn_fetch_models)

        self.txt_prompt = QTextEdit()
        self.txt_prompt.setPlainText(self.config.system_prompt)
        self.txt_prompt.setMaximumHeight(90)
        form_llm.addRow("Prompt:", self.txt_prompt)

        llm_layout.addLayout(form_llm)
        layout.addWidget(llm_group)

        self._on_format_toggled(self.config.format_text)
        layout.addStretch()

    def _setup_about_tab(self):
        layout = QVBoxLayout(self.tab_about)

        info = QLabel(
            "<h2>FreeFlow for Linux</h2>"
            "<p>A lightning-fast, privacy-first voice-to-text dictation application for Linux desktops.</p>"
            "<p><b>How to use:</b></p>"
            "<ol>"
            "<li>Place cursor into any application (browser, terminal, editor).</li>"
            "<li>Press your configured hotkey (default: <b>Alt + R</b>).</li>"
            "<li>Speak clearly into your microphone while the floating HUD pulses.</li>"
            "<li>Press the hotkey again (in Toggle mode) or release it (in Hold mode).</li>"
            "<li>The transcribed, formatted text is instantly injected at your cursor position!</li>"
            "</ol>"
            "<p><b>Display Server Notes:</b></p>"
            "<ul>"
            "<li><b>Wayland:</b> Requires <code>wtype</code> and <code>wl-clipboard</code> for injection.</li>"
            "<li><b>X11:</b> Requires <code>xdotool</code> and <code>xclip</code> for injection.</li>"
            "<li><b>Global Inputs:</b> Requires your user account in the <code>input</code> group.</li>"
            "</ul>"
        )
        info.setWordWrap(True)
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)
        layout.addStretch()

    def _toggle_show_api_key(self):
        if self.input_api_key.echoMode() == QLineEdit.EchoMode.Password:
            self.input_api_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_show_key.setText("Hide")
        else:
            self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_show_key.setText("Show")

    def _fetch_account_models(self):
        """Query Groq API for all models enabled on user's API key and refresh dropdowns."""
        key = self.input_api_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Fetch Models", "Please enter your Groq API key first.")
            return

        from groq import Groq
        try:
            client = Groq(api_key=key)
            models = client.models.list()
            chat_models = []
            whisper_models = []

            for m in models.data:
                mid = m.id.lower()
                if "whisper" in mid:
                    whisper_models.append(m.id)
                elif not any(x in mid for x in ["guard", "moderation", "tts", "embedding"]):
                    chat_models.append(m.id)

            if chat_models:
                self.combo_llm.clear()
                for m in sorted(chat_models):
                    self.combo_llm.addItem(m, m)

            if whisper_models:
                self.combo_whisper.clear()
                for m in sorted(whisper_models):
                    self.combo_whisper.addItem(m, m)

            QMessageBox.information(
                self,
                "Models Fetched",
                f"Successfully loaded {len(chat_models)} chat models and {len(whisper_models)} speech models from your Groq account."
            )
        except Exception as e:
            QMessageBox.warning(self, "Fetch Failed", f"Could not fetch models: {e}")

    def _test_groq_connection(self):
        key = self.input_api_key.text().strip()
        service = GroqService(key)
        self.btn_test_key.setEnabled(False)
        self.btn_test_key.setText("Connecting...")

        try:
            success, msg = service.test_connection()
            if success:
                QMessageBox.information(self, "Groq Connection", msg)
            else:
                QMessageBox.warning(self, "Groq Connection", msg)
        finally:
            self.btn_test_key.setEnabled(True)
            self.btn_test_key.setText("Test Connection")

    def _on_format_toggled(self, checked: bool):
        self.combo_llm.setEnabled(checked)
        self.txt_prompt.setEnabled(checked)

    def _populate_audio_devices(self):
        """Query connected microphones and populate the device selector dropdown."""
        curr_device = self.config.audio_device
        self.combo_device.clear()
        self.combo_device.addItem("System Default Microphone", "")
        
        devices = list_input_devices()
        selected_idx = 0
        for i, dev in enumerate(devices):
            display = f"{dev['name']} ({dev['channels']} ch)"
            if dev.get('default'):
                display += " [Default]"
            self.combo_device.addItem(display, dev['name'])
            if curr_device and curr_device.strip() == dev['name'].strip():
                selected_idx = i + 1

        self.combo_device.setCurrentIndex(selected_idx)

    def _check_for_updates(self):
        """Initiate manual update check."""
        self.btn_check_updates.setEnabled(False)
        self.lbl_update_status.setText("Checking GitHub...")
        self.lbl_update_status.setStyleSheet("color: #8a8f98; font-size: 12px;")

        self._settings_updater = UpdateManager(APP_VERSION, self)
        self._settings_updater.update_available.connect(self._on_settings_update_available)
        self._settings_updater.up_to_date.connect(self._on_settings_up_to_date)
        self._settings_updater.check_error.connect(self._on_settings_check_error)
        self._settings_updater.check_for_updates()

    def _on_settings_update_available(self, tag: str, notes: str, asset: dict):
        self.btn_check_updates.setEnabled(True)
        self.lbl_update_status.setText(f"Update {tag} is available!")
        self.lbl_update_status.setStyleSheet("color: #10b981; font-weight: 600; font-size: 12px;")
        
        ans = QMessageBox.question(
            self,
            "FreeFlow Update Available",
            f"A newer version ({tag}) of FreeFlow is available!\n\n"
            f"Would you like to download and install this update automatically now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if ans == QMessageBox.StandardButton.Yes:
            self._start_update_download(self._settings_updater)

    def _on_settings_up_to_date(self):
        self.btn_check_updates.setEnabled(True)
        self.lbl_update_status.setText("FreeFlow is up to date.")
        self.lbl_update_status.setStyleSheet("color: #8a8f98; font-size: 12px;")

    def _on_settings_check_error(self, err: str):
        self.btn_check_updates.setEnabled(True)
        self.lbl_update_status.setText("Could not reach GitHub.")
        self.lbl_update_status.setStyleSheet("color: #ef4444; font-size: 12px;")

    def _start_update_download(self, updater: UpdateManager):
        self.lbl_update_status.setText("Downloading update...")
        self.btn_check_updates.setEnabled(False)
        updater.download_progress.connect(lambda pct: self.lbl_update_status.setText(f"Downloading: {pct}%"))
        updater.download_finished.connect(lambda path: self._on_download_ready(updater))
        updater.download_error.connect(lambda err: self._on_download_err(err))
        updater.start_download()

    def _on_download_ready(self, updater: UpdateManager):
        self.lbl_update_status.setText("Update ready. Restarting...")
        ans = QMessageBox.information(
            self,
            "Update Ready",
            "Update downloaded successfully! The FreeFlow app will now restart to apply changes.",
            QMessageBox.StandardButton.Ok
        )
        updater.apply_update_and_restart()

    def _on_download_err(self, err: str):
        self.btn_check_updates.setEnabled(True)
        self.lbl_update_status.setText("Download failed.")
        self.lbl_update_status.setStyleSheet("color: #ef4444; font-size: 12px;")
        QMessageBox.warning(self, "Update Error", f"Failed to download update:\n{err}")

    def _save_settings(self):
        """Save form data into config and persist to disk."""
        self.config.groq_api_key = self.input_api_key.text().strip()
        self.config.hotkey_modifier = self.shortcut_recorder.modifier
        self.config.hotkey_key = self.shortcut_recorder.key
        self.config.hotkey_mode = "hold" if self.radio_hold.isChecked() else "toggle"

        self.config.show_hud = self.chk_hud.isChecked()
        self.config.enable_notifications = self.chk_notify.isChecked()
        
        # Handle autostart and minimize on boot
        self.config.autostart = self.chk_autostart.isChecked()
        self.config.start_minimized = self.chk_start_minimized.isChecked()
        self.config.close_to_tray = self.chk_close_to_tray.isChecked()
        set_autostart(self.config.autostart, self.config.start_minimized)

        # Handle audio device
        self.config.audio_device = self.combo_device.currentData() or None

        # Handle update preferences
        self.config.check_updates_on_startup = self.chk_updates.isChecked()
        self.config.auto_update_mode = "auto" if self.radio_update_auto.isChecked() else "ask"

        self.config.transcription_model = self.combo_whisper.currentData()
        self.config.sample_rate = int(self.combo_rate.currentData())
        self.config.inject_delay = float(self.spin_delay.value())

        self.config.format_text = self.chk_format.isChecked()
        self.config.format_model = self.combo_llm.currentData()
        self.config.system_prompt = self.txt_prompt.toPlainText().strip()

        # Persist to QSettings
        self.config.save()

        if self.settings_saved:
            self.settings_saved.emit(self.config)

        self.accept()
