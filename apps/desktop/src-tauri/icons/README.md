# Icons

This directory should contain the application icons for the AI Scraper desktop app.

## Required Files

Tauri expects the following icon files for building:

| File | Size | Format | Purpose |
|------|------|--------|---------|
| `icon.ico` | Multi-size | ICO | Windows application icon (16, 32, 48, 64, 128, 256px) |
| `icon.png` | 512x512 | PNG | Tray icon and general use |
| `32x32.png` | 32x32 | PNG | Small icon |
| `128x128.png` | 128x128 | PNG | Medium icon |
| `128x128@2x.png` | 256x256 | PNG | Retina/HiDPI medium icon |
| `icon.icns` | Multi-size | ICNS | macOS application icon (optional for Windows-only) |

## Generating Icons

To generate all required icon sizes from a source SVG or high-resolution PNG:

### Option 1: Tauri Icon Generator (recommended)
```bash
npx @tauri-apps/cli icon path/to/source-icon.png
```
This generates all required sizes and formats automatically.

### Option 2: ImageMagick
```bash
# From a 1024x1024 source PNG:
convert source.png -resize 32x32 32x32.png
convert source.png -resize 128x128 128x128.png
convert source.png -resize 256x256 128x128@2x.png
convert source.png -resize 512x512 icon.png
convert source.png -resize 256x256 -define icon:auto-resize=256,128,64,48,32,16 icon.ico
```

## Placeholder

The `placeholder.svg` file in this directory can be used as a starting point.
Replace it with the final AI Scraper logo before production builds.
