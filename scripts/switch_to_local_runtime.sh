#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_LABEL="ai.model-gateway.local"
LAUNCH_AGENT_PATH="${HOME}/Library/LaunchAgents/${SERVICE_LABEL}.plist"

cd "${REPO_ROOT}"

set -a
source "${REPO_ROOT}/.env"
set +a

GATEWAY_HOST_PORT="${GATEWAY_PORT:-8080}"

docker rm -f model-gateway >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)/${SERVICE_LABEL}" >/dev/null 2>&1 || true
"${REPO_ROOT}/scripts/stop_local_gateway_background.sh"
"${REPO_ROOT}/scripts/start_local_gateway_background.sh"

python - <<'PY'
import json
import time
import urllib.request

deadline = time.time() + 30
last_error = None
while time.time() < deadline:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8080/healthz", timeout=2) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("status") == "ok":
                print("local gateway ready")
                break
    except Exception as exc:  # noqa: BLE001
        last_error = exc
        time.sleep(1)
else:
    raise SystemExit(f"local gateway failed to become ready: {last_error}")
PY

FRONTEND_GATEWAY_UPSTREAM=host.docker.internal docker compose up -d --build frontend >/dev/null

echo "switched model-gateway to local runtime on host:${GATEWAY_HOST_PORT}"
