#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

COMPOSE_FILE="${CONTENT_PILOT_COMPOSE_FILE:-compose.prod.yaml}"
ENV_FILE="${CONTENT_PILOT_ENV_FILE:-.env}"

if [[ -z "${CONTENT_PILOT_IMAGE:-}" ]]; then
  echo "CONTENT_PILOT_IMAGE must be set to a GHCR image tag." >&2
  exit 1
fi

compose=(docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}")

"${compose[@]}" pull
"${compose[@]}" up -d content-pilot-db content-pilot-redis
"${compose[@]}" stop content-pilot-api content-pilot-worker content-pilot-beat
"${compose[@]}" run --rm --no-deps content-pilot-api alembic upgrade head
"${compose[@]}" up -d --no-build content-pilot-api content-pilot-worker content-pilot-beat
"${compose[@]}" ps

for service in content-pilot-api content-pilot-worker content-pilot-beat; do
  if ! "${compose[@]}" ps --status running --services | grep -qx "${service}"; then
    echo "Required service is not running: ${service}" >&2
    exit 1
  fi
done

if [[ -n "${CONTENT_PILOT_HEALTH_URL:-}" ]]; then
  HEALTH_URL="${CONTENT_PILOT_HEALTH_URL}"
else
  API_ADDRESS="$("${compose[@]}" port content-pilot-api 8000)"
  HEALTH_URL="http://${API_ADDRESS}/health"
fi

for attempt in {1..15}; do
  if curl --fail --silent --show-error "${HEALTH_URL}" >/dev/null; then
    echo "ContentPilot healthcheck passed: ${HEALTH_URL}"
    exit 0
  fi
  sleep 2
done

echo "ContentPilot healthcheck failed: ${HEALTH_URL}" >&2
exit 1
