#!/usr/bin/env bash
# ==============================================================================
# FreeFlow macOS DMG & App Bundle Generator
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VERSION="${1:-1.2.1}"
DIST_DIR="${ROOT_DIR}/dist"
APP_NAME="FreeFlow.app"

echo "[INFO] Packaging FreeFlow ${VERSION} for macOS..."

APP_PATH=""
if [ -d "${DIST_DIR}/${APP_NAME}" ]; then
    APP_PATH="${DIST_DIR}/${APP_NAME}"
elif [ -d "${DIST_DIR}/freeflow" ]; then
    APP_PATH="${DIST_DIR}/freeflow"
else
    echo "[ERROR] Application bundle not found in ${DIST_DIR}."
    exit 1
fi

DMG_OUTPUT="${DIST_DIR}/FreeFlow-${VERSION}-macOS.dmg"

# 1. Native macOS disk image creation via hdiutil (100% reliable)
if command -v hdiutil >/dev/null 2>&1; then
    echo "[INFO] Creating macOS DMG disk image via hdiutil..."
    rm -f "${DMG_OUTPUT}"
    hdiutil create -volname "FreeFlow" -srcfolder "${APP_PATH}" -ov -format UDZO "${DMG_OUTPUT}"
    echo "[OK] Generated macOS DMG: ${DMG_OUTPUT}"
fi

# 2. Also create portable compressed archive
TAR_OUTPUT="${DIST_DIR}/FreeFlow-${VERSION}-macOS-universal.tar.gz"
echo "[INFO] Creating portable macOS tarball..."
tar -czf "${TAR_OUTPUT}" -C "${DIST_DIR}" "${APP_NAME}" 2>/dev/null || tar -czf "${TAR_OUTPUT}" -C "${DIST_DIR}" freeflow
echo "[OK] Created portable macOS archive: ${TAR_OUTPUT}"
