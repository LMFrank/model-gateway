#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${REPO_ROOT}/.omx/logs"

mkdir -p "${LOG_DIR}"

set -a
source "${REPO_ROOT}/.env"
set +a

export PG_HOST="${PG_HOST_OVERRIDE:-127.0.0.1}"
export GATEWAY_PORT="${GATEWAY_PORT:-8080}"
if [[ -n "${CODEX_HOME_DIR:-}" && "${CODEX_HOME_DIR}" != /* ]]; then
  export CODEX_HOME_DIR="${REPO_ROOT}/${CODEX_HOME_DIR#./}"
fi
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

STOCK_CONDA_PYTHON="/opt/anaconda3/envs/stock/bin/python"
if [[ -n "${LOCAL_GATEWAY_PYTHON:-}" ]]; then
  PYTHON_BIN="${LOCAL_GATEWAY_PYTHON}"
elif [[ -x "${STOCK_CONDA_PYTHON}" ]]; then
  PYTHON_BIN="${STOCK_CONDA_PYTHON}"
elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
fi

exec "${PYTHON_BIN}" -m uvicorn --app-dir "${REPO_ROOT}" app.main:app --host 0.0.0.0 --port "${GATEWAY_PORT}"
