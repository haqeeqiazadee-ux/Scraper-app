#!/usr/bin/env bash
# build-desktop.sh — CI-friendly build script for AI Scraper desktop app.
#
# This script is designed to run in GitHub Actions or other CI environments.
# It handles: dependency installation, frontend build, Tauri build,
# optional code signing, and artifact collection.
#
# Environment variables:
#   SIGN_CERT_PATH       — Path to .pfx code signing certificate (optional)
#   SIGN_CERT_PASSWORD   — Certificate password (optional)
#   BUILD_TARGET         — "msi", "nsis", or "all" (default: all)
#   BUILD_MODE           — "release" or "debug" (default: release)
#   ARTIFACTS_DIR        — Output directory (default: ./artifacts)
#
# Usage:
#   ./scripts/build-desktop.sh
#   BUILD_TARGET=msi ./scripts/build-desktop.sh
#   SIGN_CERT_PATH=/path/to/cert.pfx SIGN_CERT_PASSWORD=pass ./scripts/build-desktop.sh

set -euo pipefail

# ---------- Configuration ----------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_DIR="$REPO_ROOT/apps/desktop"
TAURI_DIR="$DESKTOP_DIR/src-tauri"
BUILD_TARGET="${BUILD_TARGET:-all}"
BUILD_MODE="${BUILD_MODE:-release}"
ARTIFACTS_DIR="${ARTIFACTS_DIR:-$REPO_ROOT/artifacts}"

# Colors
if [ -t 1 ]; then
    RED='\033[0;31m' GREEN='\033[0;32m' YELLOW='\033[1;33m' BLUE='\033[0;34m' NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

log_step()  { echo -e "\n${BLUE}==>${NC} $*"; }
log_ok()    { echo -e "${GREEN}  [OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}  [WARN]${NC} $*"; }
log_error() { echo -e "${RED}  [ERROR]${NC} $*"; }

# ---------- Step 1: Validate environment ----------
log_step "Validating build environment"

for cmd in rustc cargo node npm; do
    if ! command -v "$cmd" &>/dev/null; then
        log_error "$cmd not found in PATH"
        exit 1
    fi
done

log_ok "Rust $(rustc --version | awk '{print $2}')"
log_ok "Node $(node --version)"
log_ok "npm $(npm --version)"

# ---------- Step 2: Install Node dependencies ----------
log_step "Installing Node.js dependencies"
cd "$DESKTOP_DIR"

if [ -f "package-lock.json" ]; then
    npm ci
else
    npm install
fi

log_ok "Node dependencies installed"

# ---------- Step 3: Build frontend ----------
log_step "Building frontend"
npm run build

if [ ! -d "$DESKTOP_DIR/dist" ]; then
    log_error "Frontend build failed (dist/ not found)"
    exit 1
fi

log_ok "Frontend built successfully"

# ---------- Step 4: Build Tauri ----------
log_step "Building Tauri application (mode=$BUILD_MODE, target=$BUILD_TARGET)"

TAURI_ARGS=()
if [ "$BUILD_MODE" = "debug" ]; then
    TAURI_ARGS+=("--debug")
fi

case "$BUILD_TARGET" in
    msi)  TAURI_ARGS+=("--bundles" "msi") ;;
    nsis) TAURI_ARGS+=("--bundles" "nsis") ;;
    all)  TAURI_ARGS+=("--bundles" "msi,nsis") ;;
    *)
        log_error "Unknown BUILD_TARGET: $BUILD_TARGET (expected: msi, nsis, all)"
        exit 1
        ;;
esac

cd "$DESKTOP_DIR"
npx tauri build "${TAURI_ARGS[@]}"

log_ok "Tauri build complete"

# ---------- Step 5: Code signing (optional) ----------
if [ -n "${SIGN_CERT_PATH:-}" ] && [ -f "$SIGN_CERT_PATH" ]; then
    log_step "Signing installer artifacts"

    if ! command -v signtool &>/dev/null; then
        log_warn "signtool not found, skipping signing"
        log_warn "On Windows, install Windows SDK for signtool.exe"
    else
        SIGN_CERT_PASSWORD="${SIGN_CERT_PASSWORD:-}"

        if [ "$BUILD_MODE" = "debug" ]; then
            BUNDLE_DIR="$TAURI_DIR/target/debug/bundle"
        else
            BUNDLE_DIR="$TAURI_DIR/target/release/bundle"
        fi

        # Sign MSI files
        for f in "$BUNDLE_DIR/msi/"*.msi 2>/dev/null; do
            [ -f "$f" ] || continue
            log_ok "Signing $f"
            signtool sign /f "$SIGN_CERT_PATH" /p "$SIGN_CERT_PASSWORD" \
                /t http://timestamp.digicert.com /fd sha256 "$f"
        done

        # Sign NSIS EXE files
        for f in "$BUNDLE_DIR/nsis/"*.exe 2>/dev/null; do
            [ -f "$f" ] || continue
            log_ok "Signing $f"
            signtool sign /f "$SIGN_CERT_PATH" /p "$SIGN_CERT_PASSWORD" \
                /t http://timestamp.digicert.com /fd sha256 "$f"
        done

        log_ok "Signing complete"
    fi
else
    log_warn "No SIGN_CERT_PATH set, skipping code signing"
fi

# ---------- Step 6: Collect artifacts ----------
log_step "Collecting artifacts to $ARTIFACTS_DIR"
mkdir -p "$ARTIFACTS_DIR"

if [ "$BUILD_MODE" = "debug" ]; then
    BUNDLE_DIR="$TAURI_DIR/target/debug/bundle"
else
    BUNDLE_DIR="$TAURI_DIR/target/release/bundle"
fi

COLLECTED=0

# Collect MSI
for f in "$BUNDLE_DIR/msi/"*.msi 2>/dev/null; do
    [ -f "$f" ] || continue
    cp -v "$f" "$ARTIFACTS_DIR/"
    COLLECTED=$((COLLECTED + 1))
done

# Collect NSIS EXE
for f in "$BUNDLE_DIR/nsis/"*.exe 2>/dev/null; do
    [ -f "$f" ] || continue
    cp -v "$f" "$ARTIFACTS_DIR/"
    COLLECTED=$((COLLECTED + 1))
done

# ---------- Step 7: Generate checksums ----------
if [ "$COLLECTED" -gt 0 ]; then
    log_step "Generating checksums"
    cd "$ARTIFACTS_DIR"
    if command -v sha256sum &>/dev/null; then
        sha256sum *.msi *.exe 2>/dev/null > checksums.sha256 || true
        log_ok "Checksums written to checksums.sha256"
    elif command -v shasum &>/dev/null; then
        shasum -a 256 *.msi *.exe 2>/dev/null > checksums.sha256 || true
        log_ok "Checksums written to checksums.sha256"
    fi
fi

# ---------- Summary ----------
echo ""
echo "=========================================="
echo "  Desktop Build Complete"
echo "=========================================="
echo "  Product:     AI Scraper"
echo "  Version:     $(grep '"version"' "$TAURI_DIR/tauri.conf.json" | head -1 | grep -oP '\d+\.\d+\.\d+')"
echo "  Mode:        $BUILD_MODE"
echo "  Targets:     $BUILD_TARGET"
echo "  Artifacts:   $ARTIFACTS_DIR/"
echo "  Count:       $COLLECTED file(s)"

if [ -n "${SIGN_CERT_PATH:-}" ] && [ -f "${SIGN_CERT_PATH:-}" ]; then
    echo "  Signed:      yes"
else
    echo "  Signed:      no"
fi

echo "=========================================="

if [ "$COLLECTED" -eq 0 ]; then
    log_warn "No installer artifacts were produced."
    log_warn "Ensure WiX toolset (for MSI) and/or NSIS (for EXE) are installed."
    exit 1
fi

log_ok "Build successful!"
