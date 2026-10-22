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


if __name__ == "__main__":
    unittest.main()
