#!/usr/bin/env python3
"""Start the backend server for E2E testing."""
import sys
import os

# Set project root on path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# Fix Windows: services/control_plane is a broken symlink (text file)
# Create proper module redirection
import types
import importlib.util

# Ensure 'services' package exists
services_dir = os.path.join(ROOT, "services")
if "services" not in sys.modules:
    services = types.ModuleType("services")
    services.__path__ = [services_dir]
    services.__package__ = "services"
    init_file = os.path.join(services_dir, "__init__.py")
    if os.path.exists(init_file):
        exec(open(init_file).read(), services.__dict__)
    sys.modules["services"] = services

# Map services.control_plane -> services/control-plane
cp_dir = os.path.join(services_dir, "control-plane")
if os.path.isdir(cp_dir) and "services.control_plane" not in sys.modules:
    cp_mod = types.ModuleType("services.control_plane")
    cp_mod.__path__ = [cp_dir]
    cp_mod.__package__ = "services.control_plane"
    cp_init = os.path.join(cp_dir, "__init__.py")
    if os.path.exists(cp_init):
        exec(open(cp_init).read(), cp_mod.__dict__)
    sys.modules["services.control_plane"] = cp_mod

# Do the same for worker modules
for worker in ["worker-http", "worker-browser", "worker-ai", "worker-hard-target"]:
    mod_name = f"services.{worker.replace('-', '_')}"
    worker_dir = os.path.join(services_dir, worker)
    if os.path.isdir(worker_dir) and mod_name not in sys.modules:
        wmod = types.ModuleType(mod_name)
        wmod.__path__ = [worker_dir]
        wmod.__package__ = mod_name
        sys.modules[mod_name] = wmod

# Set environment
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_e2e.db")
os.environ.setdefault("QUEUE_BACKEND", "memory")
os.environ.setdefault("STORAGE_TYPE", "filesystem")
os.environ.setdefault("SECRET_KEY", "test-secret-key-e2e")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5199")

if __name__ == "__main__":
    import uvicorn
    # Now import should work
    from services.control_plane.app import app
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="warning")
