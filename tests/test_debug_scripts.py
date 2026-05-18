from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEBUG_SCRIPT = REPO_ROOT / "scripts" / "debug" / "model_gateway_debug_bundle.sh"


def test_model_gateway_debug_bundle_is_shell_valid() -> None:
    subprocess.run(["bash", "-n", str(DEBUG_SCRIPT)], check=True)


def test_model_gateway_debug_bundle_supports_help() -> None:
    result = subprocess.run(
        ["bash", str(DEBUG_SCRIPT), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Usage:" in result.stdout
    assert "read-only" in result.stdout
