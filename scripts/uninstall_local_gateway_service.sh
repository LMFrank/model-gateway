#!/bin/bash
set -euo pipefail

SERVICE_LABEL="ai.model-gateway.local"
MAINTENANCE_LABEL="ai.model-gateway.local-log-maintenance"
LAUNCH_AGENT_PATH="${HOME}/Library/LaunchAgents/${SERVICE_LABEL}.plist"
MAINTENANCE_AGENT_PATH="${HOME}/Library/LaunchAgents/${MAINTENANCE_LABEL}.plist"
WRAPPER_PATH="${HOME}/.local/bin/model-gateway-local-runner.sh"
ROTATE_WRAPPER_PATH="${HOME}/.local/bin/model-gateway-local-logrotate.sh"
ENV_SNAPSHOT_PATH="${HOME}/.local/share/model-gateway/local-gateway.env"

launchctl bootout "gui/$(id -u)/${SERVICE_LABEL}" >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)/${MAINTENANCE_LABEL}" >/dev/null 2>&1 || true
rm -f "${LAUNCH_AGENT_PATH}" "${MAINTENANCE_AGENT_PATH}" "${WRAPPER_PATH}" "${ROTATE_WRAPPER_PATH}" "${ENV_SNAPSHOT_PATH}"

echo "uninstalled launchd service ${SERVICE_LABEL}"
