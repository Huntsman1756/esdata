from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "maintenance" / "validate_aeat_hermes_report.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_aeat_hermes_report", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _valid_report() -> dict:
    return {
        "schema_version": "aeat-hermes-curation-output/v1",
        "model_code": "210",
        "decision": "CONFLICT",
        "assertion_gate": {
            "campana_safe_to_assert": False,
            "campana_afirmable": None,
            "campana_assertion_code": "NOT_ASSERTABLE_CONFLICT",
        },
        "mcp_observations": [
            {
                "endpoint_or_tool": "get_modelo_resumen_operativo",
                "field": "campana_resolution_status",
                "value": "conflict",
                "purpose": "system_state",
            }
        ],
        "official_sources": [
            {
                "source_id": "AEAT_GF00",
                "authority": "AEAT",
                "url": "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GF00.shtml",
                "locator": "Gestiones destacadas",
                "excerpt": "Modelo 210. Devengos 2019 y siguientes. Presentacion",
            },
            {
                "source_id": "AEAT_DR_200_299_210",
                "authority": "AEAT",
                "url": "https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro/modelos-200-299.html",
                "locator": "Tabla modelos 200 al 299, fila 210",
                "excerpt": "210 - Devengos a partir del 01-01-2026",
            },
        ],
        "official_source_claims": [
            {
                "claim": "La pagina AEAT del modelo 210 contiene una gestion para devengos 2019 y siguientes.",
                "source_id": "AEAT_GF00",
                "evidence_kind": "literal_text",
                "proves_campaign": False,
            },
            {
                "claim": "La tabla oficial de disenos incluye una entrada 210 para devengos a partir del 01-01-2026.",
                "source_id": "AEAT_DR_200_299_210",
                "evidence_kind": "structural_table_entry",
                "proves_campaign": False,
            },
        ],
        "derived_claims": [
            {
                "claim": "Las fuentes oficiales muestran rangos tecnicos/documentales distintos, pero no prueban campana activa.",
                "input_claim_ids": ["AEAT_GF00", "AEAT_DR_200_299_210"],
                "confidence": "medium",
                "may_assert_campaign": False,
            }
        ],
        "system_observed_claims": [
            {
                "claim": "ESData marca el modelo como conflictivo.",
                "mcp_observation_indexes": [0],
                "may_assert_campaign": False,
            }
        ],
        "rejected_claims": [
            {
                "claim": "La campana 2026 esta activa.",
                "reason": "El diseno tecnico no prueba campana activa.",
                "blocked_by": "technical_resource_only",
            }
        ],
        "human_review_required": True,
    }


def test_valid_report_passes_contract():
    module = _load_module()

    assert module.validate_report(_valid_report()) == []


def test_official_claim_must_reference_official_source():
    module = _load_module()
    report = _valid_report()
    report["official_source_claims"][0]["source_id"] = "MCP_OBS_1"

    errors = module.validate_report(report)

    assert any("must reference official_sources" in error for error in errors)


def test_official_source_url_must_be_whitelisted():
    module = _load_module()
    report = _valid_report()
    report["official_sources"][0]["url"] = "https://example.com/modelo-210"

    errors = module.validate_report(report)

    assert any("url netloc is not whitelisted" in error for error in errors)


def test_official_claim_rejects_mcp_or_metadata_terms():
    module = _load_module()
    report = _valid_report()
    report["official_source_claims"][0][
        "claim"
    ] = "MCP dice que modelo_recurso cacheado prueba campana activa."

    errors = module.validate_report(report)

    assert any("official claim contains internal/system evidence terms" in error for error in errors)


def test_official_source_excerpt_rejects_internal_terms():
    module = _load_module()
    report = _valid_report()
    report["official_sources"][0]["excerpt"] = (
        "Recurso oficial activo cacheado en modelo_recurso; campana asociada: 2019"
    )

    errors = module.validate_report(report)

    assert any(
        "official source excerpt contains internal/system evidence terms" in error
        for error in errors
    )


def test_assertable_decision_requires_direct_official_gate():
    module = _load_module()
    report = _valid_report()
    report["decision"] = "ASSERTABLE"

    errors = module.validate_report(report)

    assert any("ASSERTABLE requires the direct official assertion gate" in error for error in errors)


def test_derived_and_system_claims_cannot_assert_campaign():
    module = _load_module()
    report = _valid_report()
    report["derived_claims"][0]["may_assert_campaign"] = True
    report["system_observed_claims"][0]["may_assert_campaign"] = True

    errors = module.validate_report(report)

    assert any("$.derived_claims[0].may_assert_campaign" in error for error in errors)
    assert any("$.system_observed_claims[0].may_assert_campaign" in error for error in errors)


def test_system_claim_must_reference_existing_mcp_observation():
    module = _load_module()
    report = _valid_report()
    report["system_observed_claims"][0]["mcp_observation_indexes"] = [2]

    errors = module.validate_report(report)

    assert any("invalid MCP observation index 2" in error for error in errors)


def test_schema_file_documents_closed_contract():
    schema = (ROOT / "docs" / "aeat" / "hermes-curation-output.schema.json").read_text(
        encoding="utf-8"
    )

    assert '"additionalProperties": false' in schema
    assert '"official_source_claims"' in schema
    assert '"system_observed_claims"' in schema
    assert '"derived_claims"' in schema


def test_mutating_valid_fixture_does_not_share_nested_state():
    first = _valid_report()
    second = copy.deepcopy(first)
    second["assertion_gate"]["campana_assertion_code"] = "ASSERTABLE_DIRECT_OFFICIAL"

    assert first["assertion_gate"]["campana_assertion_code"] == "NOT_ASSERTABLE_CONFLICT"
