#!/usr/bin/env bash
# =============================================================================
# package-extension.sh — Build and package the AI Scraper Chrome extension
#
# Usage:
#   ./scripts/package-extension.sh [--bump major|minor|patch] [--skip-validate]
#
# Requirements:
#   - Node.js >= 18 (for optional TypeScript build)
#   - zip
#
# Outputs:
#   dist/extension/              — Built extension files (ready to load unpacked)
#   dist/extension.zip           — Chrome Web Store upload package
#   dist/extension-checksums.sha256 — SHA-256 checksums
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
EXT_DIR="${PROJECT_ROOT}/apps/extension"
DIST_DIR="${PROJECT_ROOT}/dist/extension"
BUMP_TYPE=""
SKIP_VALIDATE=false

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --bump)
            BUMP_TYPE="$2"; shift 2
            if [[ ! "${BUMP_TYPE}" =~ ^(major|minor|patch)$ ]]; then
                echo "ERROR: --bump must be major, minor, or patch" >&2
                exit 1
            fi
            ;;
        --skip-validate) SKIP_VALIDATE=true; shift ;;
        -h|--help)
            echo "Usage: $0 [--bump major|minor|patch] [--skip-validate]"
            echo "  --bump TYPE       Bump manifest version before packaging"
            echo "  --skip-validate   Skip extension validation step"
            exit 0
            ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
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

command -v zip >/dev/null 2>&1 || error "'zip' is not installed"

if [[ ! -f "${EXT_DIR}/manifest.json" ]]; then
    error "manifest.json not found at ${EXT_DIR}/manifest.json"
fi

# ---------------------------------------------------------------------------
# 2. Version bump (optional)
# ---------------------------------------------------------------------------
if [[ -n "${BUMP_TYPE}" ]]; then
    log "Bumping version (${BUMP_TYPE})..."

    CURRENT_VERSION=$(node -p "require('${EXT_DIR}/manifest.json').version")
    IFS='.' read -r MAJOR MINOR PATCH <<< "${CURRENT_VERSION}"

    case "${BUMP_TYPE}" in
        major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
        minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
        patch) PATCH=$((PATCH + 1)) ;;
    esac

    NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"
    log "Version: ${CURRENT_VERSION} -> ${NEW_VERSION}"

    # Update manifest.json version using Node.js for safe JSON editing
    node -e "
        const fs = require('fs');
        const path = '${EXT_DIR}/manifest.json';
        const manifest = JSON.parse(fs.readFileSync(path, 'utf8'));
        manifest.version = '${NEW_VERSION}';
        fs.writeFileSync(path, JSON.stringify(manifest, null, 2) + '\n');
    "

    # Update package.json if it exists
    if [[ -f "${EXT_DIR}/package.json" ]]; then
        node -e "
            const fs = require('fs');
            const path = '${EXT_DIR}/package.json';
            const pkg = JSON.parse(fs.readFileSync(path, 'utf8'));
            pkg.version = '${NEW_VERSION}';
            fs.writeFileSync(path, JSON.stringify(pkg, null, 2) + '\n');
        "
    fi
else
    NEW_VERSION=$(node -p "require('${EXT_DIR}/manifest.json').version")
fi

# Override version from git tag if available
if git describe --tags --exact-match HEAD 2>/dev/null | grep -q '^v.*-extension$'; then
    TAG_VERSION=$(git describe --tags --exact-match HEAD | sed 's/^v//' | sed 's/-extension$//')
    log "Using version from git tag: ${TAG_VERSION}"
    NEW_VERSION="${TAG_VERSION}"
fi

log "Packaging version: ${NEW_VERSION}"

# ---------------------------------------------------------------------------
# 3. Validate extension (unless skipped)
# ---------------------------------------------------------------------------
if [[ "${SKIP_VALIDATE}" == "false" ]]; then
    log "Validating extension..."
    if [[ -x "${SCRIPT_DIR}/validate-extension.sh" ]]; then
        "${SCRIPT_DIR}/validate-extension.sh" || error "Extension validation failed"
    else
        log "WARNING: validate-extension.sh not found or not executable, skipping validation"
    fi
fi

# ---------------------------------------------------------------------------
# 4. Build TypeScript (if package.json has a build script)
# ---------------------------------------------------------------------------
if [[ -f "${EXT_DIR}/package.json" ]]; then
    HAS_BUILD=$(node -p "Boolean(require('${EXT_DIR}/package.json').scripts?.build)" 2>/dev/null || echo "false")
    if [[ "${HAS_BUILD}" == "true" ]]; then
        log "Building TypeScript..."
        cd "${EXT_DIR}"
        npm ci --prefer-offline 2>/dev/null || npm install
        npm run build
    fi
fi

# ---------------------------------------------------------------------------
# 5. Copy files to dist/extension/
# ---------------------------------------------------------------------------
log "Copying extension files to ${DIST_DIR}..."
rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"

# Copy all extension source files
cp -r "${EXT_DIR}"/manifest.json "${DIST_DIR}/"
cp -r "${EXT_DIR}"/popup/       "${DIST_DIR}/popup/"       2>/dev/null || true
cp -r "${EXT_DIR}"/background/  "${DIST_DIR}/background/"  2>/dev/null || true
cp -r "${EXT_DIR}"/content/     "${DIST_DIR}/content/"     2>/dev/null || true
cp -r "${EXT_DIR}"/options/     "${DIST_DIR}/options/"     2>/dev/null || true
cp -r "${EXT_DIR}"/icons/       "${DIST_DIR}/icons/"       2>/dev/null || true
cp -r "${EXT_DIR}"/lib/         "${DIST_DIR}/lib/"         2>/dev/null || true

# If there is a TypeScript build output, copy that instead
if [[ -d "${EXT_DIR}/dist" ]]; then
    log "Copying TypeScript build output..."
    cp -r "${EXT_DIR}/dist/"* "${DIST_DIR}/" 2>/dev/null || true
fi

# Remove development files from dist
find "${DIST_DIR}" -name "*.ts" ! -name "*.d.ts" -delete 2>/dev/null || true
find "${DIST_DIR}" -name "*.map" -delete 2>/dev/null || true
find "${DIST_DIR}" -name ".gitkeep" -delete 2>/dev/null || true
find "${DIST_DIR}" -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null || true

# ---------------------------------------------------------------------------
# 6. Create .zip for Chrome Web Store
# ---------------------------------------------------------------------------
log "Creating Chrome Web Store .zip..."
cd "${DIST_DIR}"
ZIP_FILE="${PROJECT_ROOT}/dist/ai-scraper-extension-${NEW_VERSION}.zip"
rm -f "${ZIP_FILE}"
zip -r "${ZIP_FILE}" . -x "*.DS_Store" -x "__MACOSX/*"

log "Created: ${ZIP_FILE}"
log "  Size: $(du -h "${ZIP_FILE}" | cut -f1)"

# ---------------------------------------------------------------------------
# 7. Generate checksums
# ---------------------------------------------------------------------------
log "Generating checksums..."
cd "${PROJECT_ROOT}/dist"

CHECKSUM_FILE="extension-checksums.sha256"
sha256sum "$(basename "${ZIP_FILE}")" > "${CHECKSUM_FILE}" 2>/dev/null \
    || shasum -a 256 "$(basename "${ZIP_FILE}")" > "${CHECKSUM_FILE}"

log "Checksums:"
cat "${CHECKSUM_FILE}"

# ---------------------------------------------------------------------------
# 8. Summary
# ---------------------------------------------------------------------------
FILE_COUNT=$(find "${DIST_DIR}" -type f | wc -l)
log "Extension packaging complete."
log "  Version:   ${NEW_VERSION}"
log "  Files:     ${FILE_COUNT} file(s) in dist/extension/"
log "  ZIP:       ${ZIP_FILE}"
log "  Checksums: ${PROJECT_ROOT}/dist/${CHECKSUM_FILE}"
