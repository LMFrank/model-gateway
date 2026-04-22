#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SESSION_NAME="model-gateway-local"
PID_FILE="${REPO_ROOT}/.omx/state/local-gateway.pid"

tmux kill-session -t "${SESSION_NAME}" >/dev/null 2>&1 || true
rm -f "${PID_FILE}"
