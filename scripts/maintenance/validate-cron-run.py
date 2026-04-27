#!/usr/bin/env python
"""
Validate first production run of cron-teac-weekly and cron-dgt-weekly.

Usage:
    python scripts/maintenance/validate-cron-run.py [--db-url URL] [--after DATETIME]

Defaults to DATABASE_PUBLIC_URL from .env if available.
"""

import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env", verbose=False)
except ImportError:
    pass


TEAC_LOW_CONFIDENCE = """
SELECT di.referencia, di.fecha, n.codigo, a.numero,
       da.confianza_enlace, da.metodo_enlace, da.nota
FROM documento_articulo da
JOIN documento_interpretativo di ON di.id = da.documento_id
JOIN articulo a ON a.id = da.articulo_id
JOIN norma n ON n.id = a.norma_id
WHERE di.organismo_emisor = 'TEAC' AND da.confianza_enlace < 1.0
ORDER BY da.confianza_enlace ASC, di.fecha DESC;
"""

DGT_LOW_CONFIDENCE = """
SELECT di.referencia, di.fecha, n.codigo, a.numero,
       da.confianza_enlace, da.metodo_enlace, da.nota
FROM documento_articulo da
JOIN documento_interpretativo di ON di.id = da.documento_id
JOIN articulo a ON a.id = da.articulo_id
JOIN norma n ON n.id = a.norma_id
WHERE di.organismo_emisor = 'DGT' AND da.confianza_enlace < 1.0
ORDER BY da.confianza_enlace ASC, di.fecha DESC;
"""

RECENT_DOCUMENTS = """
SELECT di.referencia, di.fecha, di.organismo_emisor,
       COUNT(*) FILTER (WHERE da.documento_id IS NOT NULL) AS links,
       MIN(da.confianza_enlace) AS min_conf,
       MAX(da.confianza_enlace) AS max_conf,
       AVG(da.confianza_enlace) AS avg_conf
FROM documento_interpretativo di
LEFT JOIN documento_articulo da ON da.documento_id = di.id
WHERE di.fecha >= %s
GROUP BY di.id
ORDER BY di.fecha DESC
LIMIT 50;
"""

REGRESSION_CHECK = """
SELECT di.organismo_emisor,
       COUNT(*) AS total_links,
       COUNT(*) FILTER (WHERE da.confianza_enlace < 1.0) AS low_confidence,
       COUNT(*) FILTER (WHERE da.confianza_enlace = 1.0) AS full_confidence,
       ROUND(
         100.0 * COUNT(*) FILTER (WHERE da.confianza_enlace = 1.0) / COUNT(*), 2
       ) AS pct_full
FROM documento_articulo da
JOIN documento_interpretativo di ON di.id = da.documento_id
GROUP BY di.organismo_emisor
ORDER BY di.organismo_emisor;
"""


def get_db_url(args_db_url: str | None) -> str:
    if args_db_url:
        return normalize_db_url(args_db_url)
    url = os.getenv("DATABASE_PUBLIC_URL")
    if not url:
        # Fallback to direct URL
        url = os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: No DATABASE_PUBLIC_URL or DATABASE_URL found.")
        print("Provide --db-url or set env vars.")
        sys.exit(1)
    return normalize_db_url(url)


def normalize_db_url(db_url: str) -> str:
    # psycopg2 expects plain postgres schemes, not SQLAlchemy driver suffixes.
    if db_url.startswith("postgresql+psycopg://"):
        return "postgresql://" + db_url.removeprefix("postgresql+psycopg://")
    if db_url.startswith("postgresql+psycopg2://"):
        return "postgresql://" + db_url.removeprefix("postgresql+psycopg2://")
    return db_url


def connect(db_url: str):
    try:
        return psycopg2.connect(db_url)
    except Exception as e:
        print(f"ERROR: Cannot connect to database: {e}")
        sys.exit(1)


def run_query(conn, query, params=None):
    with conn.cursor() as cur:
        cur.execute(query, params or ())
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    return cols, rows


def print_table(cols, rows, title=""):
    if title:
        print(f"\n{'=' * 60}")
        print(f" {title}")
        print(f"{'=' * 60}")

    if not rows:
        print("  (no rows)")
        return

    # Calculate column widths
    widths = [len(c) for c in cols]
    str_rows = []
    for row in rows:
        str_row = [str(v) for v in row]
        str_rows.append(str_row)
        for i, v in enumerate(str_row):
            widths[i] = max(widths[i], len(v))

    # Header
    header = " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
    sep = "-+-".join("-" * widths[i] for i in range(len(cols)))
    print(f"  {header}")
    print(f"  {sep}")

    # Rows (limit display)
    display = str_rows[:30]
    for str_row in display:
        line = " | ".join(v.ljust(widths[i]) for i, v in enumerate(str_row))
        print(f"  {line}")

    if len(str_rows) > 30:
        print(f"  ... ({len(str_rows) - 30} more rows)")


def main():
    parser = argparse.ArgumentParser(description="Validate cron weekly runs")
    parser.add_argument("--db-url", help="Database connection URL")
    parser.add_argument("--after", help="Check documents after this date (YYYY-MM-DD)")
    args = parser.parse_args()

    db_url = get_db_url(args.db_url)
    conn = connect(db_url)

    after_date = args.after or "2026-04-12"

    print(f"\n--- esdata production validation ---")
    print(f"Database: {db_url[:30]}...")
    print(f"Checking documents after: {after_date}")

    # 1. Regression check by organism
    cols, rows = run_query(conn, REGRESSION_CHECK)
    print_table(cols, rows, "REGRESSION CHECK (confidence by organism)")

    # 2. TEAC low confidence cases
    cols, rows = run_query(conn, TEAC_LOW_CONFIDENCE)
    print_table(cols, rows, f"TEAC CASES WITH confidence < 1.0 (total: {len(rows)})")

    # 3. DGT low confidence cases
    cols, rows = run_query(conn, DGT_LOW_CONFIDENCE)
    print_table(cols, rows, f"DGT CASES WITH confidence < 1.0 (total: {len(rows)})")

    # 4. Recent documents
    cols, rows = run_query(conn, RECENT_DOCUMENTS, (after_date,))
    print_table(cols, rows, f"RECENT DOCUMENTS (since {after_date})")

    conn.close()
    print(f"\n--- validation complete ---\n")


if __name__ == "__main__":
    main()
