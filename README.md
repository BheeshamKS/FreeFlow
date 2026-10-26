# FreeFlow

<div align="center">

**Fast, private voice dictation for Linux, Windows, macOS, and Android**  
*Press a shortcut, speak naturally, and text appears instantly at your cursor.*

[![Linux](https://img.shields.io/badge/Platform-Linux-10b981?style=flat-square&logo=linux&logoColor=white)](https://kernel.org)
[![Windows](https://img.shields.io/badge/Platform-Windows-0078d4?style=flat-square&logo=windows&logoColor=white)](https://microsoft.com)
[![macOS](https://img.shields.io/badge/Platform-macOS-000000?style=flat-square&logo=apple&logoColor=white)](https://apple.com)
[![Android](https://img.shields.io/badge/Platform-Android-3DDC84?style=flat-square&logo=android&logoColor=white)](https://github.com/BheeshamKS/FreeFlow-Pocket)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Groq LPU](https://img.shields.io/badge/Groq%20LPU-Whisper%20Large%20v3-f59e0b?style=flat-square)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-gray?style=flat-square)](LICENSE)

</div>

---

## What It Does

FreeFlow is a high-speed, native voice-to-text dictation application.

- **Instant Dictation (~300ms)**: Press your global shortcut from any app (terminal, IDE, browser, chat), speak, and text is typed straight into your active cursor.
- **Cross-Platform Native Injection**: Direct active window injection across Linux (Wayland & X11), Windows, and macOS.
- **Whisper Large v3**: High-accuracy speech recognition powered by Groq's ultra-fast LPUs.
- **Microphone Selection**: Choose any physical, USB, Bluetooth, or virtual input device directly in Preferences with real-time hardware scanning.
- **Automated Self-Updating**: Automatically checks GitHub Releases on startup with Auto-Update and Ask Before Updating modes—never requires manual re-downloading.
- **Minimalist HUD**: Floating waveform capsule with real-time audio visualization while speaking.
- **Private & Lightweight**: 0% idle CPU usage and 100% private local history stored on your device.

---

## Requirements

- **Operating System**: Linux (Wayland or X11), Windows 10/11, or macOS (11.0+)
- **Python**: 3.10 or higher *(only required if installing from source)*
- **Groq API Key**: Free tier available at [console.groq.com/keys](https://console.groq.com/keys)
- **Microphone**: Working audio input

---

## Installation

Choose whether to download a ready-to-run pre-built installer or install from source using a terminal command:

### Option 1: Download Pre-Built Installers (Easiest)

Download the installer or binary for your OS directly from the [Latest Release](https://github.com/BheeshamKS/FreeFlow/releases/latest):

| Operating System | Download File | Format | Description |
|---|---|---|---|
| 🪟 **Windows** | [**`FreeFlow-Setup-Windows.exe`**](https://github.com/BheeshamKS/FreeFlow/releases/latest/download/FreeFlow-Setup-Windows.exe) | Installer `.exe` | 1-Click setup installer with desktop & Start menu shortcuts *(portable [`.zip`](https://github.com/BheeshamKS/FreeFlow/releases/latest/download/FreeFlow-windows-x64.zip) also available)* |
| 🐧 **Linux** | [**`FreeFlow-x86_64.AppImage`**](https://github.com/BheeshamKS/FreeFlow/releases/latest) | AppImage | Standalone binary — runs on any Linux distribution without installation (`chmod +x && ./...`) |
| 🐧 **Linux** | [**`freeflow_amd64.deb`**](https://github.com/BheeshamKS/FreeFlow/releases/latest) | Debian Package | Native `.deb` package for Ubuntu, Debian, Linux Mint, Pop!_OS (`sudo dpkg -i`) |
| 🍎 **macOS** | [**`FreeFlow-macOS.dmg`**](https://github.com/BheeshamKS/FreeFlow/releases/latest) | Disk Image `.dmg` | Native drag-and-drop installer for `/Applications` *(portable [`.tar.gz`](https://github.com/BheeshamKS/FreeFlow/releases/latest) also available)* |

---

### Option 2: Install via Terminal Commands (From Source)

Run the single-line command for your platform. The setup script automatically creates a virtual environment, installs dependencies, and launches the onboarding wizard:

#### 🐧 Linux
```bash
git clone https://github.com/BheeshamKS/FreeFlow.git && cd FreeFlow && ./setup.sh
```

#### 🍎 macOS
```bash
git clone https://github.com/BheeshamKS/FreeFlow.git && cd FreeFlow && ./setup-mac.sh
```

#### 🪟 Windows (PowerShell)
```powershell
git clone https://github.com/BheeshamKS/FreeFlow.git; cd FreeFlow; .\setup.ps1
```
*(Or double-click `setup.bat` after cloning).*

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

## FreeFlow for Android (FreeFlow Pocket)

FreeFlow is also available on Android as **[FreeFlow Pocket](https://github.com/BheeshamKS/FreeFlow-Pocket)**:

- **Floating Voice Capsule**: Wispr Flow inspired floating orb capsule available anywhere across your apps.
- **Custom Keyboard IME**: Samsung Keys Cafe styled on-screen keyboard with instant dictation key.
- **Quick Settings Tile**: Start and stop listening right from the Android notification bar.
- **Sub-300ms Whisper Large v3**: Same ultra-fast Groq speech inference on your mobile device.

- **GitHub Repository**: [https://github.com/BheeshamKS/FreeFlow-Pocket](https://github.com/BheeshamKS/FreeFlow-Pocket)
- **Releases**: [FreeFlow Pocket Latest Release](https://github.com/BheeshamKS/FreeFlow-Pocket/releases/latest)

---

## Platform Notes & Troubleshooting

### Linux (Global Hotkey Permissions)
Kernel-level global shortcut detection (`evdev`) requires membership in the `input` group:
```bash
sudo usermod -aG input $USER
```
> If newly added to the `input` group, log out and log back in to apply changes.

### macOS (Accessibility Permissions)
macOS requires Accessibility permissions for global shortcut detection and text injection. If prompted, grant permission in:
> **System Settings → Privacy & Security → Accessibility**

### Windows
Runs out of the box with standard user permissions. Windows 11 on ARM is supported via built-in x64 emulation.

---

## Contributing & Reporting Issues

We welcome community contributions, bug reports, and feedback!

### Reporting a Bug or Requesting a Feature
1. Head to [GitHub Issues](https://github.com/BheeshamKS/FreeFlow/issues).
2. Click **New Issue** and select either **Bug Report** or **Feature Request**.
3. For bugs, please include your OS (distro/version), display session (Wayland/X11), and any relevant lines from your log file (`/tmp/freeflow.log` on Linux/macOS or `%TEMP%\freeflow.log` on Windows).

### Contributing Code
1. Fork the repository and clone your fork.
2. Create a feature branch: `git checkout -b feature/my-new-feature`.
3. Commit your changes: `git commit -m "feat: description of improvement"`.
4. Push to your fork and submit a Pull Request.

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

---

## License

Released under the [MIT License](LICENSE).
