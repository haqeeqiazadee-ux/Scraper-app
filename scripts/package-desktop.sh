#!/usr/bin/env bash
# =============================================================================
# package-desktop.sh — Build and package the AI Scraper desktop application
#
# Usage:
#   ./scripts/package-desktop.sh [--skip-frontend] [--debug]
#
# Requirements:
#   - Node.js >= 18
#   - Rust toolchain (rustup + cargo)
#   - Tauri CLI (@tauri-apps/cli v2)
#
# Outputs:
#   dist/desktop/           — Collected build artifacts
#   dist/desktop/checksums.sha256 — SHA-256 checksums of all artifacts
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DESKTOP_DIR="${PROJECT_ROOT}/apps/desktop"
DIST_DIR="${PROJECT_ROOT}/dist/desktop"
SKIP_FRONTEND=false
DEBUG_BUILD=false

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-frontend) SKIP_FRONTEND=true; shift ;;
        --debug)         DEBUG_BUILD=true; shift ;;
        -h|--help)
            echo "Usage: $0 [--skip-frontend] [--debug]"
            echo "  --skip-frontend  Skip the Vite frontend build step"
            echo "  --debug          Build in debug mode (no optimizations)"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()   { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
error() { log "ERROR: $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 1. Validate environment
# ---------------------------------------------------------------------------
log "Validating build environment..."

command -v node  >/dev/null 2>&1 || error "Node.js is not installed"
command -v npm   >/dev/null 2>&1 || error "npm is not installed"
command -v cargo >/dev/null 2>&1 || error "Rust cargo is not installed"
command -v rustc >/dev/null 2>&1 || error "Rust compiler is not installed"

NODE_VERSION=$(node --version | sed 's/^v//')
NODE_MAJOR=$(echo "${NODE_VERSION}" | cut -d. -f1)
if [[ "${NODE_MAJOR}" -lt 18 ]]; then
    error "Node.js >= 18 required (found ${NODE_VERSION})"
fi

log "Node.js: ${NODE_VERSION}"
log "Rust:    $(rustc --version)"
log "Cargo:   $(cargo --version)"

# ---------------------------------------------------------------------------
# 2. Derive version from git tag or package.json
# ---------------------------------------------------------------------------
if git describe --tags --exact-match HEAD 2>/dev/null | grep -q '^v'; then
    VERSION=$(git describe --tags --exact-match HEAD | sed 's/^v//' | sed 's/-desktop$//')
else
    VERSION=$(node -p "require('${DESKTOP_DIR}/package.json').version")
    GIT_SHA=$(git rev-parse --short=8 HEAD 2>/dev/null || echo "unknown")
    VERSION="${VERSION}+${GIT_SHA}"
fi

log "Building version: ${VERSION}"

# ---------------------------------------------------------------------------
# 3. Install dependencies
# ---------------------------------------------------------------------------
log "Installing npm dependencies..."
cd "${DESKTOP_DIR}"
npm ci --prefer-offline 2>/dev/null || npm install

# ---------------------------------------------------------------------------
# 4. Build frontend (Vite)
# ---------------------------------------------------------------------------
if [[ "${SKIP_FRONTEND}" == "false" ]]; then
    log "Building frontend (Vite)..."
    npm run build
else
    log "Skipping frontend build (--skip-frontend)"
fi

# ---------------------------------------------------------------------------
# 5. Build Tauri application
# ---------------------------------------------------------------------------
log "Building Tauri application..."
cd "${DESKTOP_DIR}"

TAURI_ARGS=()
if [[ "${DEBUG_BUILD}" == "true" ]]; then
    TAURI_ARGS+=(--debug)
fi

npx tauri build "${TAURI_ARGS[@]}"

# ---------------------------------------------------------------------------
# 6. Collect artifacts
# ---------------------------------------------------------------------------
log "Collecting artifacts to ${DIST_DIR}..."
rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"

# Tauri outputs to src-tauri/target/release/bundle/
BUNDLE_DIR="${DESKTOP_DIR}/src-tauri/target/release/bundle"
if [[ "${DEBUG_BUILD}" == "true" ]]; then
    BUNDLE_DIR="${DESKTOP_DIR}/src-tauri/target/debug/bundle"
fi

# Copy Windows installers (NSIS + WiX MSI)
if [[ -d "${BUNDLE_DIR}/nsis" ]]; then
    cp -v "${BUNDLE_DIR}"/nsis/*.exe "${DIST_DIR}/" 2>/dev/null || true
fi
if [[ -d "${BUNDLE_DIR}/msi" ]]; then
    cp -v "${BUNDLE_DIR}"/msi/*.msi "${DIST_DIR}/" 2>/dev/null || true
fi

# Copy macOS bundles (if built on macOS)
if [[ -d "${BUNDLE_DIR}/dmg" ]]; then
    cp -v "${BUNDLE_DIR}"/dmg/*.dmg "${DIST_DIR}/" 2>/dev/null || true
fi
if [[ -d "${BUNDLE_DIR}/macos" ]]; then
    cp -v "${BUNDLE_DIR}"/macos/*.app "${DIST_DIR}/" 2>/dev/null || true
fi

# Copy Linux packages (if built on Linux)
if [[ -d "${BUNDLE_DIR}/deb" ]]; then
    cp -v "${BUNDLE_DIR}"/deb/*.deb "${DIST_DIR}/" 2>/dev/null || true
fi
if [[ -d "${BUNDLE_DIR}/appimage" ]]; then
    cp -v "${BUNDLE_DIR}"/appimage/*.AppImage "${DIST_DIR}/" 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# 7. Generate checksums
# ---------------------------------------------------------------------------
log "Generating checksums..."
cd "${DIST_DIR}"

ARTIFACT_COUNT=$(find . -maxdepth 1 -type f ! -name 'checksums.sha256' | wc -l)
if [[ "${ARTIFACT_COUNT}" -eq 0 ]]; then
    log "WARNING: No artifacts found in ${DIST_DIR}"
    log "This may be expected if building on a platform without matching bundle targets."
else
    sha256sum * > checksums.sha256 2>/dev/null || shasum -a 256 * > checksums.sha256
    log "Checksums written to ${DIST_DIR}/checksums.sha256"
    cat checksums.sha256
fi

# ---------------------------------------------------------------------------
# 8. Summary
# ---------------------------------------------------------------------------
log "Desktop packaging complete."
log "  Version:   ${VERSION}"
log "  Artifacts: ${DIST_DIR}"
log "  Files:     ${ARTIFACT_COUNT} artifact(s)"
