import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"

SCRIPT = (
    "import asyncio, logging\n"
    "from core.app.contextmanager import AppContextManager\n"
    "asyncio.run(AppContextManager().startup(None))\n"
    "logging.getLogger('probe').info('probe-line')\n"
)


def _run(tmp_path: Path, script: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_startup_configures_logging_when_the_launcher_did_not(tmp_path: Path) -> None:
    result = _run(tmp_path, SCRIPT)

    assert result.returncode == 0, result.stderr
    assert "probe-line" in result.stdout
    assert "Starting AppContextManager" in result.stdout
    assert (tmp_path / "logs" / "app.log").exists()


def test_startup_keeps_an_existing_logging_setup(tmp_path: Path) -> None:
    script = "import logging\nlogging.basicConfig(level='INFO')\n" + SCRIPT

    result = _run(tmp_path, script)

    assert result.returncode == 0, result.stderr
    assert "Logging configured" not in result.stdout + result.stderr
    assert not (tmp_path / "logs").exists()
