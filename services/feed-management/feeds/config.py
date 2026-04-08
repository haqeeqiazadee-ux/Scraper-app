from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_feeds_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Feed config not found: {path}")
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict) or "sources" not in data:
        raise ValueError("Config must be a JSON object with a 'sources' array")
    sources = data["sources"]
    if not isinstance(sources, list):
        raise ValueError("'sources' must be an array")
    return data
