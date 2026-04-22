#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODE="local"
WITH_STOCK="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"
      shift 2
      ;;
    --with-stock)
      WITH_STOCK="true"
      shift
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

if [[ "${MODE}" != "local" && "${MODE}" != "docker" ]]; then
  echo "--mode must be local or docker" >&2
  exit 1
fi

cd "${REPO_ROOT}"

CLIENT_TOKEN="$(python - <<'PY'
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if line.startswith('GATEWAY_CLIENT_TOKEN='):
        print(line.split('=',1)[1]); break
PY
)"
ADMIN_TOKEN="$(python - <<'PY'
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if line.startswith('GATEWAY_ADMIN_TOKEN='):
        print(line.split('=',1)[1]); break
PY
)"

export VERIFY_MODE="${MODE}"
export VERIFY_WITH_STOCK="${WITH_STOCK}"
export VERIFY_CLIENT_TOKEN="${CLIENT_TOKEN}"
export VERIFY_ADMIN_TOKEN="${ADMIN_TOKEN}"
export VERIFY_PUBLIC_SMOKE_MODEL="${VERIFY_PUBLIC_SMOKE_MODEL:-qwen3.6-plus}"
export VERIFY_EXTRA_MODELS="${VERIFY_EXTRA_MODELS:-}"

python - <<'PY'
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

mode = os.environ["VERIFY_MODE"]
with_stock = os.environ["VERIFY_WITH_STOCK"] == "true"
client_token = os.environ["VERIFY_CLIENT_TOKEN"]
admin_token = os.environ["VERIFY_ADMIN_TOKEN"]
public_smoke_model = os.environ["VERIFY_PUBLIC_SMOKE_MODEL"].strip()
extra_models = [
    item.strip()
    for item in os.environ.get("VERIFY_EXTRA_MODELS", "").split(",")
    if item.strip()
]
smoke_models = [public_smoke_model, *extra_models]

base = "http://127.0.0.1:8080"
ui_base = "http://127.0.0.1:8620"


def fetch_json(url: str, *, token: str | None = None, method: str = "GET", body: dict | None = None, timeout: int = 60):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode())


status, health = fetch_json(f"{base}/healthz")
assert status == 200 and health.get("status") == "ok", (status, health)
print("ok healthz")

status, models = fetch_json(f"{base}/v1/models", token=client_token)
client_models = {item["id"] for item in models.get("data", [])}
for model_key in smoke_models:
    assert model_key in client_models, (model_key, client_models)
print("ok v1/models")

from datetime import date

today = date.today().isoformat()
for path in ("/api/providers", "/api/models", "/api/routes", "/admin/calls?limit=3", f"/admin/usage/summary?date_from={today}&date_to={today}"):
    status, _ = fetch_json(f"{base}{path}", token=admin_token)
    assert status == 200, path
print("ok admin endpoints")

for model in smoke_models:
    status, response = fetch_json(
        f"{base}/v1/chat/completions",
        token=client_token,
        method="POST",
        body={"model": model, "messages": [{"role": "user", "content": "回复OK，不要解释。"}], "temperature": 0},
    )
    content = ((response.get("choices") or [{}])[0].get("message") or {}).get("content", "")
    assert status == 200 and "OK" in content, (model, status, content)
print("ok smoke model chat", ", ".join(smoke_models))

_, admin_models_payload = fetch_json(f"{base}/api/models", token=admin_token)
admin_models = admin_models_payload.get("items") or []

resolved_models = {}
for model_key in smoke_models:
    for item in admin_models:
        if item.get("model_key") == model_key:
            resolved_models[model_key] = item
            break
    else:
        raise AssertionError(f"model not found in admin listing: {model_key}")

provider_expectations = []
seen_provider_ids = set()
for item in resolved_models.values():
    provider = item.get("provider") or {}
    provider_id = provider.get("id")
    provider_label = provider.get("display_name") or provider.get("name") or str(provider_id)
    assert provider_id is not None, item
    if provider_id in seen_provider_ids:
        continue
    seen_provider_ids.add(provider_id)
    provider_expectations.append((provider_id, provider_label))

for provider_id, label in provider_expectations:
    status, response = fetch_json(
        f"{base}/api/health/check/provider/{provider_id}",
        token=admin_token,
        method="POST",
    )
    assert status == 200 and response.get("status") == "healthy", (label, response)
print("ok provider health")

for model_key, item in resolved_models.items():
    model_id = item.get("id")
    assert model_id is not None, item
    status, response = fetch_json(
        f"{base}/api/health/check/model/{model_id}",
        token=admin_token,
        method="POST",
    )
    assert status == 200 and response.get("status") == "healthy", (model_key, response)
print("ok model health")

status, providers = fetch_json(f"{ui_base}/api/providers", token=admin_token)
assert status == 200 and isinstance(providers.get("items"), list), providers
print("ok frontend api proxy")

if with_stock:
    stock_base = "http://127.0.0.1:8501"
    status, payload = fetch_json(
        f"{stock_base}/api/analyze/single",
        method="POST",
        body={"code": "300757", "save_prediction": False},
    )
    task_id = ((payload.get("data") or {}).get("task_id"))
    assert status == 200 and task_id, payload
    deadline = time.time() + 180
    while time.time() < deadline:
        _, task = fetch_json(f"{stock_base}/api/tasks/{task_id}")
        task_data = task.get("data") or {}
        if task_data.get("status") in {"success", "failed", "partial_success"}:
            assert task_data.get("status") == "success", task_data
            print("ok stock analyze", task_id)
            break
        time.sleep(2)
    else:
        raise AssertionError(f"stock task timeout: {task_id}")

print("VERIFY_RUNTIME_OK", mode, "with_stock=" + str(with_stock).lower())
PY
