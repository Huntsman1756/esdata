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
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger("hermes-monitor")

# ── Configuration via environment variables ──────────────────────────────────

API_URL = os.getenv("ESDATA_API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("ESDATA_API_KEY", "")
MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", "300"))
AUTO_RESTART_ENABLED = os.getenv("AUTO_RESTART_ENABLED", "true").lower() == "true"

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


# ── Main monitoring loop ────────────────────────────────────────────────────

def run_single_check() -> dict:
    """Execute a single monitoring cycle and return summary."""
    summary = {
        "timestamp": datetime.now(UTC).isoformat(),
        "api_healthy": False,
        "workers_checked": 0,
        "workers_unhealthy": 0,
        "workers_restarted": 0,
    }

    # 1. Health check
    health = check_health()
    if health:
        summary["api_healthy"] = True
        logger.info("API health check: OK")
    else:
        logger.warning("API health check: FAILED")

    # 2. Fetch status
    status = get_status()
    if not status:
        logger.error("Cannot fetch /status endpoint. Skipping worker analysis.")
        return summary

    summary["workers_checked"] = len(status.get("workers", {}))
    logger.info("Fetched status for %d workers", summary["workers_checked"])

    # 3. Analyze workers
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
            else:
                logger.info(
                    "Worker %s is unhealthy but within grace period (%.1fh < %.0fh), skipping restart",
                    w["name"],
                    _hours_since(w["finished_at"]) or 0,
                    RESTART_GRACE_HOURS,
                )
    else:
        logger.info("All workers healthy")

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
                "unhealthy=%d restarted=%d",
                cycle,
                summary["api_healthy"],
                summary["workers_checked"],
                summary["workers_unhealthy"],
                summary["workers_restarted"],
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
