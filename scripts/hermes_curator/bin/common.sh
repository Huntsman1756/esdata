#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${HERMES_ESDATA_ROOT:-/srv/esdata/hermes-curator}"
IMAGE="${HERMES_ESDATA_IMAGE:-nousresearch/hermes-agent:latest}"
REPORTS="$ROOT/reports"
QUEUES="$ROOT/queues"
LOGS="$ROOT/logs"
RUNS="$ROOT/runs"
MAX_OTHER_HERMES="${HERMES_ESDATA_MAX_OTHER_HERMES:-3}"
MAX_ESDATA_HERMES="${HERMES_ESDATA_MAX_ESDATA_HERMES:-1}"
DEFAULT_MAX_TURNS="${HERMES_ESDATA_MAX_TURNS:-8}"
CALL_TIMEOUT="${HERMES_ESDATA_CALL_TIMEOUT:-1800}"
MIN_DELAY_SECONDS="${HERMES_ESDATA_MIN_DELAY_SECONDS:-30}"
RATE_LIMIT_LOCK="$RUNS/hermes-rate-limit.lock"
LAST_CALL_FILE="$RUNS/hermes-last-call.epoch"

mkdir -p "$REPORTS" "$QUEUES" "$LOGS" "$RUNS"

ts() { date '+%Y%m%d-%H%M%S'; }
iso() { date -Is; }
slug() { printf '%s' "$1" | tr -c 'A-Za-z0-9_.-' '_' | sed -E 's/_+/_/g; s/^_//; s/_$//'; }

running_hermes_count() {
  docker ps --format '{{.Image}}' | grep -c '^nousresearch/hermes-agent' || true
}

running_esdata_hermes_count() {
  docker ps --filter label=esdata.hermes.curator=1 --format '{{.ID}}' | wc -l | tr -d '[:space:]'
}

assert_capacity() {
  local current
  current="$(running_esdata_hermes_count)"
  if [ "$current" -ge "$MAX_ESDATA_HERMES" ]; then
    echo "Refusing to start Hermes call: $current ESData Hermes container(s) already running; limit is $MAX_ESDATA_HERMES" >&2
    return 72
  fi

  current="$(running_hermes_count)"
  if [ "$current" -ge "$MAX_OTHER_HERMES" ]; then
    echo "Refusing to start Hermes call: $current Hermes container(s) already running; pre-ESData limit is $MAX_OTHER_HERMES" >&2
    return 72
  fi
}

wait_for_rate_limit() {
  exec 8>"$RATE_LIMIT_LOCK"
  flock 8

  local now last elapsed wait_for
  now="$(date +%s)"
  last="0"
  if [ -s "$LAST_CALL_FILE" ]; then
    last="$(cat "$LAST_CALL_FILE")"
  fi

  if ! printf '%s' "$last" | grep -Eq '^[0-9]+$'; then
    last="0"
  fi

  elapsed=$((now - last))
  if [ "$elapsed" -lt "$MIN_DELAY_SECONDS" ]; then
    wait_for=$((MIN_DELAY_SECONDS - elapsed))
    echo "Hermes local rate limit: sleeping ${wait_for}s before next call" >&2
    sleep "$wait_for"
    now="$(date +%s)"
  fi

  printf '%s\n' "$now" > "$LAST_CALL_FILE"
}

run_hermes_query() {
  local name="$1"
  local max_turns="$2"
  local query="$3"

  wait_for_rate_limit
  assert_capacity

  local cname
  cname="hermes-esdata-$(slug "$name")-$(date +%s)"
  timeout "$CALL_TIMEOUT" docker run --rm \
    --name "$cname" \
    --label esdata.hermes.curator=1 \
    --label esdata.hermes.task="$(slug "$name")" \
    -v "$ROOT:/opt/data" \
    "$IMAGE" chat -Q --max-turns "$max_turns" -q "$query"
}

write_report() {
  local path="$1"
  local status="$2"
  local body_file="$3"
  mkdir -p "$(dirname "$path")"
  {
    echo "<!--"
    echo "generated_at: $(iso)"
    echo "status: $status"
    echo "-->"
    echo
    cat "$body_file"
  } > "$path"
}
