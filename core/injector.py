"""
FreeFlow Cross-Platform Text Injector
Handles robust active-window text injection across Linux (Wayland & X11),
Windows, and macOS.
Preserves and restores the user's existing clipboard buffer.
"""

import logging
import os
import shutil
import subprocess
import time
from typing import Optional

from core.platform import is_linux, is_macos, is_windows

logger = logging.getLogger("FreeFlow.Injector")


def is_wayland_session() -> bool:
    """Detect if current session is running under Linux Wayland."""
    if not is_linux():
        return False
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if "wayland" in session:
        return True
    if os.environ.get("WAYLAND_DISPLAY"):
        return True
    return False


class TextInjector:
    """Manages active-window text injection across Linux, Windows, and macOS."""

    def __init__(
        self,
        inject_delay: float = 0.15,
        use_clipboard: bool = True,
        restore_clipboard: bool = True
    ):
        self.inject_delay = inject_delay
        self.use_clipboard = use_clipboard
        self.restore_clipboard = restore_clipboard

    def inject(self, text: str) -> bool:
        """
        Inject text into the user's active window/cursor position.
        Dispatches to the appropriate OS-specific injection strategy.
        """
        if not text:
            logger.warning("Empty text passed for injection.")
            return False

        # Sleep briefly to ensure physical hotkey modifiers (Alt, Ctrl, Super, etc.) have released
        time.sleep(self.inject_delay)

        # 1. Microsoft Windows
        if is_windows():
            return self._inject_windows(text)

        # 2. Apple macOS
        if is_macos():
            return self._inject_macos(text)

        # 3. Linux (Wayland or X11)
        is_wayland = is_wayland_session()
        logger.info(f"Injecting {len(text)} characters on Linux (Wayland={is_wayland}).")

        if is_wayland:
            if self._inject_wayland(text):
                return True
            logger.info("Wayland injection unsuccessful, falling back to X11 tools...")
            if self._inject_x11(text):
                return True
        else:
            if self._inject_x11(text):
                return True
            logger.info("X11 injection unsuccessful, attempting Wayland tools fallback...")
            if self._inject_wayland(text):
                return True

        # Last-resort fallback for Linux: pynput controller simulation
        return self._inject_pynput_fallback(text)

    def _inject_windows(self, text: str) -> bool:
        """Inject text on Microsoft Windows using clipboard + Ctrl+V or SendInput."""
        try:
            import pyperclip
        except ImportError:
            pyperclip = None

        if self.use_clipboard and pyperclip is not None:
            saved_clipboard: Optional[str] = None
            if self.restore_clipboard:
                try:
                    saved_clipboard = pyperclip.paste()
                except Exception as e:
                    logger.debug(f"Could not backup Windows clipboard: {e}")

            try:
                pyperclip.copy(text)
                time.sleep(0.05)

                ctrl_v_sent = False
                # Strategy 1: Win32 native SendInput via ctypes (fastest and cleanest)
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    VK_CONTROL = 0x11
                    VK_V = 0x56
                    KEYEVENTF_KEYUP = 0x0002
                    user32.keybd_event(VK_CONTROL, 0, 0, 0)
                    user32.keybd_event(VK_V, 0, 0, 0)
                    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
                    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
                    ctrl_v_sent = True
                except Exception:
                    pass

                # Strategy 2: pyautogui fallback
                if not ctrl_v_sent:
                    try:
                        import pyautogui
                        pyautogui.hotkey("ctrl", "v")
                        ctrl_v_sent = True
                    except Exception:
                        pass

                # Strategy 3: pynput keyboard fallback
                if not ctrl_v_sent:
                    try:
                        from pynput.keyboard import Controller, Key
                        kbd = Controller()
                        with kbd.pressed(Key.ctrl):
                            kbd.tap("v")
                        ctrl_v_sent = True
                    except Exception:
                        pass

                if ctrl_v_sent:
                    logger.info("Injected text successfully via Windows clipboard + Ctrl+V.")
                    if self.restore_clipboard and saved_clipboard is not None:
                        time.sleep(0.2)
                        try:
                            pyperclip.copy(saved_clipboard)
                        except Exception as e:
                            logger.debug(f"Failed to restore Windows clipboard: {e}")
                    return True
            except Exception as e:
                logger.warning(f"Windows clipboard injection failed: {e}")

        # Fallback to direct typing
        return self._inject_pynput_fallback(text)

    def _inject_macos(self, text: str) -> bool:
        """Inject text on macOS using clipboard + Cmd+V (AppleScript/pyperclip)."""
        try:
            import pyperclip
        except ImportError:
            pyperclip = None

        has_pbcopy = shutil.which("pbcopy") is not None

        if self.use_clipboard and (pyperclip is not None or has_pbcopy):
            saved_clipboard: Optional[str] = None
            if self.restore_clipboard:
                if has_pbcopy and shutil.which("pbpaste"):
                    try:
                        res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=1.0)
                        if res.returncode == 0:
                            saved_clipboard = res.stdout
                    except Exception:
                        pass
                elif pyperclip is not None:
                    try:
                        saved_clipboard = pyperclip.paste()
                    except Exception:
                        pass

            try:
                # Copy to macOS clipboard
                if has_pbcopy:
                    proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                    proc.communicate(input=text.encode("utf-8"), timeout=2.0)
                elif pyperclip is not None:
                    pyperclip.copy(text)

                time.sleep(0.06)

                # Send Cmd+V via AppleScript (most reliable on macOS)
                cmd_v_sent = False
                if shutil.which("osascript"):
                    try:
                        script = 'tell application "System Events" to keystroke "v" using command down'
                        res = subprocess.run(["osascript", "-e", script], check=True, timeout=2.0)
                        cmd_v_sent = (res.returncode == 0)
                    except Exception as e:
                        logger.debug(f"osascript Cmd+V failed: {e}")

                if not cmd_v_sent:
                    try:
                        import pyautogui
                        pyautogui.hotkey("command", "v")
                        cmd_v_sent = True
                    except Exception:
                        pass

                if not cmd_v_sent:
                    try:
                        from pynput.keyboard import Controller, Key
                        kbd = Controller()
                        with kbd.pressed(Key.cmd):
                            kbd.tap("v")
                        cmd_v_sent = True
                    except Exception:
                        pass

                if cmd_v_sent:
                    logger.info("Injected text successfully via macOS clipboard + Cmd+V.")
                    if self.restore_clipboard and saved_clipboard is not None:
                        time.sleep(0.2)
                        try:
                            if has_pbcopy:
                                proc2 = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                                proc2.communicate(input=saved_clipboard.encode("utf-8"), timeout=1.5)
                            elif pyperclip is not None:
                                pyperclip.copy(saved_clipboard)
                        except Exception:
                            pass
                    return True
            except Exception as e:
                logger.warning(f"macOS clipboard injection failed: {e}")

        # Fallback to direct typing
        return self._inject_pynput_fallback(text)

    def _inject_wayland(self, text: str) -> bool:
        """Inject text using Wayland utilities (wl-copy, wtype)."""
        has_wl_copy = shutil.which("wl-copy") is not None
        has_wtype = shutil.which("wtype") is not None

        if not (has_wl_copy or has_wtype):
            logger.debug("Wayland tools (wl-copy/wtype) not installed on system.")
            return False

        # Strategy 1: Clipboard + simulated paste (fastest and handles unicode/newlines best)
        if self.use_clipboard and has_wl_copy and has_wtype:
            saved_clipboard: Optional[bytes] = None
            if self.restore_clipboard and shutil.which("wl-paste"):
                try:
                    res = subprocess.run(
                        ["wl-paste", "--no-newline"],
                        capture_output=True,
                        timeout=1.0
                    )
                    if res.returncode == 0:
                        saved_clipboard = res.stdout
                except Exception as e:
                    logger.debug(f"Could not backup Wayland clipboard: {e}")

            try:
                # Copy text to Wayland clipboard
                subprocess.run(
                    ["wl-copy"],
                    input=text.encode("utf-8"),
                    check=True,
                    timeout=2.0
                )
                time.sleep(0.06)

                # Send Ctrl+V using wtype
                subprocess.run(
                    ["wtype", "-M", "ctrl", "-k", "v", "-m", "ctrl"],
                    check=True,
                    timeout=2.0
                )
                logger.info("Injected text successfully via Wayland wl-copy + wtype Ctrl+V.")

                # Restore previous clipboard if requested
                if self.restore_clipboard and saved_clipboard is not None:
                    time.sleep(0.2)
                    try:
                        subprocess.run(
                            ["wl-copy"],
                            input=saved_clipboard,
                            timeout=1.5
                        )
                    except Exception as e:
                        logger.debug(f"Failed to restore Wayland clipboard: {e}")

                return True
            except Exception as e:
                logger.warning(f"Wayland clipboard injection failed: {e}. Trying wtype direct typing...")

        # Strategy 2: Direct typing via wtype
        if has_wtype:
            try:
                subprocess.run(
                    ["wtype", "-"],
                    input=text.encode("utf-8"),
                    check=True,
                    timeout=5.0
                )
                logger.info("Injected text successfully via wtype direct typing.")
                return True
            except Exception as e:
                logger.warning(f"wtype direct typing failed: {e}")

        return False

    def _inject_x11(self, text: str) -> bool:
        """Inject text using X11 utilities (xclip/xsel, xdotool)."""
        has_xclip = shutil.which("xclip") is not None
        has_xdotool = shutil.which("xdotool") is not None
        has_xsel = shutil.which("xsel") is not None

        if not (has_xdotool or has_xclip or has_xsel):
            logger.debug("X11 tools (xdotool/xclip/xsel) not installed on system.")
            return False

        # Strategy 1: Clipboard + simulated paste
        if self.use_clipboard and has_xdotool and (has_xclip or has_xsel):
            saved_clipboard: Optional[bytes] = None

            # Backup existing clipboard
            if self.restore_clipboard:
                if has_xclip:
                    try:
                        res = subprocess.run(
                            ["xclip", "-selection", "clipboard", "-o"],
                            capture_output=True,
                            timeout=1.0
                        )
                        if res.returncode == 0:
                            saved_clipboard = res.stdout
                    except Exception as e:
                        logger.debug(f"Could not backup X11 clipboard: {e}")
                elif has_xsel:
                    try:
                        res = subprocess.run(
                            ["xsel", "--clipboard", "--output"],
                            capture_output=True,
                            timeout=1.0
                        )
                        if res.returncode == 0:
                            saved_clipboard = res.stdout
                    except Exception:
                        pass

            try:
                # Copy to clipboard
                if has_xclip:
                    proc = subprocess.Popen(
                        ["xclip", "-selection", "clipboard"],
                        stdin=subprocess.PIPE
                    )
                    proc.communicate(input=text.encode("utf-8"), timeout=2.0)
                else:
                    proc = subprocess.Popen(
                        ["xsel", "--clipboard", "--input"],
                        stdin=subprocess.PIPE
                    )
                    proc.communicate(input=text.encode("utf-8"), timeout=2.0)

                time.sleep(0.06)

                # Simulate Ctrl+V with xdotool
                subprocess.run(
                    ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                    check=True,
                    timeout=2.0
                )
                logger.info("Injected text successfully via X11 clipboard + xdotool Ctrl+V.")

                # Restore previous clipboard
                if self.restore_clipboard and saved_clipboard is not None:
                    time.sleep(0.2)
                    try:
                        if has_xclip:
                            p2 = subprocess.Popen(
                                ["xclip", "-selection", "clipboard"],
                                stdin=subprocess.PIPE
                            )
                            p2.communicate(input=saved_clipboard, timeout=1.5)
                        elif has_xsel:
                            p2 = subprocess.Popen(
                                ["xsel", "--clipboard", "--input"],
                                stdin=subprocess.PIPE
                            )
                            p2.communicate(input=saved_clipboard, timeout=1.5)
                    except Exception as e:
                        logger.debug(f"Failed to restore X11 clipboard: {e}")

                return True
            except Exception as e:
                logger.warning(f"X11 clipboard injection failed: {e}. Trying xdotool type...")

        # Strategy 2: Direct typing via xdotool
        if has_xdotool:
            try:
                subprocess.run(
                    ["xdotool", "type", "--clearmodifiers", "--delay", "2", text],
                    check=True,
                    timeout=10.0
                )
                logger.info("Injected text successfully via xdotool type.")
                return True
            except Exception as e:
                logger.warning(f"xdotool type failed: {e}")

        return False

    def _inject_pynput_fallback(self, text: str) -> bool:
        """Fallback simulated keystroke typing via pynput."""
        try:
            from pynput.keyboard import Controller
            keyboard = Controller()
            keyboard.type(text)
            logger.info("Injected text successfully via pynput keyboard controller.")
            return True
        except Exception as e:
            logger.error(f"All text injection strategies failed: {e}")
            return False
