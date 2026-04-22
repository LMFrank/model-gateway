#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${REPO_ROOT}/.omx/logs"

mkdir -p "${LOG_DIR}"

cd "${REPO_ROOT}"

set -a
source "${REPO_ROOT}/.env"
set +a

export PG_HOST="${PG_HOST_OVERRIDE:-127.0.0.1}"
export GATEWAY_PORT="${GATEWAY_PORT:-8080}"
export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

PYTHON_BIN="${LOCAL_GATEWAY_PYTHON:-$(command -v python)}"
exec "${PYTHON_BIN}" -m uvicorn app.main:app --host 0.0.0.0 --port "${GATEWAY_PORT}"
