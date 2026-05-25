from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_audit_module():
    path = ROOT / "scripts" / "maintenance" / "aeat_campaign_resolution_audit.py"
    spec = importlib.util.spec_from_file_location("aeat_campaign_resolution_audit_under_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_candidate_support_prefers_explicit_aeat_year():
    audit = _load_audit_module()

    level, evidence = audit._candidate_support(
        "2025",
        [
            {
                "tipo": "modelo_recurso:instrucciones",
                "organismo": "AEAT",
                "url": "https://sede.agenciatributaria.gob.es/modelo-100-instrucciones-2025.pdf",
                "titulo": "Instrucciones",
                "campana": "2025",
            }
        ],
    )

    assert level == "explicit_aeat_year"
    assert evidence[0]["years"] == ["2025"]


def test_candidate_support_separates_implicit_aeat_resource_from_explicit_year():
    audit = _load_audit_module()

    level, evidence = audit._candidate_support(
        "2025",
        [
            {
                "tipo": "modelo_recurso:ayuda_tecnica_presentacion",
                "organismo": "AEAT",
                "url": "https://sede.agenciatributaria.gob.es/Sede/modelo-290/web-service.html",
                "titulo": "Ayuda tecnica presentacion",
                "campana": "2025",
            }
        ],
    )

    assert level == "aeat_campaign_resource"
    assert evidence[0]["support"] == "aeat_campaign_resource"


def test_candidate_support_does_not_treat_boe_as_direct_aeat_evidence():
    audit = _load_audit_module()

    level, evidence = audit._candidate_support(
        "2025",
        [
            {
                "tipo": "modelo_recurso:instrucciones",
                "organismo": "BOE",
                "url": "https://www.boe.es/buscar/doc.php?id=BOE-A-2025-1",
                "titulo": "Normativa 2025",
                "campana": "2025",
            }
        ],
    )

    assert level == "heuristic_or_implicit"
    assert evidence == []


def test_summarize_support_counts_resolved_rows_only():
    audit = _load_audit_module()

    summary = audit._summarize_support(
        [
            {
                "campana_resolution_status": "resolved",
                "campana_support_level": "explicit_aeat_year",
            },
            {
                "campana_resolution_status": "resolved",
                "campana_support_level": "aeat_campaign_resource",
            },
            {
                "campana_resolution_status": "conflict",
                "campana_support_level": "none",
            },
        ]
    )

    assert summary["resolved_total"] == 2
    assert summary["resolved_support_counts"] == {
        "aeat_campaign_resource": 1,
        "explicit_aeat_year": 1,
    }
    assert summary["resolved_explicit_aeat_year_pct"] == 50.0
    assert summary["resolved_direct_or_implicit_aeat_resource_pct"] == 100.0
