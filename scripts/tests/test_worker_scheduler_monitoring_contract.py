from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_CRON_SERVICES = (
    "cron-boe-daily",
    "cron-dgt-weekly",
    "cron-teac-weekly",
    "cron-modelos-daily",
    "cron-bdns-weekly",
    "cron-borme-weekly",
    "cron-cnmv-weekly",
    "cron-sepblac-weekly",
    "cron-bde-weekly",
    "cron-cendoj-weekly",
    "cron-aepd-weekly",
    "cron-eurlex-weekly",
)

EXPECTED_TIMER_UNITS = {
    "esdata-boe-daily.timer": "cron-boe-daily",
    "esdata-dgt-weekly.timer": "cron-dgt-weekly",
    "esdata-teac-weekly.timer": "cron-teac-weekly",
    "esdata-modelos-daily.timer": "cron-modelos-daily",
    "esdata-bdns-weekly.timer": "cron-bdns-weekly",
    "esdata-borme-weekly.timer": "cron-borme-weekly",
    "esdata-cnmv-weekly.timer": "cron-cnmv-weekly",
    "esdata-sepblac-weekly.timer": "cron-sepblac-weekly",
    "esdata-bde-weekly.timer": "cron-bde-weekly",
    "esdata-cendoj-weekly.timer": "cron-cendoj-weekly",
    "esdata-aepd-weekly.timer": "cron-aepd-weekly",
    "esdata-eurlex-weekly.timer": "cron-eurlex-weekly",
}


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _service_block(compose_text: str, service_name: str) -> str:
    lines = compose_text.splitlines()
    start = next(i for i, line in enumerate(lines) if line == f"  {service_name}:")
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if lines[i].startswith("  ") and not lines[i].startswith("    ")
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


def test_alerts_contract_uses_worker_stale_status_metric() -> None:
    content = _read("infra/observability/alerts.yml")

    assert "alert: WorkerSilent" in content
    assert "expr: worker_stale_status == 1" in content
    assert "worker_lag_seconds > 172800" not in content


def test_systemd_job_contract_uses_host_env_file_and_compose_run_rm_without_no_deps() -> None:
    content = _read("infra/deploy/systemd/esdata-job@.service")

    assert "docker compose" in content
    assert "--env-file /etc/esdata/esdata.env" in content
    assert "run --rm %i" in content
    assert "--no-deps" not in content


def test_deploy_runbook_contract_documents_scheduler_debug_and_stale_metric() -> None:
    content = _read("docs/operations/runbooks/deploy-compose.md")

    assert "systemctl cat esdata-job@.service" in content
    assert "worker_stale_status" in content


def test_compose_declares_all_documented_cron_services_on_internal_network() -> None:
    content = _read("infra/deploy/docker-compose.prod.yml")

    for service_name in EXPECTED_CRON_SERVICES:
        block = _service_block(content, service_name)
        assert "depends_on:" in block, service_name
        assert "postgres:" in block, service_name
        assert "networks:" in block, service_name
        assert "- esdata-internal" in block, service_name


def test_repo_contains_timer_templates_for_all_documented_cron_jobs() -> None:
    systemd_dir = REPO_ROOT / "infra" / "deploy" / "systemd"

    for timer_name, service_name in EXPECTED_TIMER_UNITS.items():
        timer_path = systemd_dir / timer_name
        assert timer_path.exists(), timer_name
        content = timer_path.read_text(encoding="utf-8")
        assert f"Unit=esdata-job@{service_name}.service" in content


def test_server_installation_contract_mentions_manual_weekly_dgt_cron() -> None:
    content = _read("docs/deployment/server-installation.md")

    assert "run --rm cron-dgt-weekly" in content
