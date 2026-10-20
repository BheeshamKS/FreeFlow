# Contributing to FreeFlow

We welcome contributions of all kinds: bug fixes, platform improvements, UI polish, documentation, and feature enhancements.

---

## Reporting Issues & Bugs

If you find a bug or have a suggestion:

1. **Check Existing Issues**: Search the [GitHub Issue Tracker](https://github.com/BheeshamKS/FreeFlow/issues) to see if it has already been reported.
2. **Submit a New Issue**: Use our [Bug Report Template](https://github.com/BheeshamKS/FreeFlow/issues/new?template=bug_report.md) or [Feature Request Template](https://github.com/BheeshamKS/FreeFlow/issues/new?template=feature_request.md).
3. **Include Diagnostics**:
   - Operating system & version (Linux distro, Windows version, macOS version).
   - Display server (Wayland vs. X11 on Linux).
   - Relevant log entries from `/tmp/freeflow.log` (Linux/macOS) or `%TEMP%\freeflow.log` (Windows).

---

## Local Development Setup

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/<your-username>/FreeFlow.git
   cd FreeFlow
   ```

2. **Set up Environment**:
   - **Linux**: `./setup.sh`
   - **macOS**: `./setup-mac.sh`
   - **Windows**: `.\setup.ps1`

3. **Run Application from Source**:
   ```bash
   .venv/bin/python app.py            # Linux / macOS
   .\.venv\Scripts\python.exe app.py  # Windows
   ```

---

## Pull Request Guidelines

1. **Branch Naming**:
   - `feature/your-feature-name`
   - `fix/issue-description`
   - `docs/clarify-readme`

2. **Commit Convention**:
   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: add push-to-talk indicator`
   - `fix: resolve Wayland wtype modifier delay`
   - `docs: update Windows setup guide`

3. **Code Style**:
   - Follow PEP 8 guidelines.
   - Maintain the Linear/Raycast dark design aesthetic for any UI contributions.
   - Test changes across supported platforms whenever possible.

4. **Submit PR**: Open a pull request against `main` and link any related issues (`Fixes #123`).
