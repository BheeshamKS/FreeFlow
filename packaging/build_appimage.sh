#!/usr/bin/env bash
# ==============================================================================
# FreeFlow Linux AppImage Generator
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="1.0.0"
APP_DIR="${ROOT_DIR}/build/AppDir"
DIST_DIR="${ROOT_DIR}/dist"

echo "[INFO] Packaging FreeFlow ${VERSION} as Linux AppImage..."

if [ ! -d "${DIST_DIR}/freeflow" ]; then
    echo "[ERROR] ${DIST_DIR}/freeflow not found. Build binary first with PyInstaller."
    exit 1
fi

rm -rf "${APP_DIR}"
mkdir -p "${APP_DIR}/usr/bin"
mkdir -p "${APP_DIR}/usr/lib"
mkdir -p "${APP_DIR}/opt/freeflow"

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

# 3. Desktop Entry and Icon in AppDir root
cp "${ROOT_DIR}/freeflow.desktop" "${APP_DIR}/freeflow.desktop"
cp "${ROOT_DIR}/assets/icon.png" "${APP_DIR}/freeflow.png"
cp "${ROOT_DIR}/assets/icon.png" "${APP_DIR}/.DirIcon"

# 4. Check for appimagetool or download if in CI
OUTPUT_APPIMAGE="${DIST_DIR}/FreeFlow-${VERSION}-x86_64.AppImage"

if command -v appimagetool >/dev/null 2>&1; then
    appimagetool "${APP_DIR}" "${OUTPUT_APPIMAGE}"
    echo "[OK] AppImage generated at ${OUTPUT_APPIMAGE}"
else
    # Create portable compressed archive fallback
    PORTABLE_TAR="${DIST_DIR}/FreeFlow-${VERSION}-linux-x86_64.tar.gz"
    tar -czf "${PORTABLE_TAR}" -C "${DIST_DIR}" freeflow
    echo "[OK] Created portable standalone bundle: ${PORTABLE_TAR}"
    echo "[NOTE] Install appimagetool to generate a self-mounting single-file AppImage."
fi
