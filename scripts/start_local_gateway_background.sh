#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SESSION_NAME="model-gateway-local"
PID_FILE="${REPO_ROOT}/.omx/state/local-gateway.pid"
OUT_LOG="${REPO_ROOT}/.omx/logs/launchd-local-gateway.out.log"
ERR_LOG="${REPO_ROOT}/.omx/logs/launchd-local-gateway.err.log"
ROTATE_SUFFIX="$(date +%Y%m%d-%H%M%S)"

mkdir -p "${REPO_ROOT}/.omx/state" "${REPO_ROOT}/.omx/logs"
for log_file in "${OUT_LOG}" "${ERR_LOG}"; do
  if [[ -s "${log_file}" ]]; then
    mv "${log_file}" "${log_file}.${ROTATE_SUFFIX}"
  fi
done
touch "${OUT_LOG}" "${ERR_LOG}"

if tmux has-session -t "${SESSION_NAME}" >/dev/null 2>&1; then
  tmux list-panes -t "${SESSION_NAME}" -F '#{pane_pid}' | head -n 1 >"${PID_FILE}"
  echo "local gateway already running in tmux session ${SESSION_NAME}"
  exit 0
fi

tmux new-session -d -s "${SESSION_NAME}" "cd '${REPO_ROOT}' && exec '${REPO_ROOT}/scripts/run_local_gateway.sh' >>'${OUT_LOG}' 2>>'${ERR_LOG}'"
tmux list-panes -t "${SESSION_NAME}" -F '#{pane_pid}' | head -n 1 >"${PID_FILE}"
echo "started local gateway tmux session ${SESSION_NAME}"
