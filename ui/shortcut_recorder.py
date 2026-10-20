"""
FreeFlow Interactive Shortcut Recorder Widget
Provides an interactive key-capture button (macOS/Wispr Flow style).
Listens for user keystrokes, converts Qt key sequences to evdev/pynput definitions,
and updates hotkey configuration with human-crafted, non-AI styling.
"""

import logging
from typing import Optional, Tuple

try:
    from PyQt6.QtCore import Qt, pyqtSignal, QTimer
    from PyQt6.QtGui import QKeyEvent, QKeySequence
    from PyQt6.QtWidgets import (
        QWidget, QHBoxLayout, QPushButton, QLabel, QFrame
    )
except ImportError:
    class QWidget:
        pass
    def pyqtSignal(*args):
        return None

logger = logging.getLogger("FreeFlow.ShortcutRecorder")


def qt_key_to_evdev(key_code: int, key_text: str) -> Optional[str]:
    """Map a Qt.Key integer to an evdev key name string."""
    # Function keys
    if Qt.Key.Key_F1 <= key_code <= Qt.Key.Key_F12:
        f_num = key_code - Qt.Key.Key_F1 + 1
        return f"KEY_F{f_num}"

    # Letter keys (A-Z)
    if Qt.Key.Key_A <= key_code <= Qt.Key.Key_Z:
        char = chr(key_code).upper()
        return f"KEY_{char}"

    # Number keys (0-9)
    if Qt.Key.Key_0 <= key_code <= Qt.Key.Key_9:
        digit = chr(key_code)
        return f"KEY_{digit}"

    # Specific common keys
    mapping = {
        Qt.Key.Key_Space: "KEY_SPACE",
        Qt.Key.Key_Tab: "KEY_TAB",
        Qt.Key.Key_Return: "KEY_ENTER",
        Qt.Key.Key_Enter: "KEY_ENTER",
        Qt.Key.Key_Backspace: "KEY_BACKSPACE",
        Qt.Key.Key_QuoteLeft: "KEY_GRAVE",
        Qt.Key.Key_AsciiTilde: "KEY_GRAVE",
        Qt.Key.Key_Minus: "KEY_MINUS",
        Qt.Key.Key_Equal: "KEY_EQUAL",
        Qt.Key.Key_BracketLeft: "KEY_LEFTBRACE",
        Qt.Key.Key_BracketRight: "KEY_RIGHTBRACE",
        Qt.Key.Key_Backslash: "KEY_BACKSLASH",
        Qt.Key.Key_Semicolon: "KEY_SEMICOLON",
        Qt.Key.Key_Apostrophe: "KEY_APOSTROPHE",
        Qt.Key.Key_Comma: "KEY_COMMA",
        Qt.Key.Key_Period: "KEY_DOT",
        Qt.Key.Key_Slash: "KEY_SLASH",
        Qt.Key.Key_Alt: "KEY_LEFTALT",
        Qt.Key.Key_Control: "KEY_LEFTCTRL",
        Qt.Key.Key_Shift: "KEY_LEFTSHIFT",
        Qt.Key.Key_Meta: "KEY_LEFTMETA",
    }
    if key_code in mapping:
        return mapping[key_code]

    # Fallback to key text if alphanumeric
    if key_text and key_text.isalnum():
        return f"KEY_{key_text.upper()}"

    return None


class ShortcutRecorderWidget(QWidget):
    """
    Interactive shortcut recorder widget.
    Click 'Record' -> Press your combination (e.g. Alt+R, Ctrl+Space, F9) -> Saves automatically.
    """

    shortcut_changed = pyqtSignal(str, str) if QWidget is not None else None  # (modifier_str, key_str)

    def __init__(self, modifier: str = "KEY_LEFTALT", key: str = "KEY_R", parent=None):
        super().__init__(parent)
        self.modifier = modifier
        self.key = key
        self.is_recording = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Current shortcut key badges display
        self.badge_container = QWidget(self)
        self.badge_layout = QHBoxLayout(self.badge_container)
        self.badge_layout.setContentsMargins(0, 0, 0, 0)
        self.badge_layout.setSpacing(4)
        layout.addWidget(self.badge_container)

        # The interactive record button
        self.btn_record = QPushButton("Record Shortcut", self)
        self.btn_record.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_record.clicked.connect(self.toggle_recording)
        layout.addWidget(self.btn_record)

        # Reset button
        self.btn_reset = QPushButton("Reset Default", self)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #71717a;
                border: 1px solid #1f232c;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                color: #e2e4e9;
                border-color: #2e3544;
                background-color: #14171f;
            }
        """)
        self.btn_reset.clicked.connect(self.reset_to_default)
        layout.addWidget(self.btn_reset)

        layout.addStretch()

        self._update_badges()
        self._apply_normal_style()

    def set_shortcut(self, modifier: str, key: str):
        """Set shortcut values externally."""
        self.modifier = modifier
        self.key = key
        self._update_badges()

    def _apply_normal_style(self):
        self.btn_record.setText("Record Shortcut")
        self.btn_record.setStyleSheet("""
            QPushButton {
                background-color: #14171f;
                color: #f4f4f6;
                border: 1px solid #232836;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: 600;
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

    def _apply_recording_style(self):
        self.btn_record.setText("● Press Keys (Esc to cancel)...")
        self.btn_record.setStyleSheet("""
            QPushButton {
                background-color: #261114;
                color: #ff6161;
                border: 1.5px solid #ef4444;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: 600;
            }
        """)

    def _update_badges(self):
        """Draw tactile keyboard key cap pills."""
        # Clear existing badges
        while self.badge_layout.count() > 0:
            item = self.badge_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        parts = []
        mod = self.modifier.upper()
        if "ALT" in mod:
            parts.append("Alt")
        elif "CTRL" in mod:
            parts.append("Ctrl")
        elif "SHIFT" in mod:
            parts.append("Shift")
        elif "META" in mod or "SUPER" in mod:
            parts.append("Super")

        k = self.key.upper().replace("KEY_", "")
        if k:
            parts.append(k.capitalize())

        if not parts:
            parts = ["None"]

        for i, part in enumerate(parts):
            if i > 0:
                plus = QLabel("+")
                plus.setStyleSheet("color: #52525b; font-weight: bold; font-size: 12px;")
                self.badge_layout.addWidget(plus)

            cap = QLabel(part)
            cap.setStyleSheet("""
                QLabel {
                    background-color: #14171f;
                    color: #2dd4bf;
                    border: 1px solid #232836;
                    border-bottom: 2px solid #2f3547;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 600;
                    font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace;
                }
            """)
            self.badge_layout.addWidget(cap)

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.cancel_recording()

    def start_recording(self):
        """Put widget into key-capture mode."""
        self.is_recording = True
        self._apply_recording_style()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        self.grabKeyboard()
        logger.info("Shortcut recorder activated. Waiting for key input...")

    def cancel_recording(self):
        """Cancel capture mode without saving."""
        if self.is_recording:
            self.releaseKeyboard()
            self.is_recording = False
            self._apply_normal_style()
            logger.info("Shortcut recording canceled.")

    def reset_to_default(self):
        """Reset to default Alt + R."""
        self.cancel_recording()
        self.modifier = "KEY_LEFTALT"
        self.key = "KEY_R"
        self._update_badges()
        if self.shortcut_changed:
            self.shortcut_changed.emit(self.modifier, self.key)

    def keyPressEvent(self, event: QKeyEvent):
        """Capture keyboard event and map to evdev codes."""
        if not self.is_recording:
            super().keyPressEvent(event)
            return

        key_code = event.key()

        # Handle Escape -> Cancel
        if key_code == Qt.Key.Key_Escape:
            self.cancel_recording()
            event.accept()
            return

        # Check for standalone modifier press (ignore until combined or single key released)
        standalone_mods = {
            Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift, Qt.Key.Key_Meta
        }

        modifiers = event.modifiers()
        mod_str = ""

        if modifiers & Qt.KeyboardModifier.AltModifier:
            mod_str = "KEY_LEFTALT"
        elif modifiers & Qt.KeyboardModifier.ControlModifier:
            mod_str = "KEY_LEFTCTRL"
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            mod_str = "KEY_LEFTSHIFT"
        elif modifiers & Qt.KeyboardModifier.MetaModifier:
            mod_str = "KEY_LEFTMETA"

        if key_code in standalone_mods:
            # Standalone modifier pressed without combination key yet
            event.accept()
            return

        # Regular key pressed
        key_evdev = qt_key_to_evdev(key_code, event.text())

        if key_evdev:
            self.modifier = mod_str
            self.key = key_evdev

            logger.info(f"Recorded new shortcut: modifier='{self.modifier}', key='{self.key}'")
            self._update_badges()
            self.cancel_recording()

            if self.shortcut_changed:
                self.shortcut_changed.emit(self.modifier, self.key)

        event.accept()
