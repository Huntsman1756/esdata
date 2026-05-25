#!/usr/bin/env python3
"""Read-only AEAT campaign resolution audit via the public API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from typing import Any


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
        rows.append(
            {
                "codigo": code,
                "campana_activa": payload.get("campana_activa"),
                "campana_candidata": candidate,
                "campana_resolution_status": status,
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
