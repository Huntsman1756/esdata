#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${HERMES_ESDATA_ROOT:-/srv/esdata/hermes-curator}"
REPO="${HERMES_ESDATA_REPO:-/srv/esdata}"

. "${ROOT}/bin/common.sh"

queue="${1:-$ROOT/queues/aeat-priority-modelos.txt}"
out_dir="$ROOT/reports/aeat-campaign-curation-json"
summary="$out_dir/_batch-json-$(ts)-summary.csv"
max_models="${HERMES_ESDATA_MAX_MODELS_PER_RUN:-3}"
processed=0
if ! printf '%s' "$max_models" | grep -Eq '^[0-9]+$'; then
  echo "Invalid HERMES_ESDATA_MAX_MODELS_PER_RUN=$max_models; using 3" >&2
  max_models=3
fi
mkdir -p "$out_dir"
echo 'modelo,status,json_file,markdown_file,raw_file' > "$summary"
failures=0

while IFS= read -r raw || [ -n "$raw" ]; do
  raw="${raw%%#*}"
  [ -n "${raw//[[:space:]]/}" ] || continue
  IFS=',' read -ra modelos <<< "$raw"
  for modelo in "${modelos[@]}"; do
    modelo="$(printf '%s' "$modelo" | xargs)"
    [ -n "$modelo" ] || continue
    if [ "$processed" -ge "$max_models" ]; then
      printf 'DAILY_CAP_REACHED,%s,,,\n' "$modelo" >> "$summary"
      continue
    fi
    tmp="$(mktemp)"
    if "$REPO/scripts/hermes_curator/bin/run-aeat-model-json.sh" "$modelo" > "$tmp" 2>&1; then
      tail -1 "$tmp" >> "$summary"
    else
      failures=1
      line="$(tail -1 "$tmp" || true)"
      if [ -n "$line" ] && printf '%s' "$line" | grep -qE '^ERROR_[A-Z_]+,'; then
        printf '%s\n' "$line" >> "$summary"
      else
        printf 'ERROR_UNKNOWN,%s,,,%s\n' "$modelo" "$tmp" >> "$summary"
      fi
      cat "$tmp" >&2
    fi
    rm -f "$tmp"
    processed=$((processed + 1))
    sleep "${HERMES_ESDATA_DELAY_SECONDS:-30}"
  done
done < "$queue"

if [ "$failures" -ne 0 ]; then
  echo "ERROR aeat json summary: $summary" >&2
  exit 1
fi

echo "DONE aeat json summary: $summary"
