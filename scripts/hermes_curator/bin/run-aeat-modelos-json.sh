#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${HERMES_ESDATA_ROOT:-/srv/esdata/hermes-curator}"
REPO="${HERMES_ESDATA_REPO:-/srv/esdata}"

. "${ROOT}/bin/common.sh"

queue="${1:-$ROOT/queues/aeat-priority-modelos.txt}"
out_dir="$ROOT/reports/aeat-campaign-curation-json"
summary="$out_dir/_batch-json-$(ts)-summary.csv"
mkdir -p "$out_dir"
echo 'modelo,status,json_file,markdown_file,raw_file' > "$summary"

while IFS= read -r raw || [ -n "$raw" ]; do
  raw="${raw%%#*}"
  [ -n "${raw//[[:space:]]/}" ] || continue
  IFS=',' read -ra modelos <<< "$raw"
  for modelo in "${modelos[@]}"; do
    modelo="$(printf '%s' "$modelo" | xargs)"
    [ -n "$modelo" ] || continue
    tmp="$(mktemp)"
    if "$REPO/scripts/hermes_curator/bin/run-aeat-model-json.sh" "$modelo" > "$tmp" 2>&1; then
      tail -1 "$tmp" >> "$summary"
    else
      line="$(tail -1 "$tmp" || true)"
      if [ -n "$line" ] && printf '%s' "$line" | grep -qE '^ERROR_[A-Z_]+,'; then
        printf '%s\n' "$line" >> "$summary"
      else
        printf 'ERROR_UNKNOWN,%s,,,%s\n' "$modelo" "$tmp" >> "$summary"
      fi
      cat "$tmp" >&2
    fi
    rm -f "$tmp"
    sleep "${HERMES_ESDATA_DELAY_SECONDS:-8}"
  done
done < "$queue"

echo "DONE aeat json summary: $summary"
