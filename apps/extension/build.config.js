/**
 * build.config.js — Build configuration for the AI Scraper Chrome extension
 *
 * This script handles:
 *   1. Manifest validation
 *   2. Asset copying (icons, HTML, CSS)
 *   3. JavaScript bundling (if needed)
 *   4. Output to dist/
 *
 * Usage:
 *   node build.config.js [--watch] [--production]
 */

import { readFileSync, writeFileSync, mkdirSync, cpSync, existsSync, readdirSync, statSync } from 'fs';
import { join, dirname, extname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const SRC_DIR = __dirname;
const DIST_DIR = join(__dirname, 'dist');

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/** Directories to copy into dist */
const COPY_DIRS = ['popup', 'background', 'content', 'options', 'icons', 'lib'];

/** Files to copy into dist root */
const COPY_FILES = ['manifest.json'];

/** Required icon sizes per Chrome Web Store guidelines */
const REQUIRED_ICON_SIZES = [16, 48, 128];

/** Required manifest fields */
const REQUIRED_MANIFEST_FIELDS = [
    'manifest_version',
    'name',
    'version',
    'description',
    'permissions',
    'action',
    'background',
    'icons',
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function log(msg) {
    const ts = new Date().toISOString();
    console.log(`[${ts}] ${msg}`);
}

function error(msg) {
    console.error(`[ERROR] ${msg}`);
    process.exit(1);
}

/**
 * Recursively copy a directory, optionally transforming files.
 */
function copyDir(src, dest, opts = {}) {
    if (!existsSync(src)) return;
    mkdirSync(dest, { recursive: true });

    for (const entry of readdirSync(src)) {
        const srcPath = join(src, entry);
        const destPath = join(dest, entry);
        const stat = statSync(srcPath);

        if (stat.isDirectory()) {
            copyDir(srcPath, destPath, opts);
        } else {
            // Skip .ts source files in production (keep .js output)
            if (opts.production && extname(entry) === '.ts' && !entry.endsWith('.d.ts')) {
                continue;
            }
            // Skip source maps in production
            if (opts.production && extname(entry) === '.map') {
                continue;
            }
            cpSync(srcPath, destPath);
        }
    }
}

// ---------------------------------------------------------------------------
// 1. Validate manifest
// ---------------------------------------------------------------------------

function validateManifest() {
    log('Validating manifest.json...');

    const manifestPath = join(SRC_DIR, 'manifest.json');
    if (!existsSync(manifestPath)) {
        error('manifest.json not found');
    }

    let manifest;
    try {
        manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
    } catch (e) {
        error(`manifest.json is not valid JSON: ${e.message}`);
    }

    // Check required fields
    for (const field of REQUIRED_MANIFEST_FIELDS) {
        if (!(field in manifest)) {
            error(`manifest.json is missing required field: ${field}`);
        }
    }

    // Manifest V3 check
    if (manifest.manifest_version !== 3) {
        error(`Expected manifest_version 3, got ${manifest.manifest_version}`);
    }

    // Version format check (Chrome requires 1-4 dot-separated integers)
    const versionPattern = /^\d+(\.\d+){0,3}$/;
    if (!versionPattern.test(manifest.version)) {
        error(`Invalid version format: ${manifest.version} (expected X.Y.Z)`);
    }

    // Icon size checks
    if (manifest.icons) {
        for (const size of REQUIRED_ICON_SIZES) {
            if (!manifest.icons[String(size)]) {
                log(`WARNING: Missing icon size ${size}x${size} in manifest.icons`);
            }
        }
    }

    // CSP check for MV3 (must not use unsafe-eval)
    if (manifest.content_security_policy?.extension_pages) {
        const csp = manifest.content_security_policy.extension_pages;
        if (csp.includes('unsafe-eval')) {
            error('CSP must not include unsafe-eval for Manifest V3');
        }
    }

    log(`  Name:    ${manifest.name}`);
    log(`  Version: ${manifest.version}`);
    log(`  MV:      ${manifest.manifest_version}`);

    return manifest;
}

// ---------------------------------------------------------------------------
// 2. Validate icon files
// ---------------------------------------------------------------------------

function validateIcons(manifest) {
    log('Validating icon files...');

    const icons = { ...manifest.icons };
    if (manifest.action?.default_icon) {
        Object.assign(icons, manifest.action.default_icon);
    }

    for (const [size, path] of Object.entries(icons)) {
        const fullPath = join(SRC_DIR, path);
        if (!existsSync(fullPath)) {
            log(`WARNING: Icon file missing: ${path} (${size}x${size})`);
        }
    }
}

// ---------------------------------------------------------------------------
// 3. Copy assets to dist
// ---------------------------------------------------------------------------

function copyAssets(isProduction) {
    log(`Copying assets to ${DIST_DIR}...`);

    // Clean dist
    if (existsSync(DIST_DIR)) {
        cpSync(DIST_DIR, DIST_DIR, { recursive: true }); // noop to ensure dir exists
    }
    mkdirSync(DIST_DIR, { recursive: true });

    // Copy root files
    for (const file of COPY_FILES) {
        const src = join(SRC_DIR, file);
        if (existsSync(src)) {
            cpSync(src, join(DIST_DIR, file));
            log(`  Copied ${file}`);
        }
    }

    // Copy directories
    for (const dir of COPY_DIRS) {
        const src = join(SRC_DIR, dir);
        if (existsSync(src)) {
            copyDir(src, join(DIST_DIR, dir), { production: isProduction });
            log(`  Copied ${dir}/`);
        }
    }
}

// ---------------------------------------------------------------------------
// 4. Set version in dist manifest (from env or git tag)
// ---------------------------------------------------------------------------

function setVersion(manifest) {
    const envVersion = process.env.EXTENSION_VERSION;
    if (envVersion) {
        log(`Setting version from env: ${envVersion}`);
        const distManifestPath = join(DIST_DIR, 'manifest.json');
        manifest.version = envVersion;
        writeFileSync(distManifestPath, JSON.stringify(manifest, null, 2) + '\n');
    }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
    const args = process.argv.slice(2);
    const isProduction = args.includes('--production');

    log(`Build mode: ${isProduction ? 'production' : 'development'}`);

    const manifest = validateManifest();
    validateIcons(manifest);
    copyAssets(isProduction);
    setVersion(manifest);

    const fileCount = readdirSync(DIST_DIR, { recursive: true }).length;
    log(`Build complete: ${fileCount} files in dist/`);
}

main();
