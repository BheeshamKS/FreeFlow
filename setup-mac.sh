#!/usr/bin/env bash
# ==============================================================================
# FreeFlow for macOS — Automated Setup & Dependency Installer
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
CONFIG_DIR="${HOME}/Library/Application Support/FreeFlow"

# Color formatting
BOLD="\033[1m"
GREEN="\033[32m"
CYAN="\033[36m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"

log_info() { echo -e "${CYAN}[INFO]${RESET} $*"; }
log_ok()   { echo -e "${GREEN}[OK]${RESET} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${RESET} $*"; }
log_err()  { echo -e "${RED}[ERROR]${RESET} $*"; }

echo -e "\n${BOLD}${CYAN}==============================================================================${RESET}"
echo -e "${BOLD}${CYAN}             FreeFlow for macOS — Setup & Deployment Installer                ${RESET}"
echo -e "${BOLD}${CYAN}==============================================================================${RESET}\n"

# 1. Check Homebrew & system audio dependencies
if command -v brew &>/dev/null; then
    log_info "Homebrew detected. Checking audio dependencies (portaudio, ffmpeg)..."
    brew install portaudio ffmpeg 2>/dev/null || true
    log_ok "Audio tools verified."
else
    log_warn "Homebrew not found. If audio capture encounters issues, install Homebrew from https://brew.sh and run 'brew install portaudio ffmpeg'."
fi

# 2. Check Python 3.10+
log_info "Verifying Python 3 installation..."
PYTHON_BIN=""
for candidate in python3 python3.12 python3.11 python3.10 python; do
    if command -v "$candidate" &>/dev/null; then
        PY_VER=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        MAJOR=$(echo "$PY_VER" | cut -d. -f1)
        MINOR=$(echo "$PY_VER" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    log_err "Python 3.10 or higher is required. Please install Python via 'brew install python' or python.org."
    exit 1
fi
log_ok "Using Python $($PYTHON_BIN --version) ($PYTHON_BIN)"

# 3. Create Virtual Environment
log_info "Setting up Python virtual environment at ${VENV_DIR}..."
if [ ! -d "${VENV_DIR}" ]; then
    "$PYTHON_BIN" -m venv "${VENV_DIR}"
fi
VENV_PYTHON="${VENV_DIR}/bin/python3"
VENV_PIP="${VENV_DIR}/bin/pip"
log_ok "Virtual environment configured."

# 4. Install Dependencies
log_info "Installing FreeFlow dependencies..."
"$VENV_PIP" install --upgrade pip --quiet
"$VENV_PIP" install -r "${SCRIPT_DIR}/requirements.txt" --quiet
log_ok "Python packages installed successfully."

# 5. CLI Symlink
mkdir -p "${HOME}/.local/bin"
LAUNCHER="${HOME}/.local/bin/freeflow"
cat << EOF > "$LAUNCHER"
#!/usr/bin/env bash
exec "${VENV_PYTHON}" "${SCRIPT_DIR}/app.py" "\$@"
EOF
chmod +x "$LAUNCHER"
log_ok "CLI launcher installed to ${LAUNCHER}"

# 6. macOS Permissions Reminder
echo -e "\n${BOLD}${YELLOW}[NOTE FOR macOS USERS]${RESET}"
echo -e "FreeFlow uses global shortcuts and keyboard simulation to inject text."
echo -e "If prompted, grant ${BOLD}Accessibility${RESET} permissions in:"
echo -e "  ${CYAN}System Settings → Privacy & Security → Accessibility${RESET}\n"

# 7. Launch FreeFlow in Setup Mode
echo -e "${BOLD}${GREEN}==============================================================================${RESET}"
echo -e "${BOLD}${GREEN} [SUCCESS] FreeFlow installed successfully! Launching Setup Wizard...         ${RESET}"
echo -e "${BOLD}${GREEN}==============================================================================${RESET}\n"

exec "${VENV_PYTHON}" "${SCRIPT_DIR}/app.py" --setup
