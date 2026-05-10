from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_hermes(monkeypatch, **env):
    for key in ("AUTO_RESTART_ENABLED", "RESTART_ALLOWLIST"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    path = ROOT / "scripts" / "hermes_monitor.py"
    spec = importlib.util.spec_from_file_location("hermes_monitor_under_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_validation_suite():
    path = ROOT / "scripts" / "maintenance" / "mcp_validation_suite.py"
    spec = importlib.util.spec_from_file_location("mcp_validation_suite_under_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hermes_monitor_is_read_only_by_default(monkeypatch):
    hermes = _load_hermes(monkeypatch)

    assert hermes.AUTO_RESTART_ENABLED is False
    assert hermes.should_restart({"finished_at": "2026-01-01T00:00:00+00:00"}) is False


def test_hermes_monitor_restart_requires_explicit_allowlist(monkeypatch):
    hermes = _load_hermes(
        monkeypatch,
        AUTO_RESTART_ENABLED="true",
        RESTART_ALLOWLIST="worker-boe",
    )

    allowed = {
        "name": "worker-boe",
        "finished_at": "2026-01-01T00:00:00+00:00",
    }
    disallowed = {
        "name": "worker-dgt",
        "finished_at": "2026-01-01T00:00:00+00:00",
    }

    assert hermes.should_restart(allowed) is True
    assert hermes.should_restart(disallowed) is False


def test_hermes_monitor_dlq_driver_failure_is_nonfatal(monkeypatch):
    hermes = _load_hermes(monkeypatch)
    hermes.DB_URL = "postgresql+missingdriver://example"

    assert hermes.check_dead_letter_queue() == []


def test_hermes_monitor_analyzes_domain_availability_contract(monkeypatch):
    hermes = _load_hermes(monkeypatch)

    analysis = hermes.analyze_domain_availability(
        {
            "summary": {
                "workflow_empty": 2,
                "allowed_empty": 1,
                "configured_but_unavailable": 3,
                "unknown": 0,
            },
            "items": [
                {"table": "workflow_case", "status": "workflow_empty", "availability_status": "workflow_empty"},
                {"table": "casp", "status": "configured_but_unavailable", "availability_status": "configured_but_unavailable"},
            ],
            "total": 2,
        }
    )

    assert analysis["ok"] is True
    assert analysis["total_empty_tables"] == 2
    assert analysis["configured_but_unavailable"] == 3
    assert analysis["unknown"] == 0


def test_mcp_validation_suite_accepts_explicit_empty_domain_contract():
    suite = _load_validation_suite()

    ok, details = suite._validate_domain_availability(
        {
            "summary": {
                "workflow_empty": 1,
                "allowed_empty": 1,
                "configured_but_unavailable": 1,
                "unknown": 0,
            },
            "items": [
                {"table": "workflow_case", "status": "workflow_empty", "availability_status": "workflow_empty"},
                {"table": "alert_case", "status": "allowed_empty", "availability_status": "allowed_empty"},
                {"table": "casp", "status": "configured_but_unavailable", "availability_status": "configured_but_unavailable"},
            ],
            "total": 3,
        }
    )

    assert ok is True
    assert details["legacy_statuses"] == []


def test_mcp_validation_suite_requires_fail_closed_empty_domain_response():
    suite = _load_validation_suite()

    ok, details = suite._validate_empty_domain_abstention(
        {
            "total_resultados": 0,
            "resultados": [],
            "cited_chunks": [],
            "confianza": {
                "review_required": True,
                "aviso": "NO VERIFICADO: dominio sin datos oficiales disponibles.",
                "availability": {
                    "blocked": True,
                    "tables": [
                        {"table": "casp", "safe_to_answer": False},
                    ],
                },
            },
        }
    )

    assert ok is True
    assert details["blocked"] is True
    assert "casp" in details["tables"]


def test_alertmanager_telegram_uses_secret_files():
    config = (ROOT / "infra" / "observability" / "alertmanager.yml").read_text(encoding="utf-8")
    compose = (ROOT / "infra" / "deploy" / "docker-compose.prod.yml").read_text(encoding="utf-8")
    env_example = (ROOT / "infra" / "deploy" / "compose.env.example").read_text(encoding="utf-8")

    assert "bot_token_file: /etc/alertmanager/secrets/telegram_bot_token" in config
    assert "chat_id: __TELEGRAM_CHAT_ID__" in config
    assert "${TELEGRAM_BOT_TOKEN}" not in config
    assert "${TELEGRAM_CHAT_ID}" not in config
    assert "__TELEGRAM_CHAT_ID__" in compose
    assert "./secrets/alertmanager:/etc/alertmanager/secrets:ro" in compose
    assert "TELEGRAM_CHAT_ID:" in compose
    assert "TELEGRAM_CHAT_ID=" in env_example
