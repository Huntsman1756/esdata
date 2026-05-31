#!/usr/bin/env bash
set -Eeuo pipefail

. "$(dirname "$0")/common.sh"

queue="${1:-$QUEUES/legal-sources.txt}"
out_dir="$REPORTS/legal-source-audit"
summary="$out_dir/_legal-$(ts)-summary.csv"
force="${FORCE_LEGAL:-0}"

mkdir -p "$out_dir"
echo 'source_id,status,reason,output_file' > "$summary"

while IFS= read -r line || [ -n "$line" ]; do
  line="${line%%#*}"
  [ -n "${line//[[:space:]]/}" ] || continue

  source_id="${line%%|*}"
  topic="${line#*|}"
  source_id="$(printf '%s' "$source_id" | xargs)"
  topic="$(printf '%s' "$topic" | xargs)"
  [ -n "$topic" ] || topic="$source_id"

  safe="$(slug "$source_id")"
  out="$out_dir/source-$safe.md"
  if [ -f "$out" ] && [ "$force" != "1" ]; then
    echo "\"$source_id\",\"SKIPPED_EXISTING_REPORT\",\"existing report reused; set FORCE_LEGAL=1 to refresh\",\"$out\"" >> "$summary"
    continue
  fi

  query="Actua como auditor legal/documental read-only de ESData. Revisa esta fuente o tema: $topic
Usa exclusivamente herramientas MCP esdata_curator read-only disponibles.
Reglas:
- No inventes evidencia.
- Si no puedes verificar una norma/fuente oficial, marca UNKNOWN.
- No uses fecha BOE como prueba semantica salvo texto vinculante.
- Separa: fuente encontrada, vigencia documental, relacion con modelos/campanas, riesgos.
- No propongas escrituras ni cambios productivos.
Formato markdown:
# Fuente $source_id - auditoria legal
## Decision
VERIFIED_SOURCE | UNKNOWN | CONFLICT | STALE_SUSPECTED
## Fuentes consultadas
## Evidencia directa
## Riesgo semantico
## Recomendacion"

  tmp="$(mktemp)"
  status="OK"
  reason="refreshed by Hermes legal-source audit"
  if ! run_hermes_query "legal-$safe" "${MAX_TURNS_LEGAL:-6}" "$query" > "$tmp" 2>&1; then
    status="ERROR"
    reason="Hermes legal-source audit command failed"
  elif grep -qiE 'maximum iterations|max_iterations_reached|max turns' "$tmp"; then
    status="WARNING_MAX_TURNS"
    reason="Hermes reached max turns before clean completion"
  fi

  write_report "$out" "$status" "$tmp"
  rm -f "$tmp"
  echo "\"$source_id\",\"$status\",\"$reason\",\"$out\"" >> "$summary"
  sleep "${HERMES_ESDATA_DELAY_SECONDS:-8}"
done < "$queue"

echo "DONE legal summary: $summary"
