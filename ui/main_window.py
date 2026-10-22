"""
FreeFlow Desktop Hub Application Window
========================================
Designed following the Raycast and Linear design systems (awesome-design-md + taste-skill).
Crafted with inky near-black surfaces (#08090b), hairline borders (#1c1f26), Inter typography,
handcrafted vector navigation, tactile Apple-style keycaps, and a breathing dynamic voice orb.
"""

import math
import os
import shutil
import subprocess
import time
from typing import Optional

try:
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF, QRectF
    from PyQt6.QtGui import (
        QFont, QColor, QPainter, QBrush, QPen,
        QLinearGradient, QRadialGradient, QPainterPath
    )
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QStackedWidget, QPushButton, QLabel, QLineEdit,
        QComboBox, QRadioButton, QButtonGroup, QCheckBox,
        QScrollArea, QFrame, QMessageBox, QApplication
    )
except ImportError:
    class QMainWindow:
        pass
    def pyqtSignal(*args):
        return None

from core.config import AppConfig
from core.history import HistoryManager, HistoryEntry
from core.platform import is_linux, is_macos, is_windows
from core.groq_client import GroqService
from core.recorder import list_input_devices
from core.autostart import set_autostart
from core.updater import UpdateManager
from core.version import APP_VERSION
from ui.shortcut_recorder import ShortcutRecorderWidget


class NoScrollComboBox(QComboBox):
    """
    QComboBox that ignores mouse wheel scrolling when closed.
    Prevents unintended setting changes when scrolling through preferences pages.
    Scrolling is only enabled when the dropdown popup list is open.
    """
    def wheelEvent(self, event):
        view = self.view()
        if view and view.isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()


# ==============================================================================
# Handcrafted Voice Orb Widget
# ==============================================================================
class InteractiveVoiceOrb(QWidget):
    """
    Raycast-inspired breathing voice orb with multi-layer radial light diffusion.
    Reacts dynamically to microphone amplitude and user interaction.
    """

    clicked = pyqtSignal() if QWidget is not None else None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.state = "ready"  # 'ready', 'recording', 'transcribing'
        self._phase = 0.0
        self._audio_level = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(33)

    def set_state(self, new_state: str):
        self.state = new_state
        self.update()

    def set_audio_level(self, level: float):
        self._audio_level = max(0.0, min(1.0, level))

    def _animate(self):
        self._phase += 0.18
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.clicked:
            self.clicked.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        pulse = (math.sin(self._phase * 1.8) + 1.0) / 2.0

        if self.state == "recording":
            # Active Listening: Expansive glowing aura with harmonic ripple rings
            aura_r = 68.0 + (pulse * 9.0) + (self._audio_level * 18.0)
            core_r = 44.0 + (pulse * 3.0) + (self._audio_level * 10.0)

            diffuse = QRadialGradient(center, aura_r)
            diffuse.setColorAt(0.0, QColor(16, 185, 129, int(100 + 70 * pulse)))
            diffuse.setColorAt(0.5, QColor(6, 182, 212, int(40 * pulse)))
            diffuse.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(diffuse))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, aura_r, aura_r)

            core = QRadialGradient(center, core_r)
            core.setColorAt(0.0, QColor(16, 185, 129, 255))
            core.setColorAt(0.7, QColor(5, 150, 105, 235))
            core.setColorAt(1.0, QColor(4, 120, 87, 210))
            painter.setBrush(QBrush(core))
            painter.setPen(QPen(QColor(255, 255, 255, int(140 + 80 * pulse)), 1.5))
            painter.drawEllipse(center, core_r, core_r)

            # Draw microphone icon
            self._draw_microphone_glyph(painter, center, QColor(255, 255, 255))

        elif self.state == "transcribing":
            # Amber processing state
            aura_r = 62.0 + (pulse * 6.0)
            core_r = 42.0

            diffuse = QRadialGradient(center, aura_r)
            diffuse.setColorAt(0.0, QColor(245, 158, 11, int(90 + 50 * pulse)))
            diffuse.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(diffuse))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, aura_r, aura_r)

            core = QRadialGradient(center, core_r)
            core.setColorAt(0.0, QColor(245, 158, 11, 240))
            core.setColorAt(1.0, QColor(180, 83, 9, 220))
            painter.setBrush(QBrush(core))
            painter.setPen(QPen(QColor(255, 255, 255, 160), 1.2))
            painter.drawEllipse(center, core_r, core_r)

            self._draw_microphone_glyph(painter, center, QColor(255, 255, 255))

        else:
            # Idle / Ready state: Inky deep pill orb with subtle breathing border
            aura_r = 58.0 + (pulse * 4.0)
            core_r = 42.0

            diffuse = QRadialGradient(center, aura_r)
            diffuse.setColorAt(0.0, QColor(16, 185, 129, int(20 + 20 * pulse)))
            diffuse.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(diffuse))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, aura_r, aura_r)

            core = QRadialGradient(center, core_r)
            core.setColorAt(0.0, QColor(24, 27, 34))
            core.setColorAt(0.8, QColor(16, 18, 23))
            core.setColorAt(1.0, QColor(10, 11, 14))
            painter.setBrush(QBrush(core))
            border_alpha = int(45 + 30 * pulse)
            painter.setPen(QPen(QColor(16, 185, 129, border_alpha), 1.4))
            painter.drawEllipse(center, core_r, core_r)

            self._draw_microphone_glyph(painter, center, QColor(16, 185, 129, 230))

    def _draw_microphone_glyph(self, painter: QPainter, center: QPointF, color: QColor):
        painter.setPen(QPen(color, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        cx = center.x()
        cy = center.y() - 2

        # Mic capsule
        painter.drawRoundedRect(QRectF(cx - 6, cy - 11, 12, 19), 6, 6)
        # Cradle
        painter.drawArc(int(cx - 11), int(cy - 5), 22, 18, 0, -180 * 16)
        # Stem
        painter.drawLine(int(cx), int(cy + 13), int(cx), int(cy + 19))
        # Base
        painter.drawLine(int(cx - 6), int(cy + 19), int(cx + 6), int(cy + 19))


# ==============================================================================
# Bespoke Raycast / Linear Sidebar Navigation Button
# ==============================================================================
class SidebarNavItem(QPushButton):
    """
    Raycast / Linear style navigation button for FreeFlow sidebar.
    Supports clean vector glyphs, count badges, left accent bar, and smooth hover.
    """

    def __init__(self, text: str, icon_type: str = "dictate", badge: str = "", parent=None):
        super().__init__(text, parent)
        self.icon_type = icon_type  # 'dictate', 'history', 'settings'
        self.badge_text = badge
        self.is_active = False
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_active(self, active: bool):
        self.is_active = active
        self.update()

    def set_badge(self, text: str):
        self.badge_text = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        if self.is_active:
            painter.setBrush(QColor("#181b22"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect(), 6, 6)

            # Left vertical emerald accent bar (Linear / Raycast signature)
            painter.setBrush(QColor("#10b981"))
            painter.drawRoundedRect(0, 8, 3, self.height() - 16, 1.5, 1.5)
        elif self.underMouse():
            painter.setBrush(QColor("#12141a"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect(), 6, 6)

        # Draw Icon (Clean vector glyph)
        icon_color = QColor("#10b981" if self.is_active else ("#f4f4f6" if self.underMouse() else "#71717a"))
        pen = QPen(icon_color, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        x_icon = 14
        cy = self.height() / 2.0

        if self.icon_type == "dictate":
            # Microphone glyph
            painter.drawRoundedRect(QRectF(x_icon, cy - 7, 7, 10), 3.5, 3.5)
            painter.drawArc(int(x_icon - 3), int(cy - 4), 13, 11, 0, -180 * 16)
            painter.drawLine(int(x_icon + 3.5), int(cy + 7), int(x_icon + 3.5), int(cy + 10))
            painter.drawLine(int(x_icon), int(cy + 10), int(x_icon + 7), int(cy + 10))

        elif self.icon_type == "history":
            # Clock / journal glyph
            painter.drawEllipse(QRectF(x_icon, cy - 7, 14, 14))
            painter.drawLine(int(x_icon + 7), int(cy), int(x_icon + 7), int(cy - 4))
            painter.drawLine(int(x_icon + 7), int(cy), int(x_icon + 10), int(cy))

        elif self.icon_type == "settings":
            # Sliders glyph
            painter.drawLine(int(x_icon), int(cy - 5), int(x_icon + 14), int(cy - 5))
            painter.drawLine(int(x_icon), int(cy + 1), int(x_icon + 14), int(cy + 1))
            painter.drawLine(int(x_icon), int(cy + 7), int(x_icon + 14), int(cy + 7))
            painter.setBrush(icon_color)
            painter.drawEllipse(QRectF(x_icon + 3, cy - 7, 4, 4))
            painter.drawEllipse(QRectF(x_icon + 9, cy - 1, 4, 4))
            painter.drawEllipse(QRectF(x_icon + 5, cy + 5, 4, 4))
            painter.setBrush(Qt.BrushStyle.NoBrush)

        # Draw Label Text
        text_color = QColor("#ffffff" if self.is_active else ("#f4f4f6" if self.underMouse() else "#9496a1"))
        painter.setPen(text_color)
        font = QFont("Inter", 10)
        font.setWeight(QFont.Weight.DemiBold if self.is_active else QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(QRectF(38, 0, 110, self.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())

        # Draw Badge if present
        if self.badge_text:
            painter.setFont(QFont("Inter", 9, QFont.Weight.Bold))
            badge_rect = QRectF(self.width() - 38, cy - 9, 26, 18)
            painter.setBrush(QColor("#181b24" if not self.is_active else "#222736"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(badge_rect, 9, 9)
            painter.setPen(QColor("#8a8f98" if not self.is_active else "#34d399"))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self.badge_text)


# ==============================================================================
# The Hub Application Window
# ==============================================================================
class MainWindow(QMainWindow):
    """
    Wispr Flow inspired desktop application.
    Implements a strict no-slop Raycast/Linear design aesthetic.
    """

    toggle_recording_requested = pyqtSignal() if QMainWindow is not None else None
    settings_changed = pyqtSignal(object) if QMainWindow is not None else None
    quit_requested = pyqtSignal() if QMainWindow is not None else None

    def __init__(self, config: AppConfig, history: HistoryManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.history = history

        self.setWindowTitle("FreeFlow")
        self.resize(980, 650)
        self.setMinimumSize(860, 580)

        # Apply inky Raycast-style stylesheet
        self._apply_theme()

        # Layout setup
        central = QWidget(self)
        central.setObjectName("AppCanvas")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. Left Minimalist Sidebar
        self.sidebar = self._build_sidebar()
        root.addWidget(self.sidebar)

        # 2. Main Content Area with Top Update Banner
        content_container = QWidget(self)
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._active_updater: Optional[UpdateManager] = None
        self.update_banner = self._build_update_banner()
        self.update_banner.hide()
        content_layout.addWidget(self.update_banner)

        self.stack = QStackedWidget(self)
        self.stack.setObjectName("ContentCanvas")
        content_layout.addWidget(self.stack)
        root.addWidget(content_container)

        # Views
        self.page_dashboard = self._build_dashboard_page()
        self.page_history = self._build_history_page()
        self.page_settings = self._build_settings_page()

        self.stack.addWidget(self.page_dashboard)  # Index 0
        self.stack.addWidget(self.page_history)    # Index 1
        self.stack.addWidget(self.page_settings)   # Index 2

        self.history.history_updated.connect(self._refresh_history_ui)
        self.history.history_updated.connect(self._refresh_dashboard_stats)

        # Crucial: Immediately refresh dashboard stats upon window startup!
        # Prevents stats from erroneously showing "0" before first new dictation.
        self._refresh_dashboard_stats()

    def _apply_theme(self):
        """Pure-near-black Linear/Raycast design tokens."""
        self.setStyleSheet("""
            QMainWindow, QWidget#AppCanvas {
                background-color: #08090b;
                color: #f4f4f6;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QWidget#Sidebar {
                background-color: #0c0d10;
                border-right: 1px solid #181a20;
            }
            QWidget#ContentCanvas {
                background-color: #08090b;
            }
            /* Elegant Linear Card Panels */
            QFrame#SurfaceCard, QFrame[surface="true"] {
                background-color: #0f1115;
                border: 1px solid #1c1f26;
                border-radius: 10px;
            }
            /* Buttons */
            QPushButton#PrimaryAction, QPushButton[variant="primary"] {
                background-color: #10b981;
                color: #022c22;
                border: 1px solid #10b981;
                border-radius: 8px;
                padding: 9px 18px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#PrimaryAction:hover, QPushButton[variant="primary"]:hover {
                background-color: #059669;
                border-color: #059669;
                color: #ffffff;
            }
            QPushButton#PrimaryAction:pressed, QPushButton[variant="primary"]:pressed {
                background-color: #047857;
                border-color: #047857;
            }
            QPushButton#GhostAction, QPushButton[variant="ghost"] {
                background-color: #14171f;
                color: #d0d6e0;
                border: 1px solid #232836;
                border-radius: 8px;
                padding: 7px 14px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#GhostAction:hover, QPushButton[variant="ghost"]:hover {
                background-color: #1c212c;
                border-color: #3b4559;
                color: #ffffff;
            }
            /* Form inputs */
            QLineEdit, QTextEdit, QComboBox {
                background-color: #0f1115;
                color: #f4f4f6;
                border: 1px solid #1f232c;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                selection-background-color: #10b981;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
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
            QScrollBar:vertical {
                border: none;
                background: #08090b;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: #1c1f26;
                border-radius: 3px;
                min-height: 24px;
            }
        """)

    # --------------------------------------------------------------------------
    # 1. Sidebar Navigation
    # --------------------------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget(self)
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 22, 14, 20)
        layout.setSpacing(4)

        # Brand mark (Linear-style minimal logo)
        brand = QHBoxLayout()
        pulse_dot = QLabel("●")
        pulse_dot.setStyleSheet("color: #10b981; font-size: 14px; margin-right: 4px;")
        brand.addWidget(pulse_dot)

        title = QLabel("FreeFlow")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #f4f4f6; letter-spacing: -0.3px;")
        brand.addWidget(title)

        plat_tag = "macOS" if is_macos() else ("Windows" if is_windows() else "Linux")
        tag = QLabel(plat_tag)
        tag.setStyleSheet("font-size: 10px; font-weight: 600; color: #62666d; background: #14161c; border-radius: 4px; padding: 2px 5px; margin-left: 4px;")
        brand.addWidget(tag)
        brand.addStretch()
        layout.addLayout(brand)

        layout.addSpacing(22)

        # Navigation items with custom vector glyphs & badges
        self.nav_dictate = SidebarNavItem("Dictation", icon_type="dictate")
        self.nav_dictate.set_active(True)
        self.nav_dictate.clicked.connect(lambda: self._switch_tab(0))
        layout.addWidget(self.nav_dictate)

        self.nav_history = SidebarNavItem("History", icon_type="history", badge=str(len(self.history.entries)))
        self.nav_history.set_active(False)
        self.nav_history.clicked.connect(lambda: self._switch_tab(1))
        layout.addWidget(self.nav_history)

        self.nav_settings = SidebarNavItem("Settings", icon_type="settings")
        self.nav_settings.set_active(False)
        self.nav_settings.clicked.connect(lambda: self._switch_tab(2))
        layout.addWidget(self.nav_settings)

        layout.addStretch()

        # Sidebar footer: Active Shortcut Keycaps & System Status
        status_box = QVBoxLayout()
        status_box.setSpacing(6)

        lbl_hk_title = QLabel("GLOBAL SHORTCUT")
        lbl_hk_title.setStyleSheet("font-size: 9px; font-weight: 700; color: #52525b; letter-spacing: 0.8px;")
        status_box.addWidget(lbl_hk_title)

        self.footer_keycaps_container = QWidget()
        self.footer_keycaps_layout = QHBoxLayout(self.footer_keycaps_container)
        self.footer_keycaps_layout.setContentsMargins(0, 0, 0, 0)
        self.footer_keycaps_layout.setSpacing(4)
        self._update_footer_keycaps()
        status_box.addWidget(self.footer_keycaps_container)

        self.lbl_sidebar_status = QLabel("● Ready")
        self.lbl_sidebar_status.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 500;")
        status_box.addWidget(self.lbl_sidebar_status)

        layout.addLayout(status_box)
        return sidebar

    def _update_footer_keycaps(self):
        while self.footer_keycaps_layout.count() > 0:
            item = self.footer_keycaps_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        parts = self.config.get_display_hotkey().split(" + ")
        for p in parts:
            chip = QLabel(p)
            chip.setStyleSheet("""
                background-color: #14171f;
                color: #2dd4bf;
                border: 1px solid #232836;
                border-bottom: 2px solid #2f3547;
                border-radius: 4px;
                padding: 2px 7px;
                font-size: 11px;
                font-weight: 600;
                font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace;
            """)
            self.footer_keycaps_layout.addWidget(chip)
        self.footer_keycaps_layout.addStretch()

    def _switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        self.nav_dictate.set_active(index == 0)
        self.nav_history.set_active(index == 1)
        self.nav_settings.set_active(index == 2)

    # --------------------------------------------------------------------------
    # 2. View 1: Flow Dictate Dashboard
    # --------------------------------------------------------------------------
    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(44, 36, 44, 36)
        layout.setSpacing(28)

        # Header with subtle negative letter spacing
        header = QVBoxLayout()
        h1 = QLabel("Voice Dictation")
        h1.setStyleSheet("font-size: 24px; font-weight: 600; color: #f4f4f6; letter-spacing: -0.5px;")
        sub = QLabel("Hold or toggle your shortcut anywhere to transcribe directly into your active window.")
        sub.setStyleSheet("font-size: 13px; color: #8a8f98; margin-top: 2px;")
        header.addWidget(h1)
        header.addWidget(sub)
        layout.addLayout(header)

        # Center Hero Card (Surface)
        hero = QFrame()
        hero.setObjectName("SurfaceCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(32, 44, 32, 40)
        hero_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.setSpacing(16)

        # Voice Orb
        self.orb_widget = InteractiveVoiceOrb()
        self.orb_widget.clicked.connect(self._on_orb_clicked)
        hero_layout.addWidget(self.orb_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status text below orb
        self.lbl_orb_status = QLabel("Ready to Dictate")
        self.lbl_orb_status.setStyleSheet("font-size: 15px; font-weight: 500; color: #f4f4f6; letter-spacing: -0.2px;")
        hero_layout.addWidget(self.lbl_orb_status, alignment=Qt.AlignmentFlag.AlignCenter)

        # Apple-style Tactile Keyboard Shortcut Badge
        hk_str = self.config.get_display_hotkey()
        self.btn_hotkey_badge = QPushButton(f"Shortcut: {hk_str}")
        self.btn_hotkey_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hotkey_badge.setStyleSheet("""
            QPushButton {
                background-color: #14171f;
                color: #2dd4bf;
                border: 1px solid #232836;
                border-bottom: 2px solid #2f3547;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace;
            }
            QPushButton:hover {
                border-color: #2dd4bf;
                background-color: #181d28;
            }
        """)
        self.btn_hotkey_badge.clicked.connect(self._open_shortcut_settings)
        hero_layout.addWidget(self.btn_hotkey_badge, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(hero)

        # Minimalist Stats Grid (Populated cleanly with real history)
        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)

        self.stat_today = self._build_clean_metric_card("TOTAL DICTATIONS", "0", "0 recorded today")
        self.stat_words = self._build_clean_metric_card("WORDS SPOKEN", "0", "Saved ~0 mins typing")
        self.stat_speed = self._build_clean_metric_card("LATENCY", "~300ms", "Groq Whisper Large v3")

        stats_row.addWidget(self.stat_today)
        stats_row.addWidget(self.stat_words)
        stats_row.addWidget(self.stat_speed)
        layout.addLayout(stats_row)

        layout.addStretch()
        return page

    def _build_clean_metric_card(self, label: str, value: str, note: str) -> QFrame:
        card = QFrame()
        card.setObjectName("SurfaceCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(4)

        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #62666d; letter-spacing: 0.8px;")
        layout.addWidget(lbl)

        val = QLabel(value)
        val.setObjectName("MetricVal")
        val.setStyleSheet("font-size: 24px; font-weight: 600; color: #f4f4f6; letter-spacing: -0.5px; margin: 2px 0;")
        layout.addWidget(val)

        sub = QLabel(note)
        sub.setObjectName("MetricSub")
        sub.setStyleSheet("font-size: 11px; color: #8a8f98;")
        layout.addWidget(sub)

        return card

    def _refresh_dashboard_stats(self):
        today_count = self.history.get_today_count()
        total_count = self.history.get_total_count()
        total_words = self.history.get_total_words()
        saved_mins = max(1, round(total_words / 40.0)) if total_words > 0 else 0

        self.stat_today.findChild(QLabel, "MetricVal").setText(str(total_count))
        self.stat_today.findChild(QLabel, "MetricSub").setText(f"{today_count} recorded today")
        self.stat_words.findChild(QLabel, "MetricVal").setText(f"{total_words:,}")
        self.stat_words.findChild(QLabel, "MetricSub").setText(f"Saved ~{saved_mins} mins typing")

        if hasattr(self, "nav_history"):
            self.nav_history.set_badge(str(total_count))
        if hasattr(self, "lbl_history_sub"):
            self.lbl_history_sub.setText(f"{total_count} transcripts stored locally on your device.")

    def _on_orb_clicked(self):
        if self.toggle_recording_requested:
            self.toggle_recording_requested.emit()

    def _open_shortcut_settings(self):
        self._switch_tab(2)
        if hasattr(self, "shortcut_recorder"):
            self.shortcut_recorder.start_recording()

    # --------------------------------------------------------------------------
    # 3. View 2: Dictation History
    # --------------------------------------------------------------------------
    def _build_history_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(44, 36, 44, 36)
        layout.setSpacing(18)

        # Header with subtle tracking
        header = QVBoxLayout()
        header.setSpacing(4)
        h1 = QLabel("Dictation History")
        h1.setStyleSheet("font-size: 24px; font-weight: 600; color: #f4f4f6; letter-spacing: -0.5px;")

        self.lbl_history_sub = QLabel(f"{len(self.history.entries)} transcripts stored locally on your device.")
        self.lbl_history_sub.setStyleSheet("font-size: 13px; color: #8a8f98;")
        header.addWidget(h1)
        header.addWidget(self.lbl_history_sub)
        layout.addLayout(header)

        # Toolbar: Search filter on left, discreet ghost Clear All button on right
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Search transcripts by text or keyword...")
        self.input_search.textChanged.connect(self._refresh_history_ui)
        toolbar.addWidget(self.input_search)

        self.btn_clear_history = QPushButton("Clear All")
        self.btn_clear_history.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_history.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #71717a;
                border: 1px solid #1f232c;
                border-radius: 6px;
                padding: 7px 14px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.08);
                border-color: rgba(239, 68, 68, 0.35);
                color: #ef4444;
            }
        """)
        self.btn_clear_history.clicked.connect(self._clear_history)
        toolbar.addWidget(self.btn_clear_history)
        layout.addLayout(toolbar)

        # Scrollable Feed
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(0, 4, 0, 0)
        self.history_layout.setSpacing(10)
        self.history_layout.addStretch()

        scroll.setWidget(self.history_container)
        layout.addWidget(scroll)

        self._refresh_history_ui()
        return page

    def _refresh_history_ui(self):
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        filter_text = getattr(self, "input_search", None)
        query = filter_text.text().strip().lower() if filter_text else ""
        entries = [e for e in self.history.entries if query in e.text.lower()] if query else self.history.entries

        if not entries:
            empty = QLabel("No dictations recorded yet." if not query else "No matching transcripts found.")
            empty.setStyleSheet("color: #62666d; font-size: 13px; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_layout.insertWidget(0, empty)
            return

        for e in entries:
            card = self._create_history_card(e)
            self.history_layout.insertWidget(self.history_layout.count() - 1, card)

    def _create_history_card(self, entry: HistoryEntry) -> QFrame:
        card = QFrame()
        card.setObjectName("SurfaceCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        top = QHBoxLayout()
        meta = QLabel(f"{entry.time_str}  •  {entry.word_count} words  •  {entry.duration_sec}s")
        meta.setStyleSheet("font-size: 11px; color: #62666d; font-weight: 500;")
        top.addWidget(meta)
        top.addStretch()

        btn_copy = QPushButton("Copy")
        btn_copy.setObjectName("GhostAction")
        btn_copy.setFixedWidth(56)
        btn_copy.clicked.connect(lambda _, t=entry.text, b=btn_copy: self._copy_to_clipboard(t, b))
        top.addWidget(btn_copy)
        layout.addLayout(top)

        txt = QLabel(entry.text)
        txt.setWordWrap(True)
        txt.setStyleSheet("font-size: 13px; color: #d0d6e0; line-height: 1.5;")
        layout.addWidget(txt)

        return card

    def _copy_to_clipboard(self, text: str, btn: QPushButton):
        QApplication.clipboard().setText(text)
        orig = btn.text()
        btn.setText("Copied!")
        QTimer.singleShot(1400, lambda: btn.setText(orig))

    def _clear_history(self):
        if not self.history.entries:
            return
        ans = QMessageBox.question(
            self, "Clear History",
            f"Are you sure you want to permanently delete all {len(self.history.entries)} recorded dictations?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.history.clear()
            self._refresh_dashboard_stats()

    # --------------------------------------------------------------------------
    # 4. View 3: Settings & Launch Options
    # --------------------------------------------------------------------------
    def _build_settings_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(44, 36, 44, 36)
        layout.setSpacing(24)

        h1 = QLabel("Settings & Preferences")
        h1.setStyleSheet("font-size: 24px; font-weight: 600; color: #f4f4f6; letter-spacing: -0.5px;")
        layout.addWidget(h1)

        # 1. Hotkey Section
        card_hotkey = self._create_section_card("Global Dictation Hotkey")
        hk_layout = card_hotkey.layout()

        hk_hint = QLabel("Click 'Record Shortcut' and press your desired keyboard combination:")
        hk_hint.setStyleSheet("font-size: 12px; color: #8a8f98; margin-bottom: 6px;")
        hk_layout.addWidget(hk_hint)

        self.shortcut_recorder = ShortcutRecorderWidget(
            modifier=self.config.hotkey_modifier,
            key=self.config.hotkey_key,
            parent=self
        )
        self.shortcut_recorder.shortcut_changed.connect(self._on_shortcut_recorded)
        hk_layout.addWidget(self.shortcut_recorder)

        hk_layout.addSpacing(12)
        hk_layout.addWidget(QLabel("Behavior Mode:"))
        self.radio_toggle = QRadioButton("Toggle Mode (Tap once to start, tap again to finish)")
        self.radio_hold = QRadioButton("Hold-to-Talk (Hold key while speaking, release to finish)")
        self.bg_mode = QButtonGroup(self)
        self.bg_mode.addButton(self.radio_toggle)
        self.bg_mode.addButton(self.radio_hold)
        if self.config.hotkey_mode == "hold":
            self.radio_hold.setChecked(True)
        else:
            self.radio_toggle.setChecked(True)
        hk_layout.addWidget(self.radio_toggle)
        hk_layout.addWidget(self.radio_hold)
        layout.addWidget(card_hotkey)

        # 2. Audio & Microphone Hardware
        card_audio = self._create_section_card("Audio & Microphone Device")
        au_layout = card_audio.layout()

        mic_desc = QLabel("Select the physical or virtual microphone FreeFlow records from:")
        mic_desc.setStyleSheet("font-size: 12px; color: #8a8f98; margin-bottom: 6px;")
        au_layout.addWidget(mic_desc)

        mic_row = QHBoxLayout()
        self.combo_device = NoScrollComboBox()
        self.btn_refresh_mics = QPushButton("Refresh Devices")
        self.btn_refresh_mics.setObjectName("GhostAction")
        self.btn_refresh_mics.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh_mics.setFixedWidth(130)
        self.btn_refresh_mics.clicked.connect(self._populate_audio_devices)
        mic_row.addWidget(self.combo_device, 1)
        mic_row.addWidget(self.btn_refresh_mics)
        au_layout.addLayout(mic_row)
        self._populate_audio_devices()
        layout.addWidget(card_audio)

        # 3. Window & Autostart Section
        card_launch = self._create_section_card("Startup & Window Behavior")
        l_layout = card_launch.layout()

        self.chk_autostart = QCheckBox("Start FreeFlow automatically on system login")
        self.chk_autostart.setChecked(self.config.autostart)
        l_layout.addWidget(self.chk_autostart)

        self.chk_start_minimized = QCheckBox("Start minimized to system tray on boot")
        self.chk_start_minimized.setChecked(self.config.start_minimized)
        l_layout.addWidget(self.chk_start_minimized)

        self.chk_close_to_tray = QCheckBox("Closing window minimizes to tray instead of quitting")
        self.chk_close_to_tray.setChecked(self.config.close_to_tray)
        l_layout.addWidget(self.chk_close_to_tray)

        self.chk_show_hud = QCheckBox("Show floating Wispr Flow HUD capsule during recording")
        self.chk_show_hud.setChecked(self.config.show_hud)
        l_layout.addWidget(self.chk_show_hud)
        layout.addWidget(card_launch)

        # 4. Software Updates Section
        card_updates = self._create_section_card("Software Updates")
        up_layout = card_updates.layout()

        self.chk_updates = QCheckBox("Check for updates automatically on startup")
        self.chk_updates.setChecked(self.config.check_updates_on_startup)
        up_layout.addWidget(self.chk_updates)

        u_mode_layout = QVBoxLayout()
        u_mode_layout.setContentsMargins(18, 4, 0, 8)
        u_mode_layout.setSpacing(6)

        self.radio_update_auto = QRadioButton("Auto-update: Download in background and prompt to restart the app")
        self.radio_update_ask = QRadioButton("Ask before updating: Show notification when update is available")

        self.bg_update_mode = QButtonGroup(self)
        self.bg_update_mode.addButton(self.radio_update_auto)
        self.bg_update_mode.addButton(self.radio_update_ask)

        if self.config.auto_update_mode == "auto":
            self.radio_update_auto.setChecked(True)
        else:
            self.radio_update_ask.setChecked(True)

        u_mode_layout.addWidget(self.radio_update_auto)
        u_mode_layout.addWidget(self.radio_update_ask)
        up_layout.addLayout(u_mode_layout)

        check_row = QHBoxLayout()
        lbl_v = QLabel(f"Current version: <b>v{APP_VERSION}</b>")
        lbl_v.setStyleSheet("font-size: 13px; color: #8a8f98;")
        check_row.addWidget(lbl_v)

        self.lbl_update_status = QLabel("")
        self.lbl_update_status.setStyleSheet("font-size: 12px; color: #8a8f98;")
        check_row.addWidget(self.lbl_update_status, 1)

        self.btn_check_updates = QPushButton("Check for Updates Now")
        self.btn_check_updates.setObjectName("GhostAction")
        self.btn_check_updates.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check_updates.clicked.connect(self._check_for_updates)
        check_row.addWidget(self.btn_check_updates)
        up_layout.addLayout(check_row)
        layout.addWidget(card_updates)

        # 5. Groq API Section
        card_api = self._create_section_card("Groq Cloud Speech Engine")
        a_layout = card_api.layout()

        api_row = QHBoxLayout()
        self.input_key = QLineEdit()
        self.input_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_key.setText(self.config.groq_api_key)
        self.input_key.setPlaceholderText("gsk_...")
        api_row.addWidget(self.input_key)

        btn_show = QPushButton("Show")
        btn_show.setObjectName("GhostAction")
        btn_show.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_show.clicked.connect(self._toggle_show_key)
        api_row.addWidget(btn_show)

        self.btn_test = QPushButton("Test Connection")
        self.btn_test.setObjectName("PrimaryAction")
        self.btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test.clicked.connect(self._test_connection)
        api_row.addWidget(self.btn_test)
        a_layout.addLayout(api_row)

        hint = QLabel("<small style='color:#62666d;'>Free API keys available at <a href='https://console.groq.com/keys' style='color:#10b981;'>console.groq.com/keys</a></small>")
        hint.setOpenExternalLinks(True)
        a_layout.addWidget(hint)
        layout.addWidget(card_api)

        # 4. Setup Wizard Section
        card_wizard = self._create_section_card("First-Time Setup Guide")
        w_layout = card_wizard.layout()
        w_desc = QLabel("Re-run the initial onboarding setup wizard to reconfigure speech models, shortcuts, or system integration.")
        w_desc.setStyleSheet("font-size: 12px; color: #8a8f98; margin-bottom: 6px;")
        w_layout.addWidget(w_desc)

        btn_run_wizard = QPushButton("Launch Setup Wizard")
        btn_run_wizard.setObjectName("GhostAction")
        btn_run_wizard.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_run_wizard.setFixedWidth(180)
        btn_run_wizard.clicked.connect(self._open_onboarding_wizard)
        w_layout.addWidget(btn_run_wizard)
        layout.addWidget(card_wizard)

        # 5. Troubleshooting & Solutions Guide
        card_trouble = self._create_section_card("Troubleshooting & Diagnostics")
        t_layout = card_trouble.layout()
        t_desc = QLabel("Diagnose API key authentication, connection errors, microphone silence, or submit a pre-filled issue report to GitHub.")
        t_desc.setStyleSheet("font-size: 12px; color: #8a8f98; margin-bottom: 6px;")
        t_layout.addWidget(t_desc)

        btn_trouble = QPushButton("Open Troubleshooting Guide")
        btn_trouble.setObjectName("GhostAction")
        btn_trouble.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_trouble.setFixedWidth(220)
        btn_trouble.clicked.connect(self._open_troubleshooting_guide)
        t_layout.addWidget(btn_trouble)
        layout.addWidget(card_trouble)

        # 6. Application Control (Quit)
        card_app_ctrl = self._create_section_card("Application Control")
        ac_layout = card_app_ctrl.layout()
        ac_desc = QLabel("Fully terminate FreeFlow and shut down background listeners.")
        ac_desc.setStyleSheet("font-size: 12px; color: #8a8f98; margin-bottom: 6px;")
        ac_layout.addWidget(ac_desc)

        btn_quit = QPushButton("Quit FreeFlow")
        btn_quit.setStyleSheet("""
            QPushButton {
                background-color: #1a1012;
                color: #f87171;
                border: 1px solid #3b171c;
                border-radius: 8px;
                padding: 9px 18px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #ef4444;
                border-color: #ef4444;
                color: #ffffff;
            }
        """)
        btn_quit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_quit.setFixedWidth(140)
        btn_quit.clicked.connect(self._on_quit_clicked)
        ac_layout.addWidget(btn_quit)
        layout.addWidget(card_app_ctrl)

        # Wire automatic saving on all interactive settings controls
        self.radio_toggle.toggled.connect(self._save_settings)
        self.radio_hold.toggled.connect(self._save_settings)
        self.combo_device.currentIndexChanged.connect(self._save_settings)
        self.chk_autostart.toggled.connect(self._save_settings)
        self.chk_start_minimized.toggled.connect(self._save_settings)
        self.chk_close_to_tray.toggled.connect(self._save_settings)
        self.chk_show_hud.toggled.connect(self._save_settings)
        self.chk_updates.toggled.connect(self._save_settings)
        self.radio_update_auto.toggled.connect(self._save_settings)
        self.radio_update_ask.toggled.connect(self._save_settings)
        self.input_key.editingFinished.connect(self._save_settings)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _create_section_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("SurfaceCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        t = QLabel(title)
        t.setStyleSheet("font-size: 14px; font-weight: 600; color: #f4f4f6; letter-spacing: -0.2px;")
        layout.addWidget(t)
        return card

    def _open_onboarding_wizard(self):
        from ui.onboarding import OnboardingWizard
        wiz = OnboardingWizard(self.config, self)
        wiz.wizard_completed.connect(self._on_wizard_completed)
        wiz.exec()

    def _on_wizard_completed(self, new_config: AppConfig):
        self.config = new_config
        hk_str = self.config.get_display_hotkey()
        self.btn_hotkey_badge.setText(f"Shortcut: {hk_str}")
        self._update_footer_keycaps()
        if hasattr(self, "shortcut_recorder"):
            self.shortcut_recorder.modifier = self.config.hotkey_modifier
            self.shortcut_recorder.key = self.config.hotkey_key
            self.shortcut_recorder._render_badges()
        if hasattr(self, "input_key"):
            self.input_key.setText(self.config.groq_api_key)
        if self.settings_changed:
            self.settings_changed.emit(self.config)

    def _on_shortcut_recorded(self, modifier: str, key: str):
        self.config.hotkey_modifier = modifier
        self.config.hotkey_key = key
        hk_str = self.config.get_display_hotkey()
        self.btn_hotkey_badge.setText(f"Shortcut: {hk_str}")
        self._update_footer_keycaps()
        self._save_settings()

    def _toggle_show_key(self):
        if self.input_key.echoMode() == QLineEdit.EchoMode.Password:
            self.input_key.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.input_key.setEchoMode(QLineEdit.EchoMode.Password)

    def _test_connection(self):
        key = self.input_key.text().strip()
        svc = GroqService(key)
        self.btn_test.setEnabled(False)
        self.btn_test.setText("Testing...")
        try:
            ok, msg = svc.test_connection()
            if ok:
                QMessageBox.information(self, "Groq Connection", msg)
            else:
                from core.troubleshooting import diagnose_error
                from ui.troubleshooting_dialog import TroubleshootingDialog
                diag = diagnose_error(msg)
                dlg = TroubleshootingDialog(self, diagnostic=diag, config=self.config)
                dlg.open_settings_requested.connect(self._switch_tab)
                dlg.exec()
        finally:
            self.btn_test.setEnabled(True)
            self.btn_test.setText("Test Connection")

    def _open_troubleshooting_guide(self):
        """Open the FreeFlow Troubleshooting & Solutions dialog."""
        from core.troubleshooting import diagnose_error
        from ui.troubleshooting_dialog import TroubleshootingDialog
        diag = diagnose_error("Status Check: Normal Diagnostics")
        dlg = TroubleshootingDialog(self, diagnostic=diag, config=self.config)
        dlg.open_settings_requested.connect(self._switch_tab)
        dlg.exec()

    def _build_update_banner(self) -> QFrame:
        """Create sleek banner surfaced when a newer version of FreeFlow is available."""
        banner = QFrame()
        banner.setObjectName("UpdateBanner")
        banner.setStyleSheet("""
            QFrame#UpdateBanner {
                background-color: #064e3b;
                border-bottom: 1px solid #10b981;
            }
        """)
        b_layout = QHBoxLayout(banner)
        b_layout.setContentsMargins(20, 8, 20, 8)
        b_layout.setSpacing(14)

        self.lbl_banner_text = QLabel("● FreeFlow update available")
        self.lbl_banner_text.setStyleSheet("color: #ecfdf5; font-size: 13px; font-weight: 500;")
        b_layout.addWidget(self.lbl_banner_text, 1)

        self.btn_banner_action = QPushButton("Update & Restart")
        self.btn_banner_action.setObjectName("PrimaryAction")
        self.btn_banner_action.setFixedHeight(28)
        self.btn_banner_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_banner_action.clicked.connect(self._on_banner_update_clicked)
        b_layout.addWidget(self.btn_banner_action)

        btn_dismiss = QPushButton("✕")
        btn_dismiss.setFixedSize(24, 24)
        btn_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dismiss.setStyleSheet("background: transparent; border: none; color: #a7f3d0; font-size: 14px; font-weight: bold;")
        btn_dismiss.clicked.connect(banner.hide)
        b_layout.addWidget(btn_dismiss)

        return banner

    def show_update_banner(self, tag: str, notes: str, updater: UpdateManager):
        """Surface update notification banner across top of window."""
        self._active_updater = updater
        self.lbl_banner_text.setText(f"● FreeFlow <b>{tag}</b> is available! Click to update seamlessly.")
        self.btn_banner_action.setText("Update & Restart")
        self.btn_banner_action.setEnabled(True)
        self.update_banner.show()

    def _on_banner_update_clicked(self):
        if not self._active_updater:
            return
        self.btn_banner_action.setEnabled(False)
        self.btn_banner_action.setText("Updating...")
        self.lbl_banner_text.setText("Downloading latest release from GitHub...")
        self._active_updater.download_progress.connect(
            lambda pct: self.lbl_banner_text.setText(f"Downloading update: {pct}%")
        )
        self._active_updater.download_finished.connect(
            lambda path: self._active_updater.apply_update_and_restart()
        )
        self._active_updater.download_error.connect(
            lambda err: self.lbl_banner_text.setText(f"Update failed: {err}")
        )
        self._active_updater.start_download()

    def _populate_audio_devices(self):
        """Query connected microphones and populate the device selector dropdown."""
        self.combo_device.blockSignals(True)
        try:
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
        finally:
            self.combo_device.blockSignals(False)

    def _check_for_updates(self):
        """Initiate manual update check from Settings card."""
        self.btn_check_updates.setEnabled(False)
        self.lbl_update_status.setText("Checking GitHub...")
        self.lbl_update_status.setStyleSheet("font-size: 12px; color: #8a8f98;")

        self._window_updater = UpdateManager(APP_VERSION, self)
        self._window_updater.update_available.connect(self._on_window_update_available)
        self._window_updater.up_to_date.connect(self._on_window_up_to_date)
        self._window_updater.check_error.connect(self._on_window_check_error)
        self._window_updater.check_for_updates()

    def _on_window_update_available(self, tag: str, notes: str, asset: dict):
        self.btn_check_updates.setEnabled(True)
        self.lbl_update_status.setText(f"Update {tag} available!")
        self.lbl_update_status.setStyleSheet("color: #10b981; font-weight: 600; font-size: 12px;")
        self.show_update_banner(tag, notes, self._window_updater)

    def _on_window_up_to_date(self):
        self.btn_check_updates.setEnabled(True)
        self.lbl_update_status.setText("FreeFlow is up to date.")
        self.lbl_update_status.setStyleSheet("color: #8a8f98; font-size: 12px;")

    def _on_window_check_error(self, err: str):
        self.btn_check_updates.setEnabled(True)
        self.lbl_update_status.setText("Could not reach GitHub.")
        self.lbl_update_status.setStyleSheet("color: #ef4444; font-size: 12px;")

    def _save_settings(self, *args):
        """Silently persist configuration and apply changes immediately in real time."""
        if not hasattr(self, "combo_device"):
            return

        self.config.groq_api_key = self.input_key.text().strip()
        self.config.hotkey_modifier = self.shortcut_recorder.modifier
        self.config.hotkey_key = self.shortcut_recorder.key
        self.config.hotkey_mode = "hold" if self.radio_hold.isChecked() else "toggle"

        self.config.audio_device = self.combo_device.currentData() or None
        self.config.autostart = self.chk_autostart.isChecked()
        self.config.start_minimized = self.chk_start_minimized.isChecked()
        self.config.close_to_tray = self.chk_close_to_tray.isChecked()
        self.config.show_hud = self.chk_show_hud.isChecked()
        self.config.check_updates_on_startup = self.chk_updates.isChecked()
        self.config.auto_update_mode = "auto" if self.radio_update_auto.isChecked() else "ask"

        set_autostart(self.config.autostart, self.config.start_minimized)
        self.config.save()

        hk_str = self.config.get_display_hotkey()
        self.btn_hotkey_badge.setText(f"Shortcut: {hk_str}")
        self._update_footer_keycaps()

        if self.settings_changed:
            self.settings_changed.emit(self.config)

    def closeEvent(self, event):
        if self.config.close_to_tray:
            event.ignore()
            self.hide()
        else:
            event.accept()

    def set_app_state(self, state: str):
        self.orb_widget.set_state(state)
        if state == "recording":
            self.lbl_orb_status.setText("Listening...")
            self.lbl_sidebar_status.setText("● Recording...")
            self.lbl_sidebar_status.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 600;")
        elif state == "transcribing":
            self.lbl_orb_status.setText("Transcribing with Whisper...")
            self.lbl_sidebar_status.setText("● Transcribing...")
            self.lbl_sidebar_status.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: 600;")
        else:
            self.lbl_orb_status.setText("Ready to Dictate")
            self.lbl_sidebar_status.setText("● Ready")
            self.lbl_sidebar_status.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 500;")

    def update_audio_level(self, level: float):
        self.orb_widget.set_audio_level(level)

    def _on_quit_clicked(self):
        if self.quit_requested:
            self.quit_requested.emit()
