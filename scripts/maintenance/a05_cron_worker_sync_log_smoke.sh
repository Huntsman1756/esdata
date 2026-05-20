#!/usr/bin/env bash
set -euo pipefail

cd /srv/esdata

COMPOSE=(docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml)
OUTDIR="${1:-/root/a05-cron-sync-log-20260520}"
TIMEOUT_SECONDS="${A05_TIMEOUT_SECONDS:-900}"
MIN_SYNC_LOG_ID="${A05_MIN_SYNC_LOG_ID:-1623}"
export OUTDIR

rm -rf "$OUTDIR"
mkdir -p "$OUTDIR/logs"

"${COMPOSE[@]}" --profile cron config --format json > "$OUTDIR/compose.json"

python3 - <<'PY' > "$OUTDIR/cron-services.tsv"
import json
import os

cfg = json.load(open(os.path.join(os.environ["OUTDIR"], "compose.json")))
for name, svc in sorted(cfg["services"].items()):
    profiles = svc.get("profiles") or []
    if "cron" not in profiles:
        continue
    env = svc.get("environment") or {}
    worker_cmd = env.get("WORKER_CMD", "") if isinstance(env, dict) else ""
    print(f"{name}\t{worker_cmd}")
PY

cut -f1 "$OUTDIR/cron-services.tsv" > "$OUTDIR/cron-services.txt"

psql_scalar() {
  "${COMPOSE[@]}" exec -T postgres psql -U esdata -d esdata -tAc "$1" | tr -d '[:space:]'
}

psql_table() {
  "${COMPOSE[@]}" exec -T postgres psql -U esdata -d esdata -P pager=off -c "$1"
}

{
  echo "# Cron worker sync_log smoke - 2026-05-20"
  echo
  echo "Derived from: docker compose --profile cron config --format json"
  echo
  echo "Minimum accepted sync_log id: ${MIN_SYNC_LOG_ID}"
  echo
  echo "Per-service timeout: ${TIMEOUT_SECONDS}s"
  echo
  echo "## Cron service list"
  echo
  nl -ba "$OUTDIR/cron-services.txt" | sed "s/^/- /"
  echo
  echo "## Results"
  echo
  echo "| service | exit_code | before_max_id | after_max_id | new_matching_rows | new_any_rows | outcome | log |"
  echo "|---|---:|---:|---:|---:|---:|---|---|"
} > "$OUTDIR/report.md"

while IFS=$'\t' read -r svc worker_cmd <&3; do
  log="$OUTDIR/logs/${svc}.log"
  echo "=== $svc ===" > "$log"
  echo "WORKER_CMD=${worker_cmd}" >> "$log"

  before_max="$(psql_scalar "SELECT COALESCE(MAX(id), 0) FROM sync_log;")"
  before_service_count="$(psql_scalar "SELECT COUNT(*) FROM sync_log WHERE worker = '${svc}';")"
  echo "before_max_id=${before_max}" >> "$log"
  echo "before_service_count=${before_service_count}" >> "$log"

  set +e
  timeout --kill-after=30 "$TIMEOUT_SECONDS" "${COMPOSE[@]}" run -T --rm "$svc" sh -lc "$worker_cmd" >> "$log" 2>&1 < /dev/null
  ec=$?
  set -e

  after_max="$(psql_scalar "SELECT COALESCE(MAX(id), 0) FROM sync_log;")"
  after_service_count="$(psql_scalar "SELECT COUNT(*) FROM sync_log WHERE worker = '${svc}';")"
  new_matching_rows="$(psql_scalar "SELECT COUNT(*) FROM sync_log WHERE worker = '${svc}' AND id > ${before_max} AND id > ${MIN_SYNC_LOG_ID};")"
  new_any_rows="$(psql_scalar "SELECT COUNT(*) FROM sync_log WHERE id > ${before_max} AND id > ${MIN_SYNC_LOG_ID};")"

  {
    echo "after_max_id=${after_max}"
    echo "after_service_count=${after_service_count}"
    echo "new_matching_rows=${new_matching_rows}"
    echo "new_any_rows=${new_any_rows}"
    echo "--- new sync_log rows"
    psql_table "SELECT id, worker, status, rows_processed, errors, left(coalesce(error_msg, ''), 180) AS error_msg FROM sync_log WHERE id > ${before_max} ORDER BY id;"
  } >> "$log" 2>&1

  if [ "$ec" -eq 124 ] && [ "$new_matching_rows" -gt 0 ]; then
    outcome="sync_log_written_timeout_${TIMEOUT_SECONDS}s"
  elif [ "$ec" -eq 124 ] && [ "$new_any_rows" -gt 0 ]; then
    outcome="sync_log_worker_mismatch_timeout_${TIMEOUT_SECONDS}s"
  elif [ "$ec" -eq 124 ]; then
    outcome="timeout_${TIMEOUT_SECONDS}s"
  elif [ "$ec" -ne 0 ] && [ "$new_matching_rows" -gt 0 ]; then
    outcome="sync_log_written_failed_exit"
  elif [ "$ec" -ne 0 ] && [ "$new_any_rows" -gt 0 ]; then
    outcome="sync_log_worker_mismatch_failed_exit"
  elif [ "$ec" -ne 0 ]; then
    outcome="failed"
  elif [ "$new_matching_rows" -gt 0 ]; then
    outcome="ok"
  elif [ "$new_any_rows" -gt 0 ]; then
    outcome="sync_log_worker_mismatch"
  else
    outcome="no_sync_log"
  fi

  printf "| %s | %s | %s | %s | %s | %s | %s | logs/%s.log |\n" \
    "$svc" "$ec" "$before_max" "$after_max" "$new_matching_rows" "$new_any_rows" "$outcome" "$svc" >> "$OUTDIR/report.md"
done 3< "$OUTDIR/cron-services.tsv"

{
  echo
  echo "## Summary"
  echo
  echo "- cron_service_count=$(wc -l < "$OUTDIR/cron-services.txt")"
  echo "- ok=$(grep -c "| ok |" "$OUTDIR/report.md" || true)"
  echo "- no_sync_log=$(grep -c "| no_sync_log |" "$OUTDIR/report.md" || true)"
  echo "- sync_log_worker_mismatch=$(grep -c "| sync_log_worker_mismatch |" "$OUTDIR/report.md" || true)"
  echo "- sync_log_written_timeout_${TIMEOUT_SECONDS}s=$(grep -c "| sync_log_written_timeout_${TIMEOUT_SECONDS}s |" "$OUTDIR/report.md" || true)"
  echo "- sync_log_worker_mismatch_timeout_${TIMEOUT_SECONDS}s=$(grep -c "| sync_log_worker_mismatch_timeout_${TIMEOUT_SECONDS}s |" "$OUTDIR/report.md" || true)"
  echo "- failed=$(grep -c "| failed |" "$OUTDIR/report.md" || true)"
  echo "- sync_log_written_failed_exit=$(grep -c "| sync_log_written_failed_exit |" "$OUTDIR/report.md" || true)"
  echo "- sync_log_worker_mismatch_failed_exit=$(grep -c "| sync_log_worker_mismatch_failed_exit |" "$OUTDIR/report.md" || true)"
  echo "- timeout_${TIMEOUT_SECONDS}s=$(grep -c "| timeout_${TIMEOUT_SECONDS}s |" "$OUTDIR/report.md" || true)"
} >> "$OUTDIR/report.md"

cat "$OUTDIR/report.md"
