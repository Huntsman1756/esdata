#!/usr/bin/env python
"""Run local cron/worker verification against Docker Compose.

This is intentionally local-only. It does not SSH to the VPS and does not deploy.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = ROOT / "infra" / "deploy" / "docker-compose.prod.yml"
DEFAULT_OUTPUT = ROOT / "scripts" / "ralph" / "worker-run-once-results.json"


@dataclass
class WorkerResult:
    service: str
    worker_cmd: str
    mode: str
    status: str
    exit_code: int | None
    duration_seconds: float
    stdout_tail: str
    stderr_tail: str


def _tail(value: str | None, limit: int = 3000) -> str:
    if value is None:
        return ""
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[-limit:]


def load_cron_services() -> list[tuple[str, str]]:
    data = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    services = []
    for name, service in data.get("services", {}).items():
        profiles = service.get("profiles") or []
        env = service.get("environment") or {}
        worker_cmd = env.get("WORKER_CMD") if isinstance(env, dict) else None
        if "cron" in profiles and worker_cmd:
            services.append((name, worker_cmd))
    return sorted(services)


LOCAL_COMPOSE_ENV = {
    "DATABASE_URL": "postgresql+psycopg://esdata:esdata_dev@postgres:5432/esdata",
    "POSTGRES_PASSWORD": "esdata_dev",
    "ESDATA_API_KEY": "dev-key",
    "MCP_API_KEY": "dev-mcp-key",
    "API_DOMAIN": "api.localhost",
    "WEB_DOMAIN": "localhost",
    "CADDY_EMAIL": "devnull@example.invalid",
    "GRAFANA_ADMIN_PASSWORD": "dev-grafana-password",
    "ESDATA_API_BASE_URL": "http://api:8000",
    "BDNS_SEED_URLS": "https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/749075/document/1034404",
    "BORME_SEED_URLS": "https://www.boe.es/borme/dias/2025/03/20/pdfs/BORME-A-2025-55-37.pdf",
    "CNMV_SEED_URLS": "https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133",
    "SEPBLAC_SEED_URLS": "https://www.sepblac.es/es/,https://www.sepblac.es/es/publicaciones/",
    "CENDOJ_SEED_URLS": "https://www.poderjudicial.es/search/indexAN.jsp",
    "BDE_SEED_URLS": "https://www.bde.es/wbe/es/publicaciones/informacion-estadistica/",
    "AEPD_SEED_URLS": "https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673",
    "TEAC_SEED_URLS": "https://serviciostelematicosext.hacienda.gob.es/TEAC/DYCTEA/",
    "DGT_SSL_VERIFY": "false",
}


def _compose_env() -> dict[str, str]:
    env = os.environ.copy()
    for key, value in LOCAL_COMPOSE_ENV.items():
        env.setdefault(key, value)
    return env


def _command_for(service: str, worker_cmd: str, mode: str) -> list[str]:
    container_name = f"esdata-local-verify-{service}"
    if mode == "prod-compose":
        return [
            "docker",
            "compose",
            "-p",
            "esdata-local-cron",
            "-f",
            str(COMPOSE_FILE),
            "--profile",
            "cron",
            "run",
            "-d",
            "--name",
            container_name,
            service,
        ]
    if mode == "dev-worker":
        return [
            "docker",
            "compose",
            "run",
            "-d",
            "--name",
            container_name,
            "worker-boe",
            *shlex.split(worker_cmd),
        ]
    raise ValueError(f"unsupported mode: {mode}")


def _remove_previous_container(service: str) -> None:
    subprocess.run(
        ["docker", "rm", "-f", f"esdata-local-verify-{service}"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )


def run_service(service: str, worker_cmd: str, timeout_seconds: int, mode: str) -> WorkerResult:
    cmd = _command_for(service, worker_cmd, mode)
    _remove_previous_container(service)
    started = time.monotonic()
    container_name = f"esdata-local-verify-{service}"
    try:
        launched = subprocess.run(
            cmd,
            cwd=ROOT,
            env=_compose_env(),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=120,
        )
        if launched.returncode != 0:
            return WorkerResult(
                service=service,
                worker_cmd=worker_cmd,
                mode=mode,
                status="fail",
                exit_code=launched.returncode,
                duration_seconds=round(time.monotonic() - started, 2),
                stdout_tail=_tail(launched.stdout),
                stderr_tail=_tail(launched.stderr),
            )

        deadline = time.monotonic() + timeout_seconds
        exit_code: int | None = None
        while time.monotonic() < deadline:
            inspected = subprocess.run(
                [
                    "docker",
                    "inspect",
                    container_name,
                    "--format",
                    "{{.State.Running}} {{.State.ExitCode}}",
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=30,
            )
            if inspected.returncode != 0:
                exit_code = 127
                break
            running, raw_exit_code = inspected.stdout.strip().split()
            if running == "false":
                exit_code = int(raw_exit_code)
                break
            time.sleep(2)

        logs = subprocess.run(
            ["docker", "logs", container_name],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=60,
        )

        if exit_code is None:
            _remove_previous_container(service)
            return WorkerResult(
                service=service,
                worker_cmd=worker_cmd,
                mode=mode,
                status="timeout",
                exit_code=None,
                duration_seconds=round(time.monotonic() - started, 2),
                stdout_tail=_tail(logs.stdout),
                stderr_tail=_tail(logs.stderr),
            )

        status = "pass" if exit_code == 0 else "fail"
        _remove_previous_container(service)
        return WorkerResult(
            service=service,
            worker_cmd=worker_cmd,
            mode=mode,
            status=status,
            exit_code=exit_code,
            duration_seconds=round(time.monotonic() - started, 2),
            stdout_tail=_tail(logs.stdout),
            stderr_tail=_tail(logs.stderr),
        )
    except subprocess.TimeoutExpired as exc:
        _remove_previous_container(service)
        return WorkerResult(
            service=service,
            worker_cmd=worker_cmd,
            mode=mode,
            status="timeout",
            exit_code=None,
            duration_seconds=round(time.monotonic() - started, 2),
            stdout_tail=_tail(exc.stdout or ""),
            stderr_tail=_tail(exc.stderr or ""),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify local cron worker run-once services")
    parser.add_argument("--service", action="append", help="Only run this service; may be repeated")
    parser.add_argument("--timeout", type=int, default=180, help="Per-service timeout in seconds")
    parser.add_argument(
        "--mode",
        choices=("dev-worker", "prod-compose"),
        default="dev-worker",
        help=(
            "dev-worker runs each WORKER_CMD in the local development worker container; "
            "prod-compose runs the production cron service definition with local dummy env."
        ),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--list", action="store_true", help="List discovered cron services and exit")
    args = parser.parse_args()

    services = load_cron_services()
    if args.service:
        requested = set(args.service)
        services = [(name, cmd) for name, cmd in services if name in requested]
        missing = sorted(requested - {name for name, _cmd in services})
        if missing:
            print(f"ERROR: unknown services: {', '.join(missing)}", file=sys.stderr)
            return 2

    if args.list:
        for name, worker_cmd in services:
            print(f"{name}\t{worker_cmd}")
        return 0

    results = [run_service(name, worker_cmd, args.timeout, args.mode) for name, worker_cmd in services]
    payload = {
        "total": len(results),
        "passed": sum(1 for item in results if item.status == "pass"),
        "failed": sum(1 for item in results if item.status == "fail"),
        "timeouts": sum(1 for item in results if item.status == "timeout"),
        "results": [asdict(item) for item in results],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("total", "passed", "failed", "timeouts")}, indent=2))
    return 0 if payload["failed"] == 0 and payload["timeouts"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
