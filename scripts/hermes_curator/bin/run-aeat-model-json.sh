#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${HERMES_ESDATA_ROOT:-/srv/esdata/hermes-curator}"
REPO="${HERMES_ESDATA_REPO:-/srv/esdata}"
PROMPT_TEMPLATE="${REPO}/scripts/hermes_curator/prompts/aeat_model_json.md"
REPORTS="${ROOT}/reports/aeat-campaign-curation-json"
RAW_DIR="${ROOT}/reports/aeat-campaign-curation-raw"
MD_DIR="${ROOT}/reports/aeat-campaign-curation-rendered"
MODEL_CODE="${1:?usage: run-aeat-model-json.sh <modelo>}"
MAX_TURNS="${MAX_TURNS_AEAT_JSON:-10}"

. "${ROOT}/bin/common.sh"

mkdir -p "$REPORTS" "$RAW_DIR" "$MD_DIR"
safe="$(slug "$MODEL_CODE")"
stamp="$(ts)"
prompt_file="$(mktemp)"
raw_file="${RAW_DIR}/modelo-${safe}-${stamp}.txt"
json_file="${REPORTS}/modelo-${safe}-${stamp}.json"
md_file="${MD_DIR}/modelo-${safe}-${stamp}.md"

sed "s/{{MODEL_CODE}}/${MODEL_CODE}/g" "$PROMPT_TEMPLATE" > "$prompt_file"

status="OK"
if ! run_hermes_query "aeat-json-${safe}" "$MAX_TURNS" "$(cat "$prompt_file")" > "$raw_file" 2>&1; then
  status="ERROR_HERMES"
fi
rm -f "$prompt_file"

if [ "$status" = "OK" ]; then
  if ! python "${REPO}/scripts/maintenance/extract_aeat_hermes_json.py" "$raw_file" "$json_file"; then
    status="ERROR_EXTRACT"
  elif ! python "${REPO}/scripts/maintenance/validate_aeat_hermes_report.py" "$json_file"; then
    status="ERROR_VALIDATE"
  elif ! python "${REPO}/scripts/maintenance/render_aeat_hermes_report.py" "$json_file" "$md_file"; then
    status="ERROR_RENDER"
  fi
fi

case "$status" in
  OK)
    printf 'OK,%s,%s,%s,%s\n' "$MODEL_CODE" "$json_file" "$md_file" "$raw_file"
    ;;
  *)
    printf '%s,%s,,,%s\n' "$status" "$MODEL_CODE" "$raw_file" >&2
    exit 1
    ;;
esac
