#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SESSION_NAME="model-gateway-local"
PID_FILE="${REPO_ROOT}/.omx/state/local-gateway.pid"

mkdir -p "${REPO_ROOT}/.omx/state" "${REPO_ROOT}/.omx/logs"

if tmux has-session -t "${SESSION_NAME}" >/dev/null 2>&1; then
  tmux list-panes -t "${SESSION_NAME}" -F '#{pane_pid}' | head -n 1 >"${PID_FILE}"
  echo "local gateway already running in tmux session ${SESSION_NAME}"
  exit 0
fi

tmux new-session -d -s "${SESSION_NAME}" "cd '${REPO_ROOT}' && '${REPO_ROOT}/scripts/run_local_gateway.sh'"
tmux list-panes -t "${SESSION_NAME}" -F '#{pane_pid}' | head -n 1 >"${PID_FILE}"
echo "started local gateway tmux session ${SESSION_NAME}"
