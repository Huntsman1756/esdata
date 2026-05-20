#!/usr/bin/env bash
set -euo pipefail

MAX_ITERATIONS=${1:-20}
ITERATION=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROMPT_FILE="${RALPH_PROMPT_FILE:-$SCRIPT_DIR/sprint-n-emisor-token.md}"
PRD_FILE="$ROOT_DIR/prd.json"
PROGRESS_FILE="$ROOT_DIR/progress.txt"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required" >&2
  exit 1
fi

if ! command -v opencode >/dev/null 2>&1; then
  echo "Error: opencode is required" >&2
  exit 1
fi

if [ ! -f "$PROMPT_FILE" ]; then
  echo "Error: missing prompt file: $PROMPT_FILE" >&2
  exit 1
fi

cd "$ROOT_DIR"

while [ "$ITERATION" -lt "$MAX_ITERATIONS" ]; do
  ITERATION=$((ITERATION + 1))
  echo "=== Iteration $ITERATION / $MAX_ITERATIONS ==="

  REMAINING=$(
    python3 - "$PRD_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    prd = json.load(fh)

print(sum(1 for story in prd["userStories"] if story.get("passes") is False))
PY
  )
  if [ "$REMAINING" -eq 0 ]; then
    echo "<promise>COMPLETE</promise>"
    exit 0
  fi

  PROMPT="$(cat "$PROMPT_FILE")"
  opencode run --dangerously-skip-permissions "$PROMPT" 2>&1 | tee /dev/stderr || true

  REMAINING_AFTER=$(
    python3 - "$PRD_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    prd = json.load(fh)

print(sum(1 for story in prd["userStories"] if story.get("passes") is False))
PY
  )
  if [ "$REMAINING_AFTER" -eq 0 ]; then
    echo "<promise>COMPLETE</promise>"
    exit 0
  fi

  echo "--- Iteration $ITERATION done: $(date)" >> "$PROGRESS_FILE"
done

echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
exit 1
