# FreeFlow for Linux

<div align="center">

**Sub-second voice dictation for Linux desktops**  
*Press a shortcut, speak naturally, and text appears instantly at your cursor.*

[![Linux](https://img.shields.io/badge/Platform-Linux%20(Wayland%20%26%20X11)-10b981?style=flat-square&logo=linux&logoColor=white)](https://kernel.org)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Groq LPU](https://img.shields.io/badge/Groq%20LPU-Whisper%20Large%20v3-f59e0b?style=flat-square)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-gray?style=flat-square)](LICENSE)

</div>

---

## What It Does

FreeFlow is a native voice-to-text dictation application built for Linux. 

- **Instant Dictation (~300ms)**: Press your global shortcut from any app (terminal, code editor, browser, Slack), speak, and text is typed straight into your active cursor.
- **Wayland & X11 Native**: Seamless cursor injection across modern Wayland compositors (GNOME, KDE, Hyprland, Sway) and X11 sessions.
- **Whisper Large v3**: High-accuracy speech recognition powered by Groq's ultra-fast LPUs.
- **Minimalist HUD**: Floating waveform capsule with real-time audio visualization while speaking.
- **Private & Lightweight**: 0% idle CPU usage and 100% private local history stored on your device.

---

## Requirements

- **OS**: Any modern Linux distribution (Ubuntu/Debian, Arch, Fedora, openSUSE, Void, etc.)
- **Display**: Wayland or X11
- **Python**: 3.10 or higher
- **Groq API Key**: Free tier available at [console.groq.com/keys](https://console.groq.com/keys)
- **Microphone**: Working audio input

---

## Quick Install

Run this single command in your terminal. The installer automatically detects your distribution, installs required system packages, sets up desktop integration, and launches the setup wizard:

```bash
git clone https://github.com/BheeshamKS/FreeFlow.git && cd FreeFlow && ./setup.sh
```

---

## How to Use

1. **Start Dictation**: Press **`Alt + R`** (default shortcut).
2. **Speak**: The floating waveform pill will appear and capture your voice.
3. **Paste**: Press **`Alt + R`** again (or release if using hold-to-talk). Text is transcribed and typed into your focused window in ~300ms.

### Desktop App & Settings

- Launch **FreeFlow** from your application menu or run `freeflow` in your terminal.
- **History**: Search previous dictations, copy past text, or check your spoken word counts.
- **Custom Shortcut**: Change your hotkey under **Settings** by pressing the shortcut recorder button and typing your desired key combination.
- **Setup Wizard**: Run `freeflow --setup` at any time to re-run the onboarding guide.

---

## Optional: Background Daemon (Autostart)

To have FreeFlow start automatically when you log into your desktop:

```bash
systemctl --user enable --now freeflow.service
```

To stop or disable autostart:

```bash
systemctl --user disable --now freeflow.service
```

---

## Troubleshooting

### Global Hotkey Permissions
Kernel-level global shortcut detection (`evdev`) requires membership in the `input` group:
```bash
sudo usermod -aG input $USER
```
> **Note**: If newly added to the `input` group, **log out and log back in** (or run `newgrp input`) to apply changes.

---

## License

Released under the [MIT License](LICENSE).
