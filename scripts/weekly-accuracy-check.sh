#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DEPLOY_DIR="${DEPLOY_DIR:-$ROOT_DIR/infra/deploy}"
COMPOSE_FILE="${COMPOSE_FILE:-$DEPLOY_DIR/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-/etc/esdata/esdata.env}"
BASE_URL="${BASE_URL:-http://api:8000}"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "FAIL: compose file not found: $COMPOSE_FILE" >&2
  exit 2
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "FAIL: env file not found: $ENV_FILE" >&2
  exit 2
fi

cd "$DEPLOY_DIR"

echo "== esdata weekly accuracy check =="
echo "timestamp=$(date -Is)"
echo "root=$ROOT_DIR"

echo "== mcp_validation_suite =="
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm --no-deps \
  -v "$ROOT_DIR:/workspace" \
  -w /workspace \
  api sh -lc "python scripts/maintenance/mcp_validation_suite.py --read-only --base-url '$BASE_URL'"

echo "== source freshness =="
sql=$(cat <<'SQL'
WITH checks(domain, threshold_hours, workers) AS (
  VALUES
    ('BOE', 72::numeric, ARRAY['worker-boe','cron-boe-daily','cron-boe-diario-daily']),
    ('AEAT', 168::numeric, ARRAY['worker-modelos','cron-modelos-daily','cron-aeat-current-daily','worker-boe-modelos']),
    ('EUR-Lex', 720::numeric, ARRAY['worker-eurlex','cron-eurlex-weekly']),
    ('CNMV', 192::numeric, ARRAY['worker-cnmv','cron-cnmv-weekly']),
    ('ESMA/MiCA', 192::numeric, ARRAY['cron-mica-weekly'])
),
latest AS (
  SELECT
    c.domain,
    c.threshold_hours,
    MAX(s.finished_at) AS last_updated
  FROM checks c
  LEFT JOIN sync_log s
    ON s.worker = ANY(c.workers)
   AND s.finished_at IS NOT NULL
   AND s.status IN ('ok', 'success')
  GROUP BY c.domain, c.threshold_hours
)
SELECT
  domain,
  COALESCE(last_updated::text, '') AS last_updated,
  CASE
    WHEN last_updated IS NULL THEN ''
    ELSE ROUND((EXTRACT(EPOCH FROM (NOW() - last_updated)) / 3600)::numeric, 2)::text
  END AS age_hours,
  threshold_hours::text AS threshold_hours,
  CASE
    WHEN last_updated IS NULL THEN 'STALE'
    WHEN (EXTRACT(EPOCH FROM (NOW() - last_updated)) / 3600) > threshold_hours THEN 'STALE'
    ELSE 'OK'
  END AS status
FROM latest
ORDER BY domain;
SQL
)

rows=$(
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres \
    psql -U "${POSTGRES_USER:-esdata}" -d "${POSTGRES_DB:-esdata}" -tA -F '|' -c "$sql"
)

printf '%-10s | %-32s | %-9s | %-9s | %s\n' "domain" "last_updated" "age_h" "limit_h" "status"
printf '%-10s-+-%-32s-+-%-9s-+-%-9s-+-%s\n' "----------" "--------------------------------" "---------" "---------" "------"

stale=0
while IFS='|' read -r domain last_updated age_hours threshold_hours status; do
  [[ -z "${domain:-}" ]] && continue
  printf '%-10s | %-32s | %-9s | %-9s | %s\n' "$domain" "$last_updated" "$age_hours" "$threshold_hours" "$status"
  if [[ "$status" != "OK" ]]; then
    stale=1
  fi
done <<< "$rows"

if [[ "$stale" -ne 0 ]]; then
  echo "FAIL: one or more domains exceed freshness thresholds" >&2
  exit 1
fi

echo "PASS: validation suite green and all domain freshness checks within thresholds"
