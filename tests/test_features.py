"""
Unit and Integration Tests for FreeFlow Features:
- Audio Input Device (Microphone) Selection
- Automated GitHub Release Auto-Updater
- Startup Minimize on Boot Behavior & Autostart
"""

import os
import unittest
from pathlib import Path

from core.config import AppConfig
from core.recorder import list_input_devices, resolve_device_index, AudioRecorder
from core.updater import parse_version, is_newer_version, find_matching_asset, detect_install_type
from core.autostart import _get_exec_command, set_autostart
from core.version import APP_VERSION


class TestVersionAndUpdater(unittest.TestCase):
    """Test updater parsing, version comparison, and asset matching."""

    def test_parse_version(self):
        self.assertEqual(parse_version("v1.2.0"), (1, 2, 0))
        self.assertEqual(parse_version("1.2.0"), (1, 2, 0))
        self.assertEqual(parse_version("v2.0.0-beta"), (2, 0, 0))
        self.assertEqual(parse_version(""), (0, 0, 0))

    def test_is_newer_version(self):
        self.assertTrue(is_newer_version("v1.2.1", "1.2.0"))
        self.assertTrue(is_newer_version("v1.2.0", "1.1.0"))
        self.assertTrue(is_newer_version("2.0.0", "1.9.9"))
        self.assertFalse(is_newer_version("v1.1.0", "1.1.0"))
        self.assertFalse(is_newer_version("v1.0.5", "1.1.0"))
        self.assertFalse(is_newer_version("0.9.0", "1.0.0"))

    def test_find_matching_asset(self):
        sample_assets = [
            {"name": "FreeFlow-1.2.0-x86_64.AppImage", "browser_download_url": "https://example.com/appimage"},
            {"name": "FreeFlow-Setup-Windows.exe", "browser_download_url": "https://example.com/setup.exe"},
            {"name": "FreeFlow-windows-x64.zip", "browser_download_url": "https://example.com/win.zip"},
            {"name": "FreeFlow-1.2.0-macOS.dmg", "browser_download_url": "https://example.com/mac.dmg"},
            {"name": "freeflow_1.2.0_amd64.deb", "browser_download_url": "https://example.com/deb"},
        ]

        appimage = find_matching_asset(sample_assets, "appimage")
        self.assertIsNotNone(appimage)
        self.assertTrue(appimage["name"].endswith(".AppImage"))

        win = find_matching_asset(sample_assets, "windows_exe")
        self.assertIsNotNone(win)
        self.assertEqual(win["name"], "FreeFlow-Setup-Windows.exe")

        mac = find_matching_asset(sample_assets, "macos_app")
        self.assertIsNotNone(mac)
        self.assertTrue(mac["name"].endswith(".dmg"))

        deb = find_matching_asset(sample_assets, "deb")
        self.assertIsNotNone(deb)
        self.assertTrue(deb["name"].endswith(".deb"))

    def test_detect_install_type(self):
        itype = detect_install_type()
        # In this repository clone, it should detect 'git'
        self.assertIn(itype, ["git", "source", "appimage", "deb", "windows_exe", "macos_app"])


class TestAudioInputDevice(unittest.TestCase):
    """Test microphone device enumeration and selection."""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        import sys
        if QApplication.instance() is None:
            cls._qapp = QApplication(sys.argv)

    def test_list_devices(self):
        devices = list_input_devices()
        self.assertIsInstance(devices, list)
        for dev in devices:
            self.assertIn("id", dev)
            self.assertIn("name", dev)
            self.assertIn("channels", dev)
            self.assertGreater(dev["channels"], 0)

    def test_resolve_device(self):
        self.assertIsNone(resolve_device_index(None))
        self.assertIsNone(resolve_device_index("default"))
        self.assertIsNone(resolve_device_index(""))
        # Non-existent device name should safely resolve to None instead of raising
        self.assertIsNone(resolve_device_index("NonExistentMicrophone12345"))

    def test_recorder_set_device(self):
        recorder = AudioRecorder(sample_rate=16000, channels=1, device=None)
        self.assertIsNone(recorder.device)
        recorder.set_device("My Test Mic")
        self.assertEqual(recorder.device, "My Test Mic")
        recorder.set_device(None)
        self.assertIsNone(recorder.device)

    def test_no_scroll_combo_box(self):
        from ui.main_window import NoScrollComboBox
        combo = NoScrollComboBox()
        combo.addItem("Device 1")
        combo.addItem("Device 2")
        self.assertEqual(combo.currentIndex(), 0)

        # In headless test, view is not visible, so wheel event must be ignored
        class DummyEvent:
            def __init__(self):
                self.ignored = False
            def ignore(self):
                self.ignored = True

        ev = DummyEvent()
        combo.wheelEvent(ev)
        self.assertTrue(ev.ignored)
        self.assertEqual(combo.currentIndex(), 0)  # Selection did NOT change!


class TestConfigPersistence(unittest.TestCase):
    """Test configuration fields for audio device and updates."""

    def test_config_defaults(self):
        cfg = AppConfig()
        self.assertIsNone(cfg.audio_device)
        self.assertTrue(cfg.check_updates_on_startup)
        self.assertIn(cfg.auto_update_mode, ["auto", "ask"])
        self.assertFalse(cfg.start_minimized)


class TestStartupMinimizeLogic(unittest.TestCase):
    """Test startup visibility and autostart minimize bug resolution."""

    def compute_should_show(self, start_minimized_arg, is_boot_startup, config_start_minimized):
        if start_minimized_arg:
            return False
        elif is_boot_startup:
            return not config_start_minimized
        else:
            return True

    def test_minimize_on_boot_checked(self):
        # When user checks minimize on startup, on boot it should NOT show popup
        should_show = self.compute_should_show(
            start_minimized_arg=False,
            is_boot_startup=True,
            config_start_minimized=True
        )
        self.assertFalse(should_show)

    def test_minimize_on_boot_unchecked(self):
        # When user unchecks minimize on startup, on boot it SHOULD show
        should_show = self.compute_should_show(
            start_minimized_arg=False,
            is_boot_startup=True,
            config_start_minimized=False
        )
        self.assertTrue(should_show)

    def test_manual_launch_by_user(self):
        # When user clicks app manually (not on boot), it SHOULD show even if config_start_minimized is True
        should_show = self.compute_should_show(
            start_minimized_arg=False,
            is_boot_startup=False,
            config_start_minimized=True
        )
        self.assertTrue(should_show)

    def test_cli_explicit_minimized(self):
        # When CLI flag --minimized is passed, it should NOT show
        should_show = self.compute_should_show(
            start_minimized_arg=True,
            is_boot_startup=False,
            config_start_minimized=False
        )
        self.assertFalse(should_show)

    def test_autostart_exec_command(self):
        cmd_min = _get_exec_command(start_minimized=True)
        self.assertIn("--autostart", cmd_min)
        self.assertIn("--minimized", cmd_min)

        cmd_vis = _get_exec_command(start_minimized=False)
        self.assertIn("--autostart", cmd_vis)
        self.assertNotIn("--minimized", cmd_vis)


class TestTroubleshootingAndErrorDiagnostics(unittest.TestCase):
    """Test error categorization, secret redaction, and GitHub issue generation."""

    def test_sanitize_error_text_redacts_api_key(self):
        from core.troubleshooting import sanitize_error_text
        secret_msg = "Error 401: Invalid API Key with key gsk_AbCdEf1234567890XyZ provided."
        sanitized = sanitize_error_text(secret_msg)
        self.assertNotIn("gsk_AbCdEf1234567890XyZ", sanitized)
        self.assertIn("gsk_<REDACTED_API_KEY>", sanitized)

    def test_diagnose_invalid_api_key(self):
        from core.troubleshooting import diagnose_error
        err = "AuthenticationError: Error code: 401 - {'error': {'message': 'Invalid API Key', 'code': 'invalid_api_key'}}"
        diag = diagnose_error(err)
        self.assertEqual(diag.category, "INVALID_API_KEY")
        self.assertIn("Invalid or Missing Groq API Key", diag.title)
        self.assertIn("console.groq.com/keys", diag.steps[2])
        self.assertIn("https://github.com/BheeshamKS/FreeFlow/issues/new", diag.github_issue_url)

    def test_diagnose_network_firewall(self):
        from core.troubleshooting import diagnose_error
        err = "groq.APIConnectionError: Connection error. WinError 10060 - A connection attempt failed because the connected party did not properly respond."
        diag = diagnose_error(err)
        self.assertEqual(diag.category, "NETWORK_FIREWALL")
        self.assertIn("Firewall", diag.title)
        self.assertTrue(any("Windows Defender" in s for s in diag.steps))

    def test_diagnose_rate_limit(self):
        from core.troubleshooting import diagnose_error
        err = "RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached'}}"
        diag = diagnose_error(err)
        self.assertEqual(diag.category, "RATE_LIMIT")
        self.assertIn("Rate Limit", diag.title)

    def test_diagnose_audio_empty(self):
        from core.troubleshooting import diagnose_error
        err = "ValueError: Recorded audio file is empty."
        diag = diagnose_error(err)
        self.assertEqual(diag.category, "AUDIO_EMPTY")
        self.assertIn("Microphone Silence", diag.title)

    def test_diagnose_model_unavailable(self):
        from core.troubleshooting import diagnose_error
        err = "Error code: 404 - {'error': {'message': 'The model whisper-legacy does not exist or has been decommissioned'}}"
        diag = diagnose_error(err)
        self.assertEqual(diag.category, "MODEL_ERROR")

    def test_github_issue_url_format(self):
        from core.troubleshooting import generate_github_issue_url
        url = generate_github_issue_url("Windows SSL Timeout", "NETWORK_FIREWALL", "Connection refused at api.groq.com:443")
        self.assertTrue(url.startswith("https://github.com/BheeshamKS/FreeFlow/issues/new?"))
        self.assertIn("Windows+SSL+Timeout", url)
        self.assertIn("FreeFlow+Version", url)


class TestActiveTextBoxAndSmartClipboard(unittest.TestCase):
    """Test active input box detection and smart clipboard fallback."""

    def test_inject_or_clipboard_when_no_text_box_active(self):
        from core.injector import TextInjector
        injector = TextInjector()
        # Mock is_text_box_active to return False (no text box active)
        injector.is_text_box_active = lambda: False

        copied_payload = []
        injector.copy_to_clipboard = lambda t: (copied_payload.append(t), True)[1]

        success, action = injector.inject_or_clipboard("Test transcription text")
        self.assertTrue(success)
        self.assertEqual(action, "copied_to_clipboard")
        self.assertEqual(copied_payload, ["Test transcription text"])

    def test_inject_or_clipboard_when_text_box_is_active(self):
        from core.injector import TextInjector
        injector = TextInjector()
        # Mock is_text_box_active to return True (text box IS active)
        injector.is_text_box_active = lambda: True

        injected_calls = []
        injector.inject = lambda t: (injected_calls.append(t), True)[1]

        success, action = injector.inject_or_clipboard("Dictated into active box")
        self.assertTrue(success)
        self.assertEqual(action, "injected")
        self.assertEqual(injected_calls, ["Dictated into active box"])

    def test_copy_to_clipboard_empty_returns_false(self):
        from core.injector import TextInjector
        injector = TextInjector()
        self.assertFalse(injector.copy_to_clipboard(""))

    def test_linux_active_text_box_desktop_detection(self):
        from unittest.mock import patch
        import subprocess
        from core.injector import TextInjector

        injector = TextInjector()

        # Simulate xdotool returning a window ID, but xprop says it's DESKTOP
        def mock_subprocess_run(cmd, *args, **kwargs):
            if cmd[0] == "xdotool":
                return subprocess.CompletedProcess(cmd, 0, stdout="123456\n", stderr="")
            elif cmd[0] == "xprop":
                return subprocess.CompletedProcess(cmd, 0, stdout="_NET_WM_WINDOW_TYPE(ATOM) = _NET_WM_WINDOW_TYPE_DESKTOP\n", stderr="")
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

        with patch("shutil.which", return_value="/usr/bin/mock"), \
             patch("subprocess.run", side_effect=mock_subprocess_run):
            self.assertFalse(injector._is_text_box_active_linux())

    def test_linux_active_text_box_app_window_detection(self):
        from unittest.mock import patch
        import subprocess
        from core.injector import TextInjector

        injector = TextInjector()

        # Simulate normal application window (e.g. gedit or browser)
        def mock_subprocess_run(cmd, *args, **kwargs):
            if cmd[0] == "xdotool":
                return subprocess.CompletedProcess(cmd, 0, stdout="987654\n", stderr="")
            elif cmd[0] == "xprop":
                return subprocess.CompletedProcess(cmd, 0, stdout="_NET_WM_WINDOW_TYPE_NORMAL\nWM_CLASS = \"gedit\"\n", stderr="")
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

        with patch("shutil.which", return_value="/usr/bin/mock"), \
             patch("subprocess.run", side_effect=mock_subprocess_run):
            self.assertTrue(injector._is_text_box_active_linux())


class TestHUDEnhancements(unittest.TestCase):
    """Test HUD error state and solutions signal."""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        import sys
        if QApplication.instance() is None:
            cls._qapp = QApplication(sys.argv)

    def test_hud_error_state_and_solutions_request(self):
        from ui.hud import RecordingHUD
        from PyQt6.QtCore import Qt, QPointF
        from PyQt6.QtGui import QMouseEvent

        hud = RecordingHUD()
        hud.set_error("Invalid Groq API Key", error_details="401 Unauthorized Key")
        self.assertEqual(hud.state, "error")
        self.assertEqual(hud.status_message, "Invalid Groq API Key")
        self.assertEqual(hud._last_error_details, "401 Unauthorized Key")

        # Emitted signal check on mouse click
        received_errors = []
        hud.solutions_requested.connect(lambda err: received_errors.append(err))

        click_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(20.0, 20.0),
            QPointF(20.0, 20.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        hud.mousePressEvent(click_ev)
        self.assertEqual(received_errors, ["401 Unauthorized Key"])
        hud.hide_hud()

    def test_troubleshooting_dialog_presentation(self):
        from core.troubleshooting import diagnose_error
        from ui.troubleshooting_dialog import TroubleshootingDialog

        diag = diagnose_error("AuthenticationError: 401 Invalid API Key")
        dlg = TroubleshootingDialog(parent=None, diagnostic=diag)
        self.assertIn("Invalid or Missing Groq API Key", dlg.windowTitle())
        self.assertEqual(dlg.diagnostic.category, "INVALID_API_KEY")

        # Test copy diagnostic details
        dlg._copy_diagnostic_details()
        self.assertFalse(dlg.lbl_test_result.isHidden())
        self.assertIn("copied to clipboard", dlg.lbl_test_result.text())
        dlg.close()


if __name__ == "__main__":
    unittest.main()
