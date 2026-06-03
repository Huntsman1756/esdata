#!/usr/bin/env python3
"""Read-only BOE recapture audit for AEAT modelo_recurso candidates.

Downloads each unique BOE URL once, calculates SHA-256 and byte length, compares
the fresh hash against the hash already stored in modelo_recurso, and writes CSV
and JSON reports. This script never writes to the database.

Usage:
    python scripts/maintenance/boe_recapture_audit.py --dsn postgresql://... --output ./audit_out
    python scripts/maintenance/boe_recapture_audit.py --dry-run --output ./audit_out
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REQUEST_TIMEOUT = 20
REQUEST_DELAY = 1.5
USER_AGENT = "esdata-boe-recapture-audit/1.0 (read-only; contact: ops@esdata.local)"


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_boe_doc_url(url: str, boe_id: str) -> str:
    if boe_id:
        return f"https://www.boe.es/buscar/doc.php?id={boe_id}"
    return url


def fetch_boe(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            data = response.read()
            return {
                "ok": True,
                "status_code": response.status,
                "sha256": sha256_of(data),
                "content_length": len(data),
                "text_excerpt": extract_text_excerpt(data),
            }
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status_code": exc.code, "note": str(exc)}
    except Exception as exc:  # noqa: BLE001 - audit report should capture failures.
        return {"ok": False, "status_code": None, "note": str(exc)}


def extract_text_excerpt(data: bytes, *, max_chars: int = 700) -> str:
    """Return a compact current-document excerpt for human/Hermes review.

    This is not a diff: modelo_recurso stores the previous hash, not the
    previous bytes. It gives reviewers enough current context for hash_changed.
    """
    text = data.decode("utf-8", errors="replace")
    description = re.search(
        r'<meta\s+name=["\']Description["\']\s+content=["\']([^"\']+)["\']',
        text,
        flags=re.IGNORECASE,
    )
    if description:
        normalized = html.unescape(description.group(1))
    else:
        normalized = re.sub(r"<[^>]+>", " ", text)
        normalized = html.unescape(normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized[:max_chars]


def get_candidates_from_db(dsn: str) -> list[dict[str, Any]]:
    """Return unique weak BOE candidates from production-shaped schema.

    Candidate definition matches the post-0115 follow-up audit:
    inactive generic BOE normativa rows for active AEAT campaigns, with stored
    hash but missing content_length, and no matching modelo_normativa row.
    """
    import psycopg

    sql = """
        WITH boe_resources AS (
            SELECT
                am.codigo AS modelo_codigo,
                mc.campana,
                mr.id AS recurso_id,
                mr.url_recurso,
                regexp_replace(
                    mr.url_recurso,
                    '^.*id=(BOE-A-[0-9]{4}-[0-9]+).*$',
                    '\\1'
                ) AS boe_id,
                mr.sha256_contenido AS existing_hash,
                mr.content_length AS existing_content_length,
                COALESCE(mr.metadata->>'anchor_text', mr.metadata->>'label', '') AS title
            FROM modelo_recurso mr
            JOIN modelo_campana mc ON mc.id = mr.campana_id
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE mr.url_recurso ILIKE '%boe.es%'
              AND mr.tipo_recurso = 'normativa'
              AND mr.activa IS false
              AND mr.sha256_contenido IS NOT NULL
              AND mr.content_length IS NULL
              AND mr.row_provenance = 'official_exact'
              AND mc.activo IS true
        ),
        semantic_boe AS (
            SELECT DISTINCT am.codigo AS modelo_codigo, mn.boe_id
            FROM modelo_normativa mn
            JOIN aeat_modelo am ON am.id = mn.modelo_id
        )
        SELECT
            string_agg(DISTINCT br.modelo_codigo, ',' ORDER BY br.modelo_codigo) AS modelo_codes,
            string_agg(DISTINCT br.campana, ',' ORDER BY br.campana) AS campanas,
            string_agg(br.recurso_id::text, ',' ORDER BY br.recurso_id) AS recurso_ids,
            br.boe_id,
            br.url_recurso AS url,
            br.existing_hash,
            br.existing_content_length,
            COUNT(*) AS row_count,
            left(MAX(br.title), 180) AS title
        FROM boe_resources br
        WHERE NOT EXISTS (
            SELECT 1
            FROM semantic_boe sb
            WHERE sb.modelo_codigo = br.modelo_codigo
              AND sb.boe_id = br.boe_id
        )
          AND (br.boe_id LIKE 'BOE-A-2025-%' OR br.title ILIKE '%2025%')
        GROUP BY br.boe_id, br.url_recurso, br.existing_hash, br.existing_content_length
        ORDER BY br.boe_id, br.url_recurso, br.existing_hash
    """

    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            columns = [description.name for description in cursor.description or []]
            rows = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    for row in rows:
        row["fetch_url"] = canonical_boe_doc_url(row["url"], row["boe_id"])
    return rows


def get_candidates_dry_run() -> list[dict[str, Any]]:
    return [
        {
            "modelo_codes": "182,184,193,195,199,282,345",
            "campanas": "2025",
            "recurso_ids": "2070,2158,2828,29659,3263,30620,5832",
            "boe_id": "BOE-A-2025-25389",
            "url": "https://www.boe.es/buscar/doc.php?id=BOE-A-2025-25389",
            "fetch_url": "https://www.boe.es/buscar/doc.php?id=BOE-A-2025-25389",
            "existing_hash": "45522b6eed4eca77673bffd87d7a4d744b9195e00ec4594a9fb9ae591b32421a",
            "existing_content_length": None,
            "row_count": 7,
            "title": "Orden HAC/1430/2025, de 3 de diciembre,",
        },
        {
            "modelo_codes": "190,270,347",
            "campanas": "2025",
            "recurso_ids": "2656,4658,6002",
            "boe_id": "BOE-A-2025-25390",
            "url": "https://www.boe.es/buscar/doc.php?id=BOE-A-2025-25390",
            "fetch_url": "https://www.boe.es/buscar/doc.php?id=BOE-A-2025-25390",
            "existing_hash": "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899",
            "existing_content_length": None,
            "row_count": 3,
            "title": "Orden HAC/1431/2025, de 3 de diciembre,",
        },
    ]


def audit_candidates(candidates: list[dict[str, Any]], *, dry_run: bool = False) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    capture_date = datetime.now(UTC).date().isoformat()

    for index, candidate in enumerate(candidates, 1):
        boe_id = str(candidate["boe_id"])
        fetch_url = str(candidate.get("fetch_url") or candidate["url"])
        print(f"[{index}/{len(candidates)}] {boe_id} ... ", end="", flush=True)

        if dry_run:
            response = {
                "ok": True,
                "status_code": 200,
                "sha256": (
                    candidate["existing_hash"]
                    if index == 1
                    else "f" * 64
                ),
                "content_length": 110846 if index == 1 else 111111,
                "text_excerpt": f"Dry-run excerpt for {candidate['boe_id']}",
                "note": "dry-run",
            }
        else:
            response = fetch_boe(fetch_url)
            time.sleep(REQUEST_DELAY)

        if not response["ok"]:
            row = {
                **candidate,
                "new_hash": None,
                "new_content_length": None,
                "new_text_excerpt": None,
                "status": "download_failed",
                "status_code": response.get("status_code"),
                "capture_date_new": capture_date,
                "note": response.get("note", ""),
                "comparison_note": "download failed; no current text available",
            }
        else:
            stable = response["sha256"] == candidate["existing_hash"]
            row = {
                **candidate,
                "new_hash": response["sha256"],
                "new_content_length": response["content_length"],
                "new_text_excerpt": response.get("text_excerpt"),
                "status": "stable" if stable else "hash_changed",
                "status_code": response["status_code"],
                "capture_date_new": capture_date,
                "note": "dry-run" if dry_run else "",
                "comparison_note": (
                    "current hash matches stored hash"
                    if stable
                    else "stored bytes are unavailable; excerpt is from current BOE document, not a diff"
                ),
            }

        print(row["status"])
        results.append(row)

    return results


FIELDNAMES = [
    "modelo_codes",
    "campanas",
    "recurso_ids",
    "row_count",
    "boe_id",
    "title",
    "url",
    "fetch_url",
    "existing_hash",
    "new_hash",
    "existing_content_length",
    "new_content_length",
    "new_text_excerpt",
    "status",
    "status_code",
    "capture_date_new",
    "note",
    "comparison_note",
]


def write_csv(results: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)


def write_json(results: list[dict[str, Any]], path: Path) -> None:
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total": len(results),
        "stable": sum(1 for row in results if row["status"] == "stable"),
        "hash_changed": sum(1 for row in results if row["status"] == "hash_changed"),
        "download_failed": sum(1 for row in results if row["status"] == "download_failed"),
        "results": results,
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, default=str)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dsn", help="PostgreSQL DSN")
    parser.add_argument("--output", default=".", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic fake candidates")
    args = parser.parse_args()

    if not args.dry_run and not args.dsn:
        parser.error("--dsn is required unless --dry-run is used")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== BOE recapture audit {'[DRY-RUN] ' if args.dry_run else ''}===")
    print(f"Output: {output_dir.resolve()}\n")

    candidates = get_candidates_dry_run() if args.dry_run else get_candidates_from_db(args.dsn)
    print(f"Unique candidates: {len(candidates)}\n")

    results = audit_candidates(candidates, dry_run=args.dry_run)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"boe_recapture_audit_{timestamp}.csv"
    json_path = output_dir / f"boe_recapture_audit_{timestamp}.json"

    write_csv(results, csv_path)
    write_json(results, json_path)

    stable = sum(1 for row in results if row["status"] == "stable")
    changed = sum(1 for row in results if row["status"] == "hash_changed")
    failed = sum(1 for row in results if row["status"] == "download_failed")

    print("\nSummary")
    print(f"  stable:          {stable}")
    print(f"  hash_changed:    {changed}")
    print(f"  download_failed: {failed}")
    print(f"\nCSV  -> {csv_path}")
    print(f"JSON -> {json_path}")

    if changed:
        print("\nManual review required before promotion:")
        for row in results:
            if row["status"] == "hash_changed":
                print(f"  {row['boe_id']} (models {row['modelo_codes']})")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
