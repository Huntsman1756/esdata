"""Final Ralph product-readiness gate before VPS rollout.

This gate proves local product readiness and validates VPS deployment artifacts.
It intentionally does not claim that the VPS is healthy; run the same checks on
the VPS after deployment to close that final environment-specific step.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RALPH = ROOT / "scripts" / "ralph"


@dataclass
class GateCheck:
    name: str
    status: str
    evidence: dict[str, Any]
    blocker: str | None = None


def run_command(name: str, cmd: list[str], *, timeout: int = 180) -> GateCheck:
    env = os.environ.copy()
    env.setdefault("ESDATA_API_KEY", "dev-key")
    env.setdefault("ESDATA_API_URL", "http://localhost:8001")
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
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
    }
    if proc.returncode == 0:
        return GateCheck(name, "pass", evidence)
    return GateCheck(name, "fail", evidence, f"{name} command failed")


def check_alertmanager_config() -> GateCheck:
    source = ROOT / "infra" / "observability" / "alertmanager.yml"
    rendered = source.read_text(encoding="utf-8").replace("__TELEGRAM_CHAT_ID__", "123456789")
    with tempfile.TemporaryDirectory(prefix="esdata-alertmanager-") as tmp_dir:
        tmp = Path(tmp_dir)
        config = tmp / "alertmanager.yml"
        token = tmp / "telegram_bot_token"
        config.write_text(rendered, encoding="utf-8")
        token.write_text("123456:dummy", encoding="utf-8")

        cmd = [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "amtool",
            "-v",
            f"{config}:/etc/alertmanager/alertmanager.yml:ro",
            "-v",
            f"{tmp}:/etc/alertmanager/secrets:ro",
            "prom/alertmanager:v0.28.1",
            "check-config",
            "/etc/alertmanager/alertmanager.yml",
        ]
        return run_command("alertmanager_telegram_config", cmd, timeout=120)


def check_final_prd(all_passed: bool) -> GateCheck:
    path = RALPH / "prd-final-product-readiness.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    stories = [story["id"] for story in data["userStories"]]
    evidence = {
        "path": str(path.relative_to(ROOT)),
        "stories": stories,
        "runtime_gate_passed": all_passed,
    }
    if all_passed:
        return GateCheck("final_prd_status", "pass", evidence)
    return GateCheck("final_prd_status", "fail", evidence, "One or more final product checks failed.")


def run_gate(base_url: str, api_key: str) -> dict[str, Any]:
    checks = [
        run_command(
            "local_full_gate",
            [
                sys.executable,
                "scripts/ralph/local_full_gate.py",
                "--base-url",
                base_url,
                "--api-key",
                api_key,
                "--write",
                "scripts/ralph/local-full-gate-results.json",
            ],
            timeout=240,
        ),
        run_command(
            "compose_prod_config",
            [
                "docker",
                "compose",
                "--env-file",
                "infra/deploy/compose.env.example",
                "-f",
                "infra/deploy/docker-compose.prod.yml",
                "config",
                "--quiet",
            ],
        ),
        check_alertmanager_config(),
        run_command(
            "maintenance_agent_tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "scripts/tests/test_maintenance_agents.py",
                "scripts/tests/test_deploy_hetzner.py",
                "-q",
            ],
        ),
        run_command(
            "hermes_read_only_probe",
            [
                "docker",
                "compose",
                "run",
                "--rm",
                "--no-deps",
                "-e",
                "ESDATA_API_URL=http://api:8000",
                "-e",
                f"ESDATA_API_KEY={api_key}",
                "-e",
                "DATABASE_URL=postgresql+psycopg://esdata:esdata_dev@postgres:5432/esdata",
                "worker-boe",
                "python",
                "hermes_monitor.py",
                "--no-restart",
            ],
            timeout=120,
        ),
    ]
    all_passed = all(check.status == "pass" for check in checks)
    checks.append(check_final_prd(all_passed))

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "local final product-readiness gate plus VPS artifact validation",
        "summary": {
            "total": len(checks),
            "passed": sum(1 for check in checks if check.status == "pass"),
            "failed": sum(1 for check in checks if check.status == "fail"),
        },
        "checks": [asdict(check) for check in checks],
        "ok": all(check.status == "pass" for check in checks),
        "vps_scope_note": "VPS deployment and live Telegram delivery still require running this gate and the documented smoke tests on the server.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("ESDATA_API_URL", "http://localhost:8001"))
    parser.add_argument("--api-key", default=os.getenv("ESDATA_API_KEY", "dev-key"))
    parser.add_argument("--write", type=Path, default=RALPH / "final-product-gate-results.json")
    args = parser.parse_args()

    result = run_gate(args.base_url, args.api_key)
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
