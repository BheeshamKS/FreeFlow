"""
FreeFlow Universal Design System & Theme Tokens
Synchronized with FreeFlow Pocket (Android) design language.
Aesthetic: Pitch Black (#000000) Obsidian Glass, Electric Flow Azure (#5AB4FF),
Emerald (#00E676), and Vivid Violet (#D500F9).
"""

# ==============================================================================
# 1. Color Palette Tokens (Matched to FreeFlow Pocket)
# ==============================================================================
DARK_BACKGROUND = "#000000"          # Pitch-black true dark background
DARK_SURFACE = "#0E0E12"             # Obsidian surface elevation (sidebars, panels, dialog headers)
DARK_CARD = "#18181C"                # Card frames, content containers, inputs, table cells
DARK_CARD_HOVER = "#222228"          # Interactive card hover background
DARK_CARD_BORDER = "#26262E"         # Hairline subtle border (1px)
DARK_CARD_BORDER_HOVER = "#3B3B48"   # Focused/hovered border highlight

# Brand Accent Colors
PRIMARY_BLUE = "#5AB4FF"             # FreeFlow Signature Electric Azure (Primary)
PRIMARY_BLUE_GLOW = "rgba(90, 180, 255, 0.20)"
PRIMARY_GRADIENT_START = "#32FFE4"   # Electric Cyan (from Logo)
PRIMARY_GRADIENT_END = "#0072DA"     # Flow Azure (from Logo)

ACCENT_GREEN = "#00E676"             # Active recording / Success confirmation
ACCENT_GREEN_BG = "#062B1F"          # Emerald card surface
ACCENT_GREEN_BORDER = "#00E676"

ACCENT_VIOLET = "#D500F9"            # AI formatting & Whisper processing
ACCENT_VIOLET_BG = "#2B0B30"
ACCENT_VIOLET_BORDER = "#D500F9"

ACCENT_GOLD = "#FFD600"              # Notice / Warning / Cooldown
ACCENT_RED = "#FF5252"               # Error / Diagnostic alert
ACCENT_RED_BG = "#2B0F13"
ACCENT_RED_BORDER = "#FF5252"

# Typography Colors
TEXT_PRIMARY = "#FFFFFF"             # Crisp high-contrast headline & body text
TEXT_SECONDARY = "#9E9EA8"           # Muted secondary text & subheadings
TEXT_TERTIARY = "#686874"            # Helper captions, labels & disabled indicators

# Font Family Definitions
FONT_SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Inter', 'Ubuntu', sans-serif"
FONT_MONO = "'JetBrains Mono', 'Ubuntu Mono', 'Consolas', monospace"


def get_application_stylesheet() -> str:
    """Return unified Qt stylesheet for FreeFlow desktop application."""
    return f"""
        QMainWindow, QWidget#AppCanvas {{
            background-color: {DARK_BACKGROUND};
            color: {TEXT_PRIMARY};
            font-family: {FONT_SANS};
        }}
        QWidget#Sidebar {{
            background-color: {DARK_SURFACE};
            border-right: 1px solid {DARK_CARD_BORDER};
        }}
        QWidget#ContentCanvas {{
            background-color: {DARK_BACKGROUND};
        }}
        /* Elegant Obsidian Card Panels */
        QFrame#SurfaceCard, QFrame[surface="true"], QFrame.CardFrame {{
            background-color: {DARK_CARD};
            border: 1px solid {DARK_CARD_BORDER};
            border-radius: 12px;
        }}
        QFrame#SurfaceCard:hover {{
            border-color: {DARK_CARD_BORDER_HOVER};
        }}
        /* Primary Buttons */
        QPushButton#PrimaryAction, QPushButton[variant="primary"], QPushButton.PrimaryBtn {{
            background-color: {PRIMARY_BLUE};
            color: #000000;
            border: 1px solid {PRIMARY_BLUE};
            border-radius: 8px;
            padding: 9px 18px;
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton#PrimaryAction:hover, QPushButton[variant="primary"]:hover, QPushButton.PrimaryBtn:hover {{
            background-color: #7ec5ff;
            border-color: #7ec5ff;
            color: #000000;
        }}
        QPushButton#PrimaryAction:pressed, QPushButton[variant="primary"]:pressed, QPushButton.PrimaryBtn:pressed {{
            background-color: #3b9fff;
            border-color: #3b9fff;
        }}
        /* Secondary & Ghost Buttons */
        QPushButton#GhostAction, QPushButton[variant="ghost"], QPushButton.SecondaryBtn {{
            background-color: {DARK_CARD};
            color: {TEXT_PRIMARY};
            border: 1px solid {DARK_CARD_BORDER};
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
        }}
        QPushButton#GhostAction:hover, QPushButton[variant="ghost"]:hover, QPushButton.SecondaryBtn:hover {{
            background-color: {DARK_CARD_HOVER};
            border-color: {DARK_CARD_BORDER_HOVER};
            color: #ffffff;
        }}
        /* Form inputs */
        QLineEdit, QTextEdit, QComboBox {{
            background-color: {DARK_CARD};
            color: {TEXT_PRIMARY};
            border: 1px solid {DARK_CARD_BORDER};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 13px;
            selection-background-color: {PRIMARY_BLUE};
            selection-color: #000000;
        }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
            border: 1px solid {PRIMARY_BLUE};
            background-color: #1c1c22;
        }}
        QCheckBox, QRadioButton {{
            color: {TEXT_SECONDARY};
            font-size: 13px;
            spacing: 8px;
        }}
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            background-color: {DARK_CARD};
            border: 1px solid {DARK_CARD_BORDER};
            border-radius: 4px;
        }}
        QRadioButton::indicator {{
            border-radius: 8px;
        }}
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
            background-color: {PRIMARY_BLUE};
            border-color: {PRIMARY_BLUE};
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
    """
