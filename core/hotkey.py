"""
FreeFlow Global Hotkey Listener
Provides background system-wide hotkey monitoring across Wayland and X11.
Uses evdev for kernel-level input monitoring with pynput fallback.
Supports both Hold-to-Talk and Toggle recording modes.
"""

import asyncio
import logging
import threading
from typing import List, Optional, Set

try:
    import evdev
    from evdev import ecodes
except ImportError:
    evdev = None
    ecodes = None

try:
    from pynput import keyboard as pynput_keyboard
except ImportError:
    pynput_keyboard = None

try:
    from PyQt6.QtCore import QThread, pyqtSignal
except ImportError:
    class QThread:
        pass
    def pyqtSignal(*args):
        return None

from core.config import AppConfig

logger = logging.getLogger("FreeFlow.Hotkey")


def resolve_modifier_codes(mod_str: str) -> Set[int]:
    """Map user-friendly modifier string to set of evdev key codes."""
    if not ecodes:
        return set()
    mod = mod_str.upper()
    if "ALT" in mod:
        return {ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT}
    elif "CTRL" in mod:
        return {ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL}
    elif "SHIFT" in mod:
        return {ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT}
    elif "META" in mod or "SUPER" in mod:
        return {getattr(ecodes, "KEY_LEFTMETA", 125), getattr(ecodes, "KEY_RIGHTMETA", 126)}
    return set()


def resolve_key_code(key_str: str) -> Optional[int]:
    """Resolve key string (e.g. 'KEY_R', 'KEY_SPACE') to evdev code."""
    if not ecodes:
        return None
    code_name = key_str.upper()
    if not code_name.startswith("KEY_"):
        code_name = f"KEY_{code_name}"
    return getattr(ecodes, code_name, None)


class HotkeyListener(QThread):
    """
    Background worker thread monitoring global input events for trigger combinations.
    Emits start_recording and stop_recording signals based on toggle or hold logic.
    """

    start_recording = pyqtSignal() if QThread is not None else None
    stop_recording = pyqtSignal() if QThread is not None else None
    error_occurred = pyqtSignal(str) if QThread is not None else None

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self._running = False
        self._is_active_recording = False
        
        # State tracking
        self._modifier_held = False
        self._key_held = False
        
        # evdev async loop handle
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._pynput_listener: Optional[pynput_keyboard.Listener] = None

    def update_config(self, new_config: AppConfig):
        """Update hotkey configuration."""
        self.config = new_config
        logger.info(f"Updated hotkey config: {self.config.get_display_hotkey()} (Mode: {self.config.hotkey_mode})")

    def run(self):
        """Thread entrypoint."""
        self._running = True
        logger.info(f"Starting Hotkey listener for '{self.config.get_display_hotkey()}' (mode={self.config.hotkey_mode})")

        # Try evdev first (Wayland & X11 universal)
        evdev_success = False
        if evdev is not None:
            try:
                evdev_success = self._run_evdev()
            except PermissionError:
                logger.warning("Permission denied accessing /dev/input/*. Ensure user is in 'input' group.")
            except Exception as e:
                logger.warning(f"evdev listener failed to initialize: {e}")

        # Fallback to pynput if evdev failed
        if not evdev_success and self._running:
            logger.info("Attempting pynput fallback listener...")
            if pynput_keyboard is not None:
                self._run_pynput()
            else:
                err = "No functional keyboard listener could be started. Please check /dev/input permissions."
                logger.error(err)
                if self.error_occurred:
                    self.error_occurred.emit(err)

    def _find_keyboards(self) -> List["evdev.InputDevice"]:
        """Discover all connected hardware keyboards via evdev."""
        keyboards = []
        try:
            device_paths = evdev.list_devices()
        except Exception as e:
            logger.debug(f"list_devices error: {e}")
            return []

        for path in device_paths:
            try:
                dev = evdev.InputDevice(path)
                caps = dev.capabilities()
                if ecodes.EV_KEY in caps:
                    keys = caps[ecodes.EV_KEY]
                    # Check if device has standard letter keys like KEY_A or KEY_SPACE
                    if ecodes.KEY_A in keys and ecodes.KEY_SPACE in keys:
                        keyboards.append(dev)
                        logger.debug(f"Found input keyboard: {dev.name} ({dev.path})")
            except Exception:
                continue
        return keyboards

    def _run_evdev(self) -> bool:
        """Run asynchronous evdev event loop across all keyboards."""
        keyboards = self._find_keyboards()
        if not keyboards:
            logger.debug("No evdev keyboard devices found accessible to this user.")
            return False

        logger.info(f"Listening on {len(keyboards)} keyboard device(s) via evdev.")
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def listen_all():
            tasks = [self._handle_device(dev) for dev in keyboards]
            await asyncio.gather(*tasks, return_exceptions=True)

        try:
            self._loop.run_until_complete(listen_all())
            return True
        except asyncio.CancelledError:
            return True
        finally:
            if self._loop and not self._loop.is_closed():
                self._loop.close()

    async def _handle_device(self, dev: "evdev.InputDevice"):
        """Process input events from an individual keyboard."""
        mod_codes = resolve_modifier_codes(self.config.hotkey_modifier)
        trigger_code = resolve_key_code(self.config.hotkey_key)

        try:
            async for event in dev.async_read_loop():
                if not self._running:
                    break

                if event.type != ecodes.EV_KEY:
                    continue

                # event.value: 0 = up, 1 = down, 2 = autorepeat
                if event.value == 2:
                    continue  # Ignore autorepeat

                is_press = (event.value == 1)

                # Re-evaluate codes in case config changed
                mod_codes = resolve_modifier_codes(self.config.hotkey_modifier)
                trigger_code = resolve_key_code(self.config.hotkey_key)

                if mod_codes and event.code in mod_codes:
                    self._modifier_held = is_press

                elif event.code == trigger_code:
                    self._key_held = is_press
                    self._on_trigger_event(is_press)

        except (OSError, asyncio.CancelledError):
            pass
        finally:
            dev.close()

    def _on_trigger_event(self, key_down: bool):
        """Evaluate state machine transitions for Toggle and Hold modes."""
        has_mod = bool(self.config.hotkey_modifier)
        mod_ok = (not has_mod) or self._modifier_held

        if self.config.hotkey_mode == "toggle":
            # Toggle Mode: Triggered on fresh press while modifier is satisfied
            if key_down and mod_ok:
                if not self._is_active_recording:
                    self._is_active_recording = True
                    logger.info("Hotkey TOGGLE -> START Recording")
                    if self.start_recording:
                        self.start_recording.emit()
                else:
                    self._is_active_recording = False
                    logger.info("Hotkey TOGGLE -> STOP Recording")
                    if self.stop_recording:
                        self.stop_recording.emit()

        elif self.config.hotkey_mode == "hold":
            # Hold-to-Talk Mode
            if key_down and mod_ok:
                if not self._is_active_recording:
                    self._is_active_recording = True
                    logger.info("Hotkey HOLD -> START Recording")
                    if self.start_recording:
                        self.start_recording.emit()
            elif not key_down:
                if self._is_active_recording:
                    self._is_active_recording = False
                    logger.info("Hotkey HOLD -> STOP Recording (Key Released)")
                    if self.stop_recording:
                        self.stop_recording.emit()

    def _run_pynput(self):
        """Fallback pynput global keyboard listener (for X11 / standard desktop)."""
        current_keys = set()

        def on_press(key):
            if not self._running:
                return False
            current_keys.add(key)
            self._check_pynput_combo(current_keys, is_press=True, key=key)

        def on_release(key):
            if not self._running:
                return False
            current_keys.discard(key)
            self._check_pynput_combo(current_keys, is_press=False, key=key)

        with pynput_keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            self._pynput_listener = listener
            listener.join()

    def _check_pynput_combo(self, current_keys, is_press: bool, key):
        """Evaluate pynput key combinations."""
        mod = self.config.hotkey_modifier.upper()
        target_key_char = self.config.hotkey_key.upper().replace("KEY_", "").lower()

        # Check modifier
        mod_held = True
        if "ALT" in mod:
            mod_held = any(k in current_keys for k in [pynput_keyboard.Key.alt, pynput_keyboard.Key.alt_l, pynput_keyboard.Key.alt_r])
        elif "CTRL" in mod:
            mod_held = any(k in current_keys for k in [pynput_keyboard.Key.ctrl, pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r])
        elif "SHIFT" in mod:
            mod_held = any(k in current_keys for k in [pynput_keyboard.Key.shift, pynput_keyboard.Key.shift_l, pynput_keyboard.Key.shift_r])

        # Check target key
        is_target = False
        try:
            if hasattr(key, "char") and key.char and key.char.lower() == target_key_char:
                is_target = True
            elif target_key_char == "space" and key == pynput_keyboard.Key.space:
                is_target = True
        except Exception:
            pass

        if is_target:
            self._modifier_held = mod_held
            self._on_trigger_event(is_press)

    def trigger_toggle_manual(self):
        """Allows UI (e.g. tray menu or button) to manually trigger recording toggle."""
        if not self._is_active_recording:
            self._is_active_recording = True
            if self.start_recording:
                self.start_recording.emit()
        else:
            self._is_active_recording = False
            if self.stop_recording:
                self.stop_recording.emit()

    def stop(self):
        """Safely terminate listener thread and loops."""
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._pynput_listener:
            try:
                self._pynput_listener.stop()
            except Exception:
                pass
        self.quit()
