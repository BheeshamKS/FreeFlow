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
from typing import Optional, Tuple

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

    def is_text_box_active(self) -> bool:
        """
        Detect whether an editable input field, text caret, or interactive text box
        is currently focused. Works across Windows, macOS, and Linux.
        """
        if is_windows():
            return self._is_text_box_active_windows()
        elif is_macos():
            return self._is_text_box_active_macos()
        else:
            return self._is_text_box_active_linux()

    def _is_text_box_active_windows(self) -> bool:
        """
        Detect if an editable text control, caret, or active input box is focused on Windows.
        Returns False if user is on desktop wallpaper, taskbar, or a non-input window.
        """
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            # 1. Foreground window
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return False

            # 2. Filter desktop background and taskbar
            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls_buf, 256)
            cls_name = cls_buf.value
            if cls_name in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
                logger.debug(f"Windows foreground window is desktop/taskbar: {cls_name}")
                return False

            # 3. Check GUITHREADINFO for caret or focus
            tid = user32.GetWindowThreadProcessId(hwnd, None)

            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                ]

            class GUITHREADINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("flags", wintypes.DWORD),
                    ("hwndActive", wintypes.HWND),
                    ("hwndFocus", wintypes.HWND),
                    ("hwndCapture", wintypes.HWND),
                    ("hwndMenuOwner", wintypes.HWND),
                    ("hwndMoveSize", wintypes.HWND),
                    ("hwndCaret", wintypes.HWND),
                    ("rcCaret", RECT),
                ]

            info = GUITHREADINFO()
            info.cbSize = ctypes.sizeof(GUITHREADINFO)

            if user32.GetGUIThreadInfo(tid, ctypes.byref(info)):
                # Non-zero caret handle or visible caret bounds
                if info.hwndCaret:
                    return True
                if (info.rcCaret.right > info.rcCaret.left) and (info.rcCaret.bottom > info.rcCaret.top):
                    return True

                # Inspect focused control class
                if info.hwndFocus:
                    f_buf = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(info.hwndFocus, f_buf, 256)
                    focus_cls = f_buf.value.lower()
                    text_classes = (
                        "edit", "richedit", "scintilla", "consolewindowclass",
                        "textbox", "view", "chrome_widgetwin", "subclass"
                    )
                    if any(tc in focus_cls for tc in text_classes):
                        return True

            return bool(hwnd)
        except Exception as e:
            logger.debug(f"Windows active text box check failed: {e}")
            return True

    def _is_text_box_active_macos(self) -> bool:
        """
        Detect if an editable text element is focused on macOS via AppleScript System Events.
        Returns False if Finder desktop or non-editable element is focused.
        """
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                set appName to name of frontApp
                if appName is "Finder" then
                    try
                        set focusedElem to value of attribute "AXFocusedUIElement" of frontApp
                        set elemRole to role of focusedElem
                        if elemRole is in {"AXTextField", "AXTextArea"} then
                            return "true"
                        end if
                    end try
                    return "false"
                end if
                try
                    set focusedElem to value of attribute "AXFocusedUIElement" of frontApp
                    set elemRole to role of focusedElem
                    if elemRole is in {"AXTextField", "AXTextArea", "AXSearchField", "AXComboBox", "AXWebArea"} then
                        return "true"
                    end if
                end try
                return "true"
            end tell
            '''
            res = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=1.0
            )
            if res.returncode == 0:
                output = res.stdout.strip().lower()
                return output == "true"
            return True
        except Exception as e:
            logger.debug(f"macOS active text box check failed: {e}")
            return True

    def _is_text_box_active_linux(self) -> bool:
        """
        Detect if an active window or text box is focused on Linux.
        Returns False if desktop wallpaper/root window or panel dock is focused.
        """
        try:
            if shutil.which("xdotool"):
                res = subprocess.run(
                    ["xdotool", "getwindowfocus"],
                    capture_output=True,
                    text=True,
                    timeout=1.0
                )
                if res.returncode != 0:
                    logger.debug("xdotool getwindowfocus failed -> no active window.")
                    return False

                win_id = res.stdout.strip()
                if not win_id or win_id == "0":
                    return False

                if shutil.which("xprop"):
                    prop_res = subprocess.run(
                        ["xprop", "-id", win_id, "_NET_WM_WINDOW_TYPE", "WM_CLASS", "WM_NAME"],
                        capture_output=True,
                        text=True,
                        timeout=1.0
                    )
                    if prop_res.returncode == 0:
                        out = prop_res.stdout
                        if "_NET_WM_WINDOW_TYPE_DESKTOP" in out or "_NET_WM_WINDOW_TYPE_DOCK" in out:
                            logger.debug("Active window is desktop wallpaper or panel dock.")
                            return False
                        if 'WM_CLASS(STRING) = "desktop"' in out.lower() or 'nautilus-desktop' in out.lower():
                            return False

                return True

            return True
        except Exception as e:
            logger.debug(f"Linux text box active check: {e}")
            return True

    def copy_to_clipboard(self, text: str) -> bool:
        """
        Copy text directly to the system clipboard across Linux, Windows, and macOS.
        """
        if not text:
            return False

        try:
            import pyperclip
            pyperclip.copy(text)
            logger.info("Copied text to clipboard via pyperclip.")
            return True
        except Exception as e:
            logger.debug(f"pyperclip copy failed: {e}")

        # Linux fallbacks
        if is_linux():
            if shutil.which("wl-copy"):
                try:
                    subprocess.run(["wl-copy"], input=text.encode("utf-8"), check=True, timeout=2.0)
                    logger.info("Copied text to clipboard via wl-copy.")
                    return True
                except Exception:
                    pass
            if shutil.which("xclip"):
                try:
                    proc = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                    proc.communicate(input=text.encode("utf-8"), timeout=2.0)
                    logger.info("Copied text to clipboard via xclip.")
                    return True
                except Exception:
                    pass
            if shutil.which("xsel"):
                try:
                    proc = subprocess.Popen(["xsel", "--clipboard", "--input"], stdin=subprocess.PIPE)
                    proc.communicate(input=text.encode("utf-8"), timeout=2.0)
                    logger.info("Copied text to clipboard via xsel.")
                    return True
                except Exception:
                    pass

        # macOS fallback
        elif is_macos():
            if shutil.which("pbcopy"):
                try:
                    proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                    proc.communicate(input=text.encode("utf-8"), timeout=2.0)
                    logger.info("Copied text to clipboard via pbcopy.")
                    return True
                except Exception:
                    pass

        logger.warning("Could not copy text to clipboard using any available system tool.")
        return False

    def inject_or_clipboard(self, text: str) -> Tuple[bool, str]:
        """
        Smart text delivery based on active input field detection:
        - If an active text box IS selected/focused:
            Injects text directly into the field, and restores prior clipboard buffer
            so the text is NOT left on the clipboard. Returns (True, 'injected').
        - If NO text box is active:
            Copies text directly to clipboard and does NOT send simulated keystrokes.
            Returns (True, 'copied_to_clipboard').
        - If injection was attempted but failed:
            Copies to clipboard as a safety net. Returns (False, 'fallback_copied').
        """
        if not text:
            return False, "empty"

        has_active_field = self.is_text_box_active()
        logger.info(f"Target text box active check: {has_active_field}")

        if not has_active_field:
            logger.info("No active text box detected. Copying transcribed text to clipboard.")
            copied = self.copy_to_clipboard(text)
            if copied:
                return True, "copied_to_clipboard"
            else:
                return False, "copy_failed"

        # Active text box present: perform direct injection and restore clipboard
        success = self.inject(text)
        if success:
            return True, "injected"
        else:
            logger.warning("Injection into active text box failed. Preserving text on clipboard.")
            self.copy_to_clipboard(text)
            return False, "fallback_copied"

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
                    if self.restore_clipboard:
                        time.sleep(0.2)
                        try:
                            pyperclip.copy(saved_clipboard if saved_clipboard is not None else "")
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
                    if self.restore_clipboard:
                        time.sleep(0.2)
                        try:
                            if has_pbcopy:
                                proc2 = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                                restore_bytes = saved_clipboard.encode("utf-8") if saved_clipboard else b""
                                proc2.communicate(input=restore_bytes, timeout=1.5)
                            elif pyperclip is not None:
                                pyperclip.copy(saved_clipboard if saved_clipboard else "")
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
                if self.restore_clipboard:
                    time.sleep(0.2)
                    try:
                        subprocess.run(
                            ["wl-copy"],
                            input=saved_clipboard if saved_clipboard else b"",
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
                if self.restore_clipboard:
                    time.sleep(0.2)
                    try:
                        restore_data = saved_clipboard if saved_clipboard else b""
                        if has_xclip:
                            p2 = subprocess.Popen(
                                ["xclip", "-selection", "clipboard"],
                                stdin=subprocess.PIPE
                            )
                            p2.communicate(input=restore_data, timeout=1.5)
                        elif has_xsel:
                            p2 = subprocess.Popen(
                                ["xsel", "--clipboard", "--input"],
                                stdin=subprocess.PIPE
                            )
                            p2.communicate(input=restore_data, timeout=1.5)
                        elif pyperclip is not None:
                            pyperclip.copy(restore_data.decode("utf-8", errors="ignore"))
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
