"""
FreeFlow Troubleshooting & Solutions Dialog
Interactive diagnostic guide that helps users resolve API errors, connection issues,
microphone capture errors, and submit structured GitHub bug reports.
"""

import logging
import webbrowser
from typing import Optional

try:
    from PyQt6.QtCore import Qt, QUrl, pyqtSignal
    from PyQt6.QtGui import QColor, QFont, QDesktopServices, QIcon
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QFrame, QTextEdit, QScrollArea, QWidget, QApplication
    )
except ImportError:
    class QDialog:
        pass

from core.config import AppConfig
from core.groq_client import GroqService
from core.troubleshooting import ErrorDiagnostic, diagnose_error

logger = logging.getLogger("FreeFlow.TroubleshootingUI")


class TroubleshootingDialog(QDialog):
    """
    Raycast / Linear styled dialog presenting actionable solutions
    for transcription and configuration errors.
    """

    open_settings_requested = pyqtSignal(int)  # tab index (0=Dictation, 1=Audio/Hotkeys, 2=Settings)

    def __init__(
        self,
        parent=None,
        diagnostic: Optional[ErrorDiagnostic] = None,
        config: Optional[AppConfig] = None
    ):
        super().__init__(parent)
        self.diagnostic = diagnostic or diagnose_error("Unknown error occurred")
        self.config = config or AppConfig.load()

        self.setWindowTitle(f"FreeFlow Solutions — {self.diagnostic.title}")
        self.setMinimumSize(560, 620)
        self.resize(600, 660)

        # Frameless or standard dialog with dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0d11;
                color: #f3f4f6;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #0d1117;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: #232836;
                border-radius: 3px;
                min-height: 24px;
            }
            QFrame.CardFrame {
                background-color: #12151c;
                border: 1px solid #1f2430;
                border-radius: 10px;
                padding: 14px;
            }
            QLabel {
                color: #e2e8f0;
            }
            QPushButton.PrimaryBtn {
                background-color: #10b981;
                color: #ffffff;
                border: 1px solid #10b981;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton.PrimaryBtn:hover {
                background-color: #059669;
                border-color: #059669;
            }
            QPushButton.SecondaryBtn {
                background-color: #1a202c;
                color: #cbd5e1;
                border: 1px solid #2d3748;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton.SecondaryBtn:hover {
                background-color: #242c3d;
                border-color: #4a5568;
                color: #ffffff;
            }
            QPushButton.GitHubBtn {
                background-color: #24292e;
                color: #f0f6fc;
                border: 1px solid #444c56;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton.GitHubBtn:hover {
                background-color: #2f363d;
                border-color: #58a6ff;
            }
            QTextEdit {
                background-color: #090a0d;
                color: #f87171;
                border: 1px solid #1e222d;
                border-radius: 6px;
                font-family: "JetBrains Mono", "Ubuntu Mono", "Consolas", monospace;
                font-size: 12px;
                padding: 8px;
            }
        """)

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 20)
        main_layout.setSpacing(16)

        # 1. Header Banner
        header = QFrame()
        header.setObjectName("HeaderFrame")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 8)
        h_layout.setSpacing(14)

        # Error Icon Pill
        icon_pill = QLabel()
        icon_pill.setFixedSize(44, 44)
        icon_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Color coding by category
        if self.diagnostic.category in ("INVALID_API_KEY", "MODEL_ERROR"):
            badge_bg = "#7c2d12"
            badge_border = "#ea580c"
            icon_char = "🔑"
        elif self.diagnostic.category == "NETWORK_FIREWALL":
            badge_bg = "#1e3a8a"
            badge_border = "#3b82f6"
            icon_char = "🌐"
        elif self.diagnostic.category == "AUDIO_EMPTY":
            badge_bg = "#064e3b"
            badge_border = "#10b981"
            icon_char = "🎙️"
        elif self.diagnostic.category == "RATE_LIMIT":
            badge_bg = "#581c87"
            badge_border = "#a855f7"
            icon_char = "⏱️"
        else:
            badge_bg = "#7f1d1d"
            badge_border = "#ef4444"
            icon_char = "⚠️"

        icon_pill.setStyleSheet(f"""
            background-color: {badge_bg};
            border: 1.5px solid {badge_border};
            border-radius: 22px;
            font-size: 20px;
        """)
        icon_pill.setText(icon_char)
        h_layout.addWidget(icon_pill)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        lbl_title = QLabel(self.diagnostic.title)
        lbl_title.setStyleSheet("font-size: 17px; font-weight: 700; color: #ffffff;")
        title_box.addWidget(lbl_title)

        lbl_summary = QLabel(self.diagnostic.summary)
        lbl_summary.setWordWrap(True)
        lbl_summary.setStyleSheet("font-size: 13px; color: #94a3b8; line-height: 1.4;")
        title_box.addWidget(lbl_summary)

        h_layout.addLayout(title_box, 1)
        main_layout.addWidget(header)

        # 2. Scrollable Content Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        c_layout = QVBoxLayout(content_widget)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(14)

        # Card: Step-by-Step Remediation Guide
        steps_card = QFrame()
        steps_card.setProperty("class", "CardFrame")
        steps_layout = QVBoxLayout(steps_card)
        steps_layout.setSpacing(10)

        lbl_steps_header = QLabel("RECOMMENDED SOLUTIONS")
        lbl_steps_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #10b981; letter-spacing: 0.5px;")
        steps_layout.addWidget(lbl_steps_header)

        for i, step_text in enumerate(self.diagnostic.steps, 1):
            step_row = QHBoxLayout()
            step_row.setSpacing(10)

            num_badge = QLabel(str(i))
            num_badge.setFixedSize(22, 22)
            num_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num_badge.setStyleSheet("""
                background-color: #1e293b;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 11px;
                font-size: 11px;
                font-weight: 700;
            """)
            step_row.addWidget(num_badge, 0, Qt.AlignmentFlag.AlignTop)

            step_desc = QLabel(step_text)
            step_desc.setWordWrap(True)
            step_desc.setStyleSheet("font-size: 13px; color: #e2e8f0; line-height: 1.4;")
            step_row.addWidget(step_desc, 1)

            steps_layout.addLayout(step_row)

        c_layout.addWidget(steps_card)

        # Card: Quick Actions
        actions_card = QFrame()
        actions_card.setProperty("class", "CardFrame")
        act_layout = QVBoxLayout(actions_card)
        act_layout.setSpacing(10)

        lbl_act_header = QLabel("QUICK ACTIONS")
        lbl_act_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #a855f7; letter-spacing: 0.5px;")
        act_layout.addWidget(lbl_act_header)

        btns_row = QHBoxLayout()
        btns_row.setSpacing(10)

        # Primary Action Button
        btn_primary = QPushButton(self.diagnostic.primary_action_label)
        btn_primary.setProperty("class", "PrimaryBtn")
        btn_primary.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_primary.clicked.connect(lambda: self._handle_action(self.diagnostic.primary_action_id))
        btns_row.addWidget(btn_primary)

        # Secondary Action Button
        if self.diagnostic.secondary_action_label:
            btn_secondary = QPushButton(self.diagnostic.secondary_action_label)
            btn_secondary.setProperty("class", "SecondaryBtn")
            btn_secondary.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_secondary.clicked.connect(lambda: self._handle_action(self.diagnostic.secondary_action_id))
            btns_row.addWidget(btn_secondary)

        # Always available: Test Connection Button
        self.btn_live_test = QPushButton("Test Groq Connection")
        self.btn_live_test.setProperty("class", "SecondaryBtn")
        self.btn_live_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_live_test.clicked.connect(self._run_live_connection_test)
        btns_row.addWidget(self.btn_live_test)

        btns_row.addStretch()
        act_layout.addLayout(btns_row)

        # Inline status label for connection test
        self.lbl_test_result = QLabel("")
        self.lbl_test_result.setWordWrap(True)
        self.lbl_test_result.setStyleSheet("font-size: 12px; color: #94a3b8;")
        self.lbl_test_result.setVisible(False)
        act_layout.addWidget(self.lbl_test_result)

        c_layout.addWidget(actions_card)

        # Card: Technical Details & Sanitized Error Log
        tech_card = QFrame()
        tech_card.setProperty("class", "CardFrame")
        tech_layout = QVBoxLayout(tech_card)
        tech_layout.setSpacing(8)

        tech_header_row = QHBoxLayout()
        lbl_tech_header = QLabel("TECHNICAL ERROR LOG")
        lbl_tech_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        tech_header_row.addWidget(lbl_tech_header)
        tech_header_row.addStretch()

        btn_copy_log = QPushButton("Copy Diagnostic Details")
        btn_copy_log.setStyleSheet("""
            background: transparent;
            color: #38bdf8;
            border: none;
            font-size: 12px;
            font-weight: 500;
        """)
        btn_copy_log.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_log.clicked.connect(self._copy_diagnostic_details)
        tech_header_row.addWidget(btn_copy_log)

        tech_layout.addLayout(tech_header_row)

        self.txt_error = QTextEdit()
        self.txt_error.setReadOnly(True)
        self.txt_error.setFixedHeight(85)
        display_err = self.diagnostic.sanitized_error or "No specific stack trace provided."
        self.txt_error.setPlainText(display_err)
        tech_layout.addWidget(self.txt_error)

        c_layout.addWidget(tech_card)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, 1)

        # 3. Bottom Footer
        footer = QFrame()
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(0, 8, 0, 0)
        f_layout.setSpacing(12)

        # Left: Report on GitHub
        btn_github = QPushButton("Report Issue on GitHub ↗")
        btn_github.setProperty("class", "GitHubBtn")
        btn_github.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_github.setToolTip("Opens GitHub with pre-filled diagnostic details (API keys are redacted).")
        btn_github.clicked.connect(self._open_github_issue)
        f_layout.addWidget(btn_github)

        f_layout.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setProperty("class", "SecondaryBtn")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        f_layout.addWidget(btn_close)

        main_layout.addWidget(footer)

    def _handle_action(self, action_id: Optional[str]):
        """Execute selected diagnostic remediation action."""
        if not action_id:
            return

        if action_id == "open_settings":
            self.open_settings_requested.emit(2)  # tab 2 = Settings
            self.accept()
        elif action_id == "open_audio_settings":
            self.open_settings_requested.emit(1)  # tab 1 = Audio & Shortcuts
            self.accept()
        elif action_id == "open_groq_console":
            webbrowser.open("https://console.groq.com/keys")
        elif action_id == "test_connection":
            self._run_live_connection_test()
        elif action_id == "report_github":
            self._open_github_issue()

    def _run_live_connection_test(self):
        """Execute live Groq API test and display feedback in-place."""
        self.btn_live_test.setEnabled(False)
        self.btn_live_test.setText("Testing Connection...")
        self.lbl_test_result.setVisible(True)
        self.lbl_test_result.setStyleSheet("font-size: 12px; color: #38bdf8;")
        self.lbl_test_result.setText("Contacting api.groq.com:443...")
        QApplication.processEvents()

        key = self.config.groq_api_key.strip()
        svc = GroqService(key)
        ok, msg = svc.test_connection()

        self.btn_live_test.setEnabled(True)
        self.btn_live_test.setText("Test Groq Connection")

        if ok:
            self.lbl_test_result.setStyleSheet("font-size: 12px; color: #10b981; font-weight: 600;")
            self.lbl_test_result.setText(f"✓ Success: {msg}")
        else:
            self.lbl_test_result.setStyleSheet("font-size: 12px; color: #f87171; font-weight: 500;")
            self.lbl_test_result.setText(f"✕ Failed: {msg}")

    def _copy_diagnostic_details(self):
        """Copy full sanitized diagnostic trace to system clipboard."""
        clip_text = (
            f"FreeFlow Diagnostic Report\n"
            f"Category: {self.diagnostic.category}\n"
            f"Issue: {self.diagnostic.title}\n"
            f"Summary: {self.diagnostic.summary}\n\n"
            f"Error Trace:\n{self.diagnostic.sanitized_error}\n"
        )
        try:
            import pyperclip
            pyperclip.copy(clip_text)
        except Exception:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(clip_text)

        self.lbl_test_result.setVisible(True)
        self.lbl_test_result.setStyleSheet("font-size: 12px; color: #10b981;")
        self.lbl_test_result.setText("✓ Diagnostic details copied to clipboard!")

    def _open_github_issue(self):
        """Open browser directly to pre-filled GitHub issue page."""
        url = self.diagnostic.github_issue_url
        if not url:
            url = "https://github.com/BheeshamKS/FreeFlow/issues/new"
        webbrowser.open(url)
