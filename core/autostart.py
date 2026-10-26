"""
FreeFlow Cross-Platform Autostart Manager
Configures automatic startup on graphical login across Linux (XDG Autostart & systemd),
Windows (Registry Run key), and macOS (LaunchAgents).
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
from core.platform import is_linux, is_windows, is_macos

logger = logging.getLogger("FreeFlow.Autostart")


def _get_exec_command(start_minimized: bool = False) -> str:
    """Return the absolute command string to launch FreeFlow with autostart flags."""
    flags = ["--autostart"]
    if start_minimized:
        flags.append("--minimized")

    flag_str = " ".join(flags)

    # Check if running as Linux AppImage
    appimage = os.environ.get("APPIMAGE")
    if appimage and os.path.exists(appimage):
        return f'"{appimage}" {flag_str}'

    # Check if running as PyInstaller / frozen binary
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" {flag_str}'

    # Running from Python source
    main_py = Path(__file__).resolve().parent.parent / "app.py"
    return f'"{sys.executable}" "{main_py}" {flag_str}'


def set_autostart(enable: bool, start_minimized: bool = False) -> bool:
    """
    Enable or disable application autostart on user login.
    Updates desktop/registry/systemd configurations with appropriate launch flags.
    """
    try:
        if is_linux():
            return _set_autostart_linux(enable, start_minimized)
        elif is_windows():
            return _set_autostart_windows(enable, start_minimized)
        elif is_macos():
            return _set_autostart_macos(enable, start_minimized)
        return False
    except Exception as e:
        logger.error(f"Failed to configure autostart (enable={enable}): {e}")
        return False


def ensure_desktop_launcher(target_dir: Optional[Path] = None) -> Optional[Path]:
    """Ensure standard desktop launcher entry exists in ~/.local/share/applications for app menu."""
    if not is_linux() and target_dir is None:
        return None
    try:
        apps_dir = target_dir or (Path.home() / ".local" / "share" / "applications")
        apps_dir.mkdir(parents=True, exist_ok=True)
        desktop_file = apps_dir / "freeflow.desktop"

        # Exec command WITHOUT autostart/minimized flags for standard app launcher
        main_py = Path(__file__).resolve().parent.parent / "app.py"
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"

        appimage = os.environ.get("APPIMAGE")
        if appimage and os.path.exists(appimage):
            exec_cmd = f'"{appimage}"'
        elif getattr(sys, "frozen", False):
            exec_cmd = f'"{sys.executable}"'
        else:
            exec_cmd = f'"{sys.executable}" "{main_py}"'

        content = f"""[Desktop Entry]
Name=FreeFlow
Comment=High-speed speech-to-text dictation application
Exec={exec_cmd}
Icon={icon_path}
Terminal=false
Type=Application
Categories=Utility;Audio;AudioVideo;Accessibility;
StartupNotify=false
Keywords=whisper;voice;dictation;speech;transcription;groq;freeflow;
"""
        desktop_file.write_text(content, encoding="utf-8")
        logger.debug(f"Ensured desktop application launcher at {desktop_file}")
        return desktop_file
    except Exception as e:
        logger.debug(f"Failed to ensure desktop launcher: {e}")
        return None


def _set_autostart_linux(enable: bool, start_minimized: bool) -> bool:
    """Configure XDG autostart .desktop file on Linux (standard cross-desktop specification)."""
    autostart_dir = Path.home() / ".config" / "autostart"
    desktop_file = autostart_dir / "freeflow.desktop"
    exec_cmd = _get_exec_command(start_minimized)

    if enable:
        autostart_dir.mkdir(parents=True, exist_ok=True)
        desktop_content = f"""[Desktop Entry]
Type=Application
Name=FreeFlow
Comment=FreeFlow Voice Dictation Service
Exec={exec_cmd}
Icon=freeflow
Terminal=false
Categories=Utility;Audio;
X-GNOME-Autostart-enabled=true
"""
        desktop_file.write_text(desktop_content, encoding="utf-8")
        logger.info(f"Created XDG autostart entry: {desktop_file} (exec={exec_cmd})")
    else:
        if desktop_file.exists():
            desktop_file.unlink(missing_ok=True)
            logger.info("Removed XDG autostart entry")

    # Clean up redundant systemd user service if present to avoid dual-launch race conditions on boot
    service_file = Path.home() / ".config" / "systemd" / "user" / "freeflow.service"
    if service_file.exists():
        try:
            subprocess.run(
                ["systemctl", "--user", "disable", "--now", "freeflow.service"],
                capture_output=True,
                timeout=3.0
            )
            service_file.unlink(missing_ok=True)
            logger.info("Disabled and removed redundant systemd user service in favor of XDG autostart")
        except Exception as e:
            logger.debug(f"systemd autostart cleanup: {e}")

    # Also make sure app menu entry exists so user can open app from launcher
    ensure_desktop_launcher()

    return True


def _set_autostart_windows(enable: bool, start_minimized: bool) -> bool:
    """Configure Windows Run key in registry."""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                exec_cmd = _get_exec_command(start_minimized)
                winreg.SetValueEx(key, "FreeFlow", 0, winreg.REG_SZ, exec_cmd)
                logger.info(f"Registered Windows autostart: {exec_cmd}")
            else:
                try:
                    winreg.DeleteValue(key, "FreeFlow")
                    logger.info("Unregistered Windows autostart")
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        logger.error(f"Windows autostart registry configuration error: {e}")
        return False


def _set_autostart_macos(enable: bool, start_minimized: bool) -> bool:
    """Configure macOS LaunchAgent plist."""
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    plist_file = launch_agents / "com.freeflow.app.plist"
    
    if enable:
        launch_agents.mkdir(parents=True, exist_ok=True)
        # Parse arguments
        cmd = _get_exec_command(start_minimized)
        import shlex
        args = shlex.split(cmd)
        args_xml = "\n".join(f"        <string>{a}</string>" for a in args)

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.freeflow.app</string>
    <key>ProgramArguments</key>
    <array>
{args_xml}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""
        plist_file.write_text(plist_content, encoding="utf-8")
        logger.info(f"Created macOS LaunchAgent: {plist_file}")
    else:
        if plist_file.exists():
            plist_file.unlink(missing_ok=True)
            logger.info("Removed macOS LaunchAgent")

    return True
