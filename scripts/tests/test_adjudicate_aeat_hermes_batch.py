from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "maintenance" / "adjudicate_aeat_hermes_batch.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("adjudicate_aeat_hermes_batch", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _valid_conflict_report() -> dict:
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
                "excerpt": "Modelo 210. Devengos a partir del 01-01-2026.",
            }
        ],
        "official_source_claims": [
            {
                "claim": "La tabla oficial de disenos incluye Modelo 210 para devengos a partir del 01-01-2026.",
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


def test_verified_conflict_report_is_auto_accepted_as_nonassertive_evidence(tmp_path):
    module = _load_module()
    path = _write_report(tmp_path, _valid_conflict_report())

    result = module.adjudicate_report(
        path,
        verify_sources=True,
        fetcher=lambda _url: "<html>Modelo 210. Devengos a partir del 01-01-2026.</html>",
    )

    assert result["schema_valid"] is True
    assert result["integrable"] is True
    assert result["machine_decision"] == "auto_accept_conflict_evidence"
    assert result["repository_bucket"] == "draft/conflict"
    assert result["automatic_rejection_reasons"] == []
    assert result["source_checks"][0]["excerpt_verified"] is True


def test_unverified_sources_force_rewrite_not_manual_acceptance(tmp_path):
    module = _load_module()
    path = _write_report(tmp_path, _valid_conflict_report())

    result = module.adjudicate_report(path, verify_sources=False)

    assert result["machine_decision"] == "needs_report_rewrite"
    assert result["repository_bucket"] == "rewrite/traceability"
    assert result["source_verification_required"] is True
    assert "AEAT_DR_210:source_verification_not_run" in result["automatic_rejection_reasons"]


def test_vague_locator_blocks_auto_acceptance(tmp_path):
    module = _load_module()
    report = _valid_conflict_report()
    report["official_sources"][0]["locator"] = "AEAT page"
    path = _write_report(tmp_path, report)

    result = module.adjudicate_report(
        path,
        verify_sources=True,
        fetcher=lambda _url: "Modelo 210. Devengos a partir del 01-01-2026.",
    )

    assert result["schema_valid"] is True
    assert result["machine_decision"] == "needs_report_rewrite"
    assert "AEAT_DR_210:vague_locator" in result["automatic_rejection_reasons"]


def test_assertable_candidate_is_never_auto_promoted(tmp_path):
    module = _load_module()
    report = copy.deepcopy(_valid_conflict_report())
    report["decision"] = "ASSERTABLE"
    report["assertion_gate"] = {
        "campana_safe_to_assert": True,
        "campana_afirmable": "2026",
        "campana_assertion_code": "ASSERTABLE_DIRECT_OFFICIAL",
    }
    report["official_source_claims"][0]["proves_campaign"] = True
    path = _write_report(tmp_path, report)

    result = module.adjudicate_report(
        path,
        verify_sources=True,
        fetcher=lambda _url: "Modelo 210. Devengos a partir del 01-01-2026.",
    )

    assert result["schema_valid"] is True
    assert result["machine_decision"] == "human_review_assertable_candidate"
    assert result["repository_bucket"] == "review/assertable_candidate"
    assert result["recommended_state"] == "resolved_strong"
