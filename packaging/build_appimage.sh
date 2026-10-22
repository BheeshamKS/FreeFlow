#!/usr/bin/env bash
# ==============================================================================
# FreeFlow Linux AppImage Generator
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="${1:-1.2.1}"
APP_DIR="/tmp/freeflow_appimage_build/AppDir"
DIST_DIR="${ROOT_DIR}/dist"

echo "[INFO] Packaging FreeFlow ${VERSION} as Linux AppImage..."

if [ ! -d "${DIST_DIR}/freeflow" ]; then
    echo "[ERROR] ${DIST_DIR}/freeflow not found. Build binary first with PyInstaller."
    exit 1
fi

rm -rf "/tmp/freeflow_appimage_build"
mkdir -p "${APP_DIR}/usr/bin"
mkdir -p "${APP_DIR}/usr/lib"
mkdir -p "${APP_DIR}/opt/freeflow"
mkdir -p "${APP_DIR}/usr/share/icons/hicolor/512x512/apps"
mkdir -p "${APP_DIR}/usr/share/applications"

# 1. Copy application files
cp -r "${DIST_DIR}/freeflow/"* "${APP_DIR}/opt/freeflow/"

# 2. AppRun entrypoint
cat << 'EOF' > "${APP_DIR}/AppRun"
#!/bin/sh
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${HERE}/opt/freeflow:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${HERE}/opt/freeflow:${LD_LIBRARY_PATH}"
export PYTHONHOME="${HERE}/opt/freeflow"
exec "${HERE}/opt/freeflow/freeflow" "$@"
EOF
chmod 755 "${APP_DIR}/AppRun"

# 3. Desktop Entry and Icon in AppDir root (standard AppImage spec)
cp "${ROOT_DIR}/freeflow.desktop" "${APP_DIR}/freeflow.desktop"
cp "${ROOT_DIR}/freeflow.desktop" "${APP_DIR}/usr/share/applications/freeflow.desktop"

# Standard icon naming matching Icon=freeflow
cp "${ROOT_DIR}/assets/icon.png" "${APP_DIR}/freeflow.png"
cp "${ROOT_DIR}/assets/icon.png" "${APP_DIR}/.DirIcon"
cp "${ROOT_DIR}/assets/icon.png" "${APP_DIR}/usr/share/icons/hicolor/512x512/apps/freeflow.png"

OUTPUT_APPIMAGE="${DIST_DIR}/FreeFlow-${VERSION}-x86_64.AppImage"

# 4. Check for appimagetool or download
TOOL_PATH=""
if command -v appimagetool >/dev/null 2>&1; then
    TOOL_PATH="appimagetool"
elif [ -f "${ROOT_DIR}/appimagetool-x86_64.AppImage" ]; then
    TOOL_PATH="${ROOT_DIR}/appimagetool-x86_64.AppImage"
else
    echo "[INFO] Downloading appimagetool..."
    curl -sL https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage -o /tmp/appimagetool
    chmod +x /tmp/appimagetool
    TOOL_PATH="/tmp/appimagetool"
fi

echo "[INFO] Running ${TOOL_PATH} to generate ${OUTPUT_APPIMAGE}..."
ARCH=x86_64 "${TOOL_PATH}" --appimage-extract-and-run "${APP_DIR}" "${OUTPUT_APPIMAGE}"
chmod +x "${OUTPUT_APPIMAGE}"

echo "[OK] AppImage generated successfully: ${OUTPUT_APPIMAGE}"

# Also generate portable tarball
PORTABLE_TAR="${DIST_DIR}/FreeFlow-${VERSION}-linux-x86_64.tar.gz"
echo "[INFO] Creating portable archive: ${PORTABLE_TAR}..."
tar -czf "${PORTABLE_TAR}" -C "${DIST_DIR}" freeflow
echo "[OK] Standalone tarball ready: ${PORTABLE_TAR}"

rm -rf "/tmp/freeflow_appimage_build"
