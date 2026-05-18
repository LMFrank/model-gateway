#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Model Gateway lightweight debug bundle for Codex/OpenCode.

Usage:
  bash scripts/debug/model_gateway_debug_bundle.sh [--request-id REQ] [--model MODEL] [--provider PROVIDER] [--recent 15m]

Options:
  --request-id ID      Filter admin call-log preview and Loki logs by request_id.
  --model MODEL        Filter admin call logs and Loki logs by model name.
  --provider NAME      Add provider name filter to Loki logs.
  --status STATUS      Filter admin call logs by status (success/failed).
  --recent WINDOW      Lookback window for Loki queries. Supports Ns, Nm, Nh, Nd. Default: 15m.
  --gateway-url URL    Gateway base URL. Default: GATEWAY_URL or http://127.0.0.1:8080.
  --prom-url URL       Prometheus base URL. Default: PROM_URL or http://127.0.0.1:9090.
  --loki-url URL       Loki base URL. Default: LOKI_URL or http://127.0.0.1:3100.
  --services REGEX     Monitor service regex. Default: model-gateway-api|model-gateway-ui.
  --limit N            Max rows/log lines per section. Default: 20.
  -h, --help           Show this help.

This script is read-only. It does not restart services, mutate DB rows, or delete logs.
USAGE
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

REQUEST_ID=""
MODEL_NAME=""
PROVIDER_NAME=""
STATUS_FILTER=""
RECENT="${RECENT:-15m}"
GATEWAY_URL="${GATEWAY_URL:-http://127.0.0.1:${GATEWAY_PORT:-8080}}"
PROM_URL="${PROM_URL:-http://127.0.0.1:9090}"
LOKI_URL="${LOKI_URL:-http://127.0.0.1:3100}"
SERVICES_REGEX="${DEBUG_SERVICES_REGEX:-model-gateway-api|model-gateway-ui}"
LOG_LIMIT="${LOG_LIMIT:-20}"
LOCAL_LOG_DIR="${MODEL_GATEWAY_LOCAL_LOG_DIR:-${HOME}/.local/share/model-gateway/logs}"
REPO_LOG_DIR="${ROOT_DIR}/.omx/logs"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --request-id) REQUEST_ID="${2:-}"; shift 2 ;;
    --model) MODEL_NAME="${2:-}"; shift 2 ;;
    --provider) PROVIDER_NAME="${2:-}"; shift 2 ;;
    --status) STATUS_FILTER="${2:-}"; shift 2 ;;
    --recent) RECENT="${2:-}"; shift 2 ;;
    --gateway-url) GATEWAY_URL="${2:-}"; shift 2 ;;
    --prom-url) PROM_URL="${2:-}"; shift 2 ;;
    --loki-url) LOKI_URL="${2:-}"; shift 2 ;;
    --services) SERVICES_REGEX="${2:-}"; shift 2 ;;
    --limit) LOG_LIMIT="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

export REQUEST_ID MODEL_NAME PROVIDER_NAME STATUS_FILTER RECENT GATEWAY_URL PROM_URL LOKI_URL SERVICES_REGEX LOG_LIMIT LOCAL_LOG_DIR REPO_LOG_DIR
export GATEWAY_ADMIN_TOKEN="${GATEWAY_ADMIN_TOKEN:-}"
export GATEWAY_CLIENT_TOKEN="${GATEWAY_CLIENT_TOKEN:-}"

python - <<'PY'
from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REQUEST_ID = os.getenv("REQUEST_ID", "").strip()
MODEL_NAME = os.getenv("MODEL_NAME", "").strip()
PROVIDER_NAME = os.getenv("PROVIDER_NAME", "").strip()
STATUS_FILTER = os.getenv("STATUS_FILTER", "").strip()
RECENT = os.getenv("RECENT", "15m").strip() or "15m"
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://127.0.0.1:8080").rstrip("/")
PROM_URL = os.getenv("PROM_URL", "http://127.0.0.1:9090").rstrip("/")
LOKI_URL = os.getenv("LOKI_URL", "http://127.0.0.1:3100").rstrip("/")
SERVICES_REGEX = os.getenv("SERVICES_REGEX", "model-gateway-api|model-gateway-ui").strip() or "model-gateway-api|model-gateway-ui"
LOG_LIMIT = int(os.getenv("LOG_LIMIT", "20") or "20")
ADMIN_TOKEN = os.getenv("GATEWAY_ADMIN_TOKEN", "").strip()
CLIENT_TOKEN = os.getenv("GATEWAY_CLIENT_TOKEN", "").strip()
LOCAL_LOG_DIR = Path(os.getenv("LOCAL_LOG_DIR", "")).expanduser()
REPO_LOG_DIR = Path(os.getenv("REPO_LOG_DIR", ".omx/logs")).expanduser()
TIMEOUT = 8
ERROR_PATTERN = r'(?i)("level"\s*:\s*"(error|warning|critical)"|traceback|fatal|panic|exception|HTTPException|provider_.*failed|route_rule_fetch_failed|call_log_insert_failed)'


def parse_window(value: str) -> int:
    match = re.fullmatch(r"\s*(\d+)\s*([smhd]?)\s*", value or "")
    if not match:
        return 15 * 60
    amount = int(match.group(1))
    unit = match.group(2) or "s"
    return amount * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]


def get_json(url: str, *, token: str | None = None) -> tuple[int | None, Any | None, str | None]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            raw = response.read().decode("utf-8", errors="replace")
            try:
                return response.status, json.loads(raw), None
            except json.JSONDecodeError:
                return response.status, None, raw[:1000]
    except Exception as exc:  # noqa: BLE001 - debug tool must continue after partial failure
        return None, None, str(exc)


def print_json_preview(title: str, payload: Any, *, max_chars: int = 3000) -> None:
    print(f"\n=== {title} ===")
    if payload is None:
        print("NO_DATA")
        return
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if len(text) > max_chars:
        print(text[:max_chars].rstrip())
        print(f"... <truncated {len(text) - max_chars} chars>")
    else:
        print(text)


def print_gateway_health() -> None:
    print("\n=== Gateway health ===")
    status, data, err = get_json(f"{GATEWAY_URL}/healthz")
    if err:
        print(f"WARN healthz unavailable: {err}")
    else:
        print(json.dumps({"http_status": status, "payload": data}, ensure_ascii=False))

    status, data, err = get_json(f"{GATEWAY_URL}/api/health/summary", token=ADMIN_TOKEN or None)
    if not ADMIN_TOKEN:
        print("WARN skip /api/health/summary: GATEWAY_ADMIN_TOKEN is not set")
    elif err:
        print(f"WARN health summary unavailable: {err}")
    else:
        print_json_preview("provider/model health summary", data, max_chars=1800)


def print_prometheus_targets() -> None:
    print("\n=== Prometheus target health ===")
    status, data, err = get_json(f"{PROM_URL}/api/v1/targets")
    if err or not isinstance(data, dict):
        print(f"WARN unable to query Prometheus targets: {err or status}")
        return
    regex = re.compile(SERVICES_REGEX)
    found = False
    for target in data.get("data", {}).get("activeTargets", []):
        labels = target.get("labels", {}) if isinstance(target, dict) else {}
        service = str(labels.get("service") or labels.get("job") or "")
        if not regex.search(service):
            continue
        found = True
        print(json.dumps({
            "service": service,
            "job": labels.get("job"),
            "health": target.get("health"),
            "scrapeUrl": target.get("scrapeUrl"),
            "lastError": target.get("lastError"),
            "lastScrape": target.get("lastScrape"),
        }, ensure_ascii=False))
    if not found:
        print(f"WARN no matching targets for service regex: {SERVICES_REGEX}")


def print_admin_calls() -> None:
    print("\n=== Recent admin call logs ===")
    if not ADMIN_TOKEN:
        print("WARN skip /admin/calls: GATEWAY_ADMIN_TOKEN is not set")
        return
    params: dict[str, str | int] = {"limit": min(max(LOG_LIMIT, 1), 100)}
    if MODEL_NAME:
        params["model"] = MODEL_NAME
    if STATUS_FILTER:
        params["status"] = STATUS_FILTER
    url = f"{GATEWAY_URL}/admin/calls?{urllib.parse.urlencode(params)}"
    status, data, err = get_json(url, token=ADMIN_TOKEN)
    if err or not isinstance(data, dict):
        print(f"WARN call logs unavailable: {err or status}")
        return
    items = data.get("items") or data.get("data") or []
    if REQUEST_ID and isinstance(items, list):
        items = [row for row in items if isinstance(row, dict) and str(row.get("request_id")) == REQUEST_ID]
    preview = {"total": data.get("total"), "matched_preview": items[:LOG_LIMIT] if isinstance(items, list) else items}
    print_json_preview("call log preview", preview, max_chars=5000)


def print_usage_summary() -> None:
    if not ADMIN_TOKEN:
        return
    today = time.strftime("%Y-%m-%d")
    status, data, err = get_json(
        f"{GATEWAY_URL}/admin/usage/summary?{urllib.parse.urlencode({'date_from': today, 'date_to': today})}",
        token=ADMIN_TOKEN,
    )
    if err:
        print(f"\n=== Usage summary ===\nWARN usage summary unavailable: {err}")
    else:
        print_json_preview(f"usage summary {today}", data, max_chars=2500)


def _logql_double_quoted(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_loki_query(*, errors_only: bool) -> str:
    query = f'{{job="docker", service=~"{SERVICES_REGEX}"}}'
    for value in [REQUEST_ID, MODEL_NAME, PROVIDER_NAME]:
        if value:
            query += f' |= "{_logql_double_quoted(value)}"'
    if errors_only:
        query += f' |~ "{_logql_double_quoted(ERROR_PATTERN)}"'
    return query


def query_loki(title: str, query: str) -> None:
    print(f"\n=== {title} ===")
    print(f"LogQL: {query}")
    now = time.time()
    params = urllib.parse.urlencode({
        "query": query,
        "limit": LOG_LIMIT,
        "start": int((now - parse_window(RECENT)) * 1e9),
        "end": int(now * 1e9),
        "direction": "backward",
    })
    status, data, err = get_json(f"{LOKI_URL}/loki/api/v1/query_range?{params}")
    if err or not isinstance(data, dict):
        print(f"WARN unable to query Loki: {err or status}")
        return
    result = data.get("data", {}).get("result", [])
    if not result:
        print("NO_RESULT")
        return
    for stream in result[:8]:
        labels = stream.get("stream", {}) if isinstance(stream, dict) else {}
        print(json.dumps({key: labels.get(key) for key in ["service", "container", "env", "runtime"]}, ensure_ascii=False))
        for _, line in (stream.get("values") or [])[:5]:
            print("  - " + str(line).replace("\n", " ")[:700])


def print_local_logs() -> None:
    print("\n=== Latest local runtime files ===")
    candidates: list[Path] = []
    for directory in [LOCAL_LOG_DIR, REPO_LOG_DIR]:
        if directory.is_dir():
            candidates.extend(path for path in directory.glob("*.log*") if path.is_file())
    if not candidates:
        print("WARN no local model-gateway log files found")
        return
    latest = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[:4]
    for path in latest:
        print(f"--- {path}")
        try:
            out = subprocess.run(["tail", "-n", "12", str(path)], check=False, capture_output=True, text=True, timeout=3)
            print((out.stdout or out.stderr).rstrip()[:3000] or "<empty>")
        except Exception as exc:  # noqa: BLE001
            print(f"WARN unable to tail {path}: {exc}")


print("Model Gateway debug bundle (read-only)")
print(json.dumps({
    "request_id": REQUEST_ID or None,
    "model": MODEL_NAME or None,
    "provider": PROVIDER_NAME or None,
    "status": STATUS_FILTER or None,
    "recent": RECENT,
    "gateway_url": GATEWAY_URL,
    "prom_url": PROM_URL,
    "loki_url": LOKI_URL,
    "services_regex": SERVICES_REGEX,
    "limit": LOG_LIMIT,
}, ensure_ascii=False, indent=2))

print_gateway_health()
print_prometheus_targets()
print_admin_calls()
print_usage_summary()
query_loki("Loki recent structured warnings/errors", build_loki_query(errors_only=True))
query_loki("Loki recent logs", build_loki_query(errors_only=False))
print_local_logs()

print("\n=== Next-step hints ===")
print("- healthz/Prometheus target 不通：先看本地 launchd/docker runtime 与 monitor file_sd。")
print("- call_logs 有 failed：用 --request-id 复查 admin call log，并在 Loki 中用同一 request_id 过滤。")
print("- Loki 无 request_id：确认请求响应头 X-Request-Id，或检查调用方是否记录/回传该值。")
PY
