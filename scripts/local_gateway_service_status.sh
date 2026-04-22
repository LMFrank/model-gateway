#!/bin/bash
set -euo pipefail

SERVICE_LABEL="ai.model-gateway.local"
launchctl print "gui/$(id -u)/${SERVICE_LABEL}" | sed -n '1,120p'
