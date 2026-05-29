#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${HERMES_ESDATA_ROOT:-/srv/esdata/hermes-curator}"
REPO="${HERMES_ESDATA_REPO:-/srv/esdata}"
PYTHON_BIN="${HERMES_ESDATA_PYTHON:-python3}"

. "${ROOT}/bin/common.sh"

PROMPT_TEMPLATE="${REPO}/scripts/hermes_curator/prompts/aeat_model_json.md"
REPORTS="${ROOT}/reports/aeat-campaign-curation-json"
RAW_DIR="${ROOT}/reports/aeat-campaign-curation-raw"
MD_DIR="${ROOT}/reports/aeat-campaign-curation-rendered"
MODEL_CODE="${1:?usage: run-aeat-model-json.sh <modelo>}"
MAX_TURNS="${MAX_TURNS_AEAT_JSON:-10}"
MAX_EXTRACT_ATTEMPTS="${HERMES_ESDATA_EXTRACT_ATTEMPTS:-2}"

if ! printf '%s' "$MAX_EXTRACT_ATTEMPTS" | grep -Eq '^[0-9]+$' || [ "$MAX_EXTRACT_ATTEMPTS" -lt 1 ]; then
  echo "Invalid HERMES_ESDATA_EXTRACT_ATTEMPTS=$MAX_EXTRACT_ATTEMPTS; using 2" >&2
  MAX_EXTRACT_ATTEMPTS=2
fi

mkdir -p "$REPORTS" "$RAW_DIR" "$MD_DIR"
safe="$(slug "$MODEL_CODE")"
stamp="$(ts)"
prompt_file="$(mktemp)"
json_file="${REPORTS}/modelo-${safe}-${stamp}.json"
json_tmp="${json_file}.tmp"
md_file="${MD_DIR}/modelo-${safe}-${stamp}.md"

sed "s/{{MODEL_CODE}}/${MODEL_CODE}/g" "$PROMPT_TEMPLATE" > "$prompt_file"
prompt="$(cat "$prompt_file")"
rm -f "$prompt_file"

status="OK"
attempt=1
raw_file="${RAW_DIR}/modelo-${safe}-${stamp}.txt"
while [ "$attempt" -le "$MAX_EXTRACT_ATTEMPTS" ]; do
  if [ "$attempt" -eq 1 ]; then
    raw_file="${RAW_DIR}/modelo-${safe}-${stamp}.txt"
  else
    raw_file="${RAW_DIR}/modelo-${safe}-${stamp}-retry${attempt}.txt"
  fi

  if ! run_hermes_query "aeat-json-${safe}" "$MAX_TURNS" "$prompt" > "$raw_file" 2>&1; then
    status="ERROR_HERMES"
    break
  fi

  if "$PYTHON_BIN" "${REPO}/scripts/maintenance/extract_aeat_hermes_json.py" "$raw_file" "$json_tmp"; then
    status="OK"
    break
  fi

  rm -f "$json_tmp"
  if [ "$attempt" -lt "$MAX_EXTRACT_ATTEMPTS" ]; then
    echo "Hermes JSON extraction failed for $MODEL_CODE; retrying attempt $((attempt + 1))/$MAX_EXTRACT_ATTEMPTS" >&2
  fi
  status="ERROR_EXTRACT"
  attempt=$((attempt + 1))
done

if [ "$status" = "OK" ]; then
  if ! "$PYTHON_BIN" "${REPO}/scripts/maintenance/validate_aeat_hermes_report.py" "$json_tmp"; then
    status="ERROR_VALIDATE"
  elif ! "$PYTHON_BIN" "${REPO}/scripts/maintenance/render_aeat_hermes_report.py" "$json_tmp" "$md_file"; then
    status="ERROR_RENDER"
  else
    mv "$json_tmp" "$json_file"
  fi
fi

case "$status" in
  OK)
    printf 'OK,%s,%s,%s,%s\n' "$MODEL_CODE" "$json_file" "$md_file" "$raw_file"
    ;;
  *)
    rm -f "$json_tmp"
    printf '%s,%s,,,%s\n' "$status" "$MODEL_CODE" "$raw_file" >&2
    exit 1
    ;;
esac
