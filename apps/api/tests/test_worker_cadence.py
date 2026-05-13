"""Tests for the canonical worker cadence registry."""

# ruff: noqa: E402,I001

from __future__ import annotations

import re
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = API_DIR.parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from routers.status import WORKER_THRESHOLDS_HOURS
from services.worker_cadence import (
    WORKER_CADENCE_ALIASES,
    WORKER_CADENCE_CONFIG,
    WORKER_CADENCE_EXCLUDED,
)


SYSTEMD_DIR = REPO_ROOT / "infra" / "deploy" / "systemd"
COMPOSE_FILE = REPO_ROOT / "infra" / "deploy" / "docker-compose.prod.yml"

SCHEDULER_SERVICE_TO_STATUS_WORKER = {
    "cron-boe-modelos-daily": "worker-boe-modelos",
    "cron-eurlex-market-monthly": "worker-eurlex-market",
    "cron-esma-mifir-reporting-weekly": "worker-esma-mifir-reporting",
    "cron-esma-firds-daily": "worker-esma-firds",
    "cron-esma-dlt-weekly": "worker-esma-dlt",
}

EXPECTED_SYNC_LOG_WORKERS = {
    "cron-aepd-weekly",
    "cron-aeat-current-daily",
    "cron-bde-weekly",
    "cron-bdns-weekly",
    "cron-boe-daily",
    "cron-boe-diario-daily",
    "cron-borme-weekly",
    "cron-cdi-weekly",
    "cron-cendoj-weekly",
    "cron-cnmv-weekly",
    "cron-dgt-weekly",
    "cron-eurlex-weekly",
    "cron-giin-monthly",
    "cron-mica-weekly",
    "cron-modelos-daily",
    "cron-ofac-sdn-weekly",
    "cron-pgc-boe-monthly",
    "cron-psd2-weekly",
    "cron-regulatory-daily",
    "cron-sepblac-weekly",
    "cron-teac-weekly",
    "official-regulatory-references",
    "worker-aeat-current-designs",
    "worker-aeat-modelos",
    "worker-aepd",
    "worker-bde",
    "worker-bdns",
    "worker-boe",
    "worker-boe-modelos",
    "worker-borme",
    "worker-cdi",
    "worker-cendoj",
    "worker-cnmv",
    "worker-dgt",
    "worker-eurlex",
    "worker-eurlex-market",
    "worker-esma-dlt",
    "worker-esma-firds",
    "worker-esma-mifir-reporting",
    "worker-modelos",
    "worker-sepblac",
    "worker-teac",
}


def _timer_cadence_hours(on_calendar: str) -> int:
    if on_calendar.startswith("*-*-*"):
        return 24
    if on_calendar.startswith(("Mon ", "Tue ", "Wed ", "Thu ", "Fri ", "Sat ", "Sun ")):
        return 168
    if on_calendar.startswith("weekly"):
        return 168
    if re.match(r"^\*-\*-\d{2} ", on_calendar):
        return 720
    raise AssertionError(f"Unsupported OnCalendar cadence: {on_calendar}")


def _timer_service_name(timer_text: str) -> str | None:
    match = re.search(r"^Unit=esdata-job@(.+)\.service$", timer_text, re.MULTILINE)
    return match.group(1) if match else None


def _timer_on_calendar(timer_text: str) -> str | None:
    match = re.search(r"^OnCalendar=(.+)$", timer_text, re.MULTILINE)
    return match.group(1).strip() if match else None


def _compose_worker_block(service_name: str) -> str:
    text = COMPOSE_FILE.read_text(encoding="utf-8")
    pattern = rf"^  {re.escape(service_name)}:\n(?P<body>(?:    .+\n|      .+\n|        .+\n|  \n)*)"
    match = re.search(pattern, text, re.MULTILINE)
    assert match is not None, f"Compose service missing: {service_name}"
    return match.group("body")


def _compose_interval_hours(service_name: str) -> int:
    block = _compose_worker_block(service_name)
    for line in block.splitlines():
        if "INTERVAL" not in line:
            continue
        default_match = re.search(r":-\s*(\d+)\}", line)
        if default_match is not None:
            return int(default_match.group(1)) // 3600
    raise AssertionError(f"Compose interval default missing for {service_name}")


def test_status_thresholds_are_derived_from_canonical_cadence_config():
    expected = {
        worker: config["stale_threshold_hours"]
        for worker, config in WORKER_CADENCE_CONFIG.items()
    }

    assert WORKER_THRESHOLDS_HOURS == expected


def test_every_configured_worker_has_explicit_positive_cadence_and_buffer():
    for worker, config in WORKER_CADENCE_CONFIG.items():
        assert config["expected_cadence_hours"] > 0, worker
        assert config["stale_threshold_hours"] > 0, worker
        assert config["stale_threshold_hours"] >= config["expected_cadence_hours"] * 1.5, worker
        assert config["trigger"] in {"cron_daily", "cron_weekly", "cron_monthly", "event_driven", "manual"}
        assert config["cron_expression"], worker
        assert config["notes"], worker


def test_all_known_sync_log_workers_have_cadence_config_or_alias():
    missing = sorted(
        worker
        for worker in EXPECTED_SYNC_LOG_WORKERS
        if worker not in WORKER_CADENCE_CONFIG
        and worker not in WORKER_CADENCE_ALIASES
        and worker not in WORKER_CADENCE_EXCLUDED
    )

    assert missing == []


def test_systemd_timer_cadences_match_worker_config():
    mismatches = {}
    for timer in SYSTEMD_DIR.glob("esdata-*.timer"):
        text = timer.read_text(encoding="utf-8")
        service = _timer_service_name(text)
        on_calendar = _timer_on_calendar(text)
        if not service or service in WORKER_CADENCE_EXCLUDED:
            continue
        worker = SCHEDULER_SERVICE_TO_STATUS_WORKER.get(service, service)
        if worker not in WORKER_CADENCE_CONFIG:
            continue
        expected = _timer_cadence_hours(on_calendar or "")
        actual = WORKER_CADENCE_CONFIG[worker]["expected_cadence_hours"]
        if actual != expected:
            mismatches[worker] = {"timer": timer.name, "expected": expected, "actual": actual}

    assert mismatches == {}


def test_persistent_compose_worker_intervals_match_worker_config():
    services = {
        "worker-boe",
        "worker-boe-modelos",
        "worker-modelos",
        "worker-dgt",
        "worker-teac",
        "worker-bdns",
        "worker-borme",
        "worker-cnmv",
        "worker-sepblac",
        "worker-cendoj",
        "worker-eurlex",
        "worker-bde",
        "worker-cdi",
        "worker-aepd",
    }
    mismatches = {}
    for service in services:
        interval = _compose_interval_hours(service)
        actual = WORKER_CADENCE_CONFIG[service]["expected_cadence_hours"]
        if actual != interval:
            mismatches[service] = {"compose_interval_hours": interval, "config": actual}

    assert mismatches == {}
