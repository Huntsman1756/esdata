import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = ROOT / "infra" / "deploy" / "docker-compose.prod.yml"
EXPECTED_EXTERNAL_ENV_FILE = "/etc/esdata/esdata.env"


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _continuous_worker_services() -> list[str]:
    worker_names: list[str] = []
    current_worker: str | None = None
    inside_services = False
    worker_has_profiles = False

    for raw_line in COMPOSE_FILE.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        if raw_line.startswith("services:"):
            inside_services = True
            continue

        if not inside_services:
            continue

        service_match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", raw_line)
        if service_match:
            if current_worker and not worker_has_profiles:
                worker_names.append(current_worker)

            service_name = service_match.group(1)
            current_worker = service_name if service_name.startswith("worker-") else None
            worker_has_profiles = False
            continue

        if re.match(r"^[^\s]", raw_line):
            break

        if current_worker and raw_line.startswith("    profiles:"):
            worker_has_profiles = True

    if current_worker and not worker_has_profiles:
        worker_names.append(current_worker)

    return worker_names


def _profiled_cron_services() -> list[str]:
    cron_names: list[str] = []
    current_service: str | None = None
    inside_services = False
    service_has_cron_profile = False

    for raw_line in COMPOSE_FILE.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        if raw_line.startswith("services:"):
            inside_services = True
            continue

        if not inside_services:
            continue

        service_match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", raw_line)
        if service_match:
            if current_service and current_service.startswith("cron-") and service_has_cron_profile:
                cron_names.append(current_service)

            current_service = service_match.group(1)
            service_has_cron_profile = False
            continue

        if re.match(r"^[^\s]", raw_line):
            break

        if current_service and 'profiles: ["cron"]' in raw_line:
            service_has_cron_profile = True

    if current_service and current_service.startswith("cron-") and service_has_cron_profile:
        cron_names.append(current_service)

    return cron_names


def _space_delimited_tokens(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9_-]+", text))


def _extract_up_line_workers(text: str) -> set[str]:
    for raw_line in text.splitlines():
        if " up -d " not in raw_line:
            continue
        if "worker-boe" not in raw_line:
            continue

        return {
            token
            for token in _space_delimited_tokens(raw_line)
            if token.startswith("worker-")
        }

    raise AssertionError("No canonical up -d worker line found")


def _extract_run_once_workers(text: str) -> set[str]:
    workers: set[str] = set()
    for raw_line in text.splitlines():
        if " run --rm worker-" not in raw_line:
            continue

        workers.update(
            token
            for token in _space_delimited_tokens(raw_line)
            if token.startswith("worker-")
        )

    return workers


def _service_block(text: str, service: str) -> str:
    marker = f"  {service}:"
    _, remainder = text.split(marker, 1)
    lines: list[str] = []
    for line in remainder.splitlines():
        if line.startswith("  ") and not line.startswith("    "):
            break
        lines.append(line)
    return "\n".join(lines)


def test_deploy_script_builds_ops_and_runs_migrations_before_app_services():
    script = _read("scripts/ops/deploy-hetzner.sh")

    build_ops = 'build ops'
    migrate = 'alembic upgrade head'
    verify = 'python scripts/maintenance/verify_schema.py'
    app_up = 'up -d --build --remove-orphans'

    assert build_ops in script
    assert migrate in script
    assert verify in script
    assert script.index(migrate) < script.index(verify) < script.index(app_up)


def test_deploy_workflow_delegates_to_canonical_script_with_migrations_required():
    workflow = _read(".github/workflows/deploy-hetzner.yml")

    assert "bash scripts/ops/deploy-hetzner.sh" in workflow
    assert "migrations required" in workflow.lower()


def test_server_installation_documents_canonical_deploy_script():
    doc = _read("docs/deployment/server-installation.md")

    assert "bash scripts/ops/deploy-hetzner.sh" in doc
    assert "alembic upgrade head" in doc
    assert "verify_schema.py" in doc


def test_deploy_compose_runbook_documents_canonical_deploy_script():
    doc = _read("docs/operations/runbooks/deploy-compose.md")

    assert "bash scripts/ops/deploy-hetzner.sh" in doc
    assert "alembic upgrade head" in doc
    assert "verify_schema.py" in doc


def test_canonical_deploy_worker_set_matches_continuous_compose_workers():
    expected_workers = set(_continuous_worker_services())

    script = _read("scripts/ops/deploy-hetzner.sh")
    server_doc = _read("docs/deployment/server-installation.md")
    runbook = _read("docs/operations/runbooks/deploy-compose.md")

    assert expected_workers
    assert _extract_up_line_workers(script) == expected_workers
    assert _extract_up_line_workers(server_doc) == expected_workers
    assert _extract_up_line_workers(runbook) == expected_workers
    assert _extract_run_once_workers(server_doc).issuperset(expected_workers)


def test_server_installation_root_matches_systemd_and_runbook_paths():
    expected_root = "/srv/esdata"

    server_doc = _read("docs/deployment/server-installation.md")
    runbook = _read("docs/operations/runbooks/deploy-compose.md")
    systemd_service = _read("infra/deploy/systemd/esdata-job@.service")

    assert "cd /srv" in server_doc
    assert expected_root in systemd_service
    assert f"{expected_root}/infra/observability/alertmanager.yml" in runbook


def test_canonical_deploy_uses_external_env_file_outside_repo_checkout():
    script = _read("scripts/ops/deploy-hetzner.sh")
    backup_script = _read("scripts/ops/backup-postgres.sh")
    server_doc = _read("docs/deployment/server-installation.md")
    runbook = _read("docs/operations/runbooks/deploy-compose.md")
    operations_readme = _read("docs/operations/README.md")
    operations_doc = _read("docs/operations/OPERATIONS.md")
    backup_runbook = _read("docs/operations/runbooks/backup-restore.md")
    worker_aeat_runbook = _read("docs/operations/runbooks/worker-aeat.md")
    opencode_doc = _read("docs/integrations/opencode-local-and-vps.md")
    env_doc = _read("docs/environment-variables.md")
    systemd_service = _read("infra/deploy/systemd/esdata-job@.service")
    readme = _read("README.md")
    install_doc = _read("docs/INSTALLATION.md")
    deploy_checklist = _read("DEPLOY_CHECKLIST.md")
    trial_doc = _read("docs/deployment/vps-trial-deploy.md")
    compliance_doc = _read("docs/COMPLIANCE.md")

    for text in (
        script,
        backup_script,
        server_doc,
        runbook,
        operations_readme,
        operations_doc,
        backup_runbook,
        worker_aeat_runbook,
        opencode_doc,
        env_doc,
        systemd_service,
        readme,
        install_doc,
        deploy_checklist,
        trial_doc,
        compliance_doc,
    ):
        assert EXPECTED_EXTERNAL_ENV_FILE in text

    assert "$ROOT_DIR/infra/deploy/.env.prod" not in script
    assert "$ROOT_DIR/infra/deploy/.env.prod" not in backup_script
    assert "/srv/esdata/infra/deploy/.env.prod" not in systemd_service
    assert "infra/deploy/.env.prod" not in server_doc
    assert "infra/deploy/.env.prod" not in runbook


def test_active_handoff_docs_use_canonical_deploy_flow_and_worker_set():
    expected_workers = set(_continuous_worker_services())

    readme = _read("README.md")
    install_doc = _read("docs/INSTALLATION.md")
    trial_doc = _read("docs/deployment/vps-trial-deploy.md")
    deploy_checklist = _read("DEPLOY_CHECKLIST.md")

    for text in (readme, install_doc, trial_doc, deploy_checklist):
        assert "bash scripts/ops/deploy-hetzner.sh" in text

    assert _extract_up_line_workers(readme) == expected_workers
    assert _extract_up_line_workers(install_doc) == expected_workers
    assert _extract_up_line_workers(trial_doc) == expected_workers


def test_active_handoff_docs_do_not_require_non_runtime_env_keys():
    deploy_checklist = _read("DEPLOY_CHECKLIST.md")
    trial_doc = _read("docs/deployment/vps-trial-deploy.md")

    assert "SECRET_KEY" not in deploy_checklist
    assert "MCP_RATE_LIMIT_PER_MINUTE" not in trial_doc


def test_compose_profiled_worker_does_not_depend_on_repo_local_env_file():
    compose = COMPOSE_FILE.read_text(encoding="utf-8")

    assert ".env.prod" not in compose
    assert "env_file:" not in compose


def test_systemd_cron_service_runs_compose_job_without_touching_dependencies():
    systemd_service = _read("infra/deploy/systemd/esdata-job@.service")

    assert "run --rm --no-deps %i" in systemd_service


def test_runbook_documents_no_deps_for_cron_services():
    runbook = _read("docs/operations/runbooks/deploy-compose.md")
    server_doc = _read("docs/deployment/server-installation.md")
    operations_readme = _read("docs/operations/README.md")

    assert "run --rm --no-deps cron-boe-daily" in runbook
    assert "run --rm --no-deps cron-cnmv-weekly" in server_doc
    assert "docker compose run --rm --no-deps cron-*" in operations_readme


def test_worker_silent_alert_uses_exported_stale_status_instead_of_global_lag_threshold():
    alerts = _read("infra/observability/alerts.yml")

    assert "expr: worker_stale_status == 1" in alerts
    assert "worker_lag_seconds > 172800" not in alerts


def test_cron_services_use_esdata_internal_network_for_database_resolution():
    compose = _read("infra/deploy/docker-compose.prod.yml")

    for service in (
        "cron-boe-daily",
        "cron-dgt-weekly",
        "cron-teac-weekly",
        "cron-modelos-daily",
        "cron-bdns-weekly",
        "cron-borme-weekly",
        "cron-cnmv-weekly",
        "cron-sepblac-weekly",
        "cron-bde-weekly",
    ):
        block = _service_block(compose, service)
        assert "networks:" in block
        assert "- esdata-internal" in block


def test_every_profiled_cron_service_has_systemd_timer():
    timer_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "infra" / "deploy" / "systemd").glob("*.timer")
    )

    missing = [
        service
        for service in _profiled_cron_services()
        if f"Unit=esdata-job@{service}.service" not in timer_text
    ]

    assert not missing


def test_esdata_timers_pin_europe_madrid_timezone():
    for timer in (ROOT / "infra" / "deploy" / "systemd").glob("esdata-*.timer"):
        text = timer.read_text(encoding="utf-8")
        on_calendar_lines = [
            line for line in text.splitlines() if line.startswith("OnCalendar=")
        ]
        assert on_calendar_lines, timer.name
        for line in on_calendar_lines:
            assert "Europe/Madrid" in line, f"{timer.name}: {line}"


def test_maintenance_agent_units_are_safe_by_default():
    hermes = _read("infra/deploy/systemd/esdata-hermes-monitor.service")
    validation_service = _read("infra/deploy/systemd/esdata-mcp-validation.service")
    validation_timer = _read("infra/deploy/systemd/esdata-mcp-validation.timer")

    assert "User=deploy" in hermes
    assert "AUTO_RESTART_ENABLED=false" in hermes
    assert "RESTART_ALLOWLIST=" in hermes
    assert "NoNewPrivileges=true" in hermes
    assert "ProtectSystem=strict" in hermes

    assert "User=deploy" in validation_service
    assert "mcp_validation_suite.py --read-only" in validation_service
    assert "NoNewPrivileges=true" in validation_service
    assert "Unit=esdata-mcp-validation.service" in validation_timer
