#!/usr/bin/env python3
"""Contract tests for worker scheduler drift guard."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.ops.worker_scheduler_guard import (  # type: ignore[import-not-found]
    build_fix_drift_commands,
    installed_unit_has_no_deps,
    repo_alert_uses_stale_gauge,
)


def test_installed_unit_detects_no_deps_flag() -> None:
    unit_text = "ExecStart=/usr/bin/docker compose ... run --rm --no-deps %i\n"
    assert installed_unit_has_no_deps(unit_text) is True


def test_installed_unit_accepts_clean_run_rm_contract() -> None:
    unit_text = (
        "ExecStart=/usr/bin/docker compose --env-file /etc/esdata/esdata.env "
        "-f /srv/esdata/infra/deploy/docker-compose.prod.yml run --rm %i\n"
    )
    assert installed_unit_has_no_deps(unit_text) is False


def test_repo_alert_detects_wrong_fixed_lag_rule() -> None:
    alerts_text = """
groups:
  - name: esdata.workers
    rules:
      - alert: WorkerSilent
        expr: worker_lag_seconds > 172800
"""
    assert repo_alert_uses_stale_gauge(alerts_text) is False


def test_repo_alert_accepts_exported_stale_gauge() -> None:
    alerts_text = """
groups:
  - name: esdata.workers
    rules:
      - alert: WorkerSilent
        expr: worker_stale_status == 1
"""
    assert repo_alert_uses_stale_gauge(alerts_text) is True


def test_fix_drift_commands_reference_supported_runtime_paths() -> None:
    commands = build_fix_drift_commands(repo_root="/srv/esdata")
    assert any("/etc/esdata/esdata.env" in command for command in commands)
    assert any("esdata-job@.service" in command for command in commands)
    assert any("prometheus" in command for command in commands)
