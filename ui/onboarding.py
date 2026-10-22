"""
FreeFlow First-Run Onboarding Wizard & Out of the Box Experience (OOBE)
========================================================================
Designed with a strict Raycast / Linear design aesthetic (taste-skill).
Features bespoke interactive step pills, tactile emerald primary buttons,
elevated dark secondary buttons, and instant feedback.
"""

import logging
import subprocess
from typing import Optional, List

try:
    from PyQt6.QtCore import Qt, pyqtSignal, QUrl
    from PyQt6.QtGui import QColor, QFont, QDesktopServices, QCursor
    from PyQt6.QtWidgets import (
        QDialog, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
        QPushButton, QLabel, QLineEdit, QRadioButton, QButtonGroup,
        QCheckBox, QFrame, QMessageBox, QApplication
    )
except ImportError:
    class QDialog:
        pass
    def pyqtSignal(*args):
        return None

from core.config import AppConfig
from core.groq_client import GroqService
from core.platform import is_linux, is_macos, is_windows, get_platform
from core.autostart import set_autostart
from ui.shortcut_recorder import ShortcutRecorderWidget

logger = logging.getLogger("FreeFlow.Onboarding")


# ==============================================================================
# Bespoke Interactive Stepper Pill Button
# ==============================================================================
class StepPillButton(QPushButton):
    """
    Interactive segmented step pill button in the onboarding header.
    Shows completion checkmark, active glowing dot, or subtle inactive state.
    Allows user to click and jump directly between setup steps.
    """

    step_clicked = pyqtSignal(int) if QPushButton is not None else None

    def __init__(self, step_idx: int, label: str, parent=None):
        super().__init__(label, parent)
        self.step_idx = step_idx
        self.raw_label = label
        self.is_active = False
        self.is_completed = False
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda: self.step_clicked.emit(self.step_idx) if self.step_clicked else None)
        self.update_style()

    def set_state(self, is_active: bool, is_completed: bool):
        self.is_active = is_active
        self.is_completed = is_completed
        self.update_style()

    def update_style(self):
        if self.is_active:
            self.setText(f"● {self.raw_label}")
            self.setStyleSheet("""
                QPushButton {
                    background-color: #12241b;
                    color: #34d399;
                    border: 1px solid #10b981;
                    border-radius: 16px;
                    padding: 4px 14px;
                    font-size: 12px;
                    font-weight: 600;
                    letter-spacing: -0.2px;
                }
                QPushButton:hover {
                    background-color: #162e22;
                    border-color: #34d399;
                }
            """)
        elif self.is_completed:
            self.setText(f"✓ {self.raw_label}")
            self.setStyleSheet("""
                QPushButton {
                    background-color: #14171f;
                    color: #10b981;
                    border: 1px solid #232838;
                    border-radius: 16px;
                    padding: 4px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #1c212c;
                    border-color: #384257;
                    color: #34d399;
                }
            """)
        else:
            self.setText(self.raw_label)
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #62666d;
                    border: 1px solid transparent;
                    border-radius: 16px;
                    padding: 4px 10px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #14161c;
                    color: #9ca3af;
                }
            """)


# ==============================================================================
# First-Run Onboarding Wizard Window
# ==============================================================================
class OnboardingWizard(QDialog):
    """
    First-Time Startup / Out-of-the-Box Experience Wizard for FreeFlow.
    Guides the user through connecting Groq, choosing hotkeys, and launch preferences.
    """

    wizard_completed = pyqtSignal(object) if QDialog is not None else None

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_step = 0

        self.setWindowTitle("Welcome to FreeFlow")
        self.setFixedSize(780, 600)
        self.setModal(True)

        self._apply_global_theme()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. Top Header with Interactive Step Pills
        self.header = self._build_header()
        root.addWidget(self.header)

        # 2. Main Step Stack
        self.stack = QStackedWidget(self)
        self.step_welcome = self._build_step_welcome()
        self.step_engine = self._build_step_engine()
        self.step_shortcut = self._build_step_shortcut()
        self.step_finish = self._build_step_finish()

        self.stack.addWidget(self.step_welcome)   # 0
        self.stack.addWidget(self.step_engine)    # 1
        self.stack.addWidget(self.step_shortcut)  # 2
        self.stack.addWidget(self.step_finish)    # 3
        root.addWidget(self.stack)

        # 3. Bottom Navigation Bar
        self.nav_bar = self._build_nav_bar()
        root.addWidget(self.nav_bar)

        self._update_step_state()

    def _apply_global_theme(self):
        """Strict Raycast/Linear design tokens with robust selectors."""
        self.setStyleSheet("""
            QDialog {
                background-color: #08090b;
                color: #f4f4f6;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QFrame#HeaderBar {
                background-color: #0c0d10;
                border-bottom: 1px solid #181a20;
            }
            QFrame#NavBar {
                background-color: #0c0d10;
                border-top: 1px solid #181a20;
            }
            QFrame#SurfaceCard, QFrame[surface="true"] {
                background-color: #0f1115;
                border: 1px solid #1c1f26;
                border-radius: 10px;
            }
            QLineEdit {
                background-color: #0f1115;
                color: #f4f4f6;
                border: 1px solid #1f232c;
                border-radius: 8px;
                padding: 9px 12px;
                font-size: 13px;
                selection-background-color: #10b981;
            }
            QLineEdit:focus {
                border: 1px solid #10b981;
                background-color: #12141a;
            }
            QCheckBox, QRadioButton {
                color: #d0d6e0;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 16px;
                height: 16px;
                background-color: #0f1115;
                border: 1px solid #22252e;
                border-radius: 4px;
            }
            QRadioButton::indicator {
                border-radius: 8px;
            }
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {
                background-color: #10b981;
                border-color: #10b981;
            }
        """)

    # --------------------------------------------------------------------------
    # Header & Interactive Stepper
    # --------------------------------------------------------------------------
    def _build_header(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("HeaderBar")
        bar.setFixedHeight(68)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(32, 0, 32, 0)

        # Brand mark
        brand_box = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet("color: #10b981; font-size: 14px; margin-right: 4px;")
        brand_box.addWidget(dot)

        brand_title = QLabel("FreeFlow Setup")
        brand_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #f4f4f6; letter-spacing: -0.3px;")
        brand_box.addWidget(brand_title)
        layout.addLayout(brand_box)

        layout.addStretch()

        # Step indicator pills
        self.step_buttons: List[StepPillButton] = []
        step_names = ["Welcome", "Speech Engine", "Shortcut", "Preferences"]
        stepper_box = QHBoxLayout()
        stepper_box.setSpacing(6)

        for i, name in enumerate(step_names):
            if i > 0:
                arrow = QLabel("›")
                arrow.setStyleSheet("color: #3f3f46; font-size: 14px; margin: 0 2px;")
                stepper_box.addWidget(arrow)

            btn = StepPillButton(i, f"{i+1} {name}", self)
            btn.step_clicked.connect(self._jump_to_step)
            stepper_box.addWidget(btn)
            self.step_buttons.append(btn)

        layout.addLayout(stepper_box)
        return bar

    def _build_nav_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("NavBar")
        bar.setFixedHeight(72)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(32, 0, 32, 0)
        layout.setSpacing(12)

        self.btn_skip = QPushButton("Skip Setup")
        self.btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_skip.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #71717a;
                border: none;
                font-size: 12px;
                font-weight: 500;
                padding: 8px 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                color: #f4f4f6;
                background-color: #14161c;
            }
        """)
        self.btn_skip.clicked.connect(self._skip_wizard)
        layout.addWidget(self.btn_skip)

        layout.addStretch()

        self.btn_back = QPushButton("← Back")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #14171f;
                color: #d0d6e0;
                border: 1px solid #232836;
                border-radius: 8px;
                padding: 10px 22px;
                font-size: 13px;
                font-weight: 500;
                min-width: 85px;
            }
            QPushButton:hover {
                background-color: #1c212c;
                border-color: #3b4559;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #11131a;
            }
        """)
        self.btn_back.clicked.connect(self._on_back)
        layout.addWidget(self.btn_back)

        self.btn_next = QPushButton("Continue →")
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #022c22;
                border: 1px solid #10b981;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 600;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #059669;
                border-color: #059669;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #047857;
                border-color: #047857;
            }
        """)
        self.btn_next.clicked.connect(self._on_next)
        layout.addWidget(self.btn_next)

        return bar

    def _update_step_state(self):
        self.stack.setCurrentIndex(self.current_step)

        # Update step pills
        for i, btn in enumerate(self.step_buttons):
            btn.set_state(is_active=(i == self.current_step), is_completed=(i < self.current_step))

        # Button states
        self.btn_back.setVisible(self.current_step > 0)
        if self.current_step == 3:
            self.btn_next.setText("Complete & Launch FreeFlow ✓")
            self.btn_skip.setVisible(False)
        else:
            self.btn_next.setText("Continue →")
            self.btn_skip.setVisible(True)

    def _jump_to_step(self, step_idx: int):
        # Allow navigating to previously completed steps or next step
        if step_idx <= self.current_step or step_idx == self.current_step + 1:
            self.current_step = step_idx
            self._update_step_state()

    def _on_back(self):
        if self.current_step > 0:
            self.current_step -= 1
            self._update_step_state()

    def _on_next(self):
        # Validate current step before advancing
        if self.current_step == 1:
            key = self.input_api_key.text().strip()
            if not key:
                ans = QMessageBox.question(
                    self, "Groq API Key Required",
                    "You haven't entered a Groq API key yet. FreeFlow requires a key for speech transcription.\n\n"
                    "Would you like to continue anyway and enter it later in Settings?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if ans != QMessageBox.StandardButton.Yes:
                    return
            self.config.groq_api_key = key

        elif self.current_step == 2:
            self.config.hotkey_modifier = self.shortcut_widget.modifier
            self.config.hotkey_key = self.shortcut_widget.key
            self.config.hotkey_mode = "hold" if self.radio_hold.isChecked() else "toggle"
            self.config.show_hud = self.chk_show_hud.isChecked()

        elif self.current_step == 3:
            self._finish_onboarding()
            return

        self.current_step += 1
        self._update_step_state()

    def _skip_wizard(self):
        ans = QMessageBox.question(
            self, "Skip Setup",
            "Are you sure you want to exit setup? You can configure shortcuts and your API key later in Settings.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.config.first_run_completed = True
            self.config.save()
            self.accept()

    def _finish_onboarding(self):
        self.config.autostart = self.chk_autostart.isChecked()
        self.config.start_minimized = self.chk_start_minimized.isChecked()
        self.config.close_to_tray = self.chk_close_to_tray.isChecked()
        self.config.first_run_completed = True

        set_autostart(self.config.autostart, self.config.start_minimized)

        self.config.save()
        logger.info("First-run onboarding completed successfully.")

        if self.wizard_completed:
            self.wizard_completed.emit(self.config)

        self.accept()

    # --------------------------------------------------------------------------
    # Step 1: Welcome & Architectural Overview
    # --------------------------------------------------------------------------
    def _build_step_welcome(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(44, 32, 44, 28)
        layout.setSpacing(20)

        # Title
        plat_title = "macOS" if is_macos() else ("Windows" if is_windows() else "Linux")
        t = QLabel(f"Voice-to-Text Dictation, Built for {plat_title}")
        t.setStyleSheet("font-size: 22px; font-weight: 700; color: #f4f4f6; letter-spacing: -0.4px;")
        layout.addWidget(t)

        sub = QLabel(
            "FreeFlow brings effortless, instant voice dictation straight to your desktop, "
            "powered by Groq's ultra-low latency Whisper Large v3 LPU inference."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 13px; color: #8a8f98; line-height: 1.5;")
        layout.addWidget(sub)

        # Comparison / Feature 2x2 Grid
        grid_frame = QFrame()
        grid_frame.setObjectName("SurfaceCard")
        grid_layout = QVBoxLayout(grid_frame)
        grid_layout.setContentsMargins(20, 16, 20, 16)
        grid_layout.setSpacing(14)

        row1 = QHBoxLayout()
        row1.setSpacing(24)
        c1 = self._build_feature_item(
            "Sub-Second Latency (~300ms)",
            "Groq LPUs process your spoken audio in ~300ms, transcribing up to 10× faster than typical cloud speech APIs."
        )
        if is_macos():
            inj_desc = "Injects text straight into your cursor across any Mac application via native accessibility paste."
        elif is_windows():
            inj_desc = "Injects text straight into your cursor in any application or terminal via native Windows input hooks."
        else:
            inj_desc = "Injects text straight into your cursor across Wayland (wl-clipboard/wtype) and X11 (xclip/xdotool)."

        c2 = self._build_feature_item(
            "Universal Cursor Injection",
            inj_desc
        )
        row1.addWidget(c1)
        row1.addWidget(c2)
        grid_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(24)
        c3 = self._build_feature_item(
            "Zero GPU & Battery Drain",
            "Unlike local Whisper models that heat up CPU/GPU and drain battery, FreeFlow is lightweight and instant."
        )
        c4 = self._build_feature_item(
            "100% Private Local History",
            "Transcripts are stored locally on your device (~/.config/freeflow/history.json). Audio is never retained."
        )
        row2.addWidget(c3)
        row2.addWidget(c4)
        grid_layout.addLayout(row2)

        layout.addWidget(grid_frame)

        # In-page CTA button
        cta_row = QHBoxLayout()
        btn_welcome_cta = QPushButton("Get Started with Speech Engine →")
        btn_welcome_cta.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_welcome_cta.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #022c22;
                border: 1px solid #10b981;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #059669;
                border-color: #059669;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """)
        btn_welcome_cta.clicked.connect(self._on_next)
        cta_row.addWidget(btn_welcome_cta)
        cta_row.addStretch()
        layout.addLayout(cta_row)

        layout.addStretch()
        return page

    def _build_feature_item(self, heading: str, body: str) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(4)

        h = QLabel(heading)
        h.setStyleSheet("font-size: 13px; font-weight: 600; color: #10b981;")
        l.addWidget(h)

        b = QLabel(body)
        b.setWordWrap(True)
        b.setStyleSheet("font-size: 12px; color: #8a8f98; line-height: 1.4;")
        l.addWidget(b)
        return w

    # --------------------------------------------------------------------------
    # Step 2: Speech Engine & Groq API Key
    # --------------------------------------------------------------------------
    def _build_step_engine(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(44, 32, 44, 28)
        layout.setSpacing(18)

        t = QLabel("Connect Speech Engine")
        t.setStyleSheet("font-size: 22px; font-weight: 700; color: #f4f4f6; letter-spacing: -0.4px;")
        layout.addWidget(t)

        sub = QLabel(
            "FreeFlow uses Groq Cloud's Whisper Large v3 engine for speech-to-text. "
            "Groq provides free developer keys with generous rate limits and requires no credit card."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 13px; color: #8a8f98; line-height: 1.5;")
        layout.addWidget(sub)

        # External Link Banner Card
        link_card = QFrame()
        link_card.setObjectName("SurfaceCard")
        lc_layout = QHBoxLayout(link_card)
        lc_layout.setContentsMargins(20, 16, 20, 16)
        lc_layout.setSpacing(14)

        text_side = QVBoxLayout()
        text_side.setSpacing(3)
        l_title = QLabel("Need a Free Groq API Key?")
        l_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #f4f4f6;")
        l_desc = QLabel("Sign in to the Groq Console and generate a free API key in 30 seconds.")
        l_desc.setStyleSheet("font-size: 12px; color: #8a8f98;")
        text_side.addWidget(l_title)
        text_side.addWidget(l_desc)
        lc_layout.addLayout(text_side)

        lc_layout.addStretch()

        btn_open_console = QPushButton("Open Groq Console")
        btn_open_console.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_console.setStyleSheet("""
            QPushButton {
                background-color: #14171f;
                color: #34d399;
                border: 1px solid #1e3328;
                border-radius: 8px;
                padding: 9px 18px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #172c21;
                border-color: #10b981;
                color: #10b981;
            }
            QPushButton:pressed {
                background-color: #0f1c15;
            }
        """)
        btn_open_console.clicked.connect(self._open_groq_console)
        lc_layout.addWidget(btn_open_console)
        layout.addWidget(link_card)

        # Key Input Card
        input_card = QFrame()
        input_card.setObjectName("SurfaceCard")
        ic_layout = QVBoxLayout(input_card)
        ic_layout.setContentsMargins(20, 18, 20, 18)
        ic_layout.setSpacing(12)

        lbl_input = QLabel("Enter your Groq API Key:")
        lbl_input.setStyleSheet("font-size: 13px; font-weight: 500; color: #d0d6e0;")
        ic_layout.addWidget(lbl_input)

        row_key = QHBoxLayout()
        row_key.setSpacing(8)

        self.input_api_key = QLineEdit()
        self.input_api_key.setPlaceholderText("gsk_...")
        self.input_api_key.setText(self.config.groq_api_key)
        self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_api_key.setFixedHeight(38)
        row_key.addWidget(self.input_api_key)

        btn_toggle_eye = QPushButton("Show")
        btn_toggle_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_toggle_eye.setStyleSheet("""
            QPushButton {
                background-color: #14171f;
                color: #8a8f98;
                border: 1px solid #232836;
                border-radius: 8px;
                padding: 0 14px;
                height: 38px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1c212c;
                border-color: #3b4559;
                color: #f4f4f6;
            }
        """)
        btn_toggle_eye.clicked.connect(self._toggle_key_visibility)
        row_key.addWidget(btn_toggle_eye)

        self.btn_test_key = QPushButton("Test Connection")
        self.btn_test_key.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test_key.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #022c22;
                border: 1px solid #10b981;
                border-radius: 8px;
                padding: 0 20px;
                height: 38px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #059669;
                border-color: #059669;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """)
        self.btn_test_key.clicked.connect(self._test_groq_key)
        row_key.addWidget(self.btn_test_key)
        ic_layout.addLayout(row_key)

        # Real-time feedback status label
        self.lbl_key_status = QLabel("")
        self.lbl_key_status.setStyleSheet("font-size: 12px; margin-top: 2px;")
        ic_layout.addWidget(self.lbl_key_status)

        layout.addWidget(input_card)
        layout.addStretch()
        return page

    def _open_groq_console(self):
        url = "https://console.groq.com/keys"
        QDesktopServices.openUrl(QUrl(url))

    def _toggle_key_visibility(self):
        if self.input_api_key.echoMode() == QLineEdit.EchoMode.Password:
            self.input_api_key.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)

    def _test_groq_key(self):
        key = self.input_api_key.text().strip()
        if not key:
            self.lbl_key_status.setText("Please enter an API key first.")
            self.lbl_key_status.setStyleSheet("color: #ef4444; font-size: 12px;")
            return

        self.btn_test_key.setEnabled(False)
        self.btn_test_key.setText("Testing...")
        self.lbl_key_status.setText("Connecting to Groq API...")
        self.lbl_key_status.setStyleSheet("color: #8a8f98; font-size: 12px;")
        QApplication.processEvents()

        try:
            svc = GroqService(key)
            ok, msg = svc.test_connection()
            if ok:
                self.lbl_key_status.setText("✓ Connected successfully! Whisper Large v3 is active.")
                self.lbl_key_status.setStyleSheet("color: #10b981; font-weight: 600; font-size: 12px;")
            else:
                self.lbl_key_status.setText(f"✕ Connection failed: {msg}")
                self.lbl_key_status.setStyleSheet("color: #ef4444; font-size: 12px;")
        finally:
            self.btn_test_key.setEnabled(True)
            self.btn_test_key.setText("Test Connection")

    # --------------------------------------------------------------------------
    # Step 3: Dictation Shortcut & Behavior
    # --------------------------------------------------------------------------
    def _build_step_shortcut(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(44, 32, 44, 28)
        layout.setSpacing(18)

        t = QLabel("Choose Your Dictation Shortcut")
        t.setStyleSheet("font-size: 22px; font-weight: 700; color: #f4f4f6; letter-spacing: -0.4px;")
        layout.addWidget(t)

        sub = QLabel(
            "This keyboard shortcut works system-wide. Whenever pressed, FreeFlow listens to your microphone "
            "and automatically pastes the transcribed text into your active app."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 13px; color: #8a8f98; line-height: 1.5;")
        layout.addWidget(sub)

        # Shortcut Recorder Card
        hk_card = QFrame()
        hk_card.setObjectName("SurfaceCard")
        hk_layout = QVBoxLayout(hk_card)
        hk_layout.setContentsMargins(20, 18, 20, 18)
        hk_layout.setSpacing(12)

        lbl_hk = QLabel("Global Keyboard Shortcut:")
        lbl_hk.setStyleSheet("font-size: 13px; font-weight: 600; color: #f4f4f6;")
        hk_layout.addWidget(lbl_hk)

        self.shortcut_widget = ShortcutRecorderWidget(
            modifier=self.config.hotkey_modifier,
            key=self.config.hotkey_key,
            parent=self
        )
        hk_layout.addWidget(self.shortcut_widget)
        layout.addWidget(hk_card)

        # Dictation Behavior Mode Card
        mode_card = QFrame()
        mode_card.setObjectName("SurfaceCard")
        mc_layout = QVBoxLayout(mode_card)
        mc_layout.setContentsMargins(20, 18, 20, 18)
        mc_layout.setSpacing(10)

        lbl_mode = QLabel("Interaction Behavior:")
        lbl_mode.setStyleSheet("font-size: 13px; font-weight: 600; color: #f4f4f6;")
        mc_layout.addWidget(lbl_mode)

        self.radio_toggle = QRadioButton("Toggle Mode (Recommended)")
        self.radio_toggle.setChecked(self.config.hotkey_mode != "hold")
        t_sub = QLabel("    Tap your shortcut once to start speaking. Tap again to stop and inject.")
        t_sub.setStyleSheet("color: #8a8f98; font-size: 11px; margin-bottom: 6px;")

        self.radio_hold = QRadioButton("Hold-to-Talk (Push to Talk)")
        self.radio_hold.setChecked(self.config.hotkey_mode == "hold")
        h_sub = QLabel("    Hold down the shortcut while speaking. Release the keys to finish.")
        h_sub.setStyleSheet("color: #8a8f98; font-size: 11px;")

        self.bg_mode = QButtonGroup(self)
        self.bg_mode.addButton(self.radio_toggle)
        self.bg_mode.addButton(self.radio_hold)

        mc_layout.addWidget(self.radio_toggle)
        mc_layout.addWidget(t_sub)
        mc_layout.addWidget(self.radio_hold)
        mc_layout.addWidget(h_sub)

        mc_layout.addSpacing(6)
        self.chk_show_hud = QCheckBox("Show floating Wispr Flow waveform capsule during recording")
        self.chk_show_hud.setChecked(self.config.show_hud)
        mc_layout.addWidget(self.chk_show_hud)

        layout.addWidget(mode_card)
        layout.addStretch()
        return page

    # --------------------------------------------------------------------------
    # Step 4: Preferences & Completion
    # --------------------------------------------------------------------------
    def _build_step_finish(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(44, 32, 44, 28)
        layout.setSpacing(18)

        t = QLabel("Ready to Flow")
        t.setStyleSheet("font-size: 22px; font-weight: 700; color: #f4f4f6; letter-spacing: -0.4px;")
        layout.addWidget(t)

        sub = QLabel("Configure how FreeFlow runs in the background of your desktop environment:")
        sub.setStyleSheet("font-size: 13px; color: #8a8f98;")
        layout.addWidget(sub)

        # Options Card
        pref_card = QFrame()
        pref_card.setObjectName("SurfaceCard")
        pc_layout = QVBoxLayout(pref_card)
        pc_layout.setContentsMargins(20, 18, 20, 18)
        pc_layout.setSpacing(12)

        self.chk_autostart = QCheckBox("Start FreeFlow automatically on system login (recommended)")
        self.chk_autostart.setChecked(self.config.autostart)
        pc_layout.addWidget(self.chk_autostart)

        self.chk_start_minimized = QCheckBox("Start minimized to system tray on boot")
        self.chk_start_minimized.setChecked(self.config.start_minimized)
        pc_layout.addWidget(self.chk_start_minimized)

        self.chk_close_to_tray = QCheckBox("Closing window hides to system tray (keeps listening for shortcut)")
        self.chk_close_to_tray.setChecked(self.config.close_to_tray)
        pc_layout.addWidget(self.chk_close_to_tray)

        layout.addWidget(pref_card)

        # Summary Pill Card
        summary_card = QFrame()
        summary_card.setObjectName("SurfaceCard")
        sc_layout = QHBoxLayout(summary_card)
        sc_layout.setContentsMargins(20, 16, 20, 16)
        sc_layout.setSpacing(20)

        s1 = QVBoxLayout()
        s1.addWidget(QLabel("SPEECH ENGINE"))
        s1.itemAt(0).widget().setStyleSheet("font-size: 10px; font-weight: 600; color: #62666d; letter-spacing: 0.8px;")
        s1.addWidget(QLabel("Groq Whisper Large v3"))
        s1.itemAt(1).widget().setStyleSheet("font-size: 13px; font-weight: 600; color: #10b981;")
        sc_layout.addLayout(s1)

        s2 = QVBoxLayout()
        s2.addWidget(QLabel("GLOBAL SHORTCUT"))
        s2.itemAt(0).widget().setStyleSheet("font-size: 10px; font-weight: 600; color: #62666d; letter-spacing: 0.8px;")
        self.lbl_summary_hk = QLabel(self.config.get_display_hotkey())
        self.lbl_summary_hk.setStyleSheet("font-size: 13px; font-weight: 600; color: #f4f4f6;")
        s2.addWidget(self.lbl_summary_hk)
        sc_layout.addLayout(s2)

        s3 = QVBoxLayout()
        s3.addWidget(QLabel("STORAGE"))
        s3.itemAt(0).widget().setStyleSheet("font-size: 10px; font-weight: 600; color: #62666d; letter-spacing: 0.8px;")
        s3.addWidget(QLabel("100% Local & Private"))
        s3.itemAt(1).widget().setStyleSheet("font-size: 13px; font-weight: 600; color: #f4f4f6;")
        sc_layout.addLayout(s3)

        layout.addWidget(summary_card)
        layout.addStretch()
        return page
