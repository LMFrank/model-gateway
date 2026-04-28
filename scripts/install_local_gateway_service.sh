#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_LABEL="ai.model-gateway.local"
MAINTENANCE_LABEL="ai.model-gateway.local-log-maintenance"
LAUNCH_AGENT_DIR="${HOME}/Library/LaunchAgents"
LAUNCH_AGENT_PATH="${LAUNCH_AGENT_DIR}/${SERVICE_LABEL}.plist"
MAINTENANCE_AGENT_PATH="${LAUNCH_AGENT_DIR}/${MAINTENANCE_LABEL}.plist"
WRAPPER_DIR="${HOME}/.local/bin"
WRAPPER_PATH="${WRAPPER_DIR}/model-gateway-local-runner.sh"
ROTATE_WRAPPER_PATH="${WRAPPER_DIR}/model-gateway-local-logrotate.sh"
STATE_DIR="${HOME}/.local/share/model-gateway"
ENV_SNAPSHOT_PATH="${STATE_DIR}/local-gateway.env"
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
LOG_DIR="${STATE_DIR}/logs"
ROTATE_SUFFIX="$(date +%Y%m%d-%H%M%S)"

mkdir -p "${LAUNCH_AGENT_DIR}" "${WRAPPER_DIR}" "${STATE_DIR}" "${LOG_DIR}"

for log_file in "${LOG_DIR}/launchd-local-gateway.out.log" "${LOG_DIR}/launchd-local-gateway.err.log"; do
  if [[ -s "${log_file}" ]]; then
    mv "${log_file}" "${log_file}.${ROTATE_SUFFIX}"
  fi
done

"${REPO_ROOT}/scripts/stop_local_gateway_background.sh" >/dev/null 2>&1 || true

cp "${REPO_ROOT}/.env" "${ENV_SNAPSHOT_PATH}"
chmod 600 "${ENV_SNAPSHOT_PATH}"

cat > "${WRAPPER_PATH}" <<EOF
#!/bin/bash
set -euo pipefail
REPO_ROOT="${REPO_ROOT}"
LOG_DIR="${LOG_DIR}"
ENV_SNAPSHOT_PATH="${ENV_SNAPSHOT_PATH}"
mkdir -p "\${LOG_DIR}"
set -a
source "\${ENV_SNAPSHOT_PATH}"
set +a
export PG_HOST="\${PG_HOST_OVERRIDE:-127.0.0.1}"
export GATEWAY_PORT="\${GATEWAY_PORT:-8080}"
if [[ -n "\${CODEX_HOME_DIR:-}" && "\${CODEX_HOME_DIR}" != /* ]]; then
  export CODEX_HOME_DIR="\${REPO_ROOT}/\${CODEX_HOME_DIR#./}"
fi
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
"${PYTHON_BIN}" -m uvicorn --app-dir "\${REPO_ROOT}" app.main:app --host 0.0.0.0 --port "\${GATEWAY_PORT}" >> "\${LOG_DIR}/uvicorn.out.log" 2>> "\${LOG_DIR}/uvicorn.err.log" &
child_pid=\$!
trap 'kill "\${child_pid}" >/dev/null 2>&1 || true' TERM INT HUP
wait "\${child_pid}"
EOF
chmod +x "${WRAPPER_PATH}"

cat > "${ROTATE_WRAPPER_PATH}" <<EOF
#!/bin/bash
set -euo pipefail
set -a
source "${ENV_SNAPSHOT_PATH}"
set +a
LOG_DIR="${LOG_DIR}"
RETENTION_DAYS="\${LOCAL_GATEWAY_LOG_RETENTION_DAYS:-7}"
ROTATE_SUFFIX="\$(date +%Y%m%d-%H%M%S)"
mkdir -p "\${LOG_DIR}"
shopt -s nullglob
for log_file in "\${LOG_DIR}"/*.log; do
  if [[ -s "\${log_file}" ]]; then
    cp "\${log_file}" "\${log_file}.\${ROTATE_SUFFIX}"
    : > "\${log_file}"
  fi
done
find "\${LOG_DIR}" -type f -name '*.log.*' -mtime "+\${RETENTION_DAYS}" -delete
EOF
chmod +x "${ROTATE_WRAPPER_PATH}"

cat > "${LAUNCH_AGENT_PATH}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${SERVICE_LABEL}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>${WRAPPER_PATH}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${STATE_DIR}</string>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/launchd-local-gateway.out.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/launchd-local-gateway.err.log</string>
    <key>EnvironmentVariables</key>
    <dict>
      <key>HOME</key>
      <string>${HOME}</string>
      <key>PATH</key>
      <string>${WRAPPER_DIR}:/opt/anaconda3/bin:/Users/xushuchi/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
  </dict>
</plist>
EOF

cat > "${MAINTENANCE_AGENT_PATH}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${MAINTENANCE_LABEL}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>${ROTATE_WRAPPER_PATH}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${STATE_DIR}</string>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/launchd-local-gateway-rotate.out.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/launchd-local-gateway-rotate.err.log</string>
    <key>StartCalendarInterval</key>
    <dict>
      <key>Hour</key>
      <integer>0</integer>
      <key>Minute</key>
      <integer>5</integer>
    </dict>
    <key>EnvironmentVariables</key>
    <dict>
      <key>HOME</key>
      <string>${HOME}</string>
      <key>PATH</key>
      <string>${WRAPPER_DIR}:/opt/anaconda3/bin:/Users/xushuchi/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
  </dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/${SERVICE_LABEL}" >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)/${MAINTENANCE_LABEL}" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "${LAUNCH_AGENT_PATH}"
launchctl kickstart -k "gui/$(id -u)/${SERVICE_LABEL}"
launchctl bootstrap "gui/$(id -u)" "${MAINTENANCE_AGENT_PATH}"
launchctl kickstart -k "gui/$(id -u)/${MAINTENANCE_LABEL}"
"${REPO_ROOT}/scripts/sync_monitor_local_observability.sh" enable >/dev/null || true

echo "installed launchd service ${SERVICE_LABEL}"
