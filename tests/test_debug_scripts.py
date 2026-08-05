from __future__ import annotations

import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEBUG_SCRIPT = REPO_ROOT / "scripts" / "debug" / "model_gateway_debug_bundle.sh"
LOCAL_RUNTIME_SCRIPTS = (
    REPO_ROOT / "scripts" / "switch_to_local_runtime.sh",
    REPO_ROOT / "scripts" / "verify_runtime.sh",
)


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


def test_local_runtime_scripts_use_available_python3_entrypoint() -> None:
    for script in LOCAL_RUNTIME_SCRIPTS:
        text = script.read_text()
        assert re.search(r"(?m)(?<![A-Za-z0-9_])python(?:\s|$)", text) is None
        assert "\npython3 - <<'PY'\n" in text
