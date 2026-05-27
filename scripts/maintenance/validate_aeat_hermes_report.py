#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "docs" / "aeat" / "hermes-curation-output.schema.json"
SCHEMA_VERSION = "aeat-hermes-curation-output/v1"
DECISIONS = {
    "ASSERTABLE",
    "UNKNOWN",
    "CONFLICT",
    "INSUFFICIENT_EVIDENCE",
    "STALE_SUSPECTED",
}
ASSERTION_CODES = {
    "ASSERTABLE_DIRECT_OFFICIAL",
    "NOT_ASSERTABLE_INFERRED_INTERNAL",
    "NOT_ASSERTABLE_CONFLICT",
    "INSUFFICIENT_EVIDENCE",
    "STALE_SUSPECTED",
}
OFFICIAL_AUTHORITIES = {"AEAT", "BOE", "EURLEX", "ESMA", "CNMV", "OTHER_OFFICIAL"}
OFFICIAL_NETLOCS = (
    "sede.agenciatributaria.gob.es",
    "www1.agenciatributaria.gob.es",
    "www2.agenciatributaria.gob.es",
    "www.agenciatributaria.es",
    "www.boe.es",
    "eur-lex.europa.eu",
    "www.esma.europa.eu",
    "www.cnmv.es",
)
FORBIDDEN_OFFICIAL_EVIDENCE_TERMS = (
    "cache",
    "cacheado",
    "metadata",
    "mcp",
    "esdata",
    "modelo_recurso",
    "campana_activa",
    "campana_persistida",
)


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _error(path: str, message: str) -> str:
    return f"{path}: {message}"


def _validate_required_keys(
    payload: dict[str, object],
    path: str,
    required: set[str],
    allowed: set[str],
) -> list[str]:
    errors: list[str] = []
    missing = sorted(required - set(payload))
    extra = sorted(set(payload) - allowed)
    for key in missing:
        errors.append(_error(path, f"missing required key {key}"))
    for key in extra:
        errors.append(_error(path, f"unexpected key {key}"))
    return errors


def _validate_url(path: str, url: object) -> list[str]:
    if not _is_non_empty_string(url):
        return [_error(path, "url must be a non-empty string")]
    parsed = urlparse(str(url))
    if parsed.scheme != "https":
        return [_error(path, "url must use https")]
    if parsed.netloc.lower() not in OFFICIAL_NETLOCS:
        return [_error(path, f"url netloc is not whitelisted: {parsed.netloc}")]
    return []


def _is_transactional_aeat_form_url(url: object) -> bool:
    if not _is_non_empty_string(url):
        return False
    parsed = urlparse(str(url))
    return (
        parsed.netloc.lower() in {"www1.agenciatributaria.gob.es", "www2.agenciatributaria.gob.es"}
        and parsed.path.lower().startswith("/wlpl/ov16-")
    )


def validate_report(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    root_required = {
        "schema_version",
        "model_code",
        "decision",
        "assertion_gate",
        "mcp_observations",
        "official_sources",
        "official_source_claims",
        "derived_claims",
        "system_observed_claims",
        "rejected_claims",
        "human_review_required",
    }
    errors.extend(_validate_required_keys(payload, "$", root_required, root_required))
    if errors:
        return errors

    if payload["schema_version"] != SCHEMA_VERSION:
        errors.append(_error("$.schema_version", f"must be {SCHEMA_VERSION}"))
    if not _is_non_empty_string(payload["model_code"]):
        errors.append(_error("$.model_code", "must be a non-empty string"))
    if payload["decision"] not in DECISIONS:
        errors.append(_error("$.decision", "invalid decision"))
    if payload["human_review_required"] is not True:
        errors.append(_error("$.human_review_required", "must be true"))

    gate = payload["assertion_gate"]
    if not isinstance(gate, dict):
        errors.append(_error("$.assertion_gate", "must be an object"))
    else:
        gate_required = {
            "campana_safe_to_assert",
            "campana_afirmable",
            "campana_assertion_code",
        }
        errors.extend(
            _validate_required_keys(gate, "$.assertion_gate", gate_required, gate_required)
        )
        if gate.get("campana_assertion_code") not in ASSERTION_CODES:
            errors.append(_error("$.assertion_gate.campana_assertion_code", "invalid code"))
        if not isinstance(gate.get("campana_safe_to_assert"), bool):
            errors.append(
                _error("$.assertion_gate.campana_safe_to_assert", "must be boolean")
            )
        afirmable = gate.get("campana_afirmable")
        if afirmable is not None and not _is_non_empty_string(afirmable):
            errors.append(
                _error("$.assertion_gate.campana_afirmable", "must be string or null")
            )
        can_assert = (
            gate.get("campana_safe_to_assert") is True
            and afirmable is not None
            and gate.get("campana_assertion_code") == "ASSERTABLE_DIRECT_OFFICIAL"
        )
        if payload["decision"] == "ASSERTABLE" and not can_assert:
            errors.append(
                _error("$.decision", "ASSERTABLE requires the direct official assertion gate")
            )

    mcp_observations = payload["mcp_observations"]
    if not isinstance(mcp_observations, list):
        errors.append(_error("$.mcp_observations", "must be an array"))
        mcp_count = 0
    else:
        mcp_count = len(mcp_observations)
        obs_required = {"endpoint_or_tool", "field", "value", "purpose"}
        for index, item in enumerate(mcp_observations):
            path = f"$.mcp_observations[{index}]"
            if not isinstance(item, dict):
                errors.append(_error(path, "must be an object"))
                continue
            errors.extend(_validate_required_keys(item, path, obs_required, obs_required))
            if not _is_non_empty_string(item.get("endpoint_or_tool")):
                errors.append(_error(f"{path}.endpoint_or_tool", "must be non-empty"))
            if not _is_non_empty_string(item.get("field")):
                errors.append(_error(f"{path}.field", "must be non-empty"))
            if item.get("purpose") not in {"routing", "triage", "system_state", "hypothesis"}:
                errors.append(_error(f"{path}.purpose", "invalid purpose"))

    official_sources = payload["official_sources"]
    source_ids: set[str] = set()
    if not isinstance(official_sources, list):
        errors.append(_error("$.official_sources", "must be an array"))
    else:
        source_required = {"source_id", "authority", "url", "locator", "excerpt"}
        for index, source in enumerate(official_sources):
            path = f"$.official_sources[{index}]"
            if not isinstance(source, dict):
                errors.append(_error(path, "must be an object"))
                continue
            errors.extend(_validate_required_keys(source, path, source_required, source_required))
            source_id = source.get("source_id")
            if not _is_non_empty_string(source_id):
                errors.append(_error(f"{path}.source_id", "must be non-empty"))
            elif str(source_id) in source_ids:
                errors.append(_error(f"{path}.source_id", "duplicate source_id"))
            else:
                source_ids.add(str(source_id))
            if source.get("authority") not in OFFICIAL_AUTHORITIES:
                errors.append(_error(f"{path}.authority", "invalid authority"))
            errors.extend(_validate_url(f"{path}.url", source.get("url")))
            if _is_transactional_aeat_form_url(source.get("url")):
                errors.append(
                    _error(
                        f"{path}.url",
                        "transactional AEAT form URLs are not evidence sources",
                    )
                )
            if not _is_non_empty_string(source.get("locator")):
                errors.append(_error(f"{path}.locator", "must be non-empty"))
            if not _is_non_empty_string(source.get("excerpt")):
                errors.append(_error(f"{path}.excerpt", "must be non-empty"))
            else:
                excerpt_text = str(source.get("excerpt", "")).lower()
                forbidden = [
                    term
                    for term in FORBIDDEN_OFFICIAL_EVIDENCE_TERMS
                    if term in excerpt_text
                ]
                if forbidden:
                    errors.append(
                        _error(
                            f"{path}.excerpt",
                            "official source excerpt contains internal/system evidence terms: "
                            + ", ".join(sorted(set(forbidden))),
                        )
                    )

    official_claims = payload["official_source_claims"]
    if not isinstance(official_claims, list):
        errors.append(_error("$.official_source_claims", "must be an array"))
    else:
        claim_required = {"claim", "source_id", "evidence_kind", "proves_campaign"}
        for index, claim in enumerate(official_claims):
            path = f"$.official_source_claims[{index}]"
            if not isinstance(claim, dict):
                errors.append(_error(path, "must be an object"))
                continue
            errors.extend(_validate_required_keys(claim, path, claim_required, claim_required))
            if claim.get("source_id") not in source_ids:
                errors.append(_error(f"{path}.source_id", "must reference official_sources"))
            if claim.get("evidence_kind") not in {"literal_text", "structural_table_entry"}:
                errors.append(_error(f"{path}.evidence_kind", "invalid evidence kind"))
            if not isinstance(claim.get("proves_campaign"), bool):
                errors.append(_error(f"{path}.proves_campaign", "must be boolean"))
            text = " ".join(
                str(claim.get(part, "")) for part in ("claim", "source_id", "evidence_kind")
            ).lower()
            forbidden = [term for term in FORBIDDEN_OFFICIAL_EVIDENCE_TERMS if term in text]
            if forbidden:
                errors.append(
                    _error(
                        path,
                        "official claim contains internal/system evidence terms: "
                        + ", ".join(sorted(set(forbidden))),
                    )
                )

    derived_claims = payload["derived_claims"]
    if not isinstance(derived_claims, list):
        errors.append(_error("$.derived_claims", "must be an array"))
    else:
        derived_required = {"claim", "input_claim_ids", "confidence", "may_assert_campaign"}
        for index, claim in enumerate(derived_claims):
            path = f"$.derived_claims[{index}]"
            if not isinstance(claim, dict):
                errors.append(_error(path, "must be an object"))
                continue
            errors.extend(_validate_required_keys(claim, path, derived_required, derived_required))
            if claim.get("may_assert_campaign") is not False:
                errors.append(_error(f"{path}.may_assert_campaign", "must be false"))
            if claim.get("confidence") not in {"low", "medium", "high"}:
                errors.append(_error(f"{path}.confidence", "invalid confidence"))
            if not isinstance(claim.get("input_claim_ids"), list):
                errors.append(_error(f"{path}.input_claim_ids", "must be an array"))

    system_claims = payload["system_observed_claims"]
    if not isinstance(system_claims, list):
        errors.append(_error("$.system_observed_claims", "must be an array"))
    else:
        system_required = {"claim", "mcp_observation_indexes", "may_assert_campaign"}
        for index, claim in enumerate(system_claims):
            path = f"$.system_observed_claims[{index}]"
            if not isinstance(claim, dict):
                errors.append(_error(path, "must be an object"))
                continue
            errors.extend(_validate_required_keys(claim, path, system_required, system_required))
            if claim.get("may_assert_campaign") is not False:
                errors.append(_error(f"{path}.may_assert_campaign", "must be false"))
            indexes = claim.get("mcp_observation_indexes")
            if not isinstance(indexes, list):
                errors.append(_error(f"{path}.mcp_observation_indexes", "must be an array"))
                continue
            for obs_index in indexes:
                if not isinstance(obs_index, int) or obs_index < 0 or obs_index >= mcp_count:
                    errors.append(
                        _error(
                            f"{path}.mcp_observation_indexes",
                            f"invalid MCP observation index {obs_index}",
                        )
                    )

    rejected_claims = payload["rejected_claims"]
    if not isinstance(rejected_claims, list):
        errors.append(_error("$.rejected_claims", "must be an array"))
    else:
        rejected_required = {"claim", "reason", "blocked_by"}
        allowed_blockers = {
            "no_direct_official_evidence",
            "mcp_only",
            "technical_resource_only",
            "contradictory_evidence",
            "insufficient_locator",
        }
        for index, claim in enumerate(rejected_claims):
            path = f"$.rejected_claims[{index}]"
            if not isinstance(claim, dict):
                errors.append(_error(path, "must be an object"))
                continue
            errors.extend(_validate_required_keys(claim, path, rejected_required, rejected_required))
            if not _is_non_empty_string(claim.get("claim")):
                errors.append(_error(f"{path}.claim", "must be non-empty"))
            if not _is_non_empty_string(claim.get("reason")):
                errors.append(_error(f"{path}.reason", "must be non-empty"))
            if claim.get("blocked_by") not in allowed_blockers:
                errors.append(_error(f"{path}.blocked_by", "invalid blocker"))

    return errors


def load_report(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("report root must be a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate strict AEAT Hermes curation JSON output"
    )
    parser.add_argument("report", type=Path)
    parser.add_argument(
        "--print-schema-path",
        action="store_true",
        help="Print the canonical JSON schema path before validating.",
    )
    args = parser.parse_args()

    if args.print_schema_path:
        print(SCHEMA_PATH)
    try:
        payload = load_report(args.report)
    except Exception as exc:
        print(f"invalid JSON report: {exc}")
        return 1

    errors = validate_report(payload)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("aeat hermes curation report verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
