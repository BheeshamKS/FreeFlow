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

    def test_diagnose_empty_returns_common_guide_not_error(self):
        from core.troubleshooting import diagnose_error
        diag = diagnose_error("")
        self.assertFalse(diag.is_error)
        self.assertNotIn("Transcription Error", diag.title)
        self.assertIn("Groq API Key Setup", diag.title)

        diag_check = diagnose_error("Normal Diagnostics Check")
        self.assertFalse(diag_check.is_error)
        self.assertNotIn("Transcription Error", diag_check.title)

    def test_get_common_diagnostic_topics(self):
        from core.troubleshooting import get_common_diagnostic, COMMON_TOPICS
        self.assertIn("api_key", COMMON_TOPICS)
        self.assertIn("connection", COMMON_TOPICS)
        self.assertIn("microphone", COMMON_TOPICS)
        self.assertIn("injection", COMMON_TOPICS)
        self.assertIn("rate_limit", COMMON_TOPICS)

        conn_diag = get_common_diagnostic("connection")
        self.assertFalse(conn_diag.is_error)
        self.assertIn("Windows Firewall", conn_diag.title)


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

        # Test switching to connection topic
        dlg._select_topic("connection")
        self.assertIn("Windows Firewall", dlg.lbl_title.text())
        self.assertFalse(dlg.diagnostic.is_error)

        # Test error simulation signal
        simulated = []
        dlg.simulate_error_requested.connect(lambda msg: simulated.append(msg))
        dlg.simulate_error_requested.emit("Simulated Test Error")
        self.assertEqual(simulated, ["Simulated Test Error"])
        dlg.close()


class TestAudioRecoveryAndRetry(unittest.TestCase):
    """Test audio preservation, recovery caching, HUD retry button, and tray click behavior."""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        import sys
        if QApplication.instance() is None:
            cls._qapp = QApplication(sys.argv)

    def test_recovery_audio_path(self):
        from core.platform import get_recovery_audio_path
        path = get_recovery_audio_path()
        self.assertIsNotNone(path)
        self.assertTrue(str(path).endswith(".wav"))
        self.assertTrue(path.parent.exists())

    def test_hud_retry_button_click(self):
        from ui.hud import RecordingHUD
        from PyQt6.QtCore import Qt, QPointF
        from PyQt6.QtGui import QMouseEvent

        hud = RecordingHUD()
        hud.set_error("Connection Error", error_details="Timeout", recovery_available=True)
        self.assertTrue(hud.recovery_available)

        retry_signals = []
        solutions_signals = []
        hud.retry_requested.connect(lambda: retry_signals.append(True))
        hud.solutions_requested.connect(lambda msg: solutions_signals.append(msg))

        # Click inside the retry button (x = width - 200 + 10, y = 20)
        click_retry = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(float(hud.width() - 170), 22.0),
            QPointF(float(hud.width() - 170), 22.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        hud.mousePressEvent(click_retry)
        self.assertEqual(retry_signals, [True])
        self.assertEqual(solutions_signals, [])

        # Click inside the solutions button (x = width - 30, y = 20)
        click_sol = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(float(hud.width() - 30), 22.0),
            QPointF(float(hud.width() - 30), 22.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        hud.mousePressEvent(click_sol)
        self.assertEqual(solutions_signals, ["Timeout"])
        hud.hide_hud()

    def test_tray_double_click_and_trigger(self):
        from ui.tray import SystemTrayController
        from PyQt6.QtWidgets import QSystemTrayIcon

        cfg = AppConfig()
        tray = SystemTrayController(cfg)

        hub_signals = []
        retry_signals = []
        tray.open_hub_requested.connect(lambda: hub_signals.append("hub"))
        tray.retry_transcription_requested.connect(lambda: retry_signals.append("retry"))

        # Test DoubleClick activates Hub
        tray._on_tray_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
        self.assertEqual(hub_signals, ["hub"])

        # Test Single Click / Trigger activates Hub
        tray._on_tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
        self.assertEqual(hub_signals, ["hub", "hub"])

        # Test recovery audio tray action
        tray.set_recovery_audio_available(True, duration=125.0)
        self.assertTrue(tray.retry_action.isVisible())
        self.assertIn("2m 05s", tray.retry_action.text())

        tray.retry_action.trigger()
        self.assertEqual(retry_signals, ["retry"])

        tray.set_recovery_audio_available(False)
        self.assertFalse(tray.retry_action.isVisible())

    def test_main_window_recovery_banner(self):
        from ui.main_window import MainWindow
        from core.history import HistoryManager

        cfg = AppConfig()
        hist = HistoryManager()
        win = MainWindow(cfg, hist)

        retry_signals = []
        win.retry_transcription_requested.connect(lambda: retry_signals.append("retry"))

        # Banner should be hidden initially
        self.assertTrue(win.btn_retry_recovery.isHidden())

        # Set recovery available
        win.set_recovery_audio_available(True, duration=90.0)
        self.assertFalse(win.btn_retry_recovery.isHidden())
        self.assertIn("1m 30s", win.btn_retry_recovery.text())

        # Trigger button click
        win.btn_retry_recovery.click()
        self.assertEqual(retry_signals, ["retry"])

        # Clear recovery
        win.set_recovery_audio_available(False)
        self.assertTrue(win.btn_retry_recovery.isHidden())
        win.close()

    def test_troubleshooting_dialog_recovery_card(self):
        import tempfile
        from ui.troubleshooting_dialog import TroubleshootingDialog
        from core.troubleshooting import diagnose_error

        # Create temporary dummy WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFFdummydataWAVEfmt ")
            dummy_path = f.name

        try:
            diag = diagnose_error("APIConnectionError: network down")
            dlg = TroubleshootingDialog(
                parent=None,
                diagnostic=diag,
                recovery_audio_path=dummy_path,
                recovery_audio_duration=75.0
            )

            # Check that recovery card exists
            self.assertTrue(hasattr(dlg, "recovery_card"))
            self.assertTrue(hasattr(dlg, "btn_retry_transcribe"))

            retry_signals = []
            dlg.retry_transcription_requested.connect(lambda: retry_signals.append("retry"))
            dlg.btn_retry_transcribe.click()
            self.assertEqual(retry_signals, ["retry"])
            dlg.close()
        finally:
            if os.path.exists(dummy_path):
                os.unlink(dummy_path)


class TestSingleInstanceAndLauncher(unittest.TestCase):
    """Test SingleInstanceGuard IPC, send_activation method, and desktop launcher integration."""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        import sys
        if QApplication.instance() is None:
            cls._qapp = QApplication(sys.argv)

    def test_single_instance_guard_api(self):
        from core.single_instance import SingleInstanceGuard
        guard = SingleInstanceGuard("test_ipc_guard")
        self.assertTrue(hasattr(guard, "acquire"))
        self.assertTrue(hasattr(guard, "send_activation"))
        self.assertTrue(hasattr(guard, "cleanup"))
        guard.cleanup()

    def test_desktop_launcher_creation(self):
        import tempfile
        from core.autostart import ensure_desktop_launcher
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            launcher_path = ensure_desktop_launcher(target_dir=Path(tmp_dir))
            self.assertIsNotNone(launcher_path)
            self.assertTrue(launcher_path.exists())
            content = launcher_path.read_text(encoding="utf-8")
            self.assertIn("Name=FreeFlow", content)
            self.assertIn("Exec=", content)
            # Standard launcher must NOT contain autostart/minimized flags so it always presents the app
            self.assertNotIn("--autostart", content)
            self.assertNotIn("--minimized", content)

    def test_onboarding_wizard_import_and_instantiation(self):
        from ui.onboarding import OnboardingWizard
        cfg = AppConfig(groq_api_key="gsk_test_key_123")
        wiz = OnboardingWizard(cfg)
        self.assertIsNotNone(wiz)
        self.assertEqual(wiz.current_step, 0)


class TestThemeAndFreeFlowPocketIntegration(unittest.TestCase):
    """Test unified design tokens, assets standardization, and FreeFlow Pocket documentation."""

    def test_design_tokens_parity(self):
        from core.theme import (
            DARK_BACKGROUND, DARK_SURFACE, DARK_CARD, DARK_CARD_BORDER,
            PRIMARY_BLUE, ACCENT_GREEN, ACCENT_VIOLET, get_application_stylesheet
        )
        self.assertEqual(DARK_BACKGROUND, "#000000")
        self.assertEqual(DARK_SURFACE, "#0E0E12")
        self.assertEqual(DARK_CARD, "#18181C")
        self.assertEqual(DARK_CARD_BORDER, "#26262E")
        self.assertEqual(PRIMARY_BLUE, "#5AB4FF")
        self.assertEqual(ACCENT_GREEN, "#00E676")
        self.assertEqual(ACCENT_VIOLET, "#D500F9")

        stylesheet = get_application_stylesheet()
        self.assertIn("#000000", stylesheet)
        self.assertIn("#5AB4FF", stylesheet)
        self.assertIn("#18181C", stylesheet)

    def test_assets_standardization(self):
        root = Path(__file__).resolve().parent.parent
        assets_dir = root / "assets"
        self.assertTrue((assets_dir / "logo.svg").exists(), "assets/logo.svg must exist")
        self.assertTrue((assets_dir / "icon.png").exists(), "assets/icon.png must exist")
        self.assertTrue((assets_dir / "icon.ico").exists(), "assets/icon.ico must exist")

        # Unused legacy logos must be purged
        self.assertFalse((assets_dir / "Logo.svg").exists(), "assets/Logo.svg should be purged")
        self.assertFalse((assets_dir / "Logo.vectorcraft").exists(), "assets/Logo.vectorcraft should be purged")

        # Recording microphone assets must be preserved
        self.assertTrue((assets_dir / "icon_recording.png").exists())
        self.assertTrue((assets_dir / "icon_processing.png").exists())

    def test_readme_freeflow_pocket_links(self):
        root = Path(__file__).resolve().parent.parent
        readme_path = root / "README.md"
        self.assertTrue(readme_path.exists())
        content = readme_path.read_text(encoding="utf-8")

        self.assertIn("https://github.com/BheeshamKS/FreeFlow-Pocket", content)
        self.assertIn("https://github.com/BheeshamKS/FreeFlow-Pocket/releases/latest", content)
        # Verify no direct APK download link is given
        self.assertNotIn(".apk", content)


if __name__ == "__main__":
    unittest.main()
