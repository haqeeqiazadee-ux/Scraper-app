# Installer Assets

This directory contains assets used by the Windows installer (WiX and NSIS).

## Required Files

### WiX Installer (.msi)

| File | Dimensions | Format | Description |
|------|-----------|--------|-------------|
| `banner.bmp` | 493 x 58 px | BMP (24-bit) | Top banner shown on most installer pages |
| `dialog.bmp` | 493 x 312 px | BMP (24-bit) | Side image on welcome and completion pages |
| `license.rtf` | N/A | RTF | License agreement text (included) |

### NSIS Installer (.exe)

| File | Dimensions | Format | Description |
|------|-----------|--------|-------------|
| `header.bmp` | 150 x 57 px | BMP (24-bit) | Header image on installer pages |
| `sidebar.bmp` | 164 x 314 px | BMP (24-bit) | Sidebar image on welcome/finish pages |
| `license.rtf` | N/A | RTF | License agreement text (included) |

## Generating BMP Files

From a source PNG or SVG, use ImageMagick to create the required BMP files:

```bash
# WiX banner (top strip)
convert source.png -resize 493x58! -type TrueColor BMP3:banner.bmp

# WiX dialog (side panel)
convert source.png -resize 493x312! -type TrueColor BMP3:dialog.bmp

# NSIS header
convert source.png -resize 150x57! -type TrueColor BMP3:header.bmp

# NSIS sidebar
convert source.png -resize 164x314! -type TrueColor BMP3:sidebar.bmp
```

Note: Use `BMP3:` prefix to ensure 24-bit BMP output. WiX and NSIS require uncompressed 24-bit BMPs.

## Design Guidelines

- Use the AI Scraper brand colors (blue gradient: #3b82f6 to #1d4ed8)
- Include the product name "AI Scraper" in banner/header images
- Keep text readable at small sizes
- Use a white or light background for best readability on the installer UI
- The dialog/sidebar images may include the product logo centered vertically

## Current Status

- `license.rtf` -- Included (MIT-based license)
- `banner.bmp` -- TODO: Generate from final logo
- `dialog.bmp` -- TODO: Generate from final logo
- `header.bmp` -- TODO: Generate from final logo
- `sidebar.bmp` -- TODO: Generate from final logo
