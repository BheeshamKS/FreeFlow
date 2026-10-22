"""
FreeFlow Automated GitHub Release Auto-Updater
Handles checking GitHub Releases for new updates, downloading assets in the background,
and performing seamless, zero-friction in-place self-updates across Linux (AppImage & Git),
Windows (Setup EXE), and macOS.
"""

import json
import logging
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from PyQt6.QtCore import QObject, QThread, pyqtSignal
except ImportError:
    class QObject:
        pass
    class QThread:
        pass
    def pyqtSignal(*args):
        return None

from core.platform import is_linux, is_macos, is_windows

logger = logging.getLogger("FreeFlow.Updater")

GITHUB_REPO = "BheeshamKS/FreeFlow"
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def parse_version(v_str: str) -> Tuple[int, ...]:
    """Extract numeric version tuple from string (e.g. 'v1.2.3' -> (1, 2, 3))."""
    cleaned = re.sub(r"^[vV]", "", str(v_str).strip())
    # Match numbers separated by dots
    parts = re.findall(r"\d+", cleaned)
    if not parts:
        return (0, 0, 0)
    return tuple(int(p) for p in parts)


def is_newer_version(remote_tag: str, current_version: str) -> bool:
    """Return True if remote_tag is strictly newer than current_version."""
    remote_tup = parse_version(remote_tag)
    current_tup = parse_version(current_version)
    return remote_tup > current_tup


def detect_install_type() -> str:
    """
    Detect packaging / execution environment:
    - 'appimage': Linux AppImage portable bundle
    - 'git': Cloned Git source repository
    - 'windows_exe': Windows compiled executable (Inno Setup / PyInstaller)
    - 'macos_app': macOS .app bundle
    - 'deb': Linux Debian/Ubuntu dpkg package
    - 'source': Generic Python source tree
    """
    appimage = os.environ.get("APPIMAGE")
    if appimage and os.path.exists(appimage):
        return "appimage"

    if is_windows() and getattr(sys, "frozen", False):
        return "windows_exe"

    if is_macos():
        if getattr(sys, "frozen", False) or ".app" in sys.executable:
            return "macos_app"

    repo_root = Path(__file__).resolve().parent.parent
    if (repo_root / ".git").is_dir():
        return "git"

    if is_linux() and Path("/usr/share/freeflow").is_dir():
        return "deb"

    return "source"


def find_matching_asset(assets: List[Dict[str, Any]], install_type: str) -> Optional[Dict[str, Any]]:
    """Select the best download asset from GitHub release assets based on installation type."""
    if not assets:
        return None

    install_type = install_type.lower()

    if install_type == "appimage":
        for a in assets:
            name = a.get("name", "").lower()
            if name.endswith(".appimage"):
                return a

    elif install_type == "windows_exe" or is_windows():
        # Prefer Setup.exe installer, then .zip
        for a in assets:
            name = a.get("name", "").lower()
            if "setup" in name and name.endswith(".exe"):
                return a
        for a in assets:
            name = a.get("name", "").lower()
            if name.endswith(".exe"):
                return a
        for a in assets:
            name = a.get("name", "").lower()
            if "windows" in name and name.endswith(".zip"):
                return a

    elif install_type == "macos_app" or is_macos():
        for a in assets:
            name = a.get("name", "").lower()
            if name.endswith(".dmg"):
                return a
        for a in assets:
            name = a.get("name", "").lower()
            if "macos" in name and (name.endswith(".tar.gz") or name.endswith(".zip")):
                return a

    elif install_type == "deb":
        for a in assets:
            name = a.get("name", "").lower()
            if name.endswith(".deb"):
                return a

    # Generic Linux tarball fallback
    if is_linux():
        for a in assets:
            name = a.get("name", "").lower()
            if "linux" in name and name.endswith(".tar.gz"):
                return a

    return assets[0] if assets else None


class CheckUpdateWorker(QThread):
    """Background worker to check GitHub Releases without freezing the UI."""

    update_available = pyqtSignal(str, str, dict) if QThread is not None else None  # tag, notes, asset
    no_update_found = pyqtSignal() if QThread is not None else None
    check_failed = pyqtSignal(str) if QThread is not None else None

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self.current_version = current_version

    def run(self):
        try:
            req = urllib.request.Request(
                RELEASES_API_URL,
                headers={"User-Agent": "FreeFlow-Updater"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    msg = f"GitHub API returned HTTP {resp.status}"
                    logger.warning(msg)
                    if self.check_failed:
                        self.check_failed.emit(msg)
                    return

                data = json.loads(resp.read().decode("utf-8"))

            tag_name = data.get("tag_name", "").strip()
            body = data.get("body", "").strip()
            assets = data.get("assets", [])

            if is_newer_version(tag_name, self.current_version):
                install_type = detect_install_type()
                target_asset = find_matching_asset(assets, install_type) or {}
                logger.info(f"New update found: {tag_name} (current: {self.current_version})")
                if self.update_available:
                    self.update_available.emit(tag_name, body, target_asset)
            else:
                logger.info(f"FreeFlow is up to date ({self.current_version}).")
                if self.no_update_found:
                    self.no_update_found.emit()

        except Exception as e:
            logger.warning(f"Failed to check for updates: {e}")
            if self.check_failed:
                self.check_failed.emit(str(e))


class DownloadUpdateWorker(QThread):
    """Background worker to download release binary with progress reporting."""

    progress = pyqtSignal(int) if QThread is not None else None
    download_completed = pyqtSignal(str) if QThread is not None else None
    download_failed = pyqtSignal(str) if QThread is not None else None

    def __init__(self, download_url: str, filename: str, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.filename = filename

    def run(self):
        try:
            temp_dir = tempfile.gettempdir()
            out_path = os.path.join(temp_dir, self.filename)

            req = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": "FreeFlow-Updater"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                total_size = resp.headers.get("Content-Length")
                total_bytes = int(total_size) if total_size else 0

                downloaded = 0
                block_size = 64 * 1024  # 64 KB chunks

                with open(out_path, "wb") as f:
                    while True:
                        chunk = resp.read(block_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_bytes > 0 and self.progress:
                            pct = int((downloaded / total_bytes) * 100)
                            self.progress.emit(min(100, pct))

            # Ensure executable permission on Unix
            if not is_windows():
                st = os.stat(out_path)
                os.chmod(out_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

            logger.info(f"Update downloaded successfully to {out_path} ({downloaded} bytes)")
            if self.download_completed:
                self.download_completed.emit(out_path)

        except Exception as e:
            logger.error(f"Download failed: {e}")
            if self.download_failed:
                self.download_failed.emit(str(e))


class UpdateManager(QObject):
    """High-level update coordinator managing checks, downloads, and app restart."""

    # Public Qt signals
    checking_started = pyqtSignal() if QObject is not None else None
    update_available = pyqtSignal(str, str, dict) if QObject is not None else None  # tag, notes, asset
    up_to_date = pyqtSignal() if QObject is not None else None
    check_error = pyqtSignal(str) if QObject is not None else None

    download_started = pyqtSignal() if QObject is not None else None
    download_progress = pyqtSignal(int) if QObject is not None else None
    download_finished = pyqtSignal(str) if QObject is not None else None
    download_error = pyqtSignal(str) if QObject is not None else None

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self.current_version = current_version
        self.install_type = detect_install_type()
        self._check_worker: Optional[CheckUpdateWorker] = None
        self._download_worker: Optional[DownloadUpdateWorker] = None
        self.latest_tag: Optional[str] = None
        self.latest_notes: Optional[str] = None
        self.latest_asset: Optional[Dict[str, Any]] = None
        self.downloaded_file: Optional[str] = None

    def check_for_updates(self):
        """Initiate background update check."""
        if self._check_worker and self._check_worker.isRunning():
            return

        if self.checking_started:
            self.checking_started.emit()

        self._check_worker = CheckUpdateWorker(self.current_version, self)
        self._check_worker.update_available.connect(self._on_update_available)
        self._check_worker.no_update_found.connect(self._on_up_to_date)
        self._check_worker.check_failed.connect(self._on_check_error)
        self._check_worker.start()

    def _on_update_available(self, tag: str, notes: str, asset: dict):
        self.latest_tag = tag
        self.latest_notes = notes
        self.latest_asset = asset
        if self.update_available:
            self.update_available.emit(tag, notes, asset)

    def _on_up_to_date(self):
        if self.up_to_date:
            self.up_to_date.emit()

    def _on_check_error(self, err: str):
        if self.check_error:
            self.check_error.emit(err)

    def start_download(self):
        """Download latest release asset."""
        if self._download_worker and self._download_worker.isRunning():
            return

        # Special case: Git installation updates directly via git pull
        if self.install_type == "git":
            self._apply_git_update()
            return

        if not self.latest_asset or not self.latest_asset.get("browser_download_url"):
            err = "No downloadable release asset matching this system was found."
            logger.error(err)
            if self.download_error:
                self.download_error.emit(err)
            return

        url = self.latest_asset["browser_download_url"]
        filename = self.latest_asset.get("name", "FreeFlow-update")

        if self.download_started:
            self.download_started.emit()

        self._download_worker = DownloadUpdateWorker(url, filename, self)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.download_completed.connect(self._on_download_finished)
        self._download_worker.download_failed.connect(self._on_download_error)
        self._download_worker.start()

    def _on_download_progress(self, pct: int):
        if self.download_progress:
            self.download_progress.emit(pct)

    def _on_download_finished(self, path: str):
        self.downloaded_file = path
        if self.download_finished:
            self.download_finished.emit(path)

    def _on_download_error(self, err: str):
        if self.download_error:
            self.download_error.emit(err)

    def apply_update_and_restart(self):
        """
        Apply downloaded update and restart FreeFlow seamlessly.
        Handles AppImage file replacement, Git pull, or Windows installer execution.
        """
        logger.info(f"Applying update for install type: {self.install_type}")

        if self.install_type == "appimage":
            self._apply_appimage_update()
        elif self.install_type == "git":
            self._apply_git_update()
        elif self.install_type == "windows_exe":
            self._apply_windows_update()
        elif self.install_type == "macos_app":
            self._apply_macos_update()
        else:
            # Fallback
            if self.downloaded_file:
                logger.info(f"Update downloaded to {self.downloaded_file}. Prompting user to run.")

    def _apply_appimage_update(self):
        """Replace running AppImage with downloaded file and re-exec."""
        running_appimage = os.environ.get("APPIMAGE")
        if not running_appimage or not self.downloaded_file:
            logger.error("Missing running AppImage path or downloaded update file.")
            return

        try:
            # Make downloaded AppImage executable
            os.chmod(self.downloaded_file, 0o755)

            # Atomically replace current AppImage binary
            os.replace(self.downloaded_file, running_appimage)
            logger.info(f"Replaced AppImage at {running_appimage}")

            # Spawn new AppImage process
            cmd = [running_appimage] + [a for a in sys.argv[1:] if a != "--minimized"]
            subprocess.Popen(cmd)

            # Terminate current instance cleanly
            from PyQt6.QtWidgets import QApplication
            QApplication.quit()
            sys.exit(0)
        except Exception as e:
            logger.error(f"Failed to replace AppImage: {e}")

    def _apply_git_update(self):
        """Update via git pull and relaunch."""
        repo_root = Path(__file__).resolve().parent.parent
        try:
            logger.info("Executing git pull origin main...")
            pull_res = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            logger.info(f"git pull: {pull_res.stdout.strip()}")

            # Relaunch current app
            main_script = repo_root / "app.py"
            subprocess.Popen([sys.executable, str(main_script)] + sys.argv[1:])

            from PyQt6.QtWidgets import QApplication
            QApplication.quit()
            sys.exit(0)
        except Exception as e:
            logger.error(f"Git update failed: {e}")
            if self.download_error:
                self.download_error.emit(f"Git update failed: {e}")

    def _apply_windows_update(self):
        """Execute Windows installer in silent mode and exit application."""
        if not self.downloaded_file:
            return

        try:
            # Windows installer (Inno Setup supports /SILENT /NORESTART)
            cmd = f'cmd.exe /c timeout /t 1 /nobreak & start "" "{self.downloaded_file}" /SILENT'
            subprocess.Popen(cmd, shell=True)

            from PyQt6.QtWidgets import QApplication
            QApplication.quit()
            sys.exit(0)
        except Exception as e:
            logger.error(f"Windows update launch failed: {e}")

    def _apply_macos_update(self):
        """Open downloaded DMG / bundle for user or replace app bundle."""
        if not self.downloaded_file:
            return

        try:
            subprocess.Popen(["open", self.downloaded_file])
            from PyQt6.QtWidgets import QApplication
            QApplication.quit()
            sys.exit(0)
        except Exception as e:
            logger.error(f"macOS update launch failed: {e}")
