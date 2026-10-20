# FreeFlow for Linux

<div align="center">

**The High-Speed, Native Voice Dictation Platform for Linux Desktops**  
*A private, sub-second (~300ms) open-source alternative to macOS FreeFlow and Wispr Flow.*

[![Linux](https://img.shields.io/badge/Platform-Linux%20(Wayland%20%26%20X11)-10b981?style=flat-square&logo=linux&logoColor=white)](https://kernel.org)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Groq LPU](https://img.shields.io/badge/Groq%20LPU-Whisper%20Large%20v3-f59e0b?style=flat-square)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-gray?style=flat-square)](LICENSE)

</div>

---

## Overview

**FreeFlow** brings the effortless, instant voice-to-text dictation experience of macOS **Wispr Flow** and **Superwhisper** to Linux desktops. 

Press your global shortcut (**`Alt + R`** by default) from any application—terminal, code editor, browser, or chat window—speak naturally, and your speech is instantly transcribed and injected straight into your active cursor in **~300ms**.

### Why FreeFlow vs. Other Options?

| Feature | FreeFlow Linux | Standard Cloud APIs | Local Whisper (CPU/GPU) |
|---|---|---|---|
| **Latency** | **~300ms** (Sub-second, powered by Groq LPUs) | 3,000ms – 5,000ms | 1,500ms – 4,000ms |
| **System Impact** | **0% CPU / 0% GPU idle**, lightweight daemon | Moderate memory footprint | Heavy VRAM drain, laptop heating & fan noise |
| **Linux Support** | **Native Wayland & X11 cursor injection** | Manual copy-paste | Inconsistent desktop injection |
| **Privacy** | **100% Local history** (`~/.config/freeflow/history.json`) | Audio stored by provider | Local but resource-intensive |
| **Desktop UI** | **Raycast/Linear Inky Hub + Floating HUD Pill** | Web browser only | Terminal-only or clunky GUI |

---

## Quick Install (One-Liner)

Clone and run the automated installer. The setup script automatically detects your distribution, installs required system packages, sets up the Python virtual environment, registers desktop shortcuts, and **immediately opens FreeFlow in Setup Mode**:

```bash
git clone https://github.com/BheeshamKS/FreeFlow.git && cd FreeFlow && chmod +x setup.sh && ./setup.sh
```

---

## Distro-by-Distro Quick Install Commands

If you prefer installing system prerequisites manually before running `./setup.sh`, use the command for your Linux distribution:

### 1. Ubuntu / Debian / Linux Mint / Pop!_OS / Elementary OS
```bash
sudo apt-get update && sudo apt-get install -y \
  python3 python3-venv python3-pip python3-dev \
  libportaudio2 portaudio19-dev libnotify-bin \
  xdotool xclip wtype wl-clipboard libxcb-cursor0 libxcb-xinerama0

git clone https://github.com/BheeshamKS/FreeFlow.git && cd FreeFlow && ./setup.sh
```

### 2. Arch Linux / Manjaro / EndeavourOS
```bash
sudo pacman -S --needed --noconfirm \
  python python-pip portaudio libnotify \
  xdotool xclip wtype wl-clipboard xcb-util-cursor

git clone https://github.com/BheeshamKS/FreeFlow.git && cd FreeFlow && ./setup.sh
```

### 3. Fedora / RHEL / CentOS Stream / Rocky / AlmaLinux
```bash
sudo dnf install -y \
  python3 python3-devel python3-pip portaudio-devel \
  libnotify xdotool xclip wl-clipboard

git clone https://github.com/BheeshamKS/FreeFlow.git && cd FreeFlow && ./setup.sh
```

### 4. openSUSE (Tumbleweed & Leap)
```bash
sudo zypper --non-interactive install \
  python3 python3-devel python3-pip portaudio-devel \
  libnotify-tools xdotool xclip wl-clipboard libxcb-cursor0

git clone https://github.com/BheeshamKS/FreeFlow.git && cd FreeFlow && ./setup.sh
```

### 5. Alpine Linux
```bash
sudo apk add \
  python3 py3-pip python3-dev portaudio-dev \
  libnotify xdotool xclip wl-clipboard

git clone https://github.com/BheeshamKS/FreeFlow.git && cd FreeFlow && ./setup.sh
```

### 6. Void Linux
```bash
sudo xbps-install -Sy \
  python3 python3-pip python3-devel portaudio-devel \
  libnotify xdotool xclip wl-clipboard

git clone https://github.com/BheeshamKS/FreeFlow.git && cd FreeFlow && ./setup.sh
```

### 7. Solus
```bash
sudo eopkg install -y \
  python3 portaudio-devel libnotify xdotool xclip wl-clipboard

git clone https://github.com/BheeshamKS/FreeFlow.git && cd FreeFlow && ./setup.sh
```

### 8. Gentoo
```bash
sudo emerge --ask \
  media-libs/portaudio x11-misc/xdotool x11-misc/xclip gui-apps/wl-clipboard x11-libs/libnotify

git clone https://github.com/BheeshamKS/FreeFlow.git && cd FreeFlow && ./setup.sh
```

---

## Out of the Box Experience (Setup Mode)

Upon completing installation, `./setup.sh` automatically launches FreeFlow in **Setup Mode** (`--setup`), presenting a guided 4-step onboarding wizard:

```
┌────────────────────────────────────────────────────────────────────────┐
│  ● FreeFlow Setup     [ ● 1 Welcome ] › [ 2 Engine ] › [ 3 Shortcut ]  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   Voice-to-Text Dictation, Built for Linux                             │
│   Sub-second ~300ms latency, native cursor injection, and privacy.     │
│                                                                        │
│   [ 1. Welcome ]     Architectural overview vs macOS Wispr Flow        │
│   [ 2. Engine ]      Connect free Groq Whisper key with 1-click test   │
│   [ 3. Shortcut ]    Press keys to set shortcut (default: Alt + R)     │
│   [ 4. Preferences ] Autostart on boot, start minimized, tray daemon   │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│   [ Skip Setup ]                                [ Continue → ]         │
└────────────────────────────────────────────────────────────────────────┘
```

You can re-run the Setup Wizard at any time:
```bash
.venv/bin/python3 app.py --setup
```
*(Or click **"Setup Guide"** in the sidebar at any time.)*

---

## How It Works

```
 ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
 │ Global       │     │ Microphone   │     │ Groq LPU     │     │ Cursor       │
 │ Hotkey       │ ──> │ Audio Record │ ──> │ Whisper v3   │ ──> │ Window Paste │
 │ (Alt + R)    │     │ (~16kHz Mono)│     │ (~300ms API) │     │ (Wayland/X11)│
 └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

1. **Trigger**: You press your configured global shortcut (`Alt + R`).
2. **Audio Capture**: FreeFlow records your voice at 16kHz mono (optimal for Whisper) via `sounddevice` / PortAudio, with zero-crash native fallbacks (`parecord`, `arecord`, `ffmpeg`).
3. **Floating HUD Capsule**: A translucent, draggable Wispr Flow pill displays live harmonic waveform bars reacting dynamically to your voice volume.
4. **Whisper Transcription**: Audio is sent to Groq's high-speed Whisper Large v3 LPU, returning raw transcription in under 300ms.
5. **Cursor Injection**: The text is instantly pasted into your active cursor position across Wayland (`wl-copy` + `wtype`) or X11 (`xclip` + `xdotool`).
6. **Clipboard Preservation**: FreeFlow backs up and restores your previous clipboard buffer after injection so you never lose copied content.
7. **Local Journal**: The transcription is saved to your private local history (`~/.config/freeflow/history.json`).

---

## Desktop Hub & User Interface

FreeFlow features a complete desktop Hub window crafted strictly according to the **Linear** and **Raycast** design specifications:

- **Inky Dark Palette**: Pure-near-black background (`#08090b`), elevated card surfaces (`#0f1115`), hairline borders (`#1c1f26`), and emerald accents (`#10b981`).
- **Interactive Voice Orb**: A breathing radial light orb that expands with microphone input and pulses dynamically during transcription.
- **Bespoke Sidebar Navigation**: Handcrafted vector glyphs for **Dictation**, **History**, and **Settings**, featuring a 3px active indicator bar and live transcript count badges.
- **Tactile Monospace Keycaps**: Displays your active shortcut (`[Alt]` `[R]`) in Apple-style monospace badges.
- **Dictation History Toolbar**: Search past transcripts by keyword, view exact word counts and elapsed durations, and copy with one-click tactile feedback (`"Copied!"`). Destructive actions are kept in a discreet ghost button (`Clear All`) with a confirmation safety guard.
- **Single-Instance IPC Guard**: Launching FreeFlow from your desktop app menu raises your existing window instead of spawning duplicate background processes.

---

## Global Hotkey Modes

FreeFlow supports two behavior modes:

### 1. Toggle Mode (Default & Recommended)
- Tap **`Alt + R`** once: Recording begins (floating HUD appears).
- Speak naturally.
- Tap **`Alt + R`** again: Recording stops, audio transcribes in ~300ms, and text is pasted at your cursor.

### 2. Hold-to-Talk (Push-to-Talk)
- Hold **`Alt + R`** down while speaking.
- Release the keys when done: Recording automatically stops and pastes text.

---

## Systemd Autostart (Background Daemon)

FreeFlow installs a systemd user unit so it runs silently in the background when you log into your desktop:

```bash
# Enable and start immediately
systemctl --user enable --now freeflow.service

# Check daemon status
systemctl --user status freeflow.service

# Stream live background logs
journalctl --user -u freeflow.service -f

# Disable background autostart
systemctl --user disable freeflow.service
```

---

## Configuration & Settings

Settings are persisted in `~/.config/FreeFlow/FreeFlow.conf` (via Qt `QSettings`) with fallback support for `~/.config/freeflow/.env`.

| Setting | Default | Description |
|---|---|---|
| `groq_api_key` | `""` | Groq Cloud API key (`gsk_...`) from [console.groq.com](https://console.groq.com/keys) |
| `hotkey_modifier` | `KEY_LEFTALT` | Modifier key (`KEY_LEFTALT`, `KEY_LEFTCTRL`, `KEY_LEFTSHIFT`, `KEY_LEFTMETA`) |
| `hotkey_key` | `KEY_R` | Trigger key (`KEY_R`, `KEY_SPACE`, `KEY_F9`, etc.) |
| `hotkey_mode` | `toggle` | Interaction mode (`toggle` or `hold`) |
| `transcription_model` | `whisper-large-v3` | Groq Whisper speech-to-text model |
| `format_text` | `false` | Enable LLM formatting (disabled by default for ultra-low latency) |
| `show_hud` | `true` | Show floating Wispr Flow waveform capsule during recording |
| `autostart` | `false` | Launch automatically on system login |
| `start_minimized` | `false` | Launch minimized to system tray |
| `close_to_tray` | `true` | Minimize to tray when closing Hub window |

---

## Permissions & Troubleshooting

### Global Hotkey Permissions (`input` Group)
Linux kernel input capture via `evdev` requires membership in the `input` group:
```bash
sudo usermod -aG input $USER
```
> **Note**: If you were just added to the `input` group, **log out and log back in** (or run `newgrp input`) so your desktop session picks up the new permissions.

### Wayland vs. X11
- **Wayland (GNOME / KDE / Hyprland / Sway)**: Uses `wl-clipboard` for clipboard operations and `wtype` for virtual keystroke simulation.
- **X11**: Uses `xclip` for clipboard operations and `xdotool` for active window pasting (`Ctrl+V`).
- FreeFlow auto-detects your session type at startup.

### Audio Recording
- Primary audio engine uses `sounddevice` (PortAudio).
- If PortAudio is missing or misconfigured, FreeFlow automatically falls back to native Linux system tools (`parecord` -> `arecord` -> `ffmpeg`) with zero crashes.

---

## Project Structure

```
FreeFlow/
├── app.py                      # Main application controller & IPC daemon
├── core/
│   ├── config.py               # QSettings & .env configuration manager
│   ├── groq_client.py          # Whisper Large v3 background worker
│   ├── history.py              # Local persistent JSON history manager
│   ├── hotkey.py               # Kernel evdev & pynput global hotkey listener
│   ├── injector.py             # Wayland & X11 active window text injector
│   ├── recorder.py             # Audio capture engine with multi-tool fallback
│   └── single_instance.py      # QLocalServer single-instance IPC guard
├── ui/
│   ├── hud.py                  # Floating Wispr Flow waveform capsule
│   ├── main_window.py          # Raycast/Linear Inky Desktop Hub window
│   ├── onboarding.py           # 4-step Out of the Box Experience (OOBE) wizard
│   ├── settings.py             # Standalone preferences dialog
│   ├── shortcut_recorder.py    # Interactive key-capture widget
│   └── tray.py                 # System tray icon & freedesktop notifications
├── assets/                     # Application icons (idle, recording, transcribing)
├── freeflow.desktop            # Freedesktop application menu launcher
├── setup.sh                    # Automated universal distribution installer
└── requirements.txt            # Python dependencies
```

---

## License & Credits

- FreeFlow Linux is released under the **MIT License**.
- Inspired by the macOS [FreeFlow](https://github.com/zachlatta/freeflow) project by Zach Latta and [Wispr Flow](https://wisprflow.ai/).
- Speech-to-text inference powered by [Groq Cloud LPUs](https://groq.com).
