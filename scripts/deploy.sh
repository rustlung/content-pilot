#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

COMPOSE_FILE="${CONTENT_PILOT_COMPOSE_FILE:-compose.prod.yaml}"
ENV_FILE="${CONTENT_PILOT_ENV_FILE:-.env.production}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Production environment file not found: ${ENV_FILE}" >&2
  echo "Set CONTENT_PILOT_ENV_FILE to override it." >&2
  exit 1
fi

compose=(docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}")

# Let Docker Compose parse the env file instead of sourcing it as shell code.
# A non-empty shell value deliberately takes precedence over the env file.
if [[ -z "${CONTENT_PILOT_IMAGE:-}" ]]; then
  if ! compose_environment="$("${compose[@]}" config --environment)"; then
    echo "Unable to read Docker Compose environment from ${ENV_FILE}." >&2
    exit 1
  fi
  CONTENT_PILOT_IMAGE="$(printf '%s\n' "${compose_environment}" | awk -F= '$1 == "CONTENT_PILOT_IMAGE" { sub(/^[^=]*=/, ""); print; exit }')"
fi

if [[ -z "${CONTENT_PILOT_IMAGE:-}" ]]; then
  echo "CONTENT_PILOT_IMAGE must be set in the shell or in ${ENV_FILE}." >&2
  exit 1
fi
export CONTENT_PILOT_IMAGE

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
