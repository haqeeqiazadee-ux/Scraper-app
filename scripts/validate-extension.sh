#!/usr/bin/env bash
# =============================================================================
# validate-extension.sh — Validate the Chrome extension package
#
# Checks:
#   1. manifest.json exists and is valid JSON
#   2. Manifest V3 required fields present
#   3. Version format is valid (1-4 dot-separated integers)
#   4. Required permissions are declared
#   5. Icon files exist and are correct sizes
#   6. Referenced files (service worker, content scripts, popup) exist
#   7. CSP does not include unsafe-eval (MV3 requirement)
#
# Usage:
#   ./scripts/validate-extension.sh [path/to/extension]
#
# Exit codes:
#   0 — All checks passed
#   1 — One or more checks failed
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
EXT_DIR="${1:-${PROJECT_ROOT}/apps/extension}"

ERRORS=0
WARNINGS=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
pass()    { echo "  [PASS] $*"; }
fail()    { echo "  [FAIL] $*"; ERRORS=$((ERRORS + 1)); }
warn()    { echo "  [WARN] $*"; WARNINGS=$((WARNINGS + 1)); }
section() { echo ""; echo "=== $* ==="; }

# ---------------------------------------------------------------------------
# 1. manifest.json exists and is valid JSON
# ---------------------------------------------------------------------------
section "Manifest file"

MANIFEST="${EXT_DIR}/manifest.json"
if [[ ! -f "${MANIFEST}" ]]; then
    fail "manifest.json not found at ${MANIFEST}"
    echo ""
    echo "Result: FAILED (${ERRORS} error(s), ${WARNINGS} warning(s))"
    exit 1
fi
pass "manifest.json exists"

# Validate JSON syntax
if ! node -e "JSON.parse(require('fs').readFileSync('${MANIFEST}','utf8'))" 2>/dev/null; then
    fail "manifest.json is not valid JSON"
    echo ""
    echo "Result: FAILED (${ERRORS} error(s), ${WARNINGS} warning(s))"
    exit 1
fi
pass "manifest.json is valid JSON"

# ---------------------------------------------------------------------------
# 2. Required fields
# ---------------------------------------------------------------------------
section "Required manifest fields"

REQUIRED_FIELDS=("manifest_version" "name" "version" "description" "icons")
for field in "${REQUIRED_FIELDS[@]}"; do
    HAS_FIELD=$(node -p "
        const m = JSON.parse(require('fs').readFileSync('${MANIFEST}','utf8'));
        m.hasOwnProperty('${field}')
    " 2>/dev/null)
    if [[ "${HAS_FIELD}" == "true" ]]; then
        pass "Field '${field}' present"
    else
        fail "Missing required field: ${field}"
    fi
done

# ---------------------------------------------------------------------------
# 3. Manifest version
# ---------------------------------------------------------------------------
section "Manifest version"

MV=$(node -p "JSON.parse(require('fs').readFileSync('${MANIFEST}','utf8')).manifest_version" 2>/dev/null)
if [[ "${MV}" == "3" ]]; then
    pass "Manifest V3"
else
    fail "Expected manifest_version 3, got ${MV}"
fi

# ---------------------------------------------------------------------------
# 4. Version format
# ---------------------------------------------------------------------------
section "Extension version"

EXT_VERSION=$(node -p "JSON.parse(require('fs').readFileSync('${MANIFEST}','utf8')).version" 2>/dev/null)
if [[ "${EXT_VERSION}" =~ ^[0-9]+(\.[0-9]+){0,3}$ ]]; then
    pass "Version format valid: ${EXT_VERSION}"
else
    fail "Invalid version format: ${EXT_VERSION} (expected X.Y.Z with 1-4 parts)"
fi

# ---------------------------------------------------------------------------
# 5. Permissions
# ---------------------------------------------------------------------------
section "Permissions"

# Check that only safe permissions are declared
PERMISSIONS=$(node -p "
    JSON.parse(require('fs').readFileSync('${MANIFEST}','utf8'))
        .permissions?.join(',') || ''
" 2>/dev/null)

DANGEROUS_PERMS=("debugger" "pageCapture" "desktopCapture" "ttsEngine")
for perm in "${DANGEROUS_PERMS[@]}"; do
    if echo "${PERMISSIONS}" | grep -q "${perm}"; then
        warn "Potentially dangerous permission: ${perm}"
    fi
done

if [[ -n "${PERMISSIONS}" ]]; then
    pass "Permissions declared: ${PERMISSIONS}"
fi

# ---------------------------------------------------------------------------
# 6. Icon files
# ---------------------------------------------------------------------------
section "Icon files"

ICON_SIZES=("16" "48" "128")
for size in "${ICON_SIZES[@]}"; do
    ICON_PATH=$(node -p "
        JSON.parse(require('fs').readFileSync('${MANIFEST}','utf8'))
            .icons?.['${size}'] || ''
    " 2>/dev/null)

    if [[ -z "${ICON_PATH}" ]]; then
        warn "No ${size}x${size} icon declared in manifest"
    elif [[ -f "${EXT_DIR}/${ICON_PATH}" ]]; then
        # Check file size (icons should be > 0 bytes)
        FSIZE=$(wc -c < "${EXT_DIR}/${ICON_PATH}")
        if [[ "${FSIZE}" -gt 0 ]]; then
            pass "Icon ${size}x${size}: ${ICON_PATH} (${FSIZE} bytes)"
        else
            fail "Icon ${size}x${size} is empty: ${ICON_PATH}"
        fi
    else
        fail "Icon file not found: ${ICON_PATH}"
    fi
done

# ---------------------------------------------------------------------------
# 7. Referenced files exist
# ---------------------------------------------------------------------------
section "Referenced files"

# Service worker
SW_PATH=$(node -p "
    JSON.parse(require('fs').readFileSync('${MANIFEST}','utf8'))
        .background?.service_worker || ''
" 2>/dev/null)
if [[ -n "${SW_PATH}" ]]; then
    if [[ -f "${EXT_DIR}/${SW_PATH}" ]]; then
        pass "Service worker: ${SW_PATH}"
    else
        fail "Service worker not found: ${SW_PATH}"
    fi
fi

# Content scripts
CONTENT_SCRIPTS=$(node -p "
    const m = JSON.parse(require('fs').readFileSync('${MANIFEST}','utf8'));
    (m.content_scripts || []).flatMap(cs => cs.js || []).join(',')
" 2>/dev/null)
IFS=',' read -ra CS_FILES <<< "${CONTENT_SCRIPTS}"
for cs in "${CS_FILES[@]}"; do
    if [[ -z "${cs}" ]]; then continue; fi
    if [[ -f "${EXT_DIR}/${cs}" ]]; then
        pass "Content script: ${cs}"
    else
        fail "Content script not found: ${cs}"
    fi
done

# Popup
POPUP_PATH=$(node -p "
    JSON.parse(require('fs').readFileSync('${MANIFEST}','utf8'))
        .action?.default_popup || ''
" 2>/dev/null)
if [[ -n "${POPUP_PATH}" ]]; then
    if [[ -f "${EXT_DIR}/${POPUP_PATH}" ]]; then
        pass "Popup: ${POPUP_PATH}"
    else
        fail "Popup not found: ${POPUP_PATH}"
    fi
fi

# Options page
OPTIONS_PATH=$(node -p "
    JSON.parse(require('fs').readFileSync('${MANIFEST}','utf8'))
        .options_ui?.page || ''
" 2>/dev/null)
if [[ -n "${OPTIONS_PATH}" ]]; then
    if [[ -f "${EXT_DIR}/${OPTIONS_PATH}" ]]; then
        pass "Options page: ${OPTIONS_PATH}"
    else
        fail "Options page not found: ${OPTIONS_PATH}"
    fi
fi

# ---------------------------------------------------------------------------
# 8. CSP check (MV3 must not use unsafe-eval)
# ---------------------------------------------------------------------------
section "Content Security Policy"

CSP=$(node -p "
    JSON.parse(require('fs').readFileSync('${MANIFEST}','utf8'))
        .content_security_policy?.extension_pages || 'not set'
" 2>/dev/null)

if [[ "${CSP}" == "not set" ]]; then
    pass "CSP not customized (default MV3 CSP applies)"
else
    if echo "${CSP}" | grep -q "unsafe-eval"; then
        fail "CSP contains 'unsafe-eval' — not allowed in Manifest V3"
    else
        pass "CSP is MV3-compliant: ${CSP}"
    fi
fi

# ---------------------------------------------------------------------------
# 9. Package size estimate
# ---------------------------------------------------------------------------
section "Package size"

if command -v du >/dev/null 2>&1; then
    TOTAL_SIZE=$(du -sh "${EXT_DIR}" 2>/dev/null | cut -f1)
    pass "Extension directory size: ${TOTAL_SIZE}"

    # Chrome Web Store limit is ~500MB (generous) but warn at 10MB
    SIZE_BYTES=$(du -sb "${EXT_DIR}" 2>/dev/null | cut -f1)
    if [[ "${SIZE_BYTES}" -gt 10485760 ]]; then
        warn "Extension is larger than 10MB — consider optimizing assets"
    fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "==========================================="
if [[ "${ERRORS}" -eq 0 ]]; then
    echo "Result: PASSED (${WARNINGS} warning(s))"
    exit 0
else
    echo "Result: FAILED (${ERRORS} error(s), ${WARNINGS} warning(s))"
    exit 1
fi
