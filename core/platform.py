"""
FreeFlow Cross-Platform Environment & OS Abstraction Layer
Provides unified platform detection, system paths, and OS-specific primitives
for Linux, Windows, and macOS.
"""

import os
import sys
import tempfile
from pathlib import Path


def is_linux() -> bool:
    """Return True if running on Linux / BSD."""
    return sys.platform.startswith("linux") or sys.platform.startswith("freebsd")


def is_windows() -> bool:
    """Return True if running on Microsoft Windows."""
    return sys.platform == "win32" or sys.platform == "cygwin"


def is_macos() -> bool:
    """Return True if running on Apple macOS (Darwin)."""
    return sys.platform == "darwin"


def get_platform() -> str:
    """Return normalized platform identifier: 'windows', 'macos', or 'linux'."""
    if is_windows():
        return "windows"
    elif is_macos():
        return "macos"
    return "linux"


def get_config_dir() -> Path:
    """
    Return platform-standard application configuration directory:
    - Windows: %APPDATA%/FreeFlow
    - macOS: ~/Library/Application Support/FreeFlow
    - Linux: $XDG_CONFIG_HOME/freeflow or ~/.config/freeflow
    """
    if is_windows():
        appdata = os.environ.get("APPDATA")
        if appdata:
            path = Path(appdata) / "FreeFlow"
        else:
            path = Path.home() / "AppData" / "Roaming" / "FreeFlow"
    elif is_macos():
        path = Path.home() / "Library" / "Application Support" / "FreeFlow"
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            path = Path(xdg_config) / "freeflow"
        else:
            path = Path.home() / ".config" / "freeflow"

    path.mkdir(parents=True, exist_ok=True)
    return path


def get_history_file() -> Path:
    """Return path to history.json in configuration directory."""
    return get_config_dir() / "history.json"


def get_audio_temp_path() -> str:
    """Return safe cross-platform temporary WAV audio buffer path."""
    return str(Path(tempfile.gettempdir()) / "freeflow_audio.wav")
