#!/usr/bin/env bash
# ==============================================================================
# FreeFlow macOS DMG & App Bundle Generator
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VERSION="1.0.0"
DIST_DIR="${ROOT_DIR}/dist"
APP_NAME="FreeFlow.app"

echo "[INFO] Packaging FreeFlow ${VERSION} for macOS..."

if [ ! -d "${DIST_DIR}/${APP_NAME}" ] && [ ! -d "${DIST_DIR}/freeflow" ]; then
    echo "[ERROR] Application bundle not found in ${DIST_DIR}. Run PyInstaller with --windowed first."
    exit 1
fi

DMG_OUTPUT="${DIST_DIR}/FreeFlow-${VERSION}-macOS.dmg"

# Check if create-dmg is available
if command -v create-dmg >/dev/null 2>&1; then
    create-dmg \
      --volname "FreeFlow Installer" \
      --window-pos 200 120 \
      --window-size 600 400 \
      --icon-size 100 \
      --icon "${APP_NAME}" 175 120 \
      --hide-extension "${APP_NAME}" \
      --app-drop-link 425 120 \
      "${DMG_OUTPUT}" \
      "${DIST_DIR}/${APP_NAME}"
    echo "[OK] Generated macOS DMG: ${DMG_OUTPUT}"
elif command -v hdiutil >/dev/null 2>&1; then
    # Fallback native macOS disk image creation
    hdiutil create -volname "FreeFlow" -srcfolder "${DIST_DIR}/${APP_NAME}" -ov -format UDZO "${DMG_OUTPUT}"
    echo "[OK] Generated macOS DMG via hdiutil: ${DMG_OUTPUT}"
else
    # Fallback compressed tarball
    TAR_OUTPUT="${DIST_DIR}/FreeFlow-${VERSION}-macOS.tar.gz"
    tar -czf "${TAR_OUTPUT}" -C "${DIST_DIR}" "${APP_NAME:-freeflow}"
    echo "[OK] Created portable macOS archive: ${TAR_OUTPUT}"
fi
