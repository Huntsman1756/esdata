"""Single local Ralph gate before any VPS deployment.

This gate is intentionally conservative:
- live-checks tables, script registry, and MCP/API accuracy;
- validates existing cron/worker run-once artifacts instead of re-running long
  ingestion jobs by default;
- fails non-zero on any missing artifact or failed check.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RALPH = ROOT / "scripts" / "ralph"
WORKER_RESULT_FILES = [
    "worker-run-once-results-weekly.json",
    "worker-run-once-results-psd2.json",
    "worker-run-once-results-boe-modelos.json",
    "worker-run-once-results-aeat-current.json",
    "worker-run-once-results-regulatory-fixed.json",
    "worker-run-once-results-modelos.json",
    "worker-run-once-results-boe-full.json",
]


@dataclass
class GateCheck:
    name: str
    status: str
    evidence: dict[str, Any]
    blocker: str | None = None


def run_command(name: str, cmd: list[str], *, timeout: int = 120) -> GateCheck:
    env = os.environ.copy()
    env.setdefault("ESDATA_API_KEY", "dev-key")
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    evidence = {
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }
    if proc.returncode == 0:
        return GateCheck(name, "pass", evidence)
    return GateCheck(name, "fail", evidence, f"{name} command failed")


def check_worker_artifacts() -> GateCheck:
    missing = []
    failed = []
    totals = {"total": 0, "passed": 0, "failed": 0, "timeouts": 0}
    services: list[str] = []
    for filename in WORKER_RESULT_FILES:
        path = RALPH / filename
        if not path.exists():
            missing.append(filename)
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        totals["total"] += int(data.get("total", 0))
        totals["passed"] += int(data.get("passed", 0))
        totals["failed"] += int(data.get("failed", 0))
        totals["timeouts"] += int(data.get("timeouts", 0))
        for result in data.get("results", []):
            services.append(result.get("service", "unknown"))
            if result.get("status") != "pass" or result.get("exit_code") != 0:
                failed.append(
                    {
                        "file": filename,
                        "service": result.get("service"),
                        "status": result.get("status"),
                        "exit_code": result.get("exit_code"),
                    }
                )
    evidence = {
        "files": WORKER_RESULT_FILES,
        "missing": missing,
        "failed_results": failed,
        "totals": totals,
        "services": sorted(services),
    }
    if missing or failed or totals != {"total": 16, "passed": 16, "failed": 0, "timeouts": 0}:
        return GateCheck("worker_cron_artifacts", "fail", evidence, "Cron/worker artifacts are missing or not all passing.")
    return GateCheck("worker_cron_artifacts", "pass", evidence)


def check_prd() -> GateCheck:
    path = RALPH / "prd-local-full-verification.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    incomplete = [
        story["id"]
        for story in data["userStories"]
        if story["id"] != "LOCAL-006" and not story.get("passes")
    ]
    evidence = {"path": str(path.relative_to(ROOT)), "incomplete": incomplete}
    if incomplete:
        return GateCheck("prd_status", "fail", evidence, "One or more prerequisite LOCAL stories are not passing.")
    return GateCheck("prd_status", "pass", evidence)


def run_gate(base_url: str, api_key: str) -> dict[str, Any]:
    checks = [
        check_prd(),
        run_command(
            "table_registry_gate",
            [sys.executable, "scripts/ralph/table_registry.py", "--gate", "scripts/ralph/table-remediation-registry.json"],
        ),
        check_worker_artifacts(),
        run_command(
            "script_registry_gate",
            [sys.executable, "scripts/ralph/verify_scripts_local.py", "--gate", "scripts/ralph/script-verification-registry.json"],
        ),
        run_command(
            "mcp_api_accuracy_gate",
            [
                sys.executable,
                "scripts/ralph/verify_mcp_api_local.py",
                "--base-url",
                base_url,
                "--api-key",
                api_key,
                "--write",
                "scripts/ralph/mcp-api-local-results.json",
            ],
        ),
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "local-only pre-VPS deployment gate",
        "summary": {
            "total": len(checks),
            "passed": sum(1 for check in checks if check.status == "pass"),
            "failed": sum(1 for check in checks if check.status == "fail"),
        },
        "checks": [asdict(check) for check in checks],
        "ok": all(check.status == "pass" for check in checks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("ESDATA_API_URL", "http://localhost:8001"))
    parser.add_argument("--api-key", default=os.getenv("ESDATA_API_KEY", "dev-key"))
    parser.add_argument("--write", type=Path, default=RALPH / "local-full-gate-results.json")
    args = parser.parse_args()

    result = run_gate(args.base_url, args.api_key)
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
