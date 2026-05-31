#!/usr/bin/env bash
set -Eeuo pipefail

. "$(dirname "$0")/common.sh"

out_dir="$REPORTS/ops-health"
snapshot_dir="$ROOT/snapshots/ops"
mkdir -p "$out_dir" "$snapshot_dir"

stamp="$(ts)"
snapshot="$snapshot_dir/ops-$stamp.txt"
out="$out_dir/ops-$stamp.md"

{
  echo "# OPS SNAPSHOT $stamp"
  echo "## docker ps"
  docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
  echo
  echo "## docker system df"
  docker system df || true
  echo
  echo "## esdata repo"
  cd /srv/esdata && git rev-parse --short HEAD && git status --short --branch --untracked-files=no || true
  echo
  echo "## hermes curator files"
  find "$REPORTS" -maxdepth 2 -type f -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' 2>/dev/null | sort -r | head -80 || true
} > "$snapshot"

decision="HEALTHY"
risks="- No deterministic ops blocker detected."
if grep -qiE 'unhealthy|Restarting|health: starting|ERROR|Permission denied' "$snapshot"; then
  decision="WARNING"
  risks="- Docker or command output contains unhealthy/restarting/starting/error/permission-denied signals."
fi

cat > "$out" <<EOF
<!--
generated_at: $(iso)
status: OK
mode: deterministic
decision: $decision
snapshot: $snapshot
-->
# Ops health $stamp
## Decision
$decision
## Evidence
- Snapshot: $snapshot
## Risks
$risks
## Rule
No restarts, prune, upgrades, deploys or DB writes from Hermes automation.
EOF

echo "DONE ops report: $out"
