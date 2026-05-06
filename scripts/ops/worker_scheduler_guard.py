#!/usr/bin/env python3
"""Check and remediate scheduler/alert drift for esdata cron workers."""

from __future__ import annotations

import argparse
from pathlib import Path


def installed_unit_has_no_deps(unit_text: str) -> bool:
    return "--no-deps" in unit_text


def repo_alert_uses_stale_gauge(alerts_text: str) -> bool:
    return "alert: WorkerSilent" in alerts_text and "expr: worker_stale_status == 1" in alerts_text


def build_fix_drift_commands(repo_root: str) -> list[str]:
    return [
        (
            f"install -m 0644 {repo_root}/infra/deploy/systemd/esdata-job@.service "
            "/etc/systemd/system/esdata-job@.service"
        ),
        "systemctl daemon-reload",
        (
            f"docker compose --env-file /etc/esdata/esdata.env "
            f"-f {repo_root}/infra/deploy/docker-compose.prod.yml up -d prometheus"
        ),
    ]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or remediate worker scheduler drift")
    parser.add_argument("mode", choices=["check", "fix-drift", "rerun"])
    parser.add_argument("--repo-root", default="/srv/esdata")
    parser.add_argument("--installed-unit", default="/etc/systemd/system/esdata-job@.service")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("workers", nargs="*")
    args = parser.parse_args()

    if args.mode == "check":
        repo_root = Path(args.repo_root)
        alerts_text = _read(repo_root / "infra" / "observability" / "alerts.yml")
        unit_text = _read(Path(args.installed_unit))
        print(f"WorkerSilent uses stale gauge: {repo_alert_uses_stale_gauge(alerts_text)}")
        print(f"Installed unit has --no-deps: {installed_unit_has_no_deps(unit_text)}")
        return 0

    if args.mode == "fix-drift":
        commands = build_fix_drift_commands(args.repo_root)
        for command in commands:
            print(command)
        if not args.apply:
            print("Dry run only. Re-run with --apply to execute manually approved steps.")
            return 0
        print("Apply mode requested. Execute the printed commands in an approved VPS session.")
        return 0

    if not args.workers:
        print("rerun requires at least one cron-* worker name")
        return 2

    for worker in args.workers:
        print(f"sudo systemctl start esdata-job@{worker}.service")
        print(f"systemctl show esdata-job@{worker}.service -p Result -p ExecMainStatus -p ActiveState -p SubState")
        print(f"journalctl -u esdata-job@{worker}.service -n 80 --no-pager")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
