---
name: freeflow-lead
description: FreeFlow primary self-operating skill for Antigravity. Enforces automatic activation of the core skill suite on every prompt, coordinates bug diagnosis, implementation, design taste, security hardening, testing, and maintains cumulative release history and bug fixes across all versions.
---

# FreeFlow Lead Engineer & Orchestrator Skill

This is the primary self-operating skill for **FreeFlow**. It establishes standard protocols for feature delivery, bug diagnosis, UI design taste, quality assurance, release tracking, and git hygiene.

---

## 1. Mandatory Skills Execution Matrix

In **every prompt and user task**, the agent must systematically activate, consult, and execute the relevant specialized skills from this suite:

| Skill | Category | Mandatory Trigger & Usage |
| :--- | :--- | :--- |
| **`/implement`** | Architecture & Code | Primary feature implementation, module creation, and code writing. |
| **`/diagnosing-bugs`** | Debugging | Deep root-cause diagnosis, creating failing minimal test loops before attempting fixes. |
| **`/troubleshoot`** | Triage | Systematic triage of build failures, runtime exceptions, and platform incompatibilities. |
| **`/security-and-hardening`** | Security | Automatic redaction of API keys (`gsk_...`) and tokens, input sanitization, and safe subprocess execution. |
| **`/design-taste-frontend`** | Art Direction | Enforcing dark frosted obsidian aesthetics, clean typography, and zero-slop UI design. |
| **`/generative_ui`** | Visual Widgets | Rendering interactive UI widgets, live waveform visualizers, and structured modal guides. |
| **`/frontend-visual-qa`** | Visual Testing | Verifying HUD capsule, dialog geometries, text alignment, and cross-platform display scaling. |
| **`/ui-test`** | UI Test Automation | Headless Qt (`offscreen`) testing, mouse click simulation, and signal/slot verification. |
| **`/code-documenter`** | Code Docs | Clean docstrings, architectural type hints, and code comments. |
| **`/document`** | Technical Writing | Updating README, architectural overviews, and platform installation guides. |
| **`/documenter`** | User Documentation | User guides, troubleshooting documentation, and user-facing instructions. |
| **`/banana`** | Design Assets | Iconography, button pills, color systems, and visual asset generation. |
| **`/git-workflow-manager`** | Git Workflow | Enforcing git author identity, atomic commit shapes, and release tag hygiene. |
| **`/multi-agent-coordinator`** | Agent Coordination | Orchestrating parallel research, debugging, and multi-file code modifications. |
| **`/find-skills`** | Tool Discovery | Discovering and activating complementary specialized skills when needed. |
| **`/finalize`** | Release Quality Gate | Full verification, running unit test suites, updating changelogs, and pushing clean tags. |

---

## 2. Release Management & History Tracking Protocol

> [!IMPORTANT]
> **Mandatory Rule for Every Release:**
> In **every new release**, the agent MUST:
> 1. **Clean Release Name & GitHub Changelog**:
>    The release name on GitHub must ALWAYS be clean and formatted strictly as:
>    `FreeFlow <version>` (e.g. `FreeFlow v1.0.0`, `FreeFlow v1.2.1`).
>    Execute `gh release edit <tag> --repo BheeshamKS/FreeFlow --title "FreeFlow <version>" --notes "..."` with the full, formatted summary of all newly added features, bug fixes, and test results. Never leave a release with default or blank changelogs.
> 2. **Update this Skill File** (`.agents/skills/freeflow-lead/SKILL.md`) with the new version and chronological release summary.
> 3. **Update [`CHANGELOG.md`](file:///CHANGELOG.md)** adhering to the Keep a Changelog standard.
> 4. Ensure all automated unit and integration tests pass cleanly before publishing.

### Cumulative Release Log

#### Version 1.2.2 (2026-10-27) — Audio Recovery Buffer, Background Boot Startup & Launcher Activation
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
- **Audio Preservation & Zero-Loss Recovery Buffer**:
  - Recorded audio from long dictations (e.g., 5–10+ minutes) is now automatically preserved in a persistent temporary recovery cache (`get_recovery_audio_path()`).
  - If transcription fails due to network dropouts, firewall blocks, or Groq API rate limits, the recorded audio is never lost.
  - Added interactive **"Retry Transcription with Saved Audio"** affordances across:
    - **Floating HUD Capsule**: Contextual `[🔁 Retry]` button appears directly alongside `[Solutions →]` in error state.
    - **Troubleshooting & Solutions Dialog**: Dedicated **Saved Audio Recovered** card displaying recording duration and file size, with direct `[🔁 Retry Transcription Now]` and `[💾 Export Audio (.wav)...]` actions.
    - **System Tray Menu**: Dynamic `🔁 Retry Last Audio Transcription (Mm SSs)...` context menu action.
    - **Dashboard Hero Card**: Obsidian emerald retry button appearing immediately under the Voice Orb when recovery audio is cached.
- **Quality Gate**: 37 automated unit and integration tests passing.

#### Version 1.2.1 (2026-10-23) — Diagnostics, View Solutions & Smart Text Box Detection
- **Common Troubleshooting & Help Guide**:
  - Replaced the permanent "Transcription Error Encountered" state with a browsable **Common Troubleshooting & Help** guide accessible from Settings and the System Tray.
  - Interactive topic navigation pills:
    - 🔑 **API Key**: Obtaining free keys from Groq Console, format validation, and testing connection.
    - 🌐 **Firewall & Network**: Windows Defender / Antivirus outbound rule guidance, proxies, and HTTPS connectivity.
    - 🎙️ **Microphone**: Input hardware selection, unmuting, and system permissions.
    - 📋 **Clipboard**: Automatic active text box paste vs. desktop fallback behavior.
    - ⏱️ **Rate Limits**: Quotas, cooldowns, and speech recognition model switching.
  - **On-Demand Error Flow Simulator**: Added a `[🧪 Test Error Flow ▾]` menu directly inside the troubleshooting dialog allowing users to simulate errors (API key, Network, Microphone) and verify the HUD capsule and desktop notification flows on demand.
- **Dynamic Context-Aware Error Solutions**:
  - When an error occurs during dictation, the HUD capsule presents `[View Solutions →]`, opening the guide directly focused on the active issue.
  - Closing or accessing the menu later restores the clean, common guide without permanently showing past errors.
- **Smart Active Text Box Detection & Clipboard Fallback**:
  - Cross-platform active input field detection (`core/injector.py`) across Windows (`GetGUIThreadInfo`), macOS (`AXFocusedUIElement`), and Linux (desktop/dock filtering).
  - **If active text box is focused**: Injects text directly into the focused field and restores the user's prior clipboard buffer (transcribed text is NOT left on the clipboard).
  - **If no text box is focused**: Avoids blind keystroke emission, copies transcribed text directly to the system clipboard, and displays `"Copied to clipboard (no text box active)"` on the HUD capsule.
- **Quality Gate**: 30 automated unit and integration tests passing.

#### Version 1.2.0 (2026-10-23) — Audio Input Selection & GitHub Auto-Updater
- **Audio Input Device (Microphone) Selection**:
  - Added microphone hardware device selection in Preferences and the Hub window.
  - Real-time device scanner (`[Refresh Devices]`) powered by `sounddevice`.
  - Added `NoScrollComboBox` preventing accidental wheel-scrolling of settings dropdowns.
- **Automated GitHub Release Auto-Updater**:
  - Background startup checks querying GitHub Releases API.
  - Two modes: **Auto-Update** (background download + prompt to restart app) and **Ask Before Updating** (notification with one-click update).
  - In-place self-replacement across Linux (.AppImage & Git), Windows (Setup EXE), and macOS.
- **Startup Minimize on Boot Fix**:
  - Resolved bug where FreeFlow popped up on boot even when "Start minimized to system tray on boot" was enabled.
  - Unified autostart engine (`core/autostart.py`) passing `--autostart` and `--minimized`.
- **UI Streamlining**:
  - Removed noisy recording notifications; removed Quit/Wizard buttons from sidebar; added Quit button to bottom of Settings; added silent instant auto-save.

#### Version 1.1.0 (2026-10-21) — Multi-Platform Cross-Packaging
- **Cross-Platform Releases**:
  - Native Windows executable and Inno Setup installer (`FreeFlow-Setup-Windows.exe`).
  - Native macOS application bundle and disk image (`FreeFlow-1.1.0-macOS.dmg`).
  - Official Linux AppImage portable bundle (`FreeFlow-1.1.0-x86_64.AppImage`).
- **CI/CD Pipeline**: Multi-platform automated GitHub Actions workflow.

#### Version 1.0.0 (2026-10-21) — Initial Public Release
- **Push-to-Talk Speech-to-Text**:
  - High-speed Whisper transcription via Groq Cloud API.
  - Optional LLM post-processing for grammar and filler word removal.
  - Floating ambient HUD capsule with harmonic audio waveforms.
  - Single-instance IPC protection and system tray integration.

---

## 3. Engineering Guidelines & Constraints

### Git Identity & Author Verification
All commits in this repository must strictly adhere to:
- **Author**: `BheeshamKS <bheehamkumarsajnani3@gmail.com>`
- **Command Flag**: `--author="BheeshamKS <bheehamkumarsajnani3@gmail.com>"`

### Security & Secret Protection
- Never hardcode or display user API keys. Always redact strings matching `gsk_[a-zA-Z0-9_-]+` to `gsk_<REDACTED_API_KEY>`.
- Sanitize home directory paths in diagnostics and logs before embedding in GitHub issues.

### Quality Verification
Before completing any task or cutting a release:
- Run the full test suite in offscreen mode:
  ```bash
  QT_QPA_PLATFORM=offscreen .venv/bin/python3 -m unittest tests/test_features.py
  ```
- Ensure zero failing tests and clean imports.
