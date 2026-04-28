#!/bin/bash
set -euo pipefail

STATE_DIR="${HOME}/.local/share/model-gateway"
LOG_DIR="${STATE_DIR}/logs"
RETENTION_DAYS="${LOCAL_GATEWAY_LOG_RETENTION_DAYS:-7}"
ROTATE_SUFFIX="$(date +%Y%m%d-%H%M%S)"

mkdir -p "${LOG_DIR}"

shopt -s nullglob
for log_file in "${LOG_DIR}"/*.log; do
  if [[ -s "${log_file}" ]]; then
    cp "${log_file}" "${log_file}.${ROTATE_SUFFIX}"
    : > "${log_file}"
  fi
done

find "${LOG_DIR}" -type f -name '*.log.*' -mtime "+${RETENTION_DAYS}" -delete
