from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

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


def _load_deep_contract_audit():
    path = ROOT / "scripts" / "maintenance" / "mcp_deep_contract_audit.py"
    spec = importlib.util.spec_from_file_location("mcp_deep_contract_audit_under_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
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
    monkeypatch.setattr(hermes, "_dlq_query_via_docker_compose", lambda: [])

    assert hermes.check_dead_letter_queue() == []


def test_hermes_monitor_dlq_docker_fallback_parses_json(monkeypatch):
    hermes = _load_hermes(monkeypatch)

    def fake_run(command, **kwargs):
        assert command[:2] == ["docker", "compose"]
        assert "exec" in command
        assert "psql" in command
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["env"]["DOCKER_CONFIG"] == "/tmp/esdata-hermes-monitor-docker"
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='[{"id": 1, "worker_name": "worker-boe", "entity_id": "BOE-A-1", "entity_type": "norma", "retry_count": 3, "max_retries": 3}]\n',
            stderr="",
        )

    monkeypatch.setattr(hermes.subprocess, "run", fake_run)

    entries = hermes._dlq_query_via_docker_compose()

    assert entries == [
        {
            "id": 1,
            "worker_name": "worker-boe",
            "entity_id": "BOE-A-1",
            "entity_type": "norma",
            "retry_count": 3,
            "max_retries": 3,
        }
    ]


def test_hermes_monitor_dlq_docker_fallback_failure_is_nonfatal(monkeypatch):
    hermes = _load_hermes(monkeypatch)

    def fake_run(command, **kwargs):
        assert kwargs["env"]["DOCKER_CONFIG"] == "/custom/docker-config"
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="compose failed")

    monkeypatch.setenv("DOCKER_CONFIG", "/custom/docker-config")
    monkeypatch.setattr(hermes.subprocess, "run", fake_run)

    assert hermes._dlq_query_via_docker_compose() == []


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


def test_worker_image_uses_canonical_hermes_monitor_script():
    dockerfile = (ROOT / "apps" / "workers" / "Dockerfile.worker").read_text(encoding="utf-8")

    assert "COPY scripts/hermes_monitor.py /app/hermes_monitor.py" in dockerfile
    assert not (ROOT / "apps" / "workers" / "hermes_monitor.py").exists()


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


def test_mcp_validation_suite_requires_cnmv_expanded_families_loaded():
    suite = _load_validation_suite()

    ok, details = suite._validate_cnmv_coverage_contract(
        {
            "total_cnmv_loaded": 5,
            "current_loaded": 4,
            "derogado_loaded": 1,
            "coverage_note": "CNMV devuelve corpus cargado; no cargado no equivale a inexistente.",
            "source_families": [
                {
                    "family_id": "circulares",
                    "coverage_status": "partial_loaded",
                    "loaded_count": 3,
                },
                {
                    "family_id": "guias_tecnicas",
                    "coverage_status": "partial_loaded",
                    "loaded_count": 1,
                },
                {
                    "family_id": "documentos_consulta_cnmv",
                    "coverage_status": "partial_loaded",
                    "loaded_count": 1,
                },
            ],
        }
    )

    assert ok is True
    assert details["family_count"] == 3


def test_mcp_validation_suite_excludes_cnmv_sanctions_from_subject_gate():
    source = (ROOT / "scripts" / "maintenance" / "mcp_validation_suite.py").read_text(encoding="utf-8")

    assert "cnmv_rows_missing_sujeto_obligado" in source
    assert "tipo_documento <> 'sancion_cnmv'" in source


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
                        {"table": "wallet_custodian", "safe_to_answer": False},
                    ],
                },
            },
        }
    )

    assert ok is True
    assert details["blocked"] is True
    assert "wallet_custodian" in details["tables"]


def test_mcp_validation_suite_accepts_modelo_289_fail_closed_obligation_context():
    suite = _load_validation_suite()

    ok, details = suite._validate_modelo_289_obligation_context(
        {
            "codigo": "289",
            "form_completeness": "parcial",
            "obligation_context": [
                {
                    "perfil_codigo": "sociedad_valores",
                    "verified": False,
                    "safe_to_answer": False,
                    "review_required": True,
                    "source_hash": None,
                    "capture_date": "2026-05-17",
                    "obligation_evidence_notice": (
                        "evidence_limited: falta hash o fecha de captura de la fuente"
                    ),
                }
            ],
        }
    )

    assert ok is True
    assert details["accepted_state"] == "fail_closed"


def test_mcp_validation_suite_rejects_modelo_289_unsafe_context_without_hash():
    suite = _load_validation_suite()

    ok, details = suite._validate_modelo_289_obligation_context(
        {
            "codigo": "289",
            "form_completeness": "parcial",
            "obligation_context": [
                {
                    "perfil_codigo": "sociedad_valores",
                    "verified": True,
                    "safe_to_answer": True,
                    "review_required": False,
                    "source_hash": None,
                    "capture_date": "2026-05-17",
                    "obligation_evidence_notice": "Verificado contra LGT DA 22.ª ap. 1",
                }
            ],
        }
    )

    assert ok is False
    assert details["accepted_state"] == "invalid"


def test_mcp_validation_suite_accepts_not_assertable_campaign_state():
    suite = _load_validation_suite()

    ok, details = suite._validate_aeat_campaign_assertion_safe_state(
        {
            "codigo": "124",
            "campana_activa": "2013",
            "campana_afirmable": None,
            "campana_safe_to_assert": False,
            "campana_resolution_status": "conflict",
            "campana_assertion_code": "NOT_ASSERTABLE_CONFLICT",
            "fuentes_recomendadas": [
                {
                    "tipo": "modelo_recurso:diseno_registro",
                    "titulo": "Diseno de registro oficial",
                    "proves_campaign": False,
                    "campaign_evidence_role": "weak",
                }
            ],
        },
        "124",
        {"conflict"},
    )

    assert ok is True
    assert details["accepted_state"] == "not_assertable"


def test_mcp_validation_suite_rejects_assertable_campaign_without_direct_source():
    suite = _load_validation_suite()

    ok, details = suite._validate_aeat_campaign_assertion_safe_state(
        {
            "codigo": "190",
            "campana_activa": "2025",
            "campana_afirmable": "2025",
            "campana_safe_to_assert": True,
            "campana_resolution_status": "resolved_strong",
            "campana_assertion_code": "ASSERTABLE_DIRECT_OFFICIAL",
            "fuentes_recomendadas": [
                {
                    "tipo": "modelo_recurso:formulario_html",
                    "titulo": "Plazos de presentacion",
                    "proves_campaign": False,
                    "campaign_evidence_role": "weak",
                }
            ],
        },
        "190",
        {"resolved_weak"},
    )

    assert ok is False
    assert details["accepted_state"] == "invalid"


def test_mcp_validation_suite_accepts_modelo_190_direct_instruction_campaign():
    suite = _load_validation_suite()

    ok, details = suite._validate_modelo_190_direct_instruction_campaign(
        {
            "codigo": "190",
            "campana_activa": "2025",
            "campana_afirmable": "2025",
            "campana_safe_to_assert": True,
            "campana_resolution_status": "resolved_strong",
            "campana_assertion_code": "ASSERTABLE_DIRECT_OFFICIAL",
            "fuentes_recomendadas": [
                {
                    "tipo": "modelo_recurso:instrucciones",
                    "titulo": "Modelo 190. Ejercicio 2025. Gestiones activas en AEAT Sede.",
                    "url": (
                        "https://sede.agenciatributaria.gob.es/Sede/irpf/"
                        "retenciones-ingresos-cuenta-pagos-fraccionados/"
                        "retenciones-ingresos-cuenta/modelo-190.html"
                    ),
                    "proves_campaign": True,
                    "campaign_evidence_role": "direct_official",
                }
            ],
        }
    )

    assert ok is True
    assert details["direct_instruction_sources"][0]["titulo"].startswith("Modelo 190")


def test_deep_contract_audit_accepts_verified_or_fail_closed_obligation_items():
    audit = _load_deep_contract_audit()

    assert audit._obligation_item_verified_or_fail_closed(
        {
            "verified": False,
            "safe_to_answer": False,
            "review_required": True,
            "source_hash": None,
            "capture_date": "2026-05-17",
            "evidence_notice": "evidence_limited: falta hash o fecha de captura de la fuente",
        }
    )
    assert not audit._obligation_item_verified_or_fail_closed(
        {
            "verified": True,
            "safe_to_answer": True,
            "review_required": False,
            "source_hash": None,
            "capture_date": "2026-05-17",
            "evidence_notice": "Verificado contra LGT DA 22.ª ap. 1",
        }
    )


def test_deep_contract_audit_accepts_rts_fail_closed_obligation_items():
    audit = _load_deep_contract_audit()

    assert audit._obligation_item_verified_or_fail_closed(
        {
            "descripcion": "Publicacion post-negociacion de operaciones (RTS 1)",
            "norma_codigo": "32017R0587",
            "verified": False,
            "safe_to_answer": False,
            "review_required": True,
            "source_url": "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0587",
            "source_hash": None,
            "capture_date": "2026-05-18",
            "evidence_notice": "evidence_limited: falta hash o fecha de captura de la fuente",
            "completeness": "parcial",
        }
    )


def test_deep_contract_audit_accepts_mica_fail_closed_obligation_items():
    audit = _load_deep_contract_audit()

    assert audit._obligation_item_verified_or_fail_closed(
        {
            "descripcion": "Autorizacion como CASP ante la CNMV",
            "norma_codigo": "32023R1114",
            "articulo_referencia": "art. 59",
            "verified": False,
            "safe_to_answer": False,
            "review_required": True,
            "source_url": "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32023R1114",
            "source_hash": None,
            "capture_date": "2026-05-19",
            "evidence_notice": "evidence_limited: falta hash o fecha de captura de la fuente",
            "completeness": "parcial",
        }
    )


def test_deep_contract_audit_accepts_modelo_303_fail_closed_obligation_items():
    audit = _load_deep_contract_audit()

    assert audit._obligation_item_verified_or_fail_closed(
        {
            "descripcion": "Modelo 303 - IVA autoliquidacion",
            "modelo_aeat": "303",
            "norma_codigo": "LIVA",
            "articulo_referencia": "art. 164",
            "verified": False,
            "safe_to_answer": False,
            "review_required": True,
            "source_url": "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G414.shtml",
            "source_hash": None,
            "capture_date": "2026-05-17",
            "evidence_notice": "evidence_limited: falta hash o fecha de captura de la fuente",
            "completeness": "parcial",
        }
    )


def test_mcp_validation_suite_uses_sociedad_valores_fail_closed_threshold():
    source = (ROOT / "scripts" / "maintenance" / "mcp_validation_suite.py").read_text(encoding="utf-8")

    assert "sociedad_valores_verified_or_fail_closed_ge_24" in source
    assert "sociedad_valores_verified_ge_24" not in source
    assert "fail-closed until source_hash and capture_date are loaded" in source


def test_mcp_validation_suite_uses_global_fail_closed_profile_threshold():
    source = (ROOT / "scripts" / "maintenance" / "mcp_validation_suite.py").read_text(encoding="utf-8")

    assert "all_profiles_pct_verified_or_fail_closed_ge_70" in source
    assert "all_profiles_pct_verified_ge_70" not in source
    assert "safe_to_answer IS NOT true" in source
    assert "fail-closed until source_hash and capture_date are loaded" in source


def test_mcp_validation_suite_accepts_modelo_202_fail_closed_routing():
    suite = _load_validation_suite()

    ok, details = suite._validate_sociedad_valores_fiscal_routing(
        {
            "perfil": {"codigo": "sociedad_valores"},
            "obligaciones": [
                {
                    "modelo_aeat": "202",
                    "verified": False,
                    "safe_to_answer": False,
                    "review_required": True,
                    "source_url": "https://sede.agenciatributaria.gob.es/Sede/impuesto-sobre-sociedades/modelo-202.html",
                    "source_hash": None,
                    "capture_date": "2026-05-17",
                    "evidence_notice": "evidence_limited: falta hash o fecha de captura de la fuente",
                }
            ],
        }
    )

    assert ok is True
    assert details["modelo_202_accepted_states"] == ["fail_closed"]


def test_mcp_validation_suite_rejects_modelo_202_verified_without_hash():
    suite = _load_validation_suite()

    ok, details = suite._validate_sociedad_valores_fiscal_routing(
        {
            "perfil": {"codigo": "sociedad_valores"},
            "obligaciones": [
                {
                    "modelo_aeat": "202",
                    "verified": True,
                    "safe_to_answer": True,
                    "review_required": False,
                    "source_url": "https://sede.agenciatributaria.gob.es/Sede/impuesto-sobre-sociedades/modelo-202.html",
                    "source_hash": None,
                    "capture_date": "2026-05-17",
                    "evidence_notice": "Verificado contra LIS art. 40",
                }
            ],
        }
    )

    assert ok is False
    assert details["modelo_202_accepted_states"] == ["invalid"]


def test_mcp_validation_suite_tracks_aeat_priority_partial_model_evidence():
    source = (ROOT / "scripts" / "maintenance" / "mcp_validation_suite.py").read_text(encoding="utf-8")

    assert "aeat_modelo_303_iva_traceable_partial_contract" in source
    assert "aeat_modelo_303_direct_instruction_asserts_campaign" in source
    assert "aeat_modelo_202_is_payment_traceable_partial_contract" in source
    assert "aeat_modelo_190_withholding_traceable_partial_contract" in source
    assert "aeat_modelo_190_internal_keys_rules_traceable_contract" in source
    assert "aeat_modelo_190_perception_keys_a_l_traceable_contract" in source
    assert "modelo_clave_hierarchy_schema_contract" in source
    assert "aeat_modelo_190_subclaves_77_hierarchical_contract" in source
    assert "aeat_modelo_190_direct_instruction_asserts_campaign" in source
    assert "aeat_modelo_123_design_traceable_partial_contract" in source
    assert "aeat_modelo_124_design_traceable_partial_contract" in source
    assert "aeat_modelo_289_legal_campaign_traceable_contract" in source
    assert "aeat_modelo_289_documental_traceable_fail_closed_contract" in source
    assert "aeat_modelo_123_campaign_not_overclaimed_contract" in source
    assert "aeat_modelo_124_campaign_not_overclaimed_contract" in source
    assert "aeat_modelo_289_campaign_not_overclaimed_contract" in source
    assert "aeat_priority_target_models_have_traceable_partial_evidence_7" in source
    assert "BOE-A-2024-27528" in source
    assert "COUNT(*) = 12" in source
    assert "COUNT(*) = 77" in source
    assert "SUBCLAVE_PERCEPCION" in source
    assert "ux_modelo_clave_subclave" in source
    assert "row_provenance='official_exact'" in source
    assert "sha256_contenido IS NOT NULL" in source


def test_mcp_validation_suite_checks_real_mcp_transport_tools_list(monkeypatch):
    suite = _load_validation_suite()

    class FakeResponse:
        def __init__(self, status_code=200, *, headers=None, payload=None, text=""):
            self.status_code = status_code
            self.headers = headers or {}
            self._payload = payload or {}
            self.text = text

        def json(self):
            return self._payload

    class FakeClient:
        def request(self, method, path, **kwargs):
            if method == "GET":
                return self.get(path, headers=kwargs.get("headers"))
            if method == "POST":
                return self.post(path, headers=kwargs.get("headers"), json=kwargs.get("json"))
            raise AssertionError(method)

        def get(self, path, headers=None):
            assert path == "/mcp"
            assert headers["Accept"] == "text/event-stream"
            assert headers["X-API-Key"] == "mcp-secret"
            return FakeResponse(headers={"mcp-session-id": "session-1"})

        def post(self, path, headers=None, json=None):
            assert path == "/mcp"
            assert headers["MCP-Session-ID"] == "session-1"
            assert headers["X-API-Key"] == "mcp-secret"
            if json["method"] == "initialize":
                return FakeResponse(payload={"result": {"serverInfo": {"name": "esdata"}}})
            if json["method"] == "tools/list":
                return FakeResponse(
                    payload={
                        "result": {
                            "tools": [
                                {"name": "consulta_fiscal"},
                                {"name": "list_modelos_por_supuesto"},
                                {"name": "list_domain_availability"},
                                {"name": "listar_perfiles_entidad"},
                                {"name": "obtener_obligaciones_perfil"},
                                {"name": "calendario_obligaciones_perfil"},
                                {"name": "buscar_norma_eu"},
                                {"name": "buscar_modelos_aeat_catalogo"},
                                {"name": "obtener_documentos_cnmv_perfil"},
                            ]
                        }
                    }
                )
            raise AssertionError(json)

    monkeypatch.setenv("MCP_API_KEY", "mcp-secret")

    check = suite._check_mcp_transport(FakeClient())

    assert check["ok"] is True
    assert check["missing_tools"] == []


def test_mcp_validation_suite_accepts_mcp_session_id_on_missing_session_handshake(monkeypatch):
    suite = _load_validation_suite()

    class FakeResponse:
        def __init__(self, status_code=200, *, headers=None, payload=None, text=""):
            self.status_code = status_code
            self.headers = headers or {}
            self._payload = payload or {}
            self.text = text

        def json(self):
            return self._payload

    class FakeClient:
        def request(self, method, path, **kwargs):
            if method == "GET":
                return self.get(path, headers=kwargs.get("headers"))
            if method == "POST":
                return self.post(path, headers=kwargs.get("headers"), json=kwargs.get("json"))
            raise AssertionError(method)

        def get(self, path, headers=None):
            return FakeResponse(
                status_code=400,
                headers={"Mcp-Session-Id": "session-1"},
                text='{"error":{"message":"Bad Request: Missing session ID"}}',
            )

        def post(self, path, headers=None, json=None):
            if json["method"] == "initialize":
                return FakeResponse(payload={"result": {"serverInfo": {"name": "esdata"}}})
            return FakeResponse(
                payload={
                    "result": {
                        "tools": [
                            {"name": "consulta_fiscal"},
                            {"name": "list_modelos_por_supuesto"},
                            {"name": "list_domain_availability"},
                            {"name": "listar_perfiles_entidad"},
                            {"name": "obtener_obligaciones_perfil"},
                            {"name": "calendario_obligaciones_perfil"},
                            {"name": "buscar_norma_eu"},
                            {"name": "buscar_modelos_aeat_catalogo"},
                            {"name": "obtener_documentos_cnmv_perfil"},
                        ]
                    }
                }
            )

    monkeypatch.setenv("MCP_API_KEY", "mcp-secret")

    check = suite._check_mcp_transport(FakeClient())

    assert check["handshake_status_code"] == 400
    assert check["ok"] is True


def test_maintenance_http_retry_respects_retry_after(monkeypatch):
    suite = _load_validation_suite()
    sleeps: list[float] = []

    class FakeResponse:
        def __init__(self, status_code, *, headers=None):
            self.status_code = status_code
            self.headers = headers or {}

    class FakeClient:
        def __init__(self):
            self.calls = 0

        def request(self, method, path, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return FakeResponse(429, headers={"Retry-After": "2"})
            return FakeResponse(200)

    monkeypatch.setattr(suite.time, "sleep", lambda seconds: sleeps.append(seconds))
    client = FakeClient()

    response = suite._request_with_retry(client, "GET", "/v1/domain-availability")

    assert response.status_code == 200
    assert client.calls == 2
    assert sleeps == [2.0]


def test_deep_contract_audit_detects_fk_orphans():
    audit = _load_deep_contract_audit()
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(text("CREATE TABLE parent (id INTEGER PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id))"))
        conn.execute(text("INSERT INTO child (id, parent_id) VALUES (1, 999)"))

    def fake_foreign_keys(engine):
        return [
            {
                "constraint_name": "fk_child_parent",
                "child_table": "child",
                "parent_table": "parent",
                "child_columns": ["parent_id"],
                "parent_columns": ["id"],
            }
        ]

    audit._foreign_keys = fake_foreign_keys

    result = audit.audit_foreign_keys(engine)

    assert result.ok is False
    assert result.details["relationships_checked"] == 1
    assert result.details["orphan_failures"][0]["orphan_count"] == 1


def test_dead_letter_cli_uses_boolean_filters_and_resolves_rows(capsys):
    path = ROOT / "scripts" / "maintenance" / "show_dead_letter_queue.py"
    spec = importlib.util.spec_from_file_location("show_dead_letter_queue_under_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE sync_dead_letter (
                    id INTEGER PRIMARY KEY,
                    worker_name TEXT,
                    entity_id TEXT,
                    entity_type TEXT,
                    error_message TEXT,
                    retry_count INTEGER,
                    max_retries INTEGER,
                    first_failed_at TEXT,
                    last_failed_at TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at TEXT,
                    resolved_by TEXT,
                    notes TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO sync_dead_letter (
                    id, worker_name, entity_id, entity_type, error_message,
                    retry_count, max_retries, first_failed_at, last_failed_at, resolved
                ) VALUES (
                    1, 'worker-dgt', 'session_init', 'session_init', '502 Bad Gateway',
                    1, 3, '2026-05-10T00:00:00Z', '2026-05-10T00:00:00Z', FALSE
                )
                """
            )
        )

    rows = module.show_dead_letters(engine)
    assert rows[0]["resolved"] in (False, 0)

    assert module.resolve_dead_letter(engine, 1, "transient upstream recovered") is True
    module.show_counts(engine, resolved=True)
    output = capsys.readouterr().out
    assert "worker-dgt" in output


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
    assert "receiver: default-noop" in compose
    assert "read_only: true" in compose
    assert "TELEGRAM_CHAT_ID=" in env_example
