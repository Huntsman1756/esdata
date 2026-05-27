#!/usr/bin/env python
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "maintenance"))

from audit_aeat_hermes_integration import audit_report  # noqa: E402
from validate_aeat_hermes_report import (  # noqa: E402
    FORBIDDEN_OFFICIAL_EVIDENCE_TERMS,
    load_report,
)

ASSERTABLE_CODE = "ASSERTABLE_DIRECT_OFFICIAL"
VAGUE_LOCATORS = {
    "aeat",
    "aeat page",
    "boe",
    "boe page",
    "pagina aeat",
    "página aeat",
    "pagina boe",
    "página boe",
}
BINARY_SOURCE_SUFFIXES = (".pdf", ".xls", ".xlsx", ".zip")


def _normalize_text(value: str) -> str:
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.casefold().strip()


def _plain_text(value: str) -> str:
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", "\n", value)
    value = html.unescape(value)
    return re.sub(r"[ \t\r\f\v]+", " ", value)


def _suggest_excerpt(source_text: str, model_code: str) -> str | None:
    plain = _plain_text(source_text)
    candidates = [
        re.sub(r"\s+", " ", line).strip()
        for line in plain.splitlines()
        if line.strip()
    ]
    needles = [f"modelo {model_code}".casefold(), str(model_code).casefold()]
    for candidate in candidates:
        normalized = candidate.casefold()
        if any(needle in normalized for needle in needles) and 8 <= len(candidate) <= 260:
            return candidate
    compact = re.sub(r"\s+", " ", plain).strip()
    normalized_compact = compact.casefold()
    for needle in needles:
        index = normalized_compact.find(needle)
        if index != -1:
            start = max(0, index - 80)
            end = min(len(compact), index + 180)
            return compact[start:end].strip()
    return None


def _fetch_url(url: str, timeout: int) -> str:
    request = Request(url, headers={"User-Agent": "ESData-Hermes-Adjudicator/1.0"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - whitelisted upstream URLs are validated earlier.
        raw = response.read(2_000_000)
    return raw.decode("utf-8", errors="ignore")


def _source_checks(
    payload: dict[str, Any],
    *,
    verify_sources: bool,
    fetcher: Callable[[str], str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    source_results: list[dict[str, Any]] = []
    errors: list[str] = []
    fetch_cache: dict[str, str] = {}
    official_sources = payload.get("official_sources", [])
    model_code = str(payload.get("model_code", ""))
    if not isinstance(official_sources, list):
        return source_results, ["official_sources_not_array"]

    for source in official_sources:
        if not isinstance(source, dict):
            errors.append("official_source_not_object")
            continue
        source_id = str(source.get("source_id", ""))
        locator = str(source.get("locator", "")).strip()
        excerpt = str(source.get("excerpt", "")).strip()
        url = str(source.get("url", "")).strip()
        item_errors: list[str] = []
        excerpt_verified: bool | None = None
        suggested_excerpt: str | None = None
        is_binary_source = url.casefold().split("?", 1)[0].endswith(BINARY_SOURCE_SUFFIXES)

        if locator.casefold() in VAGUE_LOCATORS or len(locator) < 8:
            item_errors.append("vague_locator")
        if not excerpt:
            item_errors.append("missing_excerpt")
        if not url:
            item_errors.append("missing_url")

        if verify_sources and url and excerpt:
            try:
                if url not in fetch_cache:
                    if fetcher is None:
                        raise RuntimeError("fetcher missing")
                    fetch_cache[url] = fetcher(url)
                if is_binary_source:
                    excerpt_verified = None
                else:
                    source_text = fetch_cache[url]
                    excerpt_verified = _normalize_text(excerpt) in _normalize_text(source_text)
                    if not excerpt_verified:
                        suggested_excerpt = _suggest_excerpt(source_text, model_code)
                        if suggested_excerpt:
                            excerpt_verified = True
                        else:
                            item_errors.append("excerpt_not_found_in_source")
            except Exception as exc:
                excerpt_verified = False
                item_errors.append(f"source_fetch_failed:{exc}")
        elif not verify_sources:
            excerpt_verified = None
            item_errors.append("source_verification_not_run")

        source_results.append(
            {
                "source_id": source_id,
                "url": url,
                "locator": locator,
                "binary_source": is_binary_source,
                "excerpt_verified": excerpt_verified,
                "suggested_excerpt": suggested_excerpt,
                "errors": item_errors,
            }
        )
        errors.extend(f"{source_id}:{error}" for error in item_errors)

    return source_results, errors


def _claim_layer_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    official_source_ids = {
        source.get("source_id")
        for source in payload.get("official_sources", [])
        if isinstance(source, dict)
    }

    for index, claim in enumerate(payload.get("official_source_claims", [])):
        if not isinstance(claim, dict):
            errors.append(f"official_claim[{index}]:not_object")
            continue
        claim_text = " ".join(str(claim.get(part, "")) for part in ("claim", "source_id"))
        lower_text = claim_text.casefold()
        forbidden = [
            term for term in FORBIDDEN_OFFICIAL_EVIDENCE_TERMS if term in lower_text
        ]
        if forbidden:
            errors.append(
                f"official_claim[{index}]:internal_terms:{','.join(sorted(set(forbidden)))}"
            )
        if claim.get("source_id") not in official_source_ids:
            errors.append(f"official_claim[{index}]:source_not_declared")

    for index, claim in enumerate(payload.get("derived_claims", [])):
        if isinstance(claim, dict) and claim.get("may_assert_campaign") is not False:
            errors.append(f"derived_claim[{index}]:may_assert_campaign")

    for index, claim in enumerate(payload.get("system_observed_claims", [])):
        if isinstance(claim, dict) and claim.get("may_assert_campaign") is not False:
            errors.append(f"system_claim[{index}]:may_assert_campaign")

    return errors


def _gate(payload: dict[str, Any]) -> dict[str, Any]:
    gate = payload.get("assertion_gate")
    return gate if isinstance(gate, dict) else {}


def _proving_claims(payload: dict[str, Any]) -> int:
    return sum(
        1
        for claim in payload.get("official_source_claims", [])
        if isinstance(claim, dict) and claim.get("proves_campaign") is True
    )


def adjudicate_report(
    path: Path,
    *,
    verify_sources: bool,
    fetcher: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    audit = audit_report(path)
    if not audit.get("schema_valid"):
        return {
            **audit,
            "machine_decision": "reject_report",
            "repository_bucket": "reject/schema_invalid",
            "source_checks": [],
            "automatic_rejection_reasons": audit.get("validation_errors", []),
        }

    payload = load_report(path)
    source_checks, source_errors = _source_checks(
        payload,
        verify_sources=verify_sources,
        fetcher=fetcher,
    )
    layer_errors = _claim_layer_errors(payload)
    automatic_rejection_reasons = source_errors + layer_errors
    gate = _gate(payload)
    proving_claims = _proving_claims(payload)
    safe_to_assert = (
        gate.get("campana_safe_to_assert") is True
        and gate.get("campana_afirmable") is not None
        and gate.get("campana_assertion_code") == ASSERTABLE_CODE
    )

    if audit.get("integrable") is not True:
        machine_decision = "needs_report_rewrite"
        bucket = "rewrite/not_integrable"
    elif automatic_rejection_reasons:
        machine_decision = "needs_report_rewrite"
        bucket = "rewrite/traceability"
    elif safe_to_assert or proving_claims:
        machine_decision = "human_review_assertable_candidate"
        bucket = "review/assertable_candidate"
    elif audit.get("decision") == "CONFLICT":
        machine_decision = "auto_accept_conflict_evidence"
        bucket = "draft/conflict"
    elif audit.get("decision") == "STALE_SUSPECTED":
        machine_decision = "auto_accept_stale_suspected_evidence"
        bucket = "draft/stale_suspected"
    else:
        machine_decision = "auto_accept_nonassertable_evidence"
        bucket = "draft/nonassertable"

    return {
        **audit,
        "machine_decision": machine_decision,
        "repository_bucket": bucket,
        "source_checks": source_checks,
        "automatic_rejection_reasons": automatic_rejection_reasons,
        "source_verification_required": not verify_sources,
    }


def _iter_reports(inputs: list[Path]) -> list[Path]:
    reports: list[Path] = []
    for item in inputs:
        if item.is_dir():
            reports.extend(sorted(item.glob("*.json")))
        else:
            reports.append(item)
    return reports


def _model_code_from_report_name(path: Path) -> str:
    name = path.name
    if not name.startswith("modelo-") or not name.endswith(".json"):
        return name
    return name.removeprefix("modelo-").removesuffix(".json").split("-", 1)[0]


def _latest_per_model(paths: list[Path]) -> list[Path]:
    latest: dict[str, Path] = {}
    for path in paths:
        model_code = _model_code_from_report_name(path)
        current = latest.get(model_code)
        if current is None or path.name > current.name:
            latest[model_code] = path
    return [latest[key] for key in sorted(latest)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch-adjudicate AEAT Hermes JSON reports without human per-model review."
    )
    parser.add_argument("reports", nargs="+", type=Path, help="JSON reports or directories")
    parser.add_argument(
        "--verify-sources",
        action="store_true",
        help="Fetch official URLs and require source excerpts to be present.",
    )
    parser.add_argument(
        "--latest-per-model",
        action="store_true",
        help="When a directory is provided, adjudicate only the newest modelo-<code>-*.json per model.",
    )
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument(
        "--fail-on-rewrite",
        action="store_true",
        help="Exit non-zero when any report needs rewrite or rejection.",
    )
    args = parser.parse_args()

    fetcher = (lambda url: _fetch_url(url, args.timeout)) if args.verify_sources else None
    report_paths = _iter_reports(args.reports)
    if args.latest_per_model:
        report_paths = _latest_per_model(report_paths)

    results = [
        adjudicate_report(path, verify_sources=args.verify_sources, fetcher=fetcher)
        for path in report_paths
    ]
    print(json.dumps({"reports": results}, ensure_ascii=False, indent=2))
    if args.fail_on_rewrite and any(
        str(item.get("machine_decision", "")).startswith(("needs_", "reject"))
        for item in results
    ):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
