from __future__ import annotations

import sys
import types
from pathlib import Path


def _services_root() -> Path:
    file_path = globals().get("__file__")
    if file_path:
        return Path(str(file_path)).resolve().parent

    package_path = globals().get("__path__")
    if package_path:
        return Path(str(list(package_path)[0])).resolve()

    return Path.cwd() / "services"


def _register_hyphenated_service(alias: str, directory_name: str) -> None:
    module_name = f"{__name__}.{alias}"
    if module_name in sys.modules:
        return

    package_dir = _services_root() / directory_name
    if not package_dir.is_dir():
        return

    module = types.ModuleType(module_name)
    module.__path__ = [str(package_dir)]  # type: ignore[attr-defined]
    module.__package__ = module_name
    sys.modules[module_name] = module
    globals()[alias] = module
    parent_module = sys.modules.get(__name__)
    if parent_module is not None:
        setattr(parent_module, alias, module)


_register_hyphenated_service("control_plane", "control-plane")
_register_hyphenated_service("worker_http", "worker-http")
_register_hyphenated_service("worker_browser", "worker-browser")
_register_hyphenated_service("worker_ai", "worker-ai")
_register_hyphenated_service("worker_hard_target", "worker-hard-target")
