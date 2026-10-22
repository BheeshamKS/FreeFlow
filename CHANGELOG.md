# Changelog

All notable changes to **FreeFlow for Linux** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
