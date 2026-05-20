#!/usr/bin/env bash
set -euo pipefail

cd /srv/esdata

COMPOSE=(docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml)
OUTDIR="${1:-/root/a04-persistent-smoke-20260520}"
TIMEOUT_SECONDS="${A04_TIMEOUT_SECONDS:-300}"
export OUTDIR

rm -rf "$OUTDIR"
mkdir -p "$OUTDIR/logs"

"${COMPOSE[@]}" --profile cron config --format json > "$OUTDIR/compose.json"

python3 - <<'PY' > "$OUTDIR/workers.tsv"
import json
import os

cfg = json.load(open(os.path.join(os.environ["OUTDIR"], "compose.json")))
for name, svc in sorted(cfg["services"].items()):
    profiles = svc.get("profiles") or []
    if name.startswith("worker-") and "cron" not in profiles:
        env = svc.get("environment") or {}
        worker_cmd = env.get("WORKER_CMD", "") if isinstance(env, dict) else ""
        print(f"{name}\t{worker_cmd}")
PY
cut -f1 "$OUTDIR/workers.tsv" > "$OUTDIR/workers.txt"

{
  echo "# Persistent worker smoke - 2026-05-20"
  echo
  echo "Derived from: docker compose --profile cron config --format json"
  echo
  echo "## Persistent worker list"
  echo
  nl -ba "$OUTDIR/workers.txt" | sed "s/^/- /"
  echo
  echo "## Results"
  echo
  echo "| service | exit_code | run_once_supported | outcome | log |"
  echo "|---|---:|---|---|---|"
} > "$OUTDIR/report.md"

while IFS=$'\t' read -r svc worker_cmd; do
  log="$OUTDIR/logs/${svc}.log"
  echo "=== $svc ===" > "$log"
  echo "command=${worker_cmd} --run-once" >> "$log"

  set +e
  timeout "$TIMEOUT_SECONDS" "${COMPOSE[@]}" run -T --rm "$svc" sh -lc "${worker_cmd} --run-once" >> "$log" 2>&1 < /dev/null
  ec=$?
  set -e

  supported="yes"
  if grep -Eiq "unrecognized arguments: --run-once|no such option: --run-once|unknown option.*run-once|Usage:.*--run-once" "$log"; then
    supported="no"
  fi

  if [ "$ec" -eq 0 ]; then
    outcome="ok"
  elif [ "$ec" -eq 124 ]; then
    outcome="timeout_${TIMEOUT_SECONDS}s"
  elif [ "$supported" = "no" ]; then
    outcome="run_once_not_supported"
  else
    outcome="failed"
  fi

  printf "| %s | %s | %s | %s | logs/%s.log |\n" "$svc" "$ec" "$supported" "$outcome" "$svc" >> "$OUTDIR/report.md"
done < "$OUTDIR/workers.tsv"

{
  echo
  echo "## Summary"
  echo
  echo "- persistent_worker_count=$(wc -l < "$OUTDIR/workers.txt")"
  echo "- run_once_not_supported=$(grep -c "run_once_not_supported" "$OUTDIR/report.md" || true)"
  echo "- failed=$(grep -c "| failed |" "$OUTDIR/report.md" || true)"
  echo "- timeout_${TIMEOUT_SECONDS}s=$(grep -c "timeout_${TIMEOUT_SECONDS}s" "$OUTDIR/report.md" || true)"
} >> "$OUTDIR/report.md"

cat "$OUTDIR/report.md"
