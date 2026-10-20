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
from ui.shortcut_recorder import ShortcutRecorderWidget

logger = logging.getLogger("FreeFlow.Settings")


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

        layout.addWidget(sys_group)
        layout.addStretch()

    def _setup_ai_tab(self):
        layout = QVBoxLayout(self.tab_ai)
        form = QFormLayout()

        # Whisper Model
        self.combo_whisper = QComboBox()
        self.combo_whisper.addItem("whisper-large-v3 (Highest Accuracy, Multilingual)", "whisper-large-v3")
        self.combo_whisper.addItem("whisper-large-v3-turbo (Fast & Accurate)", "whisper-large-v3-turbo")
        self.combo_whisper.addItem("distil-whisper-large-v3-en (Ultra-fast English)", "distil-whisper-large-v3-en")
        w_idx = self.combo_whisper.findData(self.config.transcription_model)
        if w_idx >= 0:
            self.combo_whisper.setCurrentIndex(w_idx)
        form.addRow("Speech Model:", self.combo_whisper)

        # Sample Rate
        self.combo_rate = QComboBox()
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
        self.combo_llm = QComboBox()
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

    def _save_settings(self):
        """Save form data into config and persist to disk."""
        self.config.groq_api_key = self.input_api_key.text().strip()
        self.config.hotkey_modifier = self.shortcut_recorder.modifier
        self.config.hotkey_key = self.shortcut_recorder.key
        self.config.hotkey_mode = "hold" if self.radio_hold.isChecked() else "toggle"

        self.config.show_hud = self.chk_hud.isChecked()
        self.config.enable_notifications = self.chk_notify.isChecked()
        
        # Handle autostart change
        old_autostart = self.config.autostart
        new_autostart = self.chk_autostart.isChecked()
        self.config.autostart = new_autostart
        if old_autostart != new_autostart:
            self._update_systemd_autostart(new_autostart)

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

    def _update_systemd_autostart(self, enable: bool):
        """Enable or disable systemd user service."""
        cmd = ["systemctl", "--user", "enable" if enable else "disable", "freeflow.service"]
        try:
            subprocess.run(cmd, capture_output=True, timeout=3.0)
            logger.info(f"Updated systemd autostart: {enable}")
        except Exception as e:
            logger.debug(f"Could not update systemd service autostart: {e}")
