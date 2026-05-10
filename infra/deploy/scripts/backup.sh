#!/bin/sh
set -eu
set -o pipefail

while true; do
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  TARGET="/backups/backup_${TIMESTAMP}.sql.gz"
  TMP_TARGET="${TARGET}.tmp"
  if pg_dump -h postgres -U "${POSTGRES_USER:-esdata}" "${POSTGRES_DB:-esdata}" | gzip -c > "${TMP_TARGET}"; then
    mv "${TMP_TARGET}" "${TARGET}"
    echo "Backup successful at $(date)"
  else
    rm -f "${TMP_TARGET}"
    echo "Backup FAILED at $(date)" >&2
  fi
  find /backups -name '*.sql.gz' -mtime +7 -delete
  sleep 86400
done
