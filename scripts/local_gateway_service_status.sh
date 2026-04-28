#!/bin/bash
set -euo pipefail

SERVICE_LABEL="ai.model-gateway.local"
MAINTENANCE_LABEL="ai.model-gateway.local-log-maintenance"

echo "=== ${SERVICE_LABEL} ==="
launchctl print "gui/$(id -u)/${SERVICE_LABEL}" | sed -n '1,120p'
echo
echo "=== ${MAINTENANCE_LABEL} ==="
launchctl print "gui/$(id -u)/${MAINTENANCE_LABEL}" | sed -n '1,120p'
