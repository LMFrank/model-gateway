#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODE="local"
WITH_STOCK="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"
      shift 2
      ;;
    --with-stock)
      WITH_STOCK="true"
      shift
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

if [[ "${MODE}" != "local" && "${MODE}" != "docker" ]]; then
  echo "--mode must be local or docker" >&2
  exit 1
fi

cd "${REPO_ROOT}"

if [[ "${MODE}" == "local" ]]; then
  ./scripts/switch_to_local_runtime.sh
else
  ./scripts/switch_to_docker_runtime.sh
fi

if [[ "${WITH_STOCK}" == "true" ]]; then
  if [[ -d "${REPO_ROOT}/../StockAgents" ]]; then
    (
      cd "${REPO_ROOT}/../StockAgents"
      docker compose up -d --force-recreate stockagents-core stockagents-webui
    )
  else
    echo "StockAgents repo not found next to model-gateway" >&2
    exit 1
  fi
fi

VERIFY_ARGS=(--mode "${MODE}")
if [[ "${WITH_STOCK}" == "true" ]]; then
  VERIFY_ARGS+=(--with-stock)
fi

./scripts/verify_runtime.sh "${VERIFY_ARGS[@]}"

echo "RELEASE_RUNTIME_OK mode=${MODE} with_stock=${WITH_STOCK}"
