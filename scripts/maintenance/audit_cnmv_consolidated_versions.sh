#!/usr/bin/env bash
set -euo pipefail

# Audit CNMV vigente_modificado rows and mark whether their loaded version is
# proven to be BOE consolidated text. The script is conservative: absence of a
# reliable BOE consolidated marker is recorded as not_consolidated, not guessed.
#
# Usage:
#   scripts/maintenance/audit_cnmv_consolidated_versions.sh --dry-run
#   scripts/maintenance/audit_cnmv_consolidated_versions.sh --apply
#
# Preconditions:
#   - Run from repo root on the VPS.
#   - Alembic migration 20260514_0078_cnmv_consolidated_version_audit applied.
#   - DB access only through docker compose exec postgres psql.

MODE="${1:---dry-run}"
if [[ "$MODE" != "--dry-run" && "$MODE" != "--apply" ]]; then
  echo "Usage: $0 [--dry-run|--apply]" >&2
  exit 2
fi

COMPOSE_STRING="${COMPOSE:-docker compose -f infra/deploy/docker-compose.prod.yml}"
read -r -a COMPOSE_CMD <<< "$COMPOSE_STRING"

DB_USER="${PGUSER:-${POSTGRES_USER:-esdata}}"
DB_NAME="${PGDATABASE:-${POSTGRES_DB:-esdata}}"
TAB="$(printf '\t')"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

psql_query() {
  "${COMPOSE_CMD[@]}" exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" "$@"
}

mark_version() {
  local ref="$1"
  local status="$2"
  local es_consolidado="$3"
  local source_url="$4"
  local note="$5"

  psql_query \
    -v ref="$ref" \
    -v status="$status" \
    -v es_consolidado="$es_consolidado" \
    -v source_url="$source_url" \
    -v note="$note" <<'SQL'
UPDATE documento_version
SET es_consolidado = CASE :'es_consolidado'
        WHEN 'true' THEN true
        WHEN 'false' THEN false
        ELSE NULL
    END,
    consolidated_verification_status = :'status',
    consolidated_source_url = :'source_url',
    consolidated_checked_at = NOW(),
    boe_last_modified = NULL,
    consolidated_evidence_note = :'note'
WHERE documento_referencia = :'ref';

UPDATE documento_cnmv_version
SET es_consolidado = CASE :'es_consolidado'
        WHEN 'true' THEN true
        WHEN 'false' THEN false
        ELSE NULL
    END,
    consolidated_verification_status = :'status',
    consolidated_source_url = :'source_url',
    consolidated_checked_at = NOW(),
    boe_last_modified = NULL,
    consolidated_evidence_note = :'note'
WHERE documento_referencia = :'ref';
SQL
}

rows="$(
  psql_query -At -F "$TAB" -c "
    SELECT
      d.referencia,
      COALESCE(
        NULLIF(d.referencia_boe, ''),
        substring(d.url_fuente from 'BOE-A-[0-9]{4}-[0-9]+')
      ) AS boe_id
    FROM documento_interpretativo d
    WHERE d.organismo_emisor = 'CNMV'
      AND d.tipo_fuente = 'cnmv'
      AND d.estado_vigencia = 'vigente_modificado'
    ORDER BY d.referencia;
  " </dev/null
)"

if [[ -z "$rows" ]]; then
  echo "No CNMV vigente_modificado rows found."
  exit 0
fi

echo "mode${TAB}referencia${TAB}boe_id${TAB}status${TAB}es_consolidado${TAB}note"
while IFS="$TAB" read -r ref boe_id; do
  [[ -z "${ref:-}" ]] && continue

  status="unknown"
  es_consolidado="null"
  source_url=""
  note="No BOE reference available."

  if [[ -n "${boe_id:-}" ]]; then
    source_url="https://www.boe.es/buscar/act.php?id=${boe_id}"
    html_file="$TMP_DIR/${boe_id}.html"
    if curl -fsSL --max-time 30 "$source_url" -o "$html_file"; then
      if grep -Eiq 'Texto consolidado|ltima actualizaci' "$html_file"; then
        status="consolidated"
        es_consolidado="true"
        note="BOE act.php page exposes consolidated-text marker."
      elif grep -Eiq '/buscar/doc\.php\?id='"${boe_id}" "$html_file"; then
        status="not_consolidated"
        es_consolidado="false"
        note="BOE canonical link points to doc.php/original publication and no consolidated marker was found."
      else
        status="unknown"
        es_consolidado="null"
        note="BOE page fetched but consolidated/original marker was inconclusive."
      fi
    else
      status="verification_error"
      es_consolidado="null"
      note="BOE page could not be fetched."
    fi
  fi

  echo "${MODE}${TAB}${ref}${TAB}${boe_id:-}${TAB}${status}${TAB}${es_consolidado}${TAB}${note}"
  if [[ "$MODE" == "--apply" ]]; then
    mark_version "$ref" "$status" "$es_consolidado" "$source_url" "$note" >/dev/null
  fi
done <<< "$rows"
