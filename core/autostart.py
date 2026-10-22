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


def _set_autostart_linux(enable: bool, start_minimized: bool) -> bool:
    """Configure XDG autostart .desktop file and systemd user service on Linux."""
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

    # Update systemd user service if present
    service_file = Path.home() / ".config" / "systemd" / "user" / "freeflow.service"
    if service_file.exists() or enable:
        try:
            service_dir = service_file.parent
            service_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine working directory
            working_dir = str(Path(__file__).resolve().parent.parent)
            
            service_content = f"""[Unit]
Description=FreeFlow Voice Dictation Service
Documentation=https://github.com/BheeshamKS/FreeFlow
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart={exec_cmd}
WorkingDirectory={working_dir}
Environment=PYTHONUNBUFFERED=1
Environment=DISPLAY=:0
Environment=WAYLAND_DISPLAY=wayland-0
Restart=on-failure
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical-session.target
"""
            service_file.write_text(service_content, encoding="utf-8")
            
            action = "enable" if enable else "disable"
            subprocess.run(
                ["systemctl", "--user", action, "freeflow.service"],
                capture_output=True,
                timeout=3.0
            )
            logger.info(f"systemctl --user {action} freeflow.service executed")
        except Exception as e:
            logger.debug(f"systemd autostart step skipped or failed: {e}")

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
