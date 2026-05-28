#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${HERMES_ESDATA_ROOT:-/srv/esdata/hermes-curator}"

. "${ROOT}/bin/common.sh"

exec 9>/tmp/hermes-esdata-curator.lock
if ! flock -n 9; then
  echo "Another hermes-esdata-curator run is active; exiting." >&2
  exit 75
fi

run_segment() {
  local name="$1"
  local script="$2"

  echo "[$(iso)] START ${name}"
  if "$script"; then
    return 0
  fi

  echo "[$(iso)] ERROR ${name}"
  return 1
}

run_log="$REPORTS/daily-summary/run-$(ts).log"
mkdir -p "$(dirname "$run_log")"

{
  failures=0

  run_segment "aeat-modelos" "$ROOT/bin/run-aeat-modelos.sh" || failures=1
  run_segment "legal-sources" "$ROOT/bin/run-legal-sources.sh" || failures=1
  run_segment "ops-health" "$ROOT/bin/run-ops-health.sh" || failures=1
  run_segment "qa-review" "$ROOT/bin/run-qa-review.sh" || failures=1
  run_segment "writer-summary" "$ROOT/bin/run-writer-summary.sh" || failures=1

  if [ "$failures" -ne 0 ]; then
    echo "[$(iso)] FAILED"
    exit 1
  fi

  echo "[$(iso)] DONE"
} 2>&1 | tee "$run_log"
