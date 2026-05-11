"""Local Ralph gate for MCP/API legal accuracy checks.

This is intentionally read-only against the API. It validates deterministic
responses, provenance fields, freshness metadata, safe negative behavior, and
query audit traceability.
"""

from __future__ import annotations

import argparse
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


@dataclass
class Check:
    name: str
    status: str
    evidence: dict[str, Any]
    blocker: str | None = None


def _ok(name: str, evidence: dict[str, Any]) -> Check:
    return Check(name=name, status="pass", evidence=evidence)


def _fail(name: str, evidence: dict[str, Any], blocker: str) -> Check:
    return Check(name=name, status="fail", evidence=evidence, blocker=blocker)


def _headers(api_key: str, request_id: str | None = None) -> dict[str, str]:
    headers = {"X-API-Key": api_key} if api_key else {}
    if request_id:
        headers["X-Request-ID"] = request_id
        headers["X-User-ID"] = "ralph-local"
    return headers


def _get(client: httpx.Client, path: str, api_key: str, request_id: str | None = None) -> httpx.Response:
    return client.get(path, headers=_headers(api_key, request_id), timeout=30)


def _require_text(payload: dict[str, Any], expected: str) -> bool:
    return expected in payload.get("texto", "")


def run_suite(base_url: str, api_key: str) -> dict[str, Any]:
    checks: list[Check] = []
    base_url = base_url.rstrip("/")
    audit_request_id = f"ralph-local-005-{uuid.uuid4().hex[:10]}"

    with httpx.Client(base_url=base_url, timeout=30) as client:
        for path in ("/health", "/status"):
            response = _get(client, path, api_key)
            if response.status_code == 200:
                checks.append(_ok(path, {"status_code": response.status_code}))
            else:
                checks.append(_fail(path, {"status_code": response.status_code}, "Endpoint is not healthy."))

        response = _get(client, "/v1/legislacion/LIVA/articulos/90", api_key, audit_request_id)
        current = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        current_ok = (
            response.status_code == 200
            and _require_text(current, "21 por ciento")
            and current.get("vigente_desde") == "2012-07-15"
            and current.get("vigente_hasta") is None
            and current.get("boe_reference") == "BOE-A-1992-28740"
            and current.get("source_url") == "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a90"
        )
        checks.append(
            _ok(
                "liva_90_current",
                {
                    "status_code": response.status_code,
                    "vigente_desde": current.get("vigente_desde"),
                    "vigente_hasta": current.get("vigente_hasta"),
                    "boe_reference": current.get("boe_reference"),
                    "source_url": current.get("source_url"),
                    "contains_21": _require_text(current, "21 por ciento"),
                },
            )
            if current_ok
            else _fail(
                "liva_90_current",
                {
                    "status_code": response.status_code,
                    "payload": current,
                },
                "LIVA art. 90 current response does not match BOE consolidated current text/provenance.",
            )
        )

        historical_cases = [
            ("liva_90_1994", "1994-01-01", "15 por 100", "1993-01-01", "1995-01-20"),
            ("liva_90_2011", "2011-01-01", "18 por ciento", "2010-07-01", "2012-07-15"),
            ("liva_90_2012_boundary", "2012-07-15", "21 por ciento", "2012-07-15", None),
        ]
        for name, date_value, expected_text, expected_from, expected_until in historical_cases:
            response = _get(
                client,
                f"/v1/legislacion/LIVA/articulos/90?vigente_en={date_value}",
                api_key,
            )
            payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            ok = (
                response.status_code == 200
                and _require_text(payload, expected_text)
                and payload.get("vigente_desde") == expected_from
                and payload.get("vigente_hasta") == expected_until
                and payload.get("boe_reference") == "BOE-A-1992-28740"
            )
            evidence = {
                "status_code": response.status_code,
                "vigente_en": date_value,
                "expected_text": expected_text,
                "contains_expected_text": _require_text(payload, expected_text),
                "vigente_desde": payload.get("vigente_desde"),
                "vigente_hasta": payload.get("vigente_hasta"),
                "boe_reference": payload.get("boe_reference"),
            }
            checks.append(
                _ok(name, evidence)
                if ok
                else _fail(name, evidence, f"Historical LIVA art. 90 response is incorrect for {date_value}.")
            )

        response = _get(client, "/v1/sources/freshness", api_key)
        freshness = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        sources = freshness.get("sources", [])
        official_sources = {source.get("source_id") for source in sources}
        stale_sources = [source.get("source_id") for source in sources if source.get("stale")]
        freshness_ok = response.status_code == 200 and len(sources) >= 1 and not stale_sources
        checks.append(
            _ok(
                "source_freshness",
                {
                    "status_code": response.status_code,
                    "total": freshness.get("total"),
                    "source_ids": sorted(source_id for source_id in official_sources if source_id),
                    "stale_sources": stale_sources,
                },
            )
            if freshness_ok
            else _fail(
                "source_freshness",
                {
                    "status_code": response.status_code,
                    "payload": freshness,
                },
                "Source freshness endpoint is empty, stale, or unavailable.",
            )
        )

        for name, path in {
            "missing_article_safe_404": "/v1/legislacion/LIVA/articulos/9999",
            "unknown_norma_safe_404": "/v1/legislacion/NOEXISTE/articulos/1",
        }.items():
            response = _get(client, path, api_key)
            detail = response.json().get("detail") if response.headers.get("content-type", "").startswith("application/json") else None
            ok = response.status_code == 404 and isinstance(detail, dict) and "error" in detail
            checks.append(
                _ok(name, {"status_code": response.status_code, "detail": detail})
                if ok
                else _fail(name, {"status_code": response.status_code, "detail": detail}, "Negative lookup did not fail explicitly and safely.")
            )

        response = _get(client, f"/v1/ai/query-audit/{audit_request_id}", api_key)
        audit = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        entries = audit.get("entries", [])
        audit_ok = (
            response.status_code == 200
            and audit.get("total", 0) >= 1
            and any(
                entry.get("tool_name") == "get_articulo"
                and entry.get("verified") is True
                and entry.get("path") == "/v1/legislacion/LIVA/articulos/90"
                and entry.get("retrieved_chunks")
                for entry in entries
            )
        )
        checks.append(
            _ok(
                "query_audit_traceability",
                {
                    "status_code": response.status_code,
                    "request_id": audit_request_id,
                    "total": audit.get("total"),
                    "tool_names": [entry.get("tool_name") for entry in entries],
                },
            )
            if audit_ok
            else _fail(
                "query_audit_traceability",
                {
                    "status_code": response.status_code,
                    "request_id": audit_request_id,
                    "payload": audit,
                },
                "API call was not traceable through query_audit_log.",
            )
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "official_reference_checked": {
            "source": "BOE",
            "url": "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a90",
            "reference": "BOE-A-1992-28740",
            "expected_current_text": "Artículo 90: tipo general 21 por ciento",
            "expected_historical_2011": "Artículo 90: tipo general 18 por ciento desde 2010-07-01 hasta 2012-07-15",
        },
        "summary": {
            "total": len(checks),
            "passed": sum(1 for check in checks if check.status == "pass"),
            "failed": sum(1 for check in checks if check.status == "fail"),
        },
        "checks": [asdict(check) for check in checks],
        "ok": all(check.status == "pass" for check in checks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("ESDATA_API_URL", "http://localhost:8001"))
    parser.add_argument("--api-key", default=os.getenv("ESDATA_API_KEY", "dev-key"))
    parser.add_argument("--write", type=Path)
    args = parser.parse_args()

    result = run_suite(args.base_url, args.api_key)
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
