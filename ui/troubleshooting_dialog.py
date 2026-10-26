"""
FreeFlow Troubleshooting & Solutions Dialog
Interactive diagnostic guide that helps users resolve API errors, connection issues,
microphone capture errors, and submit structured GitHub bug reports.
Supports browsable common troubleshooting topics and on-demand error flow simulation.
"""

import logging
import os
import shutil
import webbrowser
from pathlib import Path
from typing import Optional, Dict

try:
    from PyQt6.QtCore import Qt, QUrl, pyqtSignal
    from PyQt6.QtGui import QColor, QFont, QDesktopServices, QIcon
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QFrame, QTextEdit, QScrollArea, QWidget, QApplication,
        QMenu, QFileDialog, QMessageBox
    )
except ImportError:
    class QDialog:
        pass
    def pyqtSignal(*args):
        return None
    QFileDialog = None
    QMessageBox = None

from core.config import AppConfig
from core.groq_client import GroqService
from core.troubleshooting import (
    ErrorDiagnostic, diagnose_error, get_common_diagnostic, COMMON_TOPICS
)
from core.theme import (
    DARK_BACKGROUND, DARK_SURFACE, DARK_CARD, DARK_CARD_HOVER,
    DARK_CARD_BORDER, DARK_CARD_BORDER_HOVER, PRIMARY_BLUE,
    ACCENT_GREEN, ACCENT_VIOLET, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY
)

logger = logging.getLogger("FreeFlow.TroubleshootingUI")


class TroubleshootingDialog(QDialog):
    """
    Raycast / Linear styled dialog presenting actionable solutions
    for common issues, active transcription errors, and on-demand diagnostics.
    """

    open_settings_requested = pyqtSignal(int)  # tab index (0=Dictation, 1=Audio/Hotkeys, 2=Settings)
    simulate_error_requested = pyqtSignal(str) # error string to simulate on HUD
    retry_transcription_requested = pyqtSignal()

    def __init__(
        self,
        parent=None,
        diagnostic: Optional[ErrorDiagnostic] = None,
        config: Optional[AppConfig] = None,
        recovery_audio_path: Optional[str] = None,
        recovery_audio_duration: float = 0.0
    ):
        super().__init__(parent)
        self.diagnostic = diagnostic or get_common_diagnostic()
        self.config = config or AppConfig.load()
        self.recovery_audio_path = recovery_audio_path
        self.recovery_audio_duration = recovery_audio_duration
        self._initial_active_error = self.diagnostic if self.diagnostic.is_error else None

        self._update_window_title()
        self.setMinimumSize(600, 680)
        self.resize(650, 710)

        assets_dir = Path(__file__).resolve().parent.parent / "assets"
        icon_path = assets_dir / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DARK_BACKGROUND};
                color: {TEXT_PRIMARY};
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {DARK_BACKGROUND};
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {DARK_CARD_BORDER};
                border-radius: 3px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {DARK_CARD_BORDER_HOVER};
            }}
            QFrame.CardFrame {{
                background-color: {DARK_CARD};
                border: 1px solid {DARK_CARD_BORDER};
                border-radius: 12px;
                padding: 14px;
            }}
            QLabel {{
                color: {TEXT_PRIMARY};
            }}
            QPushButton.TopicTab {{
                background-color: {DARK_CARD};
                color: {TEXT_SECONDARY};
                border: 1px solid {DARK_CARD_BORDER};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton.TopicTab:hover {{
                background-color: {DARK_CARD_HOVER};
                color: {TEXT_PRIMARY};
                border-color: {DARK_CARD_BORDER_HOVER};
            }}
            QPushButton.TopicTabActive {{
                background-color: #162438;
                color: {PRIMARY_BLUE};
                border: 1px solid {PRIMARY_BLUE};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton.ErrorTabActive {{
                background-color: #3b1219;
                color: #f87171;
                border: 1px solid {ACCENT_RED};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton.PrimaryBtn {{
                background-color: {PRIMARY_BLUE};
                color: #000000;
                border: 1px solid {PRIMARY_BLUE};
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton.PrimaryBtn:hover {{
                background-color: #7ec5ff;
                border-color: #7ec5ff;
                color: #000000;
            }}
            QPushButton.SecondaryBtn {{
                background-color: {DARK_CARD};
                color: {TEXT_PRIMARY};
                border: 1px solid {DARK_CARD_BORDER};
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton.SecondaryBtn:hover {{
                background-color: {DARK_CARD_HOVER};
                border-color: {DARK_CARD_BORDER_HOVER};
                color: {TEXT_PRIMARY};
            }}
            QPushButton.GitHubBtn {{
                background-color: {DARK_CARD};
                color: {TEXT_PRIMARY};
                border: 1px solid {DARK_CARD_BORDER};
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton.GitHubBtn:hover {{
                background-color: {DARK_CARD_HOVER};
                border-color: {PRIMARY_BLUE};
            }}
            QPushButton.SimulateBtn {{
                background-color: #2d1522;
                color: #f472b6;
                border: 1px solid #831843;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton.SimulateBtn:hover {{
                background-color: #4c1d38;
                border-color: #f472b6;
            }}
            QTextEdit {{
                background-color: {DARK_SURFACE};
                color: #f87171;
                border: 1px solid {DARK_CARD_BORDER};
                border-radius: 8px;
                font-family: "JetBrains Mono", "Ubuntu Mono", "Consolas", monospace;
                font-size: 12px;
                padding: 8px;
            }}
        """)

        self.tab_buttons: Dict[str, QPushButton] = {}
        self._build_ui()
        self._refresh_content()

    def _update_window_title(self):
        if self.diagnostic.is_error:
            self.setWindowTitle(f"FreeFlow Diagnostics — {self.diagnostic.title}")
        else:
            self.setWindowTitle("FreeFlow Common Troubleshooting & Help")

    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(14)

        # 1. Topic Bar
        self.nav_frame = QFrame()
        nav_layout = QHBoxLayout(self.nav_frame)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)

        # If opened with an active error, show "Active Issue" pill first
        if self._initial_active_error is not None:
            btn_active_err = QPushButton("⚠️ Active Issue")
            btn_active_err.setProperty("class", "ErrorTabActive")
            btn_active_err.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_active_err.clicked.connect(lambda: self._select_topic("active_error"))
            nav_layout.addWidget(btn_active_err)
            self.tab_buttons["active_error"] = btn_active_err

        # Common Topics
        topic_labels = [
            ("api_key", "🔑 API Key"),
            ("connection", "🌐 Firewall & Network"),
            ("microphone", "🎙️ Microphone"),
            ("injection", "📋 Clipboard"),
            ("rate_limit", "⏱️ Quotas")
        ]
        for key, label in topic_labels:
            btn = QPushButton(label)
            btn.setProperty("class", "TopicTab")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._select_topic(k))
            nav_layout.addWidget(btn)
            self.tab_buttons[key] = btn

        nav_layout.addStretch()

        # Simulate Error Flow Menu / Button
        self.btn_simulate = QPushButton("🧪 Test Error Flow ▾")
        self.btn_simulate.setProperty("class", "SimulateBtn")
        self.btn_simulate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_simulate.setToolTip("Test how the error notification and HUD capsule appear on demand.")
        self.btn_simulate.clicked.connect(self._show_simulation_menu)
        nav_layout.addWidget(self.btn_simulate)

        self.main_layout.addWidget(self.nav_frame)

        # 2. Header Banner
        self.header = QFrame()
        self.h_layout = QHBoxLayout(self.header)
        self.h_layout.setContentsMargins(0, 4, 0, 4)
        self.h_layout.setSpacing(14)

        self.icon_pill = QLabel()
        self.icon_pill.setFixedSize(44, 44)
        self.icon_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.h_layout.addWidget(self.icon_pill)

        self.title_box = QVBoxLayout()
        self.title_box.setSpacing(3)
        self.lbl_title = QLabel("")
        self.lbl_title.setStyleSheet("font-size: 17px; font-weight: 700; color: #ffffff;")
        self.title_box.addWidget(self.lbl_title)

        self.lbl_summary = QLabel("")
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setStyleSheet("font-size: 13px; color: #94a3b8; line-height: 1.4;")
        self.title_box.addWidget(self.lbl_summary)

        self.h_layout.addLayout(self.title_box, 1)
        self.main_layout.addWidget(self.header)

        # 3. Scrollable Content Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.c_layout = QVBoxLayout(self.content_widget)
        self.c_layout.setContentsMargins(0, 0, 0, 0)
        self.c_layout.setSpacing(14)

        # Recovery Audio Card (Surfaced when recorded audio is cached from a failed/interrupted run)
        if self.recovery_audio_path and os.path.isfile(self.recovery_audio_path):
            self.recovery_card = QFrame()
            self.recovery_card.setStyleSheet("""
                QFrame {
                    background-color: #062b1f;
                    border: 1px solid #10b981;
                    border-radius: 10px;
                    padding: 14px;
                }
            """)
            rec_layout = QVBoxLayout(self.recovery_card)
            rec_layout.setSpacing(10)

            mins, secs = divmod(int(self.recovery_audio_duration), 60)
            file_size_mb = os.path.getsize(self.recovery_audio_path) / (1024 * 1024)
            dur_str = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"

            lbl_rec_title = QLabel(f"🎙️ Unsaved Audio Recovered ({dur_str} • {file_size_mb:.2f} MB)")
            lbl_rec_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #a7f3d0;")
            rec_layout.addWidget(lbl_rec_title)

            lbl_rec_desc = QLabel(
                "Your last recorded speech was safely preserved. Once you review your connection, "
                "API key, or settings, you can transcribe it immediately without talking again."
            )
            lbl_rec_desc.setWordWrap(True)
            lbl_rec_desc.setStyleSheet("font-size: 12px; color: #6ee7b7; line-height: 1.4;")
            rec_layout.addWidget(lbl_rec_desc)

            btn_row = QHBoxLayout()
            btn_row.setSpacing(10)

            self.btn_retry_transcribe = QPushButton("🔁 Retry Transcription with Saved Audio")
            self.btn_retry_transcribe.setProperty("class", "PrimaryBtn")
            self.btn_retry_transcribe.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_retry_transcribe.clicked.connect(self._on_retry_transcribe_clicked)
            btn_row.addWidget(self.btn_retry_transcribe)

            self.btn_export_audio = QPushButton("💾 Export Audio (.wav)...")
            self.btn_export_audio.setProperty("class", "SecondaryBtn")
            self.btn_export_audio.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_export_audio.clicked.connect(self._on_export_audio_clicked)
            btn_row.addWidget(self.btn_export_audio)

            btn_row.addStretch()
            rec_layout.addLayout(btn_row)

            self.c_layout.addWidget(self.recovery_card)

        # Steps Card
        self.steps_card = QFrame()
        self.steps_card.setProperty("class", "CardFrame")
        self.steps_layout = QVBoxLayout(self.steps_card)
        self.steps_layout.setSpacing(10)
        self.c_layout.addWidget(self.steps_card)

        # Quick Actions Card
        self.actions_card = QFrame()
        self.actions_card.setProperty("class", "CardFrame")
        self.act_layout = QVBoxLayout(self.actions_card)
        self.act_layout.setSpacing(10)
        self.c_layout.addWidget(self.actions_card)

        # Technical Details Card (Visible only when an actual error occurred or status normal)
        self.tech_card = QFrame()
        self.tech_card.setProperty("class", "CardFrame")
        self.tech_layout = QVBoxLayout(self.tech_card)
        self.tech_layout.setSpacing(8)
        self.c_layout.addWidget(self.tech_card)

        self.scroll.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll, 1)

        # 4. Footer
        self.footer = QFrame()
        f_layout = QHBoxLayout(self.footer)
        f_layout.setContentsMargins(0, 8, 0, 0)
        f_layout.setSpacing(12)

        self.btn_github = QPushButton("Report Issue on GitHub ↗")
        self.btn_github.setProperty("class", "GitHubBtn")
        self.btn_github.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_github.setToolTip("Opens GitHub with pre-filled diagnostic details (API keys are redacted).")
        self.btn_github.clicked.connect(self._open_github_issue)
        f_layout.addWidget(self.btn_github)

        f_layout.addStretch()

        self.btn_close = QPushButton("Close")
        self.btn_close.setProperty("class", "SecondaryBtn")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.accept)
        f_layout.addWidget(self.btn_close)

        self.main_layout.addWidget(self.footer)

    def _select_topic(self, topic_key: str):
        """Switch view to selected common topic or active error."""
        # Update button highlights
        for key, btn in self.tab_buttons.items():
            if key == topic_key:
                if key == "active_error":
                    btn.setProperty("class", "ErrorTabActive")
                else:
                    btn.setProperty("class", "TopicTabActive")
            else:
                btn.setProperty("class", "TopicTab")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if topic_key == "active_error" and self._initial_active_error:
            self.diagnostic = self._initial_active_error
        else:
            self.diagnostic = get_common_diagnostic(topic_key)

        self._update_window_title()
        self._refresh_content()

    def _refresh_content(self):
        """Render diagnostic title, steps, actions, and logs based on current selection."""
        # Header Styling
        if self.diagnostic.is_error:
            badge_bg = "#7f1d1d"
            badge_border = "#ef4444"
            icon_char = "⚠️"
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
        else:
            badge_bg = "#064e3b"
            badge_border = "#10b981"
            icon_char = "💡"

        self.icon_pill.setStyleSheet(f"""
            background-color: {badge_bg};
            border: 1.5px solid {badge_border};
            border-radius: 22px;
            font-size: 20px;
        """)
        self.icon_pill.setText(icon_char)
        self.lbl_title.setText(self.diagnostic.title)
        self.lbl_summary.setText(self.diagnostic.summary)

        # Clear Steps Card
        while self.steps_layout.count():
            item = self.steps_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        header_title = "RECOMMENDED SOLUTIONS" if self.diagnostic.is_error else "STEP-BY-STEP INSTRUCTIONS"
        lbl_steps_header = QLabel(header_title)
        lbl_steps_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #10b981; letter-spacing: 0.5px;")
        self.steps_layout.addWidget(lbl_steps_header)

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

            self.steps_layout.addLayout(step_row)

        # Clear Actions Card
        while self.act_layout.count():
            item = self.act_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        lbl_act_header = QLabel("QUICK ACTIONS")
        lbl_act_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #a855f7; letter-spacing: 0.5px;")
        self.act_layout.addWidget(lbl_act_header)

        btns_row = QHBoxLayout()
        btns_row.setSpacing(10)

        btn_primary = QPushButton(self.diagnostic.primary_action_label)
        btn_primary.setProperty("class", "PrimaryBtn")
        btn_primary.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_primary.clicked.connect(lambda: self._handle_action(self.diagnostic.primary_action_id))
        btns_row.addWidget(btn_primary)

        if self.diagnostic.secondary_action_label:
            btn_secondary = QPushButton(self.diagnostic.secondary_action_label)
            btn_secondary.setProperty("class", "SecondaryBtn")
            btn_secondary.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_secondary.clicked.connect(lambda: self._handle_action(self.diagnostic.secondary_action_id))
            btns_row.addWidget(btn_secondary)

        self.btn_live_test = QPushButton("Test Groq Connection")
        self.btn_live_test.setProperty("class", "SecondaryBtn")
        self.btn_live_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_live_test.clicked.connect(self._run_live_connection_test)
        btns_row.addWidget(self.btn_live_test)

        btns_row.addStretch()
        self.act_layout.addLayout(btns_row)

        self.lbl_test_result = QLabel("")
        self.lbl_test_result.setWordWrap(True)
        self.lbl_test_result.setStyleSheet("font-size: 12px; color: #94a3b8;")
        self.lbl_test_result.setVisible(False)
        self.act_layout.addWidget(self.lbl_test_result)

        # Clear Tech Details Card
        while self.tech_layout.count():
            item = self.tech_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        tech_header_row = QHBoxLayout()
        header_text = "TECHNICAL ERROR LOG" if self.diagnostic.is_error else "SYSTEM DIAGNOSTIC STATUS"
        lbl_tech_header = QLabel(header_text)
        lbl_tech_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        tech_header_row.addWidget(lbl_tech_header)
        tech_header_row.addStretch()

        btn_copy_log = QPushButton("Copy Diagnostic Details")
        btn_copy_log.setStyleSheet("background: transparent; color: #38bdf8; border: none; font-size: 12px; font-weight: 500;")
        btn_copy_log.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_log.clicked.connect(self._copy_diagnostic_details)
        tech_header_row.addWidget(btn_copy_log)

        self.tech_layout.addLayout(tech_header_row)

        self.txt_error = QTextEdit()
        self.txt_error.setReadOnly(True)
        self.txt_error.setFixedHeight(85)
        display_err = self.diagnostic.sanitized_error or "System Status: Normal. No active runtime error recorded."
        if not self.diagnostic.is_error:
            self.txt_error.setStyleSheet("background-color: #090a0d; color: #34d399; border: 1px solid #1e222d; font-family: monospace; font-size: 12px; padding: 8px;")
        else:
            self.txt_error.setStyleSheet("background-color: #090a0d; color: #f87171; border: 1px solid #1e222d; font-family: monospace; font-size: 12px; padding: 8px;")
        self.txt_error.setPlainText(display_err)
        self.tech_layout.addWidget(self.txt_error)

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def _handle_action(self, action_id: Optional[str]):
        if not action_id:
            return
        if action_id == "open_settings":
            self.open_settings_requested.emit(2)
            self.accept()
        elif action_id == "open_audio_settings":
            self.open_settings_requested.emit(1)
            self.accept()
        elif action_id == "open_groq_console":
            webbrowser.open("https://console.groq.com/keys")
        elif action_id == "test_connection":
            self._run_live_connection_test()
        elif action_id == "report_github":
            self._open_github_issue()

    def _run_live_connection_test(self):
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

    def _show_simulation_menu(self):
        """Surface menu allowing user to simulate different error scenarios for testing."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #12151c;
                color: #f1f5f9;
                border: 1px solid #232836;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1e293b;
                color: #38bdf8;
            }
        """)

        act_api = menu.addAction("Simulate: Invalid Groq API Key (401)")
        act_net = menu.addAction("Simulate: Windows Firewall / Connection Drop")
        act_mic = menu.addAction("Simulate: Microphone Silence / Capture Failure")
        act_rate = menu.addAction("Simulate: Groq Rate Limit (429)")

        selected = menu.exec(self.btn_simulate.mapToGlobal(self.btn_simulate.rect().bottomLeft()))
        if not selected:
            return

        if selected == act_api:
            err = "AuthenticationError: Error code: 401 - {'error': {'message': 'Invalid API Key', 'code': 'invalid_api_key'}}"
        elif selected == act_net:
            err = "groq.APIConnectionError: Connection error. WinError 10060 - Outbound connection to api.groq.com:443 blocked by firewall."
        elif selected == act_mic:
            err = "ValueError: Recorded audio file is empty (0 bytes received from microphone device)."
        elif selected == act_rate:
            err = "RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model whisper-large-v3'}}"
        else:
            return

        # Close current dialog and emit simulation to trigger HUD capsule and desktop alert
        if self.simulate_error_requested:
            self.simulate_error_requested.emit(err)
        self.accept()

    def _copy_diagnostic_details(self):
        clip_text = (
            f"FreeFlow Diagnostic Report\n"
            f"Category: {self.diagnostic.category}\n"
            f"Issue: {self.diagnostic.title}\n"
            f"Summary: {self.diagnostic.summary}\n\n"
            f"Details / Trace:\n{self.diagnostic.sanitized_error}\n"
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
        url = self.diagnostic.github_issue_url
        if not url:
            url = "https://github.com/BheeshamKS/FreeFlow/issues/new"
        webbrowser.open(url)

    def _on_retry_transcribe_clicked(self):
        if self.retry_transcription_requested:
            self.retry_transcription_requested.emit()
        self.accept()

    def _on_export_audio_clicked(self):
        if not self.recovery_audio_path or not os.path.isfile(self.recovery_audio_path):
            return
        if QFileDialog is None:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Export Recovered Audio",
            str(Path.home() / "FreeFlow_Recovered_Audio.wav"),
            "WAV Audio (*.wav)"
        )
        if dest:
            try:
                shutil.copy2(self.recovery_audio_path, dest)
                logger.info(f"Exported recovery audio to {dest}")
                if QMessageBox:
                    QMessageBox.information(self, "Audio Saved", f"Successfully exported audio to:\n{dest}")
            except Exception as e:
                if QMessageBox:
                    QMessageBox.warning(self, "Export Failed", f"Could not export audio: {e}")
