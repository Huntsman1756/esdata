#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"

COMPOSE_FILE="${ESDATA_BACKUP_COMPOSE_FILE:-$ROOT_DIR/infra/deploy/docker-compose.prod.yml}"
ENV_FILE="${ESDATA_BACKUP_ENV_FILE:-/etc/esdata/esdata.env}"
REMOTE_DIR="${ESDATA_BACKUP_REMOTE:-}"
RETENTION_DAYS="${ESDATA_BACKUP_RETENTION_DAYS:-30}"
TMP_PARENT="${ESDATA_BACKUP_TMP_DIR:-/tmp}"
LOG_FILE="${ESDATA_BACKUP_LOG:-/var/log/esdata-backup.log}"
LAST_BACKUP_FILE="${ESDATA_LAST_BACKUP_FILE:-/var/lib/esdata/last_offsite_backup}"
MIN_SIZE_BYTES="${ESDATA_BACKUP_MIN_SIZE_BYTES:-1000000}"

CHECK_CONFIG=false
DRY_RUN=false

usage() {
  cat <<'EOF'
Usage: scripts/backup-offsite.sh [--check-config] [--dry-run]

Creates a PostgreSQL custom-format dump through Docker Compose, uploads it to an
offsite rclone remote, verifies the remote size, prunes backups older than the
retention window, and records the last successful backup timestamp.

Required production configuration:
  ESDATA_BACKUP_REMOTE          rclone destination directory, e.g. b2-esdata:esdata-backups

Optional configuration:
  ESDATA_BACKUP_COMPOSE_FILE    defaults to infra/deploy/docker-compose.prod.yml
  ESDATA_BACKUP_ENV_FILE        defaults to /etc/esdata/esdata.env
  ESDATA_BACKUP_RETENTION_DAYS  defaults to 30
  ESDATA_BACKUP_TMP_DIR         defaults to /tmp
  ESDATA_BACKUP_LOG             defaults to /var/log/esdata-backup.log
  ESDATA_LAST_BACKUP_FILE       defaults to /var/lib/esdata/last_offsite_backup
  ESDATA_BACKUP_MIN_SIZE_BYTES  defaults to 1000000

Secrets must live in the host rclone configuration or environment, never in git.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-config)
      CHECK_CONFIG=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

log() {
  local message="$1"
  local line
  line="$(date -u +%Y-%m-%dT%H:%M:%SZ) $message"
  if [[ -w "$(dirname -- "$LOG_FILE")" || ( ! -e "$LOG_FILE" && -w "$(dirname -- "$LOG_FILE")" ) ]]; then
    printf '%s\n' "$line" | tee -a "$LOG_FILE"
  else
    printf '%s\n' "$line"
  fi
}

die() {
  log "ERROR: $1"
  exit "${2:-1}"
}

require_command() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || die "missing required command: $cmd" 2
}

validate_positive_integer() {
  local name="$1"
  local value="$2"
  [[ "$value" =~ ^[1-9][0-9]*$ ]] || die "$name must be a positive integer, got: $value" 2
}

check_config() {
  [[ -n "$REMOTE_DIR" ]] || die "ESDATA_BACKUP_REMOTE is required, e.g. b2-esdata:esdata-backups" 2
  [[ -f "$COMPOSE_FILE" ]] || die "compose file not found: $COMPOSE_FILE" 2
  [[ -f "$ENV_FILE" ]] || die "env file not found: $ENV_FILE" 2
  validate_positive_integer "ESDATA_BACKUP_RETENTION_DAYS" "$RETENTION_DAYS"
  validate_positive_integer "ESDATA_BACKUP_MIN_SIZE_BYTES" "$MIN_SIZE_BYTES"
  require_command docker
  require_command gzip
  require_command rclone
  require_command jq
  require_command stat
  log "Configuration OK: remote=$REMOTE_DIR retention_days=$RETENTION_DAYS compose=$COMPOSE_FILE"
}

if [[ "$CHECK_CONFIG" == true ]]; then
  check_config
  exit 0
fi

check_config

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
TMP_DIR="$(mktemp -d "$TMP_PARENT/esdata-offsite-backup.XXXXXX")"
BACKUP_FILE="$TMP_DIR/esdata_${TIMESTAMP}.dump.gz"
REMOTE_FILE="${REMOTE_DIR%/}/$(basename -- "$BACKUP_FILE")"

cleanup() {
  rm -rf -- "$TMP_DIR"
}
trap cleanup EXIT

if [[ "$DRY_RUN" == true ]]; then
  log "DRY RUN: would create dump and upload to $REMOTE_FILE"
  exit 0
fi

log "Starting offsite backup: target=$REMOTE_FILE"

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-esdata}" -d "${POSTGRES_DB:-esdata}" --format=custom \
  | gzip -c > "$BACKUP_FILE"

LOCAL_SIZE="$(stat -c%s "$BACKUP_FILE")"
if [[ "$LOCAL_SIZE" -lt "$MIN_SIZE_BYTES" ]]; then
  die "dump too small: ${LOCAL_SIZE} bytes, minimum=${MIN_SIZE_BYTES}"
fi
log "Dump complete: ${LOCAL_SIZE} bytes"

rclone copyto "$BACKUP_FILE" "$REMOTE_FILE" --log-level INFO

REMOTE_SIZE="$(rclone size "$REMOTE_FILE" --json | jq -r '.bytes')"
validate_positive_integer "remote backup size" "$REMOTE_SIZE"
if [[ "$REMOTE_SIZE" -lt "$LOCAL_SIZE" ]]; then
  die "remote file smaller than local dump: remote=${REMOTE_SIZE}, local=${LOCAL_SIZE}"
fi
log "Remote verification complete: ${REMOTE_SIZE} bytes"

rclone delete "${REMOTE_DIR%/}" \
  --min-age "${RETENTION_DAYS}d" \
  --include 'esdata_*.dump.gz' \
  --log-level INFO

mkdir -p "$(dirname -- "$LAST_BACKUP_FILE")"
date -u +%Y-%m-%dT%H:%M:%SZ > "$LAST_BACKUP_FILE"

log "Offsite backup complete: timestamp=$TIMESTAMP retention_days=$RETENTION_DAYS"
