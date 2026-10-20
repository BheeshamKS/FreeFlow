# Changelog

All notable changes to **FreeFlow for Linux** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
