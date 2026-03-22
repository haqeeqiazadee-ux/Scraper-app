"""
Companion Installer — registers the native messaging host with Chrome/Chromium.

Writes the native messaging host manifest to the appropriate OS-specific location.

Usage:
  python install.py [--uninstall] [--browser chrome|chromium|edge]
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path

APP_NAME = "com.scraper.companion"
DESCRIPTION = "AI Scraper companion — bridges Chrome extension to local engine"


def get_host_path() -> str:
    """Get the absolute path to the native host script."""
    return str(Path(__file__).parent / "native_host.py")


def get_manifest() -> dict:
    """Generate the native messaging host manifest."""
    return {
        "name": APP_NAME,
        "description": DESCRIPTION,
        "path": get_host_path(),
        "type": "stdio",
        "allowed_origins": [
            "chrome-extension://placeholder-extension-id/",
        ],
    }


def get_manifest_dir(browser: str = "chrome") -> Path:
    """Get the OS-specific directory for native messaging host manifests."""
    system = platform.system()

    if system == "Windows":
        # On Windows, we write to registry + local dir
        return Path(os.environ.get("LOCALAPPDATA", "")) / f"Google/{browser.title()}/NativeMessagingHosts"
    elif system == "Darwin":
        if browser == "chrome":
            return Path.home() / "Library/Application Support/Google/Chrome/NativeMessagingHosts"
        elif browser == "chromium":
            return Path.home() / "Library/Application Support/Chromium/NativeMessagingHosts"
        else:
            return Path.home() / "Library/Application Support/Microsoft Edge/NativeMessagingHosts"
    else:
        # Linux
        if browser == "chrome":
            return Path.home() / ".config/google-chrome/NativeMessagingHosts"
        elif browser == "chromium":
            return Path.home() / ".config/chromium/NativeMessagingHosts"
        else:
            return Path.home() / ".config/microsoft-edge/NativeMessagingHosts"


def install(browser: str = "chrome") -> None:
    """Install the native messaging host manifest."""
    manifest_dir = get_manifest_dir(browser)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = manifest_dir / f"{APP_NAME}.json"
    manifest = get_manifest()

    # On non-Windows, the path should be the Python interpreter + script
    if platform.system() != "Windows":
        manifest["path"] = sys.executable
        # Wrapper script that calls the host
        wrapper_path = Path(__file__).parent / "run_host.sh"
        wrapper_path.write_text(
            f"#!/bin/bash\nexec {sys.executable} {get_host_path()}\n"
        )
        wrapper_path.chmod(0o755)
        manifest["path"] = str(wrapper_path)

    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"Installed native messaging host manifest to: {manifest_path}")

    if platform.system() == "Windows":
        _install_windows_registry(manifest_path)


def uninstall(browser: str = "chrome") -> None:
    """Remove the native messaging host manifest."""
    manifest_dir = get_manifest_dir(browser)
    manifest_path = manifest_dir / f"{APP_NAME}.json"

    if manifest_path.exists():
        manifest_path.unlink()
        print(f"Removed: {manifest_path}")
    else:
        print(f"Not found: {manifest_path}")

    wrapper_path = Path(__file__).parent / "run_host.sh"
    if wrapper_path.exists():
        wrapper_path.unlink()


def _install_windows_registry(manifest_path: Path) -> None:
    """Register native host in Windows registry."""
    try:
        import winreg
        key_path = f"SOFTWARE\\Google\\Chrome\\NativeMessagingHosts\\{APP_NAME}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(manifest_path))
        print(f"Registry key created: HKCU\\{key_path}")
    except ImportError:
        print("Note: winreg not available (non-Windows platform)")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Install/uninstall native messaging host")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall instead of install")
    parser.add_argument("--browser", choices=["chrome", "chromium", "edge"], default="chrome")
    args = parser.parse_args()

    if args.uninstall:
        uninstall(args.browser)
    else:
        install(args.browser)


if __name__ == "__main__":
    main()
