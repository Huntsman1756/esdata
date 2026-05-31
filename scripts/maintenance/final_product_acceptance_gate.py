#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib import error, parse, request

SOURCE_KEYS = {
    "source_url",
    "url_fuente",
    "source",
    "fuente",
    "referencia_boe",
    "boe_id",
    "eli_uri",
    "url",
    "source_ref",
    "referencia",
}
EVIDENCE_STATUS_KEYS = {
    "safe_to_answer",
    "verified",
    "completeness",
    "availability_status",
    "evidence_limited",
    "evidence_status",
    "review_required",
    "campana_safe_to_assert",
    "campana_assertion_code",
    "status",
}
FAIL_CLOSED_STATUSES = {
    "workflow_empty",
    "allowed_empty",
    "configured_but_unavailable",
    "not_exposed",
    "evidence_limited",
    "insufficient_evidence",
    "partial",
    "unknown",
}


@dataclass(frozen=True)
class CanonicalCheck:
    name: str
    domain: str
    path: str
    params: dict[str, str] | None = None
    requires_source: bool = False
    requires_evidence_status: bool = False
    allow_fail_closed_empty: bool = False
    status_check: bool = False


@dataclass(frozen=True)
class CheckResult:
    name: str
    domain: str
    ok: bool
    reason: str
    path: str = ""
    status_code: int | None = None


DEFAULT_CHECKS = [
    CanonicalCheck("health", "infra", "/health"),
    CanonicalCheck("status", "infra", "/status", status_check=True),
    CanonicalCheck(
        "domain_availability",
        "infra",
        "/v1/domain-availability",
        requires_evidence_status=True,
    ),
    CanonicalCheck(
        "boe_legislation_liva",
        "BOE",
        "/v1/legislacion/LIVA",
        requires_source=True,
        requires_evidence_status=True,
    ),
    CanonicalCheck(
        "aeat_model_124_summary",
        "AEAT",
        "/v1/modelos/124/resumen-operativo",
        requires_evidence_status=True,
    ),
    CanonicalCheck(
        "doctrina_coverage",
        "DGT/TEAC",
        "/v1/doctrina/lineas/coverage",
        requires_evidence_status=True,
    ),
    CanonicalCheck(
        "cnmv_coverage",
        "CNMV",
        "/v1/cnmv/coverage",
        requires_evidence_status=True,
    ),
    CanonicalCheck(
        "eurlex_market_acts",
        "EUR-Lex/ESMA",
        "/v1/eurlex/market/acts",
        requires_source=True,
        requires_evidence_status=True,
    ),
    CanonicalCheck(
        "mica_casp",
        "MiCA/CASP",
        "/v1/mica/casp",
        requires_source=True,
        requires_evidence_status=True,
    ),
    CanonicalCheck(
        "screening_entries",
        "Screening",
        "/v1/screening/entries",
        params={"codigo": "EU_SANCTIONS", "limit": "1"},
        requires_source=True,
        requires_evidence_status=True,
    ),
    CanonicalCheck(
        "aepd_partial",
        "AEPD",
        "/v1/aepd",
        requires_source=True,
        requires_evidence_status=True,
        allow_fail_closed_empty=True,
    ),
    CanonicalCheck(
        "sepblac_partial",
        "SEPBLAC",
        "/v1/sepblac",
        requires_source=True,
        requires_evidence_status=True,
        allow_fail_closed_empty=True,
    ),
    CanonicalCheck(
        "bde_partial",
        "BDE",
        "/v1/bde",
        requires_source=True,
        requires_evidence_status=True,
        allow_fail_closed_empty=True,
    ),
]


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _has_key_with_value(payload: Any, keys: set[str]) -> bool:
    for item in _walk(payload):
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if key in keys and value not in (None, "", [], {}):
                return True
    return False


def has_source_reference(payload: Any) -> bool:
    return _has_key_with_value(payload, SOURCE_KEYS)


def has_evidence_status(payload: Any) -> bool:
    return _has_key_with_value(payload, EVIDENCE_STATUS_KEYS)


def is_empty_response(payload: Any) -> bool:
    if payload in (None, [], {}):
        return True
    if isinstance(payload, dict):
        if payload.get("total") == 0:
            return True
        for key in ("items", "resultados", "results", "data", "sources"):
            if key in payload and payload.get(key) == []:
                return True
    return False


def is_fail_closed(payload: Any) -> bool:
    for item in _walk(payload):
        if not isinstance(item, dict):
            continue
        if item.get("safe_to_answer") is False:
            return True
        if item.get("verified") is False and item.get("review_required") is True:
            return True
        for key in ("availability_status", "status", "evidence_status", "completeness"):
            value = item.get(key)
            if isinstance(value, str) and value.lower() in FAIL_CLOSED_STATUSES:
                return True
    return False


def evaluate_payload(check: CanonicalCheck, payload: Any) -> CheckResult:
    if is_empty_response(payload):
        if check.allow_fail_closed_empty and is_fail_closed(payload):
            return CheckResult(check.name, check.domain, True, "ok", check.path)
        return CheckResult(
            check.name,
            check.domain,
            False,
            "empty response without fail-closed status",
            check.path,
        )

    if check.requires_source and not has_source_reference(payload):
        return CheckResult(check.name, check.domain, False, "missing source", check.path)

    if check.requires_evidence_status and not has_evidence_status(payload):
        return CheckResult(
            check.name,
            check.domain,
            False,
            "missing evidence status",
            check.path,
        )

    return CheckResult(check.name, check.domain, True, "ok", check.path)


def evaluate_status_payload(payload: dict[str, Any]) -> CheckResult:
    if payload.get("api") != "ok" or payload.get("database") != "ok":
        return CheckResult("status", "infra", False, "api/database not ok", "/status")
    workers = payload.get("workers")
    if not isinstance(workers, dict):
        return CheckResult("status", "infra", False, "missing workers", "/status")
    stale = [
        name
        for name, worker in workers.items()
        if isinstance(worker, dict) and worker.get("stale") is True
    ]
    errored = [
        name
        for name, worker in workers.items()
        if isinstance(worker, dict)
        and str(worker.get("status", "")).lower() in {"error", "failed"}
    ]
    if stale:
        return CheckResult("status", "infra", False, f"stale workers: {stale}", "/status")
    if errored:
        return CheckResult("status", "infra", False, f"worker errors: {errored}", "/status")
    return CheckResult("status", "infra", True, "ok", "/status")


def _request_json(base_url: str, check: CanonicalCheck, api_key: str | None) -> tuple[int, Any]:
    url = base_url.rstrip("/") + check.path
    if check.params:
        url += "?" + parse.urlencode(check.params)
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    req = request.Request(url, headers=headers)
    with request.urlopen(req, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
        return response.status, json.loads(body)


def run_gate(
    base_url: str,
    api_key: str | None = None,
    checks: list[CanonicalCheck] | None = None,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    for check in checks or DEFAULT_CHECKS:
        try:
            status_code, payload = _request_json(base_url, check, api_key)
        except (OSError, error.URLError, json.JSONDecodeError) as exc:
            results.append(
                CheckResult(check.name, check.domain, False, f"request failed: {exc}", check.path)
            )
            continue
        if not (200 <= status_code < 300):
            results.append(
                CheckResult(
                    check.name,
                    check.domain,
                    False,
                    f"unexpected http status {status_code}",
                    check.path,
                    status_code,
                )
            )
            continue
        result = evaluate_status_payload(payload) if check.status_check else evaluate_payload(check, payload)
        results.append(
            CheckResult(
                result.name,
                result.domain,
                result.ok,
                result.reason,
                result.path,
                status_code,
            )
        )
    return results


def write_reports(results: list[CheckResult], json_path: Path | None, md_path: Path | None) -> None:
    summary = {
        "ok": all(result.ok for result in results),
        "total": len(results),
        "failed": [asdict(result) for result in results if not result.ok],
        "results": [asdict(result) for result in results],
    }
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if md_path:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# ESData final product acceptance gate",
            "",
            f"- ok: {str(summary['ok']).lower()}",
            f"- total: {summary['total']}",
            f"- failed: {len(summary['failed'])}",
            "",
            "| Domain | Check | Result | Reason |",
            "| --- | --- | --- | --- |",
        ]
        for result in results:
            lines.append(
                f"| {result.domain} | {result.name} | {'OK' if result.ok else 'FAIL'} | {result.reason} |"
            )
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ESData final product acceptance smoke")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    args = parser.parse_args()

    results = run_gate(args.base_url, args.api_key)
    write_reports(results, args.json_out, args.md_out)
    print(json.dumps({"ok": all(item.ok for item in results), "results": [asdict(item) for item in results]}, indent=2))
    return 0 if all(item.ok for item in results) else 1


if __name__ == "__main__":
    sys.exit(main())
