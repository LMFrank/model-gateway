#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_LABEL="ai.model-gateway.local"

cd "${REPO_ROOT}"

"${REPO_ROOT}/scripts/stop_local_gateway_background.sh"
launchctl bootout "gui/$(id -u)/${SERVICE_LABEL}" >/dev/null 2>&1 || true
docker rm -f model-gateway >/dev/null 2>&1 || true
"${REPO_ROOT}/scripts/sync_monitor_local_observability.sh" disable >/dev/null || true

FRONTEND_GATEWAY_UPSTREAM=model-gateway \
  docker compose --profile docker-runtime up -d --build model-gateway frontend >/dev/null

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
                print("docker gateway ready")
                break
    except Exception as exc:  # noqa: BLE001
        last_error = exc
        time.sleep(1)
else:
    raise SystemExit(f"docker gateway failed to become ready: {last_error}")
PY

echo "switched model-gateway to docker runtime on host:8080"
