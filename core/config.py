"""
FreeFlow Configuration Manager
Handles application settings persistence via PyQt6 QSettings and .env fallback.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from PyQt6.QtCore import QSettings
except ImportError:
    QSettings = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path=None):
        return False


from core.platform import get_config_dir

# Standard search locations for .env fallback
CONFIG_DIR = get_config_dir()
ENV_PATHS = [
    CONFIG_DIR / ".env",
    Path(".env"),
    Path(__file__).resolve().parent.parent / ".env",
]

# Pre-load any existing .env files
for p in ENV_PATHS:
    if p.is_file():
        load_dotenv(p)
        break


def _parse_bool(val, default: bool = False) -> bool:
    """Robustly parse boolean values that may be serialized as strings in QSettings INI files."""
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "on")
    if isinstance(val, (int, float)):
        return bool(val)
    return default


@dataclass
class AppConfig:
    """FreeFlow Application Configuration Data Object."""
    
    # Groq API Configuration
    groq_api_key: str = ""
    transcription_model: str = "whisper-large-v3"
    
    # LLM Text Formatting (Disabled by default: Whisper-large-v3 produces excellent native punctuation & capitalization)
    format_text: bool = False
    format_model: str = "openai/gpt-oss-20b"
    system_prompt: str = (
        "You are an expert transcription editor. Clean up the provided raw speech-to-text transcription. "
        "Fix punctuation, capitalization, and minor grammatical slips. "
        "Remove stuttering and verbal filler words (such as 'um', 'uh', 'you know', 'like', 'ah'). "
        "Do NOT change the underlying meaning, tone, or technical jargon. "
        "Return ONLY the finalized, ready-to-paste text without any preamble, quotes, markdown formatting or commentary."
    )
    
    # Hotkey Configuration
    # Defaults to Alt + R (toggle mode) as requested
    hotkey_modifier: str = "KEY_LEFTALT"    # e.g., KEY_LEFTALT, KEY_RIGHTALT, KEY_LEFTCTRL, ""
    hotkey_key: str = "KEY_R"               # e.g., KEY_R, KEY_SPACE, KEY_F9
    hotkey_mode: str = "toggle"             # "toggle" (press to start, press to stop) or "hold" (push-to-talk)
    
    # Audio Settings
    sample_rate: int = 16000                # 16000 Hz is native & optimal for Whisper
    channels: int = 1                       # Mono
    audio_device: Optional[str] = None      # None = system default
    
    # Text Injection Settings
    inject_delay: float = 0.15              # Delay in seconds to allow modifier keys to release
    use_clipboard_injection: bool = True    # True = fast clipboard paste, False = direct simulated typing
    restore_clipboard: bool = True          # Restore user's previous clipboard buffer after paste
    
    # UI / Feedback Settings
    show_hud: bool = True                   # Floating animated waveform HUD
    enable_notifications: bool = True       # Desktop notifications via notify-send
    autostart: bool = False                 # Launch on graphical session start
    start_minimized: bool = False           # Launch minimized to tray on boot
    close_to_tray: bool = True              # Closing window hides to tray instead of quitting
    first_run_completed: bool = False       # Tracks whether first-time onboarding wizard has completed
    
    @classmethod
    def load(cls) -> "AppConfig":
        """Load configuration from QSettings, falling back to environment variables."""
        cfg = cls()
        
        # 1. Check environment variable first for API key
        env_key = os.environ.get("GROQ_API_KEY", "").strip()
        if env_key:
            cfg.groq_api_key = env_key

        if QSettings is None:
            return cfg

        s = QSettings("FreeFlow", "FreeFlow")
        
        # If QSettings has stored key, prioritize or use it
        stored_key = s.value("groq_api_key", "", type=str).strip()
        if stored_key:
            cfg.groq_api_key = stored_key
        elif not cfg.groq_api_key:
            cfg.groq_api_key = s.value("groq_api_key", "", type=str)
            
        cfg.transcription_model = str(s.value("transcription_model", cfg.transcription_model))
        cfg.format_text = _parse_bool(s.value("format_text"), cfg.format_text)
        cfg.format_model = str(s.value("format_model", cfg.format_model))
        cfg.system_prompt = str(s.value("system_prompt", cfg.system_prompt))
        
        cfg.hotkey_modifier = str(s.value("hotkey_modifier", cfg.hotkey_modifier))
        cfg.hotkey_key = str(s.value("hotkey_key", cfg.hotkey_key))
        cfg.hotkey_mode = str(s.value("hotkey_mode", cfg.hotkey_mode))
        
        cfg.sample_rate = int(s.value("sample_rate", cfg.sample_rate))
        cfg.channels = int(s.value("channels", cfg.channels))
        cfg.inject_delay = float(s.value("inject_delay", cfg.inject_delay))
        cfg.use_clipboard_injection = _parse_bool(s.value("use_clipboard_injection"), cfg.use_clipboard_injection)
        cfg.restore_clipboard = _parse_bool(s.value("restore_clipboard"), cfg.restore_clipboard)
        
        cfg.show_hud = _parse_bool(s.value("show_hud"), cfg.show_hud)
        cfg.enable_notifications = _parse_bool(s.value("enable_notifications"), cfg.enable_notifications)
        cfg.autostart = _parse_bool(s.value("autostart"), cfg.autostart)
        cfg.start_minimized = _parse_bool(s.value("start_minimized"), cfg.start_minimized)
        cfg.close_to_tray = _parse_bool(s.value("close_to_tray"), cfg.close_to_tray)
        cfg.first_run_completed = _parse_bool(s.value("first_run_completed"), cfg.first_run_completed)
        
        return cfg

    def save(self) -> None:
        """Persist current settings to QSettings."""
        if QSettings is None:
            return
            
        s = QSettings("FreeFlow", "FreeFlow")
        s.setValue("groq_api_key", self.groq_api_key)
        s.setValue("transcription_model", self.transcription_model)
        s.setValue("format_text", self.format_text)
        s.setValue("format_model", self.format_model)
        s.setValue("system_prompt", self.system_prompt)
        
        s.setValue("hotkey_modifier", self.hotkey_modifier)
        s.setValue("hotkey_key", self.hotkey_key)
        s.setValue("hotkey_mode", self.hotkey_mode)
        
        s.setValue("sample_rate", self.sample_rate)
        s.setValue("channels", self.channels)
        s.setValue("inject_delay", self.inject_delay)
        s.setValue("use_clipboard_injection", self.use_clipboard_injection)
        s.setValue("restore_clipboard", self.restore_clipboard)
        
        s.setValue("show_hud", self.show_hud)
        s.setValue("enable_notifications", self.enable_notifications)
        s.setValue("autostart", self.autostart)
        s.setValue("start_minimized", self.start_minimized)
        s.setValue("close_to_tray", self.close_to_tray)
        s.setValue("first_run_completed", self.first_run_completed)
        s.sync()

    def get_display_hotkey(self) -> str:
        """Returns human-readable representation of hotkey, e.g. 'Alt + R'."""
        parts = []
        mod = self.hotkey_modifier.upper()
        if "ALT" in mod:
            parts.append("Alt")
        elif "CTRL" in mod:
            parts.append("Ctrl")
        elif "SHIFT" in mod:
            parts.append("Shift")
        elif "META" in mod or "SUPER" in mod:
            parts.append("Super")

        k = self.hotkey_key.upper().replace("KEY_", "")
        if k:
            parts.append(k.capitalize())
            
        return " + ".join(parts) if parts else "None"
