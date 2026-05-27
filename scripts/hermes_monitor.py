#!/usr/bin/env python
"""Hermes Monitor - Real-time health monitoring for esdata workers.

Polls the API /status endpoint, detects unhealthy workers, auto-restarts
stale containers, and reports dead-letter queue entries exceeding max retries.

Usage:
    python scripts/hermes_monitor.py                          # Run once
    python scripts/hermes_monitor.py --daemon                 # Continuous monitoring
    python scripts/hermes_monitor.py --daemon --logfile /tmp/monitor.log
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import threading
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger("hermes-monitor")

# ── Configuration via environment variables ──────────────────────────────────

API_URL = os.getenv("ESDATA_API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("ESDATA_API_KEY", "")
MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", "300"))
AUTO_RESTART_ENABLED = os.getenv("AUTO_RESTART_ENABLED", "false").lower() == "true"
RESTART_ALLOWLIST = {
    item.strip()
    for item in os.getenv("RESTART_ALLOWLIST", "").split(",")
    if item.strip()
}
DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata")
DEPLOY_ROOT = os.getenv("ESDATA_DEPLOY_ROOT", "/srv/esdata")
COMPOSE_FILE = os.getenv("ESDATA_COMPOSE_FILE", f"{DEPLOY_ROOT}/infra/deploy/docker-compose.prod.yml")
COMPOSE_ENV_FILE = os.getenv("ESDATA_COMPOSE_ENV_FILE", "/etc/esdata/esdata.env")
POSTGRES_SERVICE = os.getenv("ESDATA_POSTGRES_SERVICE", "postgres")
POSTGRES_USER = os.getenv("ESDATA_POSTGRES_USER", "esdata")
POSTGRES_DB = os.getenv("ESDATA_POSTGRES_DB", "esdata")

# Stale threshold: workers older than this (hours) are considered unhealthy
STALE_THRESHOLD_HOURS = 2

# Grace period: only auto-restart if worker has been stale for > this duration
RESTART_GRACE_HOURS = 2


# ── Signal handling ─────────────────────────────────────────────────────────

_shutdown_event = threading.Event()


def _handle_signal(signum: int, _frame: Any) -> None:
    logger.info("Received signal %s, shutting down gracefully...", signal.Signals(signum).name)
    _shutdown_event.set()


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# ── HTTP client ─────────────────────────────────────────────────────────────

def get_status() -> dict | None:
    """Fetch the /status endpoint and return parsed JSON, or None on failure."""
    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY

    url = f"{API_URL}/status"
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return None
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error from %s: %s %s", url, exc.response.status_code, exc.response.text)
        return None


def check_health() -> dict | None:
    """Fetch the /health endpoint to verify API is reachable."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{API_URL}/health")
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        logger.error("Health check failed: %s", exc)
        return None


# ── Worker health analysis ──────────────────────────────────────────────────

def check_domain_availability() -> dict | None:
    """Fetch empty-domain availability metadata without mutating data."""
    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY

    url = f"{API_URL}/v1/domain-availability"
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params={"only_empty": "true"}, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        logger.error("Domain availability check failed for %s: %s", url, exc)
        return None
    except ValueError as exc:
        logger.error("Domain availability returned invalid JSON: %s", exc)
        return None


def analyze_domain_availability(payload: dict) -> dict[str, Any]:
    """Return operational counters for explicit empty-table states."""
    summary = payload.get("summary") or {}
    items = payload.get("items") or []
    statuses = {item.get("availability_status") for item in items}
    legacy = statuses & {"not_available", "operational_data"}
    mismatched = [
        item.get("table")
        for item in items
        if item.get("status") != item.get("availability_status")
    ]
    unknown = int(summary.get("unknown") or 0)

    return {
        "ok": unknown == 0 and not legacy and not mismatched,
        "total_empty_tables": int(payload.get("total") or len(items)),
        "workflow_empty": int(summary.get("workflow_empty") or 0),
        "allowed_empty": int(summary.get("allowed_empty") or 0),
        "configured_but_unavailable": int(summary.get("configured_but_unavailable") or 0),
        "unknown": unknown,
        "legacy_statuses": sorted(legacy),
        "mismatched_status_tables": mismatched[:20],
    }


def analyze_workers(status: dict) -> list[dict]:
    """Analyze workers from status payload and return list of unhealthy entries."""
    unhealthy = []
    workers = status.get("workers", {})

    for worker_name, info in workers.items():
        status_val = info.get("status", "unknown")
        stale = info.get("stale", False)
        finished_at = info.get("finished_at")
        last_run = info.get("last_run")

        entry = {
            "name": worker_name,
            "status": status_val,
            "stale": stale,
            "finished_at": finished_at,
            "last_run": last_run,
        }

        # Detect unhealthy: stale flag set, or explicit error status
        if stale:
            entry["reason"] = "stale"
            unhealthy.append(entry)
        elif status_val in ("error", "partial"):
            entry["reason"] = f"status={status_val}"
            unhealthy.append(entry)

    return unhealthy


def _parse_iso(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, TypeError):
        return None


def _hours_since(dt_str: str | None) -> float | None:
    dt = _parse_iso(dt_str)
    if not dt:
        return None
    return (datetime.now(UTC) - dt).total_seconds() / 3600


def should_restart(worker: dict) -> bool:
    """Determine if a worker should be auto-restarted.

    Only restart if the worker has been stale/unhealthy for more than
    RESTART_GRACE_HOURS.
    """
    if not AUTO_RESTART_ENABLED:
        return False
    if worker.get("name") not in RESTART_ALLOWLIST:
        return False

    hours = _hours_since(worker.get("finished_at"))
    if hours is None or hours < RESTART_GRACE_HOURS:
        return False

    return True


# ── Docker restart ──────────────────────────────────────────────────────────

def restart_worker_docker(worker_name: str) -> bool:
    """Restart a Docker container for the given worker name.

    Maps worker names to Docker container/service names:
        worker-boe -> worker-boe
        cron-boe-daily -> cron-boe-daily
    """
    container_name = worker_name.replace("worker-", "").replace("cron-", "")
    # Try the worker name directly as container/service name first
    candidates = [worker_name, container_name]

    for name in candidates:
        try:
            logger.info("Restarting Docker container/service: %s", name)
            result = subprocess.run(
                ["docker", "restart", name],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                logger.info(
                    "Successfully restarted %s (stdout: %s)",
                    name,
                    result.stdout.strip(),
                )
                return True
            else:
                logger.warning(
                    "docker restart %s failed (rc=%d): %s",
                    name,
                    result.returncode,
                    result.stderr.strip(),
                )
        except FileNotFoundError:
            logger.error("docker command not found. Is Docker installed?")
            return False
        except subprocess.TimeoutExpired:
            logger.error("docker restart %s timed out", name)
            return False
        except Exception as exc:
            logger.error("Failed to restart %s: %s", name, exc)
            return False

    logger.error("No matching Docker container found for worker: %s", worker_name)
    return False


# ── Dead Letter Queue ───────────────────────────────────────────────────────

_DLQ_SQL = """
SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json)
FROM (
    SELECT id, worker_name, entity_id, entity_type,
           error_message, retry_count, max_retries,
           first_failed_at, last_failed_at
    FROM sync_dead_letter
    WHERE resolved IS NOT TRUE
      AND retry_count >= max_retries
    ORDER BY last_failed_at DESC
    LIMIT 50
) AS t
"""


def _dlq_query_via_docker_compose() -> list[dict]:
    """Read DLQ through the Postgres container when host DB drivers are missing."""
    env = os.environ.copy()
    docker_config = env.setdefault("DOCKER_CONFIG", "/tmp/esdata-hermes-monitor-docker")
    try:
        os.makedirs(docker_config, mode=0o700, exist_ok=True)
    except OSError as exc:
        logger.warning("DLQ docker fallback could not prepare DOCKER_CONFIG=%s: %s", docker_config, exc)

    command = [
        "docker",
        "compose",
        "--env-file",
        COMPOSE_ENV_FILE,
        "-f",
        COMPOSE_FILE,
        "exec",
        "-T",
        POSTGRES_SERVICE,
        "psql",
        "-U",
        POSTGRES_USER,
        "-d",
        POSTGRES_DB,
        "-At",
        "-c",
        _DLQ_SQL,
    ]
    result = subprocess.run(
        command,
        cwd=DEPLOY_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    if result.returncode != 0:
        logger.warning("DLQ docker fallback failed (rc=%d): %s", result.returncode, result.stderr.strip())
        return []

    raw = result.stdout.strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("DLQ docker fallback returned invalid JSON: %s", exc)
        return []
    if not isinstance(data, list):
        logger.warning("DLQ docker fallback returned non-list JSON")
        return []
    return [item for item in data if isinstance(item, dict)]


def check_dead_letter_queue() -> list[dict]:
    """Query the sync_dead_letter table and return entries at max retries."""
    dlq_entries = []

    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        logger.info("sqlalchemy not installed, using DLQ docker fallback")
        return _dlq_query_via_docker_compose()

    try:
        engine = create_engine(DB_URL, future=True, pool_pre_ping=True)
    except Exception as exc:
        logger.info("DLQ database engine unavailable, using docker fallback: %s", exc)
        return _dlq_query_via_docker_compose()

    try:
        with engine.connect() as conn:
            # Find entries at max retries that are not resolved
            rows = conn.execute(
                text("""
                    SELECT id, worker_name, entity_id, entity_type,
                           error_message, retry_count, max_retries,
                           first_failed_at, last_failed_at
                    FROM sync_dead_letter
                    WHERE resolved IS NOT TRUE
                      AND retry_count >= max_retries
                    ORDER BY last_failed_at DESC
                    LIMIT 50
                """)
            ).mappings().all()

            for row in rows:
                dlq_entries.append(dict(row))

    except Exception as exc:
        logger.error("Failed to query dead letter queue via SQLAlchemy: %s", exc)
        return _dlq_query_via_docker_compose()
    finally:
        engine.dispose()

    return dlq_entries


def format_dlq_report(entries: list[dict]) -> str:
    """Format dead letter queue entries into a human-readable report."""
    if not entries:
        return "DLQ: No entries exceeding max retries."

    lines = [f"DLQ ALERT: {len(entries)} entity/entities exceeding max retries:"]
    for entry in entries[:20]:  # Limit display
        worker = entry.get("worker_name", "?")
        entity = entry.get("entity_id", "?")
        entity_type = entry.get("entity_type", "?")
        retries = entry.get("retry_count", 0)
        max_retries = entry.get("max_retries", 0)
        last_failed = entry.get("last_failed_at", "unknown")
        error_msg = (entry.get("error_message") or "")[:100]

        lines.append(
            f"  [{entry.get('id','?')}] {worker} | {entity_type}:{entity} | "
            f"retries={retries}/{max_retries} | last={last_failed} | "
            f"err={error_msg}"
        )

    if len(entries) > 20:
        lines.append(f"  ... and {len(entries) - 20} more entries")

    return "\n".join(lines)


# ── Main monitoring loop ────────────────────────────────────────────────────

def run_single_check() -> dict:
    """Execute a single monitoring cycle and return summary."""
    summary = {
        "timestamp": datetime.now(UTC).isoformat(),
        "api_healthy": False,
        "availability_ok": False,
        "availability_empty_tables": 0,
        "availability_configured_but_unavailable": 0,
        "availability_unknown": 0,
        "workers_checked": 0,
        "workers_unhealthy": 0,
        "workers_restarted": 0,
        "dlq_entries": 0,
    }

    # 1. Health check
    health = check_health()
    if health:
        summary["api_healthy"] = True
        logger.info("API health check: OK")
    else:
        logger.warning("API health check: FAILED")

    # 2. Availability contract for empty domains. Read-only: no regulatory
    # records are written, repaired, or interpreted by this monitor.
    availability_payload = check_domain_availability()
    if availability_payload:
        availability = analyze_domain_availability(availability_payload)
        summary["availability_ok"] = availability["ok"]
        summary["availability_empty_tables"] = availability["total_empty_tables"]
        summary["availability_configured_but_unavailable"] = availability["configured_but_unavailable"]
        summary["availability_unknown"] = availability["unknown"]
        if availability["ok"]:
            logger.info(
                "Domain availability: OK empty=%d workflow=%d allowed=%d configured_unavailable=%d",
                availability["total_empty_tables"],
                availability["workflow_empty"],
                availability["allowed_empty"],
                availability["configured_but_unavailable"],
            )
        else:
            logger.warning("Domain availability contract issue: %s", availability)
    else:
        logger.warning("Domain availability check: FAILED")

    # 3. Fetch status
    status = get_status()
    if not status:
        logger.error("Cannot fetch /status endpoint. Skipping worker analysis.")
        return summary

    summary["workers_checked"] = len(status.get("workers", {}))
    logger.info("Fetched status for %d workers", summary["workers_checked"])

    # 4. Analyze workers
    unhealthy = analyze_workers(status)
    summary["workers_unhealthy"] = len(unhealthy)

    if unhealthy:
        logger.warning(
            "Unhealthy workers detected: %d", len(unhealthy)
        )
        for w in unhealthy:
            hours = _hours_since(w.get("finished_at"))
            hours_str = f"{hours:.1f}h" if hours is not None else "unknown"
            logger.warning(
                "  UNHEALTHY: %s (reason=%s, stale=%s, hours_since_run=%s)",
                w["name"],
                w["reason"],
                w["stale"],
                hours_str,
            )

        # 4. Auto-restart workers that have been stale > RESTART_GRACE_HOURS
        for w in unhealthy:
            if should_restart(w):
                logger.info(
                    "Worker %s has been stale for %.1fh > %.0fh threshold. Attempting restart...",
                    w["name"],
                    _hours_since(w["finished_at"]) or 0,
                    RESTART_GRACE_HOURS,
                )
                if restart_worker_docker(w["name"]):
                    summary["workers_restarted"] += 1
                    logger.info("Restart successful for %s", w["name"])
                else:
                    logger.error("Restart FAILED for %s", w["name"])
            elif not AUTO_RESTART_ENABLED:
                logger.info(
                    "Worker %s is unhealthy; auto-restart disabled, skipping restart",
                    w["name"],
                )
            elif w.get("name") not in RESTART_ALLOWLIST:
                logger.info(
                    "Worker %s is unhealthy; not in restart allowlist, skipping restart",
                    w["name"],
                )
            else:
                hours = _hours_since(w.get("finished_at"))
                hours_str = f"{hours:.1f}h" if hours is not None else "unknown"
                logger.info(
                    "Worker %s is unhealthy but within grace period (%s < %.0fh), skipping restart",
                    w["name"],
                    hours_str,
                    RESTART_GRACE_HOURS,
                )
    else:
        logger.info("All workers healthy")

    # 5. Check DLQ
    dlq = check_dead_letter_queue()
    summary["dlq_entries"] = len(dlq)

    if dlq:
        report = format_dlq_report(dlq)
        logger.warning(report)
    else:
        logger.info("DLQ: No entries exceeding max retries")

    return summary


def run_daemon() -> None:
    """Run continuous monitoring loop."""
    logger.info(
        "Starting Hermes Monitor daemon (interval=%ds, auto_restart=%s, api=%s)",
        MONITOR_INTERVAL,
        AUTO_RESTART_ENABLED,
        API_URL,
    )

    cycle = 0
    while not _shutdown_event.is_set():
        cycle += 1
        logger.info("--- Monitor cycle #%d ---", cycle)

        try:
            summary = run_single_check()

            # Log summary line
            logger.info(
                "Cycle #%d summary: api_healthy=%s workers_checked=%d "
                "availability_ok=%s availability_unknown=%d unhealthy=%d restarted=%d dlq=%s",
                cycle,
                summary["api_healthy"],
                summary["workers_checked"],
                summary["availability_ok"],
                summary["availability_unknown"],
                summary["workers_unhealthy"],
                summary["workers_restarted"],
                summary["dlq_entries"],
            )

        except Exception:
            logger.exception("Error in monitor cycle #%d", cycle)

        # Wait for next cycle or shutdown signal
        if _shutdown_event.wait(timeout=MONITOR_INTERVAL):
            break


# ── CLI ──────────────────────────────────────────────────────────────────────

def setup_logging(logfile: str | None = None) -> None:
    """Configure structured logging to stdout and optionally a file."""
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if logfile:
        file_handler = logging.FileHandler(logfile, mode="a", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        handlers.append(file_handler)

    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hermes Monitor - Real-time health monitoring for esdata workers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment variables:
  ESDATA_API_URL       API URL (default: http://localhost:8000)
  ESDATA_API_KEY       API key for authentication
  MONITOR_INTERVAL     Polling interval in seconds (default: 300)
  AUTO_RESTART_ENABLED Enable auto-restart of stale workers (default: true)
  DATABASE_URL         PostgreSQL connection string for DLQ check
  LOGFILE              Write logs to file in addition to stdout
        """,
    )

    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in continuous monitoring mode (default: run once)",
    )
    parser.add_argument(
        "--logfile",
        type=str,
        default=None,
        help="Log file path (default: stdout only)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=f"Polling interval in seconds (default: {MONITOR_INTERVAL})",
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="Disable auto-restart of stale workers",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help=f"API URL override (default: {API_URL})",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Apply CLI overrides
    if args.interval is not None:
        global MONITOR_INTERVAL
        MONITOR_INTERVAL = args.interval
    if args.no_restart:
        global AUTO_RESTART_ENABLED
        AUTO_RESTART_ENABLED = False
    if args.api_url:
        global API_URL
        API_URL = args.api_url.rstrip("/")

    setup_logging(logfile=args.logfile)

    logger.info(
        "Hermes Monitor starting: api=%s interval=%ds auto_restart=%s",
        API_URL,
        MONITOR_INTERVAL,
        AUTO_RESTART_ENABLED,
    )

    if args.daemon:
        run_daemon()
    else:
        run_single_check()

    logger.info("Hermes Monitor finished.")


if __name__ == "__main__":
    main()
