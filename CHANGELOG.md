# Changelog

All notable changes to **FreeFlow for Linux** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.2] - 2026-10-27

### Fixed
- **Silent Background Startup on Boot**:
  - Eliminated dual-autostart race condition on Linux where both `freeflow.service` (systemd) and `freeflow.desktop` (XDG autostart) launched concurrently at login, causing the second instance to erroneously activate the first instance's window.
  - Hardened single-instance guard so any instance launched with `--autostart` or `--minimized` exits silently without sending an `ACTIVATE` signal to the running daemon.
  - Cleaned up redundant systemd user services in favor of standard XDG desktop autostart specification.
- **Application Menu & Launcher Activation**:
  - Fixed issue where clicking FreeFlow from the desktop application menu / launcher while running in the background did not present the app.
  - Implemented `send_activation()` in `SingleInstanceGuard` and ensured `SingleInstanceGuard` forwards the `ACTIVATE` command over local socket IPC.
  - Enhanced `show_main_window()` to restore minimized windows (`showNormal()`), clear minimized window state, set active focus, and raise to foreground across Linux, Windows, and macOS.
  - Added automatic installation of `~/.local/share/applications/freeflow.desktop` so FreeFlow is always discoverable in desktop application menus.
- **Taskbar / System Tray Click Behavior**:
  - Resolved duplicate `_on_tray_activated` event handler in `SystemTrayController` that previously routed double-clicks to preferences instead of the main app.
  - Standardized tray activation: Double-clicking and single-clicking the system tray icon now consistently opens and presents the FreeFlow Hub window, while right-clicking opens the default context menu.

### Added
- **Audio Preservation & Zero-Loss Recovery Buffer**:
  - Recorded audio from long dictations (e.g., 5–10+ minutes) is now automatically preserved in a persistent temporary recovery cache (`get_recovery_audio_path()`).
  - If transcription fails due to network dropouts, firewall blocks, or Groq API rate limits, the recorded audio is never lost.
  - Added interactive **"Retry Transcription with Saved Audio"** affordances across:
    - **Floating HUD Capsule**: Contextual `[🔁 Retry]` button appears directly alongside `[Solutions →]` in error state.
    - **Troubleshooting & Solutions Dialog**: Dedicated **Saved Audio Recovered** card displaying recording duration and file size, with direct `[🔁 Retry Transcription Now]` and `[💾 Export Audio (.wav)...]` actions.
    - **System Tray Menu**: Dynamic `🔁 Retry Last Audio Transcription (Mm SSs)...` context menu action.
    - **Dashboard Hero Card**: Obsidian emerald retry button appearing immediately under the Voice Orb when recovery audio is cached.

## [1.2.1] - 2026-10-23

### Added
- **Common Troubleshooting & Help Guide**:
  - Replaced permanent error displays with a browsable **Common Troubleshooting & Help** guide accessible via Preferences and System Tray.
  - Interactive topic pills allowing users to review setup instructions and fixes for:
    - 🔑 **API Key**: Obtaining free keys from Groq Console, format validation, and test connection.
    - 🌐 **Firewall & Network**: Windows Defender / Antivirus rule guidance, proxies, and HTTPS connectivity.
    - 🎙️ **Microphone**: Input hardware selection, unmuting, and system permissions.
    - 📋 **Clipboard**: Automatic active text box paste vs. desktop fallback behavior.
    - ⏱️ **Rate Limits**: Quotas, cooldowns, and speech recognition model switching.
  - **On-Demand Error Flow Simulator**: Added a `[Test Error Flow ▾]` tool inside the guide allowing users to simulate errors (API key, Network, Microphone) and verify the HUD capsule and desktop notification flows on demand.
- **Dynamic Context-Aware Error Solutions**:
  - When an error occurs during dictation, the HUD capsule presents `[View Solutions →]`, opening the guide directly focused on the active issue.
  - Closing or accessing the menu later restores the clean, common guide without permanently showing past errors.
- **Smart Active Text Box Detection & Clipboard Fallback**:
  - Cross-platform active input field detection (`core/injector.py`) across Windows (`GetGUIThreadInfo`), macOS (`AXFocusedUIElement`), and Linux (desktop/dock filtering).
  - **If active text box is focused**: Injects text directly into the focused field and restores the user's prior clipboard buffer (transcribed text is NOT left on the clipboard).
  - **If no text box is focused**: Avoids blind keystroke emission, copies transcribed text directly to the system clipboard, and displays `"Copied to clipboard (no text box active)"` on the HUD capsule.

## [1.2.0] - 2026-10-23

### Added
- **Audio Input Device (Microphone) Selection**:
  - Direct hardware microphone selection in Preferences and Main Window Hub.
  - Dynamic discovery of audio devices using `sounddevice` with a real-time `[Refresh Devices]` scanner.
  - Safe automatic fallback to system default if an external USB/Bluetooth microphone is unplugged.
- **Automated GitHub Release Auto-Updater**:
  - Automatic background update checks against GitHub Releases API on startup.
  - User-configurable update behavior:
    - **Auto-Update**: Background silent asset download with prompt to restart when ready.
    - **Ask Before Updating**: Desktop notification when a new version is published with one-click update & restart.
  - Zero-friction in-place self-replacement across Linux (AppImage & Git), Windows (Setup EXE), and macOS.
  - In-app interactive update notification banner in the Desktop Hub header.
- **Startup Minimize on Boot Fix**:
  - Resolved issue where FreeFlow popped up on boot even when "Start minimized to system tray on boot" was selected.
  - Unified cross-platform autostart engine (`core/autostart.py`) managing XDG Autostart, systemd user services, Windows Run registry, and macOS LaunchAgents.

## [1.1.0] - 2026-10-21

### Added
- **Cross-Platform Support for Windows & macOS**:
  - Native Windows executable and Inno Setup installer (`FreeFlow-Setup-Windows.exe`).
  - Native macOS application bundle and disk image (`FreeFlow-1.1.0-macOS.dmg`).
  - Official Linux AppImage portable bundle (`FreeFlow-1.1.0-x86_64.AppImage`).
  - GitHub Actions automated multi-platform release CI/CD pipeline.

## [1.0.0] - 2026-10-21

### Initial Public Release

Welcome to the first official release of **FreeFlow for Linux**, an open-source, private, sub-second (~300ms) voice-to-text dictation application built as a native Linux alternative to macOS Wispr Flow and Superwhisper.

### Added
- **Sub-Second Groq Whisper Engine**: Powered by Groq LPUs running `whisper-large-v3` for speech transcription in ~300ms without GPU or battery drain.
- **Out of the Box Experience (OOBE) Wizard**:
  - 4-step setup wizard automatically triggered on first launch or via `app.py --setup`.
  - Step 1: Architectural comparison vs macOS tools and cloud APIs.
  - Step 2: Groq API key setup with direct console links and real-time connection test.
  - Step 3: Global hotkey configuration with interactive key capture.
  - Step 4: System login autostart, minimize to tray, and close-to-tray settings.
- **Inky Desktop Hub Window**:
  - Raycast/Linear design aesthetic with pure-near-black surfaces (`#08090b`).
  - Breathing interactive Voice Orb with radial light diffusion reacting to microphone levels.
  - Handcrafted vector glyph navigation (`SidebarNavItem`) with active indicators and dynamic transcript count badges.
  - Apple-style tactile monospace keyboard badges (`[Alt]` `[R]`).
  - Open 3-column stats cards: Total Dictations, Words Spoken, and Engine Latency.
- **Wispr Flow Floating HUD Capsule**:
  - Non-focus-stealing floating pill overlay with animated harmonic audio waveforms.
  - Draggable positioning and smooth state transitions (`Listening`, `Transcribing`, `Done`).
- **Universal Linux Cursor Injection**:
  - Native Wayland injection via `wl-clipboard` and `wtype`.
  - Native X11 injection via `xclip` and `xdotool`.
  - Automatic clipboard preservation and restoration.
- **Interactive Shortcut Recorder**:
  - Physical key-capture widget allowing users to press any shortcut combination (e.g. `Alt + R`, `Ctrl + Space`, `F9`).
  - Supports both **Toggle Mode** (tap to start, tap to finish) and **Hold-to-Talk** (push-to-talk).
- **Private Local Dictation History**:
  - Transcripts stored locally on device at `~/.config/freeflow/history.json`.
  - Filter and search bar, word counts, and instant copy with tactile feedback (`"Copied!"`).
  - Discreet ghost action (`Clear All`) with safety confirmation guard.
- **Single-Instance IPC Enforcement**:
  - `QLocalServer`/`QLocalSocket` guard preventing duplicate background processes.
  - Raising the existing window when clicked from the application launcher.
- **Multi-Distribution System Installer**:
  - [`setup.sh`](setup.sh) supporting Ubuntu/Debian, Arch Linux, Fedora, openSUSE, Alpine, Void, and Gentoo.
  - Automatically launches FreeFlow in Setup Mode upon completing installation.
  - Systemd user service (`freeflow.service`) for background autostart.
