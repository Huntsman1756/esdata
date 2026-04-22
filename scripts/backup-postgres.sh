#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/infra/deploy/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/infra/deploy/.env.prod}"
BACKUP_DIR="${BACKUP_DIR:-/srv/backups/esdata}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 2
fi

set -a
source "$ENV_FILE"
set +a

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
TARGET="$BACKUP_DIR/esdata_${STAMP}.sql.gz"

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-esdata}" "${POSTGRES_DB:-esdata}" | gzip > "$TARGET"

find "$BACKUP_DIR" -name 'esdata_*.sql.gz' -mtime +"$RETENTION_DAYS" -delete
