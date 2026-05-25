#!/usr/bin/env python3
"""Read-only AEAT campaign resolution audit via the public API."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from typing import Any

AEAT_HOST_MARKERS = ("agenciatributaria.gob.es",)
DIRECT_AEAT_CAMPAIGN_TYPES = {
    "aeat_formato",
    "aeat_instrucciones",
    "modelo_recurso:ayuda_tecnica_presentacion",
    "modelo_recurso:diseno_registro",
    "modelo_recurso:formulario_html",
    "modelo_recurso:formulario_pdf",
    "modelo_recurso:instrucciones",
}


def _request_json(base_url: str, path: str, api_key: str | None) -> dict[str, Any]:
    request = urllib.request.Request(urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/")))
    if api_key:
        request.add_header("x-api-key", api_key)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 4:
                raise
            try:
                delay = float(exc.headers.get("Retry-After", ""))
            except ValueError:
                delay = 2.0 * (attempt + 1)
            if delay <= 0:
                delay = 2.0 * (attempt + 1)
            time.sleep(delay)
    raise RuntimeError("unreachable retry state")


def _list_model_codes(base_url: str, api_key: str | None, limit: int) -> list[str]:
    payload = _request_json(base_url, f"/v1/modelos?limit={limit}&offset=0", api_key)
    rows = payload.get("modelos", [])
    codes = [str(row["codigo"]) for row in rows if row.get("codigo")]
    total = int(payload.get("total", len(codes)) or len(codes))
    if total > len(codes):
        payload = _request_json(base_url, f"/v1/modelos?limit={total}&offset=0", api_key)
        codes = [str(row["codigo"]) for row in payload.get("modelos", []) if row.get("codigo")]
    return sorted(set(codes))


def _extract_years(*values: str | None) -> list[str]:
    current_year = datetime.now(UTC).year
    years = set()
    for value in values:
        for match in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", value or ""):
            year = int(match)
            if 1990 <= year <= current_year + 1:
                years.add(match)
    return sorted(years)


def _is_aeat_url(url: str | None) -> bool:
    return bool(url and any(marker in url for marker in AEAT_HOST_MARKERS))


def _candidate_support(
    candidate: str | None,
    fuentes: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    if not candidate:
        return "none", []

    implicit_evidence = []
    for source in fuentes:
        if source.get("tipo") not in DIRECT_AEAT_CAMPAIGN_TYPES:
            continue
        if not _is_aeat_url(source.get("url")) and source.get("organismo") != "AEAT":
            continue

        years = _extract_years(source.get("url"), source.get("titulo"), source.get("fecha"))
        evidence = {
            "tipo": source.get("tipo"),
            "url": source.get("url"),
            "years": years,
            "support": "explicit_aeat_year" if candidate in years else "aeat_campaign_resource",
        }
        if candidate in years:
            return "explicit_aeat_year", [evidence]
        if source.get("campana") == candidate:
            implicit_evidence.append(evidence)

    if implicit_evidence:
        return "aeat_campaign_resource", implicit_evidence[:3]
    return "heuristic_or_implicit", []


def _summarize_support(rows: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = [row for row in rows if row["campana_resolution_status"] == "resolved"]
    support_counts: Counter[str] = Counter(row["campana_support_level"] for row in resolved)
    total_resolved = len(resolved)

    def pct(value: int) -> float:
        return round((value / total_resolved) * 100, 2) if total_resolved else 0.0

    return {
        "resolved_total": total_resolved,
        "resolved_support_counts": dict(sorted(support_counts.items())),
        "resolved_explicit_aeat_year_pct": pct(support_counts.get("explicit_aeat_year", 0)),
        "resolved_direct_or_implicit_aeat_resource_pct": pct(
            support_counts.get("explicit_aeat_year", 0)
            + support_counts.get("aeat_campaign_resource", 0)
        ),
    }


def audit(base_url: str, api_key: str | None, limit: int, request_delay: float) -> dict[str, Any]:
    codes = _list_model_codes(base_url, api_key, limit)
    status_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    candidate_count = 0
    rows = []

    for code in codes:
        payload = _request_json(base_url, f"/v1/modelos/{code}/fuentes-oficiales", api_key)
        if request_delay:
            time.sleep(request_delay)
        status = payload.get("campana_resolution_status") or "unknown"
        severity = payload.get("campana_conflict_severity") or "none"
        candidate = payload.get("campana_candidata")
        status_counts[status] += 1
        severity_counts[severity] += 1
        if candidate is not None:
            candidate_count += 1
        support_level, support_evidence = _candidate_support(
            str(candidate) if candidate is not None else None,
            payload.get("fuentes_oficiales") or [],
        )
        rows.append(
            {
                "codigo": code,
                "campana_activa": payload.get("campana_activa"),
                "campana_candidata": candidate,
                "campana_resolution_status": status,
                "campana_support_level": support_level,
                "campana_support_evidence": support_evidence,
                "campana_conflict": bool(payload.get("campana_conflict")),
                "campana_conflict_severity": severity,
                "campana_conflict_years": payload.get("campana_conflict_years") or [],
            }
        )

    total = len(rows)

    def pct(value: int) -> float:
        return round((value / total) * 100, 2) if total else 0.0
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "total_modelos": total,
        "status_counts": dict(sorted(status_counts.items())),
        "severity_counts": dict(sorted(severity_counts.items())),
        "campana_candidata_non_null": candidate_count,
        "campana_candidata_non_null_pct": pct(candidate_count),
        "campana_conflict_pct": pct(status_counts.get("conflict", 0)),
        **_summarize_support(rows),
        "review_queues": {
            "conflict_strong": [
                row["codigo"] for row in rows if row["campana_conflict_severity"] == "strong"
            ],
            "conflict_weak": [
                row["codigo"] for row in rows if row["campana_conflict_severity"] == "weak"
            ],
            "insufficient_evidence": [
                row["codigo"]
                for row in rows
                if row["campana_resolution_status"] == "insufficient_evidence"
            ],
            "resolved_without_direct_aeat_year": [
                row["codigo"]
                for row in rows
                if row["campana_resolution_status"] == "resolved"
                and row["campana_support_level"] != "explicit_aeat_year"
            ][:50],
        },
        "modelos": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("ESDATA_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--api-key", default=os.getenv("ESDATA_API_KEY") or os.getenv("API_KEY"))
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--request-delay", type=float, default=0.1)
    args = parser.parse_args()

    print(
        json.dumps(
            audit(args.base_url, args.api_key, args.limit, args.request_delay),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
