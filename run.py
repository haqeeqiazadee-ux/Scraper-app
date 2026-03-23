"""
Windows-friendly startup script for the AI Scraping Platform.

Usage:
    python run.py

This handles the symlink issue on Windows where git doesn't
create real symlinks for the underscore-named directories.
"""

import os
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Ensure the project root is on PYTHONPATH
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Fix symlinks on Windows ---
# On Linux these are real symlinks; on Windows git clones them as text files.
# We fix this by copying the real directories if the symlink targets are broken.

SYMLINK_MAP = {
    "services/control_plane": "services/control-plane",
    "services/worker_ai": "services/worker-ai",
    "services/worker_browser": "services/worker-browser",
    "services/worker_hard_target": "services/worker-hard-target",
    "services/worker_http": "services/worker-http",
}


def fix_symlinks():
    fixed = []
    for link_name, target_name in SYMLINK_MAP.items():
        link_path = ROOT / link_name
        target_path = ROOT / target_name

        if not target_path.is_dir():
            continue

        # If it's already a working directory (real or symlink), skip
        if link_path.is_dir():
            # Check it's not a broken symlink or a plain file
            try:
                list(link_path.iterdir())
                continue
            except (OSError, NotADirectoryError):
                pass

        # Remove broken symlink / text file
        if link_path.exists() or link_path.is_symlink():
            if link_path.is_file():
                link_path.unlink()
            elif link_path.is_symlink():
                link_path.unlink()

        # Try creating a real symlink first, fall back to copying
        try:
            os.symlink(target_path, link_path)
            fixed.append(f"  symlinked {link_name} -> {target_name}")
        except OSError:
            shutil.copytree(target_path, link_path)
            fixed.append(f"  copied {target_name} -> {link_name}")

    if fixed:
        print("Fixed Windows symlinks:")
        for f in fixed:
            print(f)
        print()


if __name__ == "__main__":
    fix_symlinks()

    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting AI Scraping Platform on http://0.0.0.0:{port}")
    print("Press Ctrl+C to stop.\n")
    uvicorn.run(
        "services.control_plane.app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
