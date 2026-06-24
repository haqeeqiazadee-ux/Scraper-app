from __future__ import annotations

import os
import subprocess
import sys


def test_hyphenated_service_directories_import_without_pytest_conftest() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.getcwd()

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import services.control_plane.routers.actors; "
                "import services.worker_http; "
                "assert services.worker_http.__path__; "
                "print('ok')"
            ),
        ],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
