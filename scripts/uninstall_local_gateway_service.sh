#!/bin/bash
set -euo pipefail

SERVICE_LABEL="ai.model-gateway.local"
LAUNCH_AGENT_PATH="${HOME}/Library/LaunchAgents/${SERVICE_LABEL}.plist"
WRAPPER_PATH="${HOME}/.local/bin/model-gateway-local-runner.sh"
ENV_SNAPSHOT_PATH="${HOME}/.local/share/model-gateway/local-gateway.env"

launchctl bootout "gui/$(id -u)/${SERVICE_LABEL}" >/dev/null 2>&1 || true
rm -f "${LAUNCH_AGENT_PATH}" "${WRAPPER_PATH}" "${ENV_SNAPSHOT_PATH}"

echo "uninstalled launchd service ${SERVICE_LABEL}"
