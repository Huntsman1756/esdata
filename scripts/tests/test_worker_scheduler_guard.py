#!/usr/bin/env python3
"""Contract tests for worker scheduler drift guard."""

import shutil
import sys
from importlib import import_module
from pathlib import Path
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

worker_scheduler_guard = import_module("scripts.ops.worker_scheduler_guard")
build_fix_drift_commands = worker_scheduler_guard.build_fix_drift_commands
installed_unit_has_no_deps = worker_scheduler_guard.installed_unit_has_no_deps
main = worker_scheduler_guard.main
repo_alert_uses_stale_gauge = worker_scheduler_guard.repo_alert_uses_stale_gauge


def test_installed_unit_detects_no_deps_flag() -> None:
    unit_text = "ExecStart=/usr/bin/docker compose ... run --rm --no-deps %i\n"
    assert installed_unit_has_no_deps(unit_text) is True


def test_installed_unit_accepts_clean_run_rm_contract() -> None:
    unit_text = (
        "ExecStart=/usr/bin/docker compose --env-file /etc/esdata/esdata.env "
        "-f /srv/esdata/infra/deploy/docker-compose.prod.yml run --rm %i\n"
    )
    assert installed_unit_has_no_deps(unit_text) is False


def test_installed_unit_ignores_no_deps_in_comments() -> None:
    unit_text = "# keep run --rm --no-deps documented for old installs\nExecStart=/usr/bin/docker compose run --rm %i\n"

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


def test_repo_alert_accepts_spacing_variations_in_expr() -> None:
    alerts_text = """
groups:
  - name: esdata.workers
    rules:
      - alert: WorkerSilent
        expr: worker_stale_status   ==   1
"""

    assert repo_alert_uses_stale_gauge(alerts_text) is True


def test_repo_unit_file_uses_clean_run_rm_contract() -> None:
    unit_text = (REPO_ROOT / "infra/deploy/systemd/esdata-job@.service").read_text(encoding="utf-8")

    assert installed_unit_has_no_deps(unit_text) is False
    assert "/etc/esdata/esdata.env" in unit_text


def test_repo_alert_file_uses_stale_gauge_contract() -> None:
    alerts_text = (REPO_ROOT / "infra/observability/alerts.yml").read_text(encoding="utf-8")

    assert repo_alert_uses_stale_gauge(alerts_text) is True


def test_fix_drift_commands_reference_supported_runtime_paths() -> None:
    commands = build_fix_drift_commands(repo_root="/srv/esdata")
    assert any("/etc/esdata/esdata.env" in command for command in commands)
    assert any("esdata-job@.service" in command for command in commands)
    assert any("prometheus" in command for command in commands)


def test_check_reports_repo_and_installed_unit_contracts(capsys: pytest.CaptureFixture[str]) -> None:
    temp_root = REPO_ROOT / ".tmp-test-worker-scheduler-guard" / uuid4().hex

    try:
        repo_root = temp_root / "repo"
        alerts_path = repo_root / "infra/observability"
        alerts_path.mkdir(parents=True)
        (alerts_path / "alerts.yml").write_text(
            """
groups:
  - name: esdata.workers
    rules:
      - alert: WorkerSilent
        expr: worker_stale_status == 1
""".strip(),
            encoding="utf-8",
        )

        installed_unit = temp_root / "esdata-job@.service"
        installed_unit.write_text(
            "ExecStart=/usr/bin/docker compose --env-file /etc/esdata/esdata.env "
            "-f /srv/esdata/infra/deploy/docker-compose.prod.yml run --rm %i\n",
            encoding="utf-8",
        )

        exit_code = main(["check", "--repo-root", str(repo_root), "--installed-unit", str(installed_unit)])

        captured = capsys.readouterr()

        assert exit_code == 0
        assert "WorkerSilent uses stale gauge: True" in captured.out
        assert "Installed unit has --no-deps: False" in captured.out
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_fix_drift_dry_run_prints_commands_and_dry_run_message(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["fix-drift", "--repo-root", "/srv/esdata"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "install -m 0644 /srv/esdata/infra/deploy/systemd/esdata-job@.service" in captured.out
    assert "Dry run only. Re-run with --apply to execute manually approved steps." in captured.out


def test_fix_drift_apply_prints_apply_guidance(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["fix-drift", "--repo-root", "/srv/esdata", "--apply"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "systemctl daemon-reload" in captured.out
    assert "Apply mode requested. Execute the printed commands in an approved VPS session." in captured.out


def test_rerun_requires_worker_names(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["rerun"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "rerun requires at least one cron-* worker name" in captured.out


def test_rerun_rejects_non_cron_worker_names(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["rerun", "worker-dgt"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "rerun requires at least one cron-* worker name" in captured.out


def test_rerun_prints_three_validation_commands_per_worker(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["rerun", "cron-dgt-weekly", "cron-teac-weekly"])

    captured = capsys.readouterr()
    lines = [line for line in captured.out.strip().splitlines() if line]

    assert exit_code == 0
    assert lines == [
        "sudo systemctl start esdata-job@cron-dgt-weekly.service",
        "systemctl show esdata-job@cron-dgt-weekly.service -p Result -p ExecMainStatus -p ActiveState -p SubState",
        "journalctl -u esdata-job@cron-dgt-weekly.service -n 80 --no-pager",
        "sudo systemctl start esdata-job@cron-teac-weekly.service",
        "systemctl show esdata-job@cron-teac-weekly.service -p Result -p ExecMainStatus -p ActiveState -p SubState",
        "journalctl -u esdata-job@cron-teac-weekly.service -n 80 --no-pager",
    ]
