#!/usr/bin/env bash
# ==============================================================================
# FreeFlow Linux — Automated Production Setup & Dependency Installer
# ==============================================================================
# Configures system-level libraries, virtual environment, desktop integration,
# evdev permissions, and systemd user daemon for Ubuntu/Debian, Arch, and Fedora.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
CONFIG_DIR="${HOME}/.config/freeflow"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
APPLICATIONS_DIR="${HOME}/.local/share/applications"

# Color formatting
BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
CYAN="\033[36m"
RED="\033[31m"
RESET="\033[0m"

log_info()  { echo -e "${CYAN}[INFO]${RESET} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${RESET} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${RESET} $*"; }
log_err()   { echo -e "${RED}[ERROR]${RESET} $*"; }

echo -e "\n${BOLD}${CYAN}==============================================================================${RESET}"
echo -e "${BOLD}${CYAN}            FreeFlow for Linux — Setup & Deployment Installer                 ${RESET}"
echo -e "${BOLD}${CYAN}==============================================================================${RESET}\n"

# ------------------------------------------------------------------------------
# 1. Detect Package Manager & Distro
# ------------------------------------------------------------------------------
log_info "Detecting Linux distribution and package manager..."

INSTALL_CMD=""
SYS_PACKAGES=()

if command -v apt-get &>/dev/null; then
    DISTRO="Debian/Ubuntu"
    INSTALL_CMD="sudo apt-get update && sudo apt-get install -y"
    SYS_PACKAGES=(
        python3 python3-venv python3-pip python3-dev
        libportaudio2 portaudio19-dev
        libnotify-bin
        xdotool xclip
        wtype wl-clipboard
        libxcb-cursor0 libxcb-xinerama0
    )
elif command -v pacman &>/dev/null; then
    DISTRO="Arch Linux"
    INSTALL_CMD="sudo pacman -S --needed --noconfirm"
    SYS_PACKAGES=(
        python python-pip
        portaudio
        libnotify
        xdotool xclip
        wtype wl-clipboard
        xcb-util-cursor
    )
elif command -v dnf &>/dev/null; then
    DISTRO="Fedora/RHEL"
    INSTALL_CMD="sudo dnf install -y"
    SYS_PACKAGES=(
        python3 python3-devel python3-pip
        portaudio-devel
        libnotify
        xdotool xclip
        wl-clipboard
    )
elif command -v zypper &>/dev/null; then
    DISTRO="openSUSE"
    INSTALL_CMD="sudo zypper --non-interactive install"
    SYS_PACKAGES=(
        python3 python3-devel python3-pip
        portaudio-devel
        libnotify-tools
        xdotool xclip
        wl-clipboard
        libxcb-cursor0
    )
elif command -v apk &>/dev/null; then
    DISTRO="Alpine Linux"
    INSTALL_CMD="sudo apk add"
    SYS_PACKAGES=(
        python3 py3-pip python3-dev
        portaudio-dev
        libnotify
        xdotool xclip
        wl-clipboard
    )
elif command -v xbps-install &>/dev/null; then
    DISTRO="Void Linux"
    INSTALL_CMD="sudo xbps-install -Sy"
    SYS_PACKAGES=(
        python3 python3-pip python3-devel
        portaudio-devel
        libnotify
        xdotool xclip
        wl-clipboard
    )
else
    DISTRO="Generic Linux"
    log_warn "Unknown package manager. Please ensure PortAudio, xdotool/wtype, and wl-clipboard are installed."
fi

log_ok "Detected environment: ${DISTRO}"

# ------------------------------------------------------------------------------
# 2. Install System Dependencies
# ------------------------------------------------------------------------------
if [ -n "${INSTALL_CMD}" ]; then
    log_info "Installing system packages: ${SYS_PACKAGES[*]}"
    if ! ${INSTALL_CMD} "${SYS_PACKAGES[@]}"; then
        log_warn "Some system packages could not be installed automatically via sudo."
        log_warn "Continuing with Python setup. You may need to install missing packages manually."
    else
        log_ok "System packages installed successfully."
    fi
fi

# ------------------------------------------------------------------------------
# 3. Configure Input Group Permissions (for evdev kernel input reading)
# ------------------------------------------------------------------------------
log_info "Verifying hardware input group permissions..."
CURRENT_USER="$(whoami)"

if id -nG "$CURRENT_USER" | grep -qw "input"; then
    log_ok "User '$CURRENT_USER' is already a member of the 'input' group."
else
    log_info "Adding user '$CURRENT_USER' to 'input' group for global hotkey support..."
    if sudo usermod -aG input "$CURRENT_USER"; then
        log_ok "Added '$CURRENT_USER' to 'input' group."
        NEED_RELOGIN=1
    else
        log_warn "Could not add user to 'input' group. You may need to run: sudo usermod -aG input $CURRENT_USER"
    fi
fi

# ------------------------------------------------------------------------------
# 4. Create and Configure Python Virtual Environment
# ------------------------------------------------------------------------------
log_info "Setting up Python virtual environment at ${VENV_DIR}..."

if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
    log_ok "Created virtual environment."
else
    log_ok "Existing virtual environment found."
fi

VENV_PYTHON="${VENV_DIR}/bin/python3"
VENV_PIP="${VENV_DIR}/bin/pip"

log_info "Upgrading pip and installing required Python packages..."
"${VENV_PIP}" install --upgrade pip setuptools wheel --quiet
"${VENV_PIP}" install -r "${SCRIPT_DIR}/requirements.txt" --quiet
log_ok "Python dependencies installed successfully."

# ------------------------------------------------------------------------------
# 5. Generate Application Icons & Assets
# ------------------------------------------------------------------------------
log_info "Verifying application icon assets..."
mkdir -p "${SCRIPT_DIR}/assets"

if [ ! -f "${SCRIPT_DIR}/assets/icon.png" ]; then
    "${VENV_PYTHON}" - << 'EOF'
import os
from PIL import Image, ImageDraw

assets = "/mnt/SSD_Storage/Coding/FreeFlow/assets"
os.makedirs(assets, exist_ok=True)

def create_icon(fg, bg, name):
    img = Image.new("RGBA", (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 124, 124], fill=bg, outline=(255,255,255,40), width=2)
    d.rounded_rectangle([48, 28, 80, 72], radius=16, fill=fg)
    d.arc([38, 45, 90, 85], start=0, end=180, fill=fg, width=6)
    d.line([64, 85, 64, 102], fill=fg, width=6)
    d.line([48, 102, 80, 102], fill=fg, width=6)
    img.save(os.path.join(assets, name))

create_icon((0, 225, 175, 255), (24, 28, 38, 255), "icon.png")
create_icon((255, 59, 48, 255), (38, 18, 20, 255), "icon_recording.png")
create_icon((255, 179, 0, 255), (36, 30, 18, 255), "icon_processing.png")
print("Assets verified.")
EOF
fi
log_ok "Icon assets are ready."

# ------------------------------------------------------------------------------
# 6. Setup Configuration Directory
# ------------------------------------------------------------------------------
mkdir -p "${CONFIG_DIR}"
if [ ! -f "${CONFIG_DIR}/.env" ] && [ -f "${SCRIPT_DIR}/.env.example" ]; then
    cp "${SCRIPT_DIR}/.env.example" "${CONFIG_DIR}/.env"
    log_ok "Created configuration template at ${CONFIG_DIR}/.env"
fi

# ------------------------------------------------------------------------------
# 7. Desktop Application Launcher Integration
# ------------------------------------------------------------------------------
log_info "Installing desktop launcher (.desktop file)..."
mkdir -p "${APPLICATIONS_DIR}"

DESKTOP_FILE="${APPLICATIONS_DIR}/freeflow.desktop"
cat << EOF > "${DESKTOP_FILE}"
[Desktop Entry]
Name=FreeFlow
Comment=High-speed speech-to-text dictation application
Exec=${VENV_PYTHON} ${SCRIPT_DIR}/app.py
Icon=${SCRIPT_DIR}/assets/icon.png
Terminal=false
Type=Application
Categories=Utility;Audio;AudioVideo;Accessibility;
StartupNotify=false
Keywords=whisper;voice;dictation;speech;transcription;groq;freeflow;
EOF

chmod +x "${DESKTOP_FILE}"
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "${APPLICATIONS_DIR}" &>/dev/null || true
fi
log_ok "Desktop launcher installed at ${DESKTOP_FILE}"

# ------------------------------------------------------------------------------
# 8. Configure Systemd User Service (Background Daemon)
# ------------------------------------------------------------------------------
log_info "Configuring systemd user service for background execution..."
mkdir -p "${SYSTEMD_USER_DIR}"

SERVICE_FILE="${SYSTEMD_USER_DIR}/freeflow.service"
cat << EOF > "${SERVICE_FILE}"
[Unit]
Description=FreeFlow Voice Dictation Service
Documentation=https://github.com/BheeshamKS/FreeFlow
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=${VENV_PYTHON} ${SCRIPT_DIR}/app.py --minimized
WorkingDirectory=${SCRIPT_DIR}
Environment=PYTHONUNBUFFERED=1
Environment=DISPLAY=:0
Environment=WAYLAND_DISPLAY=wayland-0
Restart=on-failure
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical-session.target
EOF

if command -v systemctl &>/dev/null; then
    systemctl --user daemon-reload
    log_ok "Systemd user service installed at ${SERVICE_FILE}"
fi

# ------------------------------------------------------------------------------
# 9. Launch FreeFlow in Setup Mode
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${GREEN}==============================================================================${RESET}"
echo -e "${BOLD}${GREEN}                     FreeFlow Setup Completed Successfully!                   ${RESET}"
echo -e "${BOLD}${GREEN}==============================================================================${RESET}\n"

if [ -n "${DISPLAY}" ] || [ -n "${WAYLAND_DISPLAY}" ]; then
    log_info "Opening FreeFlow Setup Wizard in setup mode..."
    nohup "${VENV_PYTHON}" "${SCRIPT_DIR}/app.py" --setup >/dev/null 2>&1 &
    disown
    log_ok "FreeFlow Setup Wizard launched."
else
    log_warn "No graphical display detected (\$DISPLAY / \$WAYLAND_DISPLAY)."
    log_info "Launch FreeFlow in setup mode with: ${CYAN}${VENV_PYTHON} ${SCRIPT_DIR}/app.py --setup${RESET}"
fi

echo -e "\nDesktop Integration Summary:"
echo -e "  • ${BOLD}Application Launcher:${RESET} Search for 'FreeFlow' in your application menu."
echo -e "  • ${BOLD}Global Shortcut:${RESET} Press ${CYAN}Alt + R${RESET} from any window to dictate."
echo -e "  • ${BOLD}Setup Wizard:${RESET} Run ${CYAN}${VENV_PYTHON} ${SCRIPT_DIR}/app.py --setup${RESET} anytime."
echo -e "  • ${BOLD}Autostart Daemon:${RESET} Run ${CYAN}systemctl --user enable --now freeflow.service${RESET}\n"

if [ "${NEED_RELOGIN}" = "1" ]; then
    echo -e "  ${YELLOW}${BOLD}[IMPORTANT NOTE]${RESET}"
    echo -e "  Your user was added to the 'input' group. Please ${BOLD}log out and log back in${RESET}"
    echo -e "  (or run 'newgrp input') so your session picks up the new global hotkey permissions.\n"
fi
