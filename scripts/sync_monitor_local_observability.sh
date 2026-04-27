#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODE="${1:-}"

if [[ "${MODE}" != "enable" && "${MODE}" != "disable" ]]; then
  echo "usage: $0 <enable|disable>" >&2
  exit 1
fi

resolve_monitor_file_sd_dir() {
  if [[ -n "${MONITOR_FILE_SD_DIR:-}" ]]; then
    echo "${MONITOR_FILE_SD_DIR}"
    return 0
  fi

  local candidates=(
    "${REPO_ROOT}/../../AI/monitor/app/collector/file_sd"
    "${REPO_ROOT}/../AI/monitor/app/collector/file_sd"
    "${REPO_ROOT}/../monitor/app/collector/file_sd"
  )

  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -d "${candidate%/file_sd}" ]]; then
      echo "${candidate}"
      return 0
    fi
  done

  return 1
}

FILE_SD_DIR="$(resolve_monitor_file_sd_dir || true)"
TARGET_FILE=""
if [[ -n "${FILE_SD_DIR}" ]]; then
  TARGET_FILE="${FILE_SD_DIR}/model-gateway-local.json"
fi

if [[ -z "${TARGET_FILE}" ]]; then
  echo "monitor file_sd directory not found; skip syncing local observability target" >&2
  exit 0
fi

mkdir -p "${FILE_SD_DIR}"

if [[ "${MODE}" == "disable" ]]; then
  rm -f "${TARGET_FILE}"
  echo "removed ${TARGET_FILE}"
  exit 0
fi

set -a
source "${REPO_ROOT}/.env"
set +a

GATEWAY_HOST_PORT="${GATEWAY_PORT:-8080}"
APP_ENV_VALUE="${APP_ENV:-prod}"

cat >"${TARGET_FILE}" <<EOF
[
  {
    "targets": ["host.docker.internal:${GATEWAY_HOST_PORT}"],
    "labels": {
      "service": "model-gateway-api",
      "env": "${APP_ENV_VALUE}",
      "container": "model-gateway-local",
      "runtime": "local"
    }
  }
]
EOF

echo "updated ${TARGET_FILE}"
