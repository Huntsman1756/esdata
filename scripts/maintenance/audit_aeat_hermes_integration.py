#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "maintenance"))

from validate_aeat_hermes_report import load_report, validate_report  # noqa: E402

ASSERTABLE_CODE = "ASSERTABLE_DIRECT_OFFICIAL"


def _gate_allows_assertion(payload: dict[str, Any]) -> bool:
    gate = payload.get("assertion_gate")
    if not isinstance(gate, dict):
        return False
    return (
        gate.get("campana_safe_to_assert") is True
        and gate.get("campana_afirmable") is not None
        and gate.get("campana_assertion_code") == ASSERTABLE_CODE
    )


def _recommended_state(payload: dict[str, Any]) -> str:
    official_claims = payload.get("official_source_claims")
    if not isinstance(official_claims, list) or not official_claims:
        return "insufficient_evidence"

    decision = payload.get("decision")
    if decision == "ASSERTABLE" and _gate_allows_assertion(payload):
        proves_campaign = any(
            claim.get("proves_campaign") is True
            for claim in official_claims
            if isinstance(claim, dict)
        )
        return "resolved_strong" if proves_campaign else "insufficient_evidence"
    if decision == "CONFLICT":
        return "conflict"
    if decision == "STALE_SUSPECTED":
        return "stale_suspected"
    if decision == "INSUFFICIENT_EVIDENCE":
        return "insufficient_evidence"
    return "resolved_weak"


def audit_report(path: Path) -> dict[str, Any]:
    try:
        payload = load_report(path)
    except Exception as exc:
        return {
            "path": str(path),
            "model_code": None,
            "schema_valid": False,
            "integrable": False,
            "reason": f"invalid JSON report: {exc}",
            "validation_errors": [str(exc)],
            "official_claims_valid_count": 0,
            "official_claims_proving_campaign_count": 0,
            "claims_rejected_count": 0,
            "recommended_state": "insufficient_evidence",
        }

    validation_errors = validate_report(payload)
    official_claims = payload.get("official_source_claims", [])
    rejected_claims = payload.get("rejected_claims", [])
    official_claim_count = len(official_claims) if isinstance(official_claims, list) else 0
    proving_campaign_count = (
        sum(
            1
            for claim in official_claims
            if isinstance(claim, dict) and claim.get("proves_campaign") is True
        )
        if isinstance(official_claims, list)
        else 0
    )
    rejected_count = len(rejected_claims) if isinstance(rejected_claims, list) else 0
    source_count = (
        len(payload.get("official_sources", []))
        if isinstance(payload.get("official_sources"), list)
        else 0
    )
    gate = payload.get("assertion_gate") if isinstance(payload.get("assertion_gate"), dict) else {}

    schema_valid = not validation_errors
    if not schema_valid:
        reason = "schema_or_contract_invalid"
        integrable = False
    elif official_claim_count == 0:
        reason = "no_official_source_claims"
        integrable = False
    elif payload.get("decision") == "ASSERTABLE" and not _gate_allows_assertion(payload):
        reason = "assertable_without_direct_official_gate"
        integrable = False
    else:
        reason = "official_claims_traceable_human_review_required"
        integrable = True

    return {
        "path": str(path),
        "model_code": payload.get("model_code"),
        "schema_valid": schema_valid,
        "integrable": integrable,
        "reason": reason,
        "validation_errors": validation_errors,
        "decision": payload.get("decision"),
        "campana_safe_to_assert": gate.get("campana_safe_to_assert"),
        "campana_afirmable": gate.get("campana_afirmable"),
        "campana_assertion_code": gate.get("campana_assertion_code"),
        "official_sources_count": source_count,
        "official_claims_valid_count": official_claim_count if schema_valid else 0,
        "official_claims_proving_campaign_count": proving_campaign_count if schema_valid else 0,
        "claims_rejected_count": rejected_count,
        "human_review_required": payload.get("human_review_required"),
        "recommended_state": _recommended_state(payload) if schema_valid else "insufficient_evidence",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit whether validated AEAT Hermes JSON can be integrated as documentary evidence."
    )
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument(
        "--fail-on-not-integrable",
        action="store_true",
        help="Exit non-zero if any report is not integrable as evidence.",
    )
    args = parser.parse_args()

    results = [audit_report(path) for path in args.reports]
    print(json.dumps({"reports": results}, ensure_ascii=False, indent=2))
    if args.fail_on_not_integrable and any(not item["integrable"] for item in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
