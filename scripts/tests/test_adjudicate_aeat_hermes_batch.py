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


def test_unreferenced_source_failure_does_not_block_claim_adjudication(tmp_path):
    module = _load_module()
    report = _valid_conflict_report()
    report["official_sources"].append(
        {
            "source_id": "AEAT_FORM_UNUSED",
            "authority": "AEAT",
            "url": "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G614.shtml",
            "locator": "Formulario dinamico",
            "excerpt": "Formulario Html del modelo 113",
        }
    )
    path = _write_report(tmp_path, report)

    result = module.adjudicate_report(
        path,
        verify_sources=True,
        fetcher=lambda url: (
            "Modelo 210. Devengos a partir del 01-01-2026."
            if "modelos-200-299" in url
            else "dynamic form without expected excerpt"
        ),
    )

    assert result["machine_decision"] == "auto_accept_conflict_evidence"
    assert result["source_checks"][1]["referenced_by_claim"] is False
    assert result["source_checks"][1]["errors"] == ["excerpt_not_found_in_source"]
    assert result["automatic_rejection_reasons"] == []


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


def test_binary_official_source_requires_reachability_not_literal_excerpt(tmp_path):
    module = _load_module()
    report = _valid_conflict_report()
    report["official_sources"][0]["url"] = (
        "https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/"
        "DR_200_299/archivos_26/dr210_2026.xlsx"
    )
    path = _write_report(tmp_path, report)

    result = module.adjudicate_report(
        path,
        verify_sources=True,
        fetcher=lambda _url: "binary bytes decoded without the literal excerpt",
    )

    assert result["machine_decision"] == "auto_accept_conflict_evidence"
    assert result["source_checks"][0]["binary_source"] is True
    assert result["source_checks"][0]["excerpt_verified"] is None
    assert result["automatic_rejection_reasons"] == []


def test_html_source_excerpt_can_be_repaired_from_official_text(tmp_path):
    module = _load_module()
    report = _valid_conflict_report()
    report["official_sources"][0]["excerpt"] = "Ficha AEAT del modelo 210"
    path = _write_report(tmp_path, report)

    result = module.adjudicate_report(
        path,
        verify_sources=True,
        fetcher=lambda _url: "<h1>Modelo 210. Impuesto sobre la Renta de no Residentes</h1>",
    )

    assert result["machine_decision"] == "auto_accept_conflict_evidence"
    assert result["source_checks"][0]["excerpt_verified"] is True
    assert result["source_checks"][0]["suggested_excerpt"] == (
        "Modelo 210. Impuesto sobre la Renta de no Residentes"
    )
    assert result["automatic_rejection_reasons"] == []


def test_latest_per_model_selects_newest_report_name(tmp_path):
    module = _load_module()
    paths = [
        tmp_path / "modelo-210-20260527-071917.json",
        tmp_path / "modelo-128-20260527-072022.json",
        tmp_path / "modelo-210-20260527-152228.json",
    ]
    for path in paths:
        path.write_text("{}", encoding="utf-8")

    selected = module._latest_per_model(paths)

    assert [path.name for path in selected] == [
        "modelo-128-20260527-072022.json",
        "modelo-210-20260527-152228.json",
    ]


def test_summarize_results_reports_operational_metrics():
    module = _load_module()
    results = [
        {
            "decision": "CONFLICT",
            "machine_decision": "auto_accept_conflict_evidence",
            "repository_bucket": "draft/conflict",
            "recommended_state": "conflict",
            "automatic_rejection_reasons": [],
            "source_checks": [
                {
                    "suggested_excerpt": "Modelo 210",
                    "errors": [],
                    "referenced_by_claim": True,
                },
                {
                    "suggested_excerpt": None,
                    "errors": ["excerpt_not_found_in_source"],
                    "referenced_by_claim": False,
                },
            ],
        },
        {
            "decision": "ASSERTABLE",
            "machine_decision": "human_review_assertable_candidate",
            "repository_bucket": "review/assertable_candidate",
            "recommended_state": "resolved_strong",
            "automatic_rejection_reasons": [],
            "source_checks": [],
        },
        {
            "decision": "UNKNOWN",
            "machine_decision": "needs_report_rewrite",
            "repository_bucket": "rewrite/traceability",
            "recommended_state": "insufficient_evidence",
            "automatic_rejection_reasons": ["A:error"],
            "source_checks": [],
        },
    ]

    metrics = module.summarize_results(results)

    assert metrics["reports_total"] == 3
    assert metrics["auto_accepted_total"] == 1
    assert metrics["human_review_required_total"] == 1
    assert metrics["rewrite_or_reject_total"] == 1
    assert metrics["assertable_candidates_total"] == 1
    assert metrics["repaired_excerpts_total"] == 1
    assert metrics["unused_source_warnings_total"] == 1
    assert metrics["blocking_errors_total"] == 1
    assert metrics["ratios"]["repaired_excerpt_ratio"] == 0.333333
    assert metrics["ratios"]["rewrite_ratio"] == 0.333333
    assert metrics["ratios"]["assertable_candidate_ratio"] == 0.333333
    assert metrics["ratios"]["unused_source_warning_ratio"] == 0.333333
    assert metrics["ratios"]["blocking_error_ratio"] == 0.333333
    assert metrics["drilldown"]["top_models_by_repaired_excerpts"] == [
        {"model_code": "None", "count": 1}
    ]
    assert metrics["drilldown"]["top_models_by_rewrite"] == [
        {"model_code": "None", "count": 1}
    ]


def test_build_run_output_includes_reproducibility_metadata(tmp_path):
    module = _load_module()
    history_path = tmp_path / "history" / "20260527T120000Z.json"
    output = module.build_run_output(
        results=[],
        report_paths=[tmp_path / "modelo-210.json"],
        verify_sources=True,
        latest_per_model=True,
        generated_at="2026-05-27T12:00:00+00:00",
        history_path=history_path,
    )

    metadata = output["run_metadata"]
    assert metadata["generated_at"] == "2026-05-27T12:00:00+00:00"
    assert metadata["adjudicator_version"] == "aeat-hermes-batch-adjudicator/v1"
    assert metadata["verify_sources"] is True
    assert metadata["latest_per_model"] is True
    assert metadata["history_path"] == str(history_path)
    assert metadata["reports_input_count"] == 1
    assert metadata["schema_version"] == "aeat-hermes-curation-output/v1"
    assert metadata["schema_sha256"]
    assert metadata["prompt_sha256"]
    assert metadata["adjudicator_sha256"]
    assert output["metrics"]["reports_total"] == 0
