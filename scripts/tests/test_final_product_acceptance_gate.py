from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "scripts" / "maintenance" / "final_product_acceptance_gate.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("final_product_acceptance_gate", GATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_affirmative_payload_without_source_fails():
    gate = _load_gate()
    check = gate.CanonicalCheck(
        name="boe_norm",
        domain="BOE",
        path="/v1/legislacion/LIVA",
        requires_source=True,
        requires_evidence_status=True,
    )
    payload = {"codigo": "LIVA", "titulo": "Ley del IVA", "verified": True}

    result = gate.evaluate_payload(check, payload)

    assert not result.ok
    assert "missing source" in result.reason


def test_empty_payload_with_explicit_fail_closed_status_passes():
    gate = _load_gate()
    check = gate.CanonicalCheck(
        name="empty_domain",
        domain="empty",
        path="/v1/domain-empty",
        allow_fail_closed_empty=True,
        requires_evidence_status=True,
    )
    payload = {
        "items": [],
        "total": 0,
        "safe_to_answer": False,
        "availability_status": "workflow_empty",
    }

    result = gate.evaluate_payload(check, payload)

    assert result.ok
    assert result.reason == "ok"


def test_empty_payload_without_fail_closed_status_fails():
    gate = _load_gate()
    check = gate.CanonicalCheck(
        name="empty_domain",
        domain="empty",
        path="/v1/domain-empty",
        allow_fail_closed_empty=True,
        requires_evidence_status=True,
    )
    payload = {"items": [], "total": 0}

    result = gate.evaluate_payload(check, payload)

    assert not result.ok
    assert "empty response without fail-closed status" in result.reason


def test_non_empty_secondary_collection_is_not_treated_as_empty():
    gate = _load_gate()
    check = gate.CanonicalCheck(
        name="partial_domain",
        domain="partial",
        path="/v1/partial",
        requires_source=True,
        requires_evidence_status=True,
    )
    payload = {
        "items": [],
        "documentos": [
            {
                "titulo": "Documento oficial",
                "url_fuente": "https://example.invalid/source",
                "coverage_status": "partial_loaded",
            }
        ],
    }

    result = gate.evaluate_payload(check, payload)

    assert result.ok
    assert result.reason == "ok"


def test_status_payload_with_stale_worker_fails():
    gate = _load_gate()
    payload = {
        "api": "ok",
        "database": "ok",
        "workers": {
            "worker-boe": {"status": "ok", "stale": False},
            "worker-cnmv": {"status": "ok", "stale": True},
        },
    }

    result = gate.evaluate_status_payload(payload)

    assert not result.ok
    assert "stale workers" in result.reason
