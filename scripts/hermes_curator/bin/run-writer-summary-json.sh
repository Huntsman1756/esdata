#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${HERMES_ESDATA_ROOT:-/srv/esdata/hermes-curator}"

. "${ROOT}/bin/common.sh"

out_dir="$ROOT/reports/daily-summary"
mkdir -p "$out_dir"
stamp="$(ts)"
out="$out_dir/summary-$stamp.md"
latest_campaign_json="$(find "$ROOT/reports/aeat-campaign-curation-json" -maxdepth 1 -name '_batch-json-*-summary.csv' -type f 2>/dev/null | sort | tail -1 || true)"
latest_campaign_legacy="$(find "$ROOT/reports/aeat-campaign-curation" -maxdepth 1 -name '_batch-*-summary.csv' -type f 2>/dev/null | sort | tail -1 || true)"
latest_legal="$(find "$REPORTS/legal-source-audit" -maxdepth 1 -name '_legal-*-summary.csv' -type f 2>/dev/null | sort | tail -1 || true)"
latest_ops="$(find "$REPORTS/ops-health" -maxdepth 1 -name 'ops-*.md' -type f 2>/dev/null | sort | tail -1 || true)"
latest_qa="$(find "$REPORTS/qa-review" -maxdepth 1 -name 'qa-*.md' -type f 2>/dev/null | sort | tail -1 || true)"
latest_run="$(find "$REPORTS/daily-summary" -maxdepth 1 -name 'run-*.log' -type f 2>/dev/null | sort | tail -1 || true)"

decision="NEEDS_HUMAN_REVIEW"
campaign_status="MISSING"
legal_status="MISSING"
if [ -z "$latest_campaign_json" ]; then
  decision="BLOCKED"
  campaign_status="MISSING_JSON_SUMMARY"
elif grep -q '^ERROR_' "$latest_campaign_json"; then
  decision="BLOCKED"
  campaign_status="JSON_ERRORS"
else
  campaign_status="JSON_VALIDATED"
fi
if [ -n "$latest_qa" ] && grep -q '^BLOCKER$' "$latest_qa"; then
  decision="BLOCKED"
fi
if [ -z "$latest_legal" ]; then
  decision="BLOCKED"
  legal_status="MISSING_LEGAL_SUMMARY"
elif grep -q '"SKIPPED",' "$latest_legal"; then
  decision="BLOCKED"
  legal_status="AMBIGUOUS_SKIPPED"
elif grep -q '"ERROR"' "$latest_legal"; then
  decision="BLOCKED"
  legal_status="LEGAL_ERRORS"
else
  legal_status="EXPLICIT"
fi

{
  echo "<!--"
  echo "generated_at: $(iso)"
  echo "status: OK"
  echo "mode: deterministic-json"
  echo "-->"
  echo
  echo "# ESData autonomous audit summary $stamp"
  echo
  echo "## Decision"
  echo "$decision"
  echo
  echo "## Inputs"
  echo "- Campaign JSON summary: ${latest_campaign_json:-MISSING}"
  echo "- Campaign legacy summary: ${latest_campaign_legacy:-IGNORED}"
  echo "- Legal summary: ${latest_legal:-MISSING}"
  echo "- Ops report: ${latest_ops:-MISSING}"
  echo "- QA report: ${latest_qa:-MISSING}"
  echo "- Run log: ${latest_run:-MISSING}"
  echo
  echo "## Findings"
  case "$campaign_status" in
    JSON_VALIDATED)
      echo "- AEAT campaign curation uses validated JSON as primary source."
      ;;
    MISSING_JSON_SUMMARY)
      echo "- BLOCKER: missing AEAT JSON campaign summary."
      ;;
    JSON_ERRORS)
      echo "- BLOCKER: AEAT JSON campaign summary contains validation/execution errors."
      ;;
  esac
  echo "- Human review is still required before data changes."
  case "$legal_status" in
    EXPLICIT)
      echo "- Legal source audit statuses include explicit reasons."
      ;;
    MISSING_LEGAL_SUMMARY)
      echo "- BLOCKER: missing legal source audit summary."
      ;;
    AMBIGUOUS_SKIPPED)
      echo "- BLOCKER: legal source audit contains ambiguous SKIPPED rows."
      ;;
    LEGAL_ERRORS)
      echo "- BLOCKER: legal source audit contains ERROR rows."
      ;;
  esac
  echo
  echo "## AEAT JSON Summary"
  [ -n "$latest_campaign_json" ] && cat "$latest_campaign_json"
  echo
  echo "## Legal Summary"
  [ -n "$latest_legal" ] && cat "$latest_legal"
  echo
  echo "## Rule"
  echo "No campaign or legal source may be promoted without human review and direct official evidence."
  echo "Markdown is a rendered view; validated JSON is the primary artifact for Hermes AEAT curation."
} > "$out"

echo "DONE summary report: $out"
