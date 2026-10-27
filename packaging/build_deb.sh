#!/usr/bin/env bash
# ==============================================================================
# FreeFlow Debian/Ubuntu (.deb) Package Generator
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="${1:-1.2.2}"
ARCH="amd64"
DIST_DIR="${ROOT_DIR}/dist"
PKG_DIR="/tmp/freeflow_deb_build/freeflow_${VERSION}_${ARCH}"

echo "[INFO] Packaging FreeFlow ${VERSION} for Debian/Ubuntu (${ARCH})..."

# Ensure dist/freeflow exists
if [ ! -d "${DIST_DIR}/freeflow" ]; then
    echo "[ERROR] ${DIST_DIR}/freeflow not found. Build binary first with PyInstaller."
    exit 1
fi

rm -rf "/tmp/freeflow_deb_build"
mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/opt/freeflow"
mkdir -p "${PKG_DIR}/usr/bin"
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/usr/share/icons/hicolor/512x512/apps"

chmod 755 "${PKG_DIR}"
chmod 755 "${PKG_DIR}/DEBIAN"

# 1. Copy application bundle
cp -r "${DIST_DIR}/freeflow/"* "${PKG_DIR}/opt/freeflow/"

# 2. Symlink launcher
cat << 'EOF' > "${PKG_DIR}/usr/bin/freeflow"
#!/bin/sh
exec /opt/freeflow/freeflow "$@"
EOF
chmod 755 "${PKG_DIR}/usr/bin/freeflow"

# 3. Desktop entry
cat << 'EOF' > "${PKG_DIR}/usr/share/applications/freeflow.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=FreeFlow
GenericName=Voice Dictation Platform
Comment=Sub-second native voice-to-text dictation
Exec=/usr/bin/freeflow %u
Icon=freeflow
Terminal=false
Categories=Utility;AudioVideo;Audio;Office;Accessibility;
Keywords=voice;dictation;whisper;groq;speech-to-text;transcription;
StartupNotify=true
StartupWMClass=freeflow
EOF
chmod 644 "${PKG_DIR}/usr/share/applications/freeflow.desktop"

# 4. Icon
cp "${ROOT_DIR}/assets/icon.png" "${PKG_DIR}/usr/share/icons/hicolor/512x512/apps/freeflow.png"
chmod 644 "${PKG_DIR}/usr/share/icons/hicolor/512x512/apps/freeflow.png"

# 5. Control file
cat << EOF > "${PKG_DIR}/DEBIAN/control"
Package: freeflow
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: BheeshamKS <bheeshamkumarsajnani3@gmail.com>
Depends: libportaudio2, libnotify-bin, xclip, xdotool
Recommends: wl-clipboard, wtype
Description: Sub-second voice dictation for Linux desktops
 FreeFlow brings instant voice-to-text dictation to Linux desktops,
 powered by Groq Whisper Large v3 LPU inference.
EOF
chmod 644 "${PKG_DIR}/DEBIAN/control"

# 6. Post-install script
cat << 'EOF' > "${PKG_DIR}/DEBIAN/postinst"
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi
exit 0
EOF
chmod 755 "${PKG_DIR}/DEBIAN/postinst"

# 7. Build DEB package
DEB_FILE="${DIST_DIR}/freeflow_${VERSION}_${ARCH}.deb"
dpkg-deb --build --root-owner-group "${PKG_DIR}" "${DEB_FILE}"

rm -rf "/tmp/freeflow_deb_build"
echo "[OK] Debian package generated successfully: ${DEB_FILE}"
