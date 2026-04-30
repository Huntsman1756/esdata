#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/infra/deploy/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/infra/deploy/.env.prod}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 2
fi

cd "$ROOT_DIR"

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config >/dev/null

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d postgres
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm ops python scripts/maintenance/verify_schema.py
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build --remove-orphans \
  caddy api web \
  worker-boe worker-dgt worker-teac worker-modelos \
  worker-bdns worker-borme worker-cnmv worker-sepblac

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
