"""
FreeFlow Floating HUD — Human-Crafted Wispr Flow Interface
Features an ambient floating glass capsule, interactive dragging,
multi-layered breathing voice orb, harmonic audio visualizer, and reliable
always-on-top rendering across Linux X11 and Wayland desktops.
"""

import math
import random
import time
from typing import List, Optional

try:
    from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF, pyqtSignal
    from PyQt6.QtGui import (
        QPainter, QColor, QPen, QBrush, QFont,
        QLinearGradient, QRadialGradient, QMouseEvent
    )
    from PyQt6.QtWidgets import QWidget, QApplication
except ImportError:
    class QWidget:
        pass
    def pyqtSignal(*args):
        return None


class RecordingHUD(QWidget):
    """
    Floating desktop capsule HUD.
    Renders cleanly above all windows (browsers, IDEs, terminals) without stealing focus.
    Draggable by clicking and moving anywhere on the capsule.
    """

    solutions_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Linux Window Flags:
        # ToolTip + Frameless + WindowStaysOnTopHint is the most robust cross-distro combination
        # on modern X11 and Wayland (GNOME/Mutter, KDE/KWin, Pop!_OS) to float above all apps.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.ToolTip
        )

        # Translucent background & no focus stealing
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.setFixedSize(380, 58)

        # State management
        self.state = "hidden"
        self.status_message = "Listening..."
        self._current_audio_level = 0.0
        self._record_start_time = 0.0
        self._last_error_details = ""

        # Dragging support
        self._drag_pos: Optional[QPoint] = None

        # Waveform animation
        self._phase = 0.0
        self.num_bars = 9
        self.bar_heights: List[float] = [7.0] * self.num_bars

        # 30 FPS render animation loop
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)

        # Auto-hide timer for finished states
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_hud)

    def snap_to_screen(self):
        """Center the HUD capsule above the bottom dock/taskbar."""
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            x = int(geom.center().x() - (self.width() / 2))
            # 70px above bottom to ensure clearance over Pop!_OS COSMIC / GNOME docks
            y = int(geom.bottom() - self.height() - 70)
            self.move(x, y)

    def set_error(self, message: str = "Transcription Failed", error_details: str = ""):
        """Helper to transition HUD directly to error state with diagnostic info."""
        self._last_error_details = error_details
        self.set_state("error", message=message)

    def set_state(self, new_state: str, message: Optional[str] = None):
        """Transition HUD state and force immediate top-level presentation."""
        self.state = new_state
        self.hide_timer.stop()

        if new_state == "recording":
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.status_message = message or "Listening..."
            self._record_start_time = time.time()
            self.snap_to_screen()
            self.show()
            self.raise_()
            if not self.anim_timer.isActive():
                self.anim_timer.start(33)

        elif new_state == "transcribing":
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.status_message = message or "Transcribing..."
            self.show()
            self.raise_()
            if not self.anim_timer.isActive():
                self.anim_timer.start(33)

        elif new_state == "formatting":
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.status_message = message or "Polishing with AI..."
            self.show()
            self.raise_()
            if not self.anim_timer.isActive():
                self.anim_timer.start(33)

        elif new_state == "done":
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.status_message = message or "Injected!"
            self.anim_timer.stop()
            self.show()
            self.raise_()
            self.update()
            self.hide_timer.start(1800)

        elif new_state == "error":
            # Change cursor to hand to show clickability for solutions
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.status_message = message or "Transcription Failed"
            self.anim_timer.stop()
            self.show()
            self.raise_()
            self.update()
            # Give user 8 seconds to click for solutions before auto-dismissing
            self.hide_timer.start(8000)

        elif new_state == "hidden":
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.hide_hud()

    def update_audio_level(self, level: float):
        """Update live voice volume (0.0 to 1.0)."""
        self._current_audio_level = max(0.0, min(1.0, level))

    def _update_animation(self):
        """Animate visualizer with harmonic wave math and live microphone level."""
        self._phase += 0.24

        if self.state == "recording":
            for i in range(self.num_bars):
                harmonic = math.sin(self._phase + (i * 0.75))
                base = 6.0
                voice_boost = self._current_audio_level * 36.0 * (0.6 + 0.4 * abs(harmonic))
                target = base + voice_boost + random.uniform(0.0, 3.0)
                self.bar_heights[i] += (target - self.bar_heights[i]) * 0.45

        elif self.state in ("transcribing", "formatting"):
            for i in range(self.num_bars):
                target = 6.0 + abs(math.sin(self._phase + (i * 0.65))) * 18.0
                self.bar_heights[i] += (target - self.bar_heights[i]) * 0.35

        self.update()

    def hide_hud(self):
        self.state = "hidden"
        self.anim_timer.stop()
        self.hide()

    # --------------------------------------------------------------------------
    # Interactive Dragging Support
    # --------------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent):
        if self.state == "error":
            # Clicking on the error capsule directly opens the Troubleshooting & Solutions dialog
            self.solutions_requested.emit(self._last_error_details)
            self.hide_hud()
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None

    # --------------------------------------------------------------------------
    # Painting
    # --------------------------------------------------------------------------
    def paintEvent(self, event):
        if self.state == "hidden":
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)

        # 1. Dark Frosted Obsidian Capsule Container
        bg_gradient = QLinearGradient(0, 0, 0, self.height())
        bg_gradient.setColorAt(0.0, QColor(18, 24, 38, 245))
        bg_gradient.setColorAt(1.0, QColor(9, 13, 22, 252))

        # Ambient border glow depending on state
        if self.state == "recording":
            border_color = QColor(0, 225, 175, 140)   # Glowing Mint
        elif self.state in ("transcribing", "formatting"):
            border_color = QColor(168, 85, 247, 150)  # Violet
        elif self.state == "done":
            border_color = QColor(16, 185, 129, 180)  # Emerald
        else:
            border_color = QColor(239, 68, 68, 170)   # Red

        painter.setBrush(QBrush(bg_gradient))
        painter.setPen(QPen(border_color, 1.5))
        painter.drawRoundedRect(rect, 27.0, 27.0)

        # 2. Glowing Voice Orb (Wispr style multi-layer radial gradient)
        orb_center = QPointF(28.0, float(self.height() / 2.0))
        pulse = (math.sin(self._phase * 2.2) + 1.0) / 2.0

        if self.state == "recording":
            glow_radius = 18.0 + (pulse * 5.0) + (self._current_audio_level * 8.0)
            orb_radius = 7.5 + (pulse * 2.0) + (self._current_audio_level * 5.0)

            # Outer diffuse aura
            aura = QRadialGradient(orb_center, glow_radius)
            aura.setColorAt(0.0, QColor(0, 225, 175, int(90 + 70 * pulse)))
            aura.setColorAt(0.6, QColor(6, 182, 212, int(35 * pulse)))
            aura.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(aura))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(orb_center, glow_radius, glow_radius)

            # Core
            core = QRadialGradient(orb_center, orb_radius)
            core.setColorAt(0.0, QColor(240, 253, 250))
            core.setColorAt(0.5, QColor(45, 212, 191))
            core.setColorAt(1.0, QColor(13, 148, 136))
            painter.setBrush(QBrush(core))
            painter.drawEllipse(orb_center, orb_radius, orb_radius)

        elif self.state in ("transcribing", "formatting"):
            aura = QRadialGradient(orb_center, 18.0)
            aura.setColorAt(0.0, QColor(168, 85, 247, 130))
            aura.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(aura))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(orb_center, 18.0, 18.0)

            painter.setBrush(QBrush(QColor(192, 132, 252)))
            painter.drawEllipse(orb_center, 6.5, 6.5)

        elif self.state == "done":
            painter.setBrush(QBrush(QColor(16, 185, 129)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(orb_center, 6.0, 6.0)

        else:
            painter.setBrush(QBrush(QColor(239, 68, 68)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(orb_center, 6.0, 6.0)

        # 3. Typography & Duration Timer
        painter.setPen(QColor(241, 245, 249))
        font_main = QFont("Inter, Ubuntu, Cantarell, Sans-Serif", 10, QFont.Weight.DemiBold)
        painter.setFont(font_main)

        if self.state == "error":
            # Confine error text so it doesn't collide with the "View Solutions" pill
            text_rect = QRectF(48, 12, float(self.width() - 48 - 148), 34)
            painter.drawText(
                text_rect,
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                self.status_message
            )
        else:
            painter.drawText(48, 34, self.status_message)

        if self.state == "recording" and self._record_start_time > 0:
            elapsed = int(time.time() - self._record_start_time)
            mins, secs = divmod(elapsed, 60)
            painter.setPen(QColor(148, 163, 184))
            font_timer = QFont("JetBrains Mono, Ubuntu Mono, monospace", 9, QFont.Weight.Normal)
            painter.setFont(font_timer)
            painter.drawText(136, 34, f"{mins}:{secs:02d}")

        # 4. Harmonic Audio Waveform Bars (Right Side)
        if self.state in ("recording", "transcribing", "formatting"):
            bar_width = 3.2
            bar_spacing = 4.0
            total_bars_width = (self.num_bars * bar_width) + ((self.num_bars - 1) * bar_spacing)
            start_x = self.width() - 24.0 - total_bars_width
            center_y = float(self.height() / 2.0)

            for i, h in enumerate(self.bar_heights):
                x = start_x + (i * (bar_width + bar_spacing))
                clamped_h = max(4.0, min(34.0, h))
                y = center_y - (clamped_h / 2.0)

                bar_grad = QLinearGradient(x, y, x, y + clamped_h)
                if self.state == "recording":
                    bar_grad.setColorAt(0.0, QColor(45, 212, 191, 250))
                    bar_grad.setColorAt(1.0, QColor(6, 182, 212, 220))
                else:
                    bar_grad.setColorAt(0.0, QColor(192, 132, 252, 240))
                    bar_grad.setColorAt(1.0, QColor(147, 51, 234, 220))

                painter.setBrush(QBrush(bar_grad))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(QRectF(x, y, bar_width, clamped_h), 1.6, 1.6)

        elif self.state == "done":
            painter.setPen(QPen(QColor(16, 185, 129), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            cx = self.width() - 28
            cy = self.height() // 2
            painter.drawLine(cx - 6, cy, cx - 2, cy + 4)
            painter.drawLine(cx - 2, cy + 4, cx + 6, cy - 4)

        elif self.state == "error":
            # Interactive "View Solutions →" pill button on the right side
            btn_w = 126.0
            btn_h = 26.0
            btn_x = float(self.width() - btn_w - 14.0)
            btn_y = float((self.height() - btn_h) / 2.0)
            btn_rect = QRectF(btn_x, btn_y, btn_w, btn_h)

            painter.setBrush(QBrush(QColor(239, 68, 68, 48)))
            painter.setPen(QPen(QColor(239, 68, 68, 190), 1.2))
            painter.drawRoundedRect(btn_rect, 13.0, 13.0)

            painter.setPen(QColor(254, 202, 202))
            font_btn = QFont("Inter, Ubuntu, Cantarell, Sans-Serif", 9, QFont.Weight.DemiBold)
            painter.setFont(font_btn)
            painter.drawText(btn_rect, int(Qt.AlignmentFlag.AlignCenter), "View Solutions →")
