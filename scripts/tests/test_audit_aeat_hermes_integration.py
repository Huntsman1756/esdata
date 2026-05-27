from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "maintenance" / "audit_aeat_hermes_integration.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_aeat_hermes_integration", MODULE_PATH)
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
                "source_id": "AEAT_DR_210",
                "authority": "AEAT",
                "url": "https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro/modelos-200-299.html",
                "locator": "Tabla modelos 200 al 299, fila 210",
                "excerpt": "210 - Devengos a partir del 01-01-2026",
            }
        ],
        "official_source_claims": [
            {
                "claim": "La tabla oficial de disenos incluye una entrada 210 para devengos a partir del 01-01-2026.",
                "source_id": "AEAT_DR_210",
                "evidence_kind": "structural_table_entry",
                "proves_campaign": False,
            }
        ],
        "derived_claims": [
            {
                "claim": "El recurso prueba cobertura tecnica, no campana activa.",
                "input_claim_ids": ["AEAT_DR_210"],
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


def _write_report(tmp_path: Path, report: dict) -> Path:
    path = tmp_path / f"modelo-{report.get('model_code', 'x')}.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_traceable_official_claim_is_integrable_as_human_review_evidence(tmp_path):
    module = _load_module()
    path = _write_report(tmp_path, _valid_report())

    result = module.audit_report(path)

    assert result["schema_valid"] is True
    assert result["integrable"] is True
    assert result["reason"] == "official_claims_traceable_human_review_required"
    assert result["official_claims_valid_count"] == 1
    assert result["claims_rejected_count"] == 1
    assert result["recommended_state"] == "conflict"


def test_no_official_claims_is_not_integrable(tmp_path):
    module = _load_module()
    report = _valid_report()
    report["official_sources"] = []
    report["official_source_claims"] = []
    path = _write_report(tmp_path, report)

    result = module.audit_report(path)

    assert result["schema_valid"] is True
    assert result["integrable"] is False
    assert result["reason"] == "no_official_source_claims"
    assert result["recommended_state"] == "insufficient_evidence"


def test_invalid_schema_is_not_integrable(tmp_path):
    module = _load_module()
    report = _valid_report()
    report["official_source_claims"][0]["source_id"] = "MISSING"
    path = _write_report(tmp_path, report)

    result = module.audit_report(path)

    assert result["schema_valid"] is False
    assert result["integrable"] is False
    assert result["reason"] == "schema_or_contract_invalid"
    assert result["official_claims_valid_count"] == 0


def test_assertable_requires_proving_official_claim_for_resolved_strong(tmp_path):
    module = _load_module()
    report = copy.deepcopy(_valid_report())
    report["decision"] = "ASSERTABLE"
    report["assertion_gate"] = {
        "campana_safe_to_assert": True,
        "campana_afirmable": "2026",
        "campana_assertion_code": "ASSERTABLE_DIRECT_OFFICIAL",
    }
    path = _write_report(tmp_path, report)

    result = module.audit_report(path)

    assert result["schema_valid"] is True
    assert result["integrable"] is True
    assert result["recommended_state"] == "insufficient_evidence"

    report["official_source_claims"][0]["proves_campaign"] = True
    path = _write_report(tmp_path, report)
    result = module.audit_report(path)

    assert result["recommended_state"] == "resolved_strong"
