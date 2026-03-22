#!/usr/bin/env bash
# build-installer.sh — Build Windows installer for AI Scraper desktop app.
# Works on Windows (Git Bash / MSYS2) and CI (Linux cross-compile awareness).
#
# Usage:
#   ./build-installer.sh              # Build all targets
#   ./build-installer.sh --msi        # WiX MSI only
#   ./build-installer.sh --nsis       # NSIS EXE only
#   ./build-installer.sh --debug      # Debug build (faster, no optimizations)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
TAURI_DIR="$PROJECT_DIR/src-tauri"
DIST_DIR="$PROJECT_DIR/dist-installer"

# Colors (only if terminal supports them)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---------- Parse arguments ----------
BUILD_TARGET="all"
BUILD_MODE="release"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --msi)   BUILD_TARGET="msi";   shift ;;
        --nsis)  BUILD_TARGET="nsis";  shift ;;
        --debug) BUILD_MODE="debug";   shift ;;
        --help|-h)
            echo "Usage: $0 [--msi|--nsis] [--debug]"
            exit 0
            ;;
        *)
            log_error "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# ---------- Prerequisite checks ----------
log_info "Checking prerequisites..."

check_command() {
    if ! command -v "$1" &>/dev/null; then
        log_error "$1 is not installed. $2"
        return 1
    fi
    log_ok "$1 found: $(command -v "$1")"
}

PREREQ_FAIL=0

check_command "rustc" "Install from https://rustup.rs/" || PREREQ_FAIL=1
check_command "cargo" "Install from https://rustup.rs/" || PREREQ_FAIL=1
check_command "node"  "Install from https://nodejs.org/" || PREREQ_FAIL=1
check_command "npm"   "Install from https://nodejs.org/" || PREREQ_FAIL=1

# Check Rust version (need 1.70+)
if command -v rustc &>/dev/null; then
    RUST_VERSION=$(rustc --version | grep -oP '\d+\.\d+\.\d+')
    RUST_MINOR=$(echo "$RUST_VERSION" | cut -d. -f2)
    if [ "$RUST_MINOR" -lt 70 ]; then
        log_error "Rust 1.70+ required, found $RUST_VERSION"
        PREREQ_FAIL=1
    else
        log_ok "Rust version: $RUST_VERSION"
    fi
fi

# Check Node version (need 18+)
if command -v node &>/dev/null; then
    NODE_MAJOR=$(node --version | grep -oP '\d+' | head -1)
    if [ "$NODE_MAJOR" -lt 18 ]; then
        log_error "Node.js 18+ required, found $(node --version)"
        PREREQ_FAIL=1
    else
        log_ok "Node.js version: $(node --version)"
    fi
fi

# Check for Tauri CLI
if ! npx tauri --version &>/dev/null 2>&1; then
    log_warn "@tauri-apps/cli not found locally, will install"
fi

# Platform-specific checks
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*|Windows*)
        IS_WINDOWS=true
        log_info "Detected Windows platform"

        # Check WiX toolset (for MSI)
        if [ "$BUILD_TARGET" = "all" ] || [ "$BUILD_TARGET" = "msi" ]; then
            if ! command -v candle &>/dev/null && ! command -v wix &>/dev/null; then
                log_warn "WiX toolset not found. MSI builds may fail."
                log_warn "Install: dotnet tool install --global wix"
                log_warn "Or download from https://wixtoolset.org/"
            else
                log_ok "WiX toolset found"
            fi
        fi

        # Check NSIS (for EXE installer)
        if [ "$BUILD_TARGET" = "all" ] || [ "$BUILD_TARGET" = "nsis" ]; then
            if ! command -v makensis &>/dev/null; then
                log_warn "NSIS not found. EXE installer builds may fail."
                log_warn "Install: choco install nsis  OR  winget install NSIS.NSIS"
            else
                log_ok "NSIS found"
            fi
        fi
        ;;
    Linux*)
        IS_WINDOWS=false
        log_info "Detected Linux platform (cross-compile or CI)"
        log_warn "Windows installer builds on Linux require cross-compilation toolchain"
        ;;
    Darwin*)
        IS_WINDOWS=false
        log_info "Detected macOS platform"
        log_warn "Windows installer builds on macOS require cross-compilation toolchain"
        ;;
esac

if [ "$PREREQ_FAIL" -ne 0 ]; then
    log_error "Prerequisite check failed. Please install missing dependencies."
    exit 1
fi

log_ok "All prerequisites satisfied"

# ---------- Install Node dependencies ----------
log_info "Installing Node.js dependencies..."
cd "$PROJECT_DIR"

if [ ! -d "node_modules" ]; then
    npm install
else
    log_ok "node_modules exists, skipping npm install (use --clean for fresh install)"
fi

# ---------- Build frontend ----------
log_info "Building frontend (Vite)..."
npm run build

if [ ! -d "$PROJECT_DIR/dist" ]; then
    log_error "Frontend build failed — dist/ directory not found"
    exit 1
fi
log_ok "Frontend build complete"

# ---------- Build Tauri app ----------
log_info "Building Tauri application ($BUILD_MODE mode)..."

TAURI_BUILD_ARGS=()

if [ "$BUILD_MODE" = "debug" ]; then
    TAURI_BUILD_ARGS+=("--debug")
fi

# Select bundle targets
case "$BUILD_TARGET" in
    msi)  TAURI_BUILD_ARGS+=("--bundles" "msi") ;;
    nsis) TAURI_BUILD_ARGS+=("--bundles" "nsis") ;;
    all)  TAURI_BUILD_ARGS+=("--bundles" "msi,nsis") ;;
esac

cd "$PROJECT_DIR"
npx tauri build "${TAURI_BUILD_ARGS[@]}"

log_ok "Tauri build complete"

# ---------- Collect artifacts ----------
log_info "Collecting build artifacts..."
mkdir -p "$DIST_DIR"

# Find built installers
if [ "$BUILD_MODE" = "debug" ]; then
    BUNDLE_DIR="$TAURI_DIR/target/debug/bundle"
else
    BUNDLE_DIR="$TAURI_DIR/target/release/bundle"
fi

ARTIFACT_COUNT=0

# Copy MSI files
if [ -d "$BUNDLE_DIR/msi" ]; then
    cp -v "$BUNDLE_DIR/msi/"*.msi "$DIST_DIR/" 2>/dev/null && \
        ARTIFACT_COUNT=$((ARTIFACT_COUNT + 1)) || true
fi

# Copy NSIS files
if [ -d "$BUNDLE_DIR/nsis" ]; then
    cp -v "$BUNDLE_DIR/nsis/"*.exe "$DIST_DIR/" 2>/dev/null && \
        ARTIFACT_COUNT=$((ARTIFACT_COUNT + 1)) || true
fi

if [ "$ARTIFACT_COUNT" -eq 0 ]; then
    log_warn "No installer artifacts found in $BUNDLE_DIR"
    log_warn "Check build output for errors"
else
    log_ok "Collected $ARTIFACT_COUNT artifact(s) to $DIST_DIR/"
    ls -lh "$DIST_DIR/"
fi

# ---------- Summary ----------
echo ""
echo "=========================================="
echo "  Build Summary"
echo "=========================================="
echo "  Product:    AI Scraper"
echo "  Version:    $(grep '"version"' "$TAURI_DIR/tauri.conf.json" | head -1 | grep -oP '\d+\.\d+\.\d+')"
echo "  Mode:       $BUILD_MODE"
echo "  Targets:    $BUILD_TARGET"
echo "  Artifacts:  $DIST_DIR/"
echo "=========================================="
