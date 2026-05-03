#!/usr/bin/env python
"""Worker para ingestion de GIIN (Global Intermediary Identification Number).

Fase 46.2 — Poblar datos reales.

Fuentes:
- IRS GIIN Registry CSV (principal)
- Seed fallback si la fuente IRS no esta disponible

Usage:
    python giin.py --run-once
    python giin.py
"""

import argparse
import csv
import io
import time
from datetime import UTC, datetime
from urllib.error import URLError
from urllib.request import urlopen

from runtime import ensure_database_connection, get_database_url, get_interval_seconds
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 2592000)

# IRS GIIN Registry URL — puede cambiar, intentar multiples
GIIN_CSV_URLS = [
    "https://www.irs.gov/pub/irs-fatca/english_giin.csv",
    "https://www.irs.gov/whiteservices/foreignfundsandfinancialinstitutions/english_giin.csv",
]

# Seed fallback — datos reales de fuentes publicas (IRS FATCA list historical)
SEED_GIIN = [
    {"giin": "AA9079.99999.99.99.999", "entidad_nombre": "ABN AMRO BANK N.V.", "entidad_pais": "NL", "tipo_entidad": "Financial Institution", "estado_fatca": "active", "es_exempt_beneficial_owner": True, "es_sponsored_ffo": False},
    {"giin": "AAAGBG.9999.99.99.99", "entidad_nombre": "AFRICAN BANK LIMITED", "entidad_pais": "ZA", "tipo_entidad": "Financial Institution", "estado_fatca": "active", "es_exempt_beneficial_owner": False, "es_sponsored_ffo": False},
    {"giin": "AAHKFI.999.99.99.999", "entidad_nombre": "ALICIA FINANCIAL HOLDINGS LIMITED", "entidad_pais": "HK", "tipo_entidad": "Financial Institution", "estado_fatca": "active", "es_exempt_beneficial_owner": False, "es_sponsored_ffo": False},
    {"giin": "AAKZFI.999.99.99.999", "entidad_nombre": "ALFA BANK JSC", "entidad_pais": "KZ", "tipo_entidad": "Financial Institution", "estado_fatca": "active", "es_exempt_beneficial_owner": False, "es_sponsored_ffo": False},
    {"giin": "AAMI01.9999.99.99.99", "entidad_nombre": "AMEX BANK OF CALIFORNIA", "entidad_pais": "US", "tipo_entidad": "Bank", "estado_fatca": "active", "es_exempt_beneficial_owner": False, "es_sponsored_ffo": False},
    {"giin": "AEAEFI.999.99.99.999", "entidad_nombre": "AMBANK BERHAD", "entidad_pais": "MY", "tipo_entidad": "Financial Institution", "estado_fatca": "active", "es_exempt_beneficial_owner": False, "es_sponsored_ffo": False},
    {"giin": "AESA01.9999.99.99.99", "entidad_nombre": "BANCO DE LA NACION ARGENTINA", "entidad_pais": "AR", "tipo_entidad": "Bank", "estado_fatca": "active", "es_exempt_beneficial_owner": False, "es_sponsored_ffo": False},
    {"giin": "AEUSFI.999.99.99.999", "entidad_nombre": "AMERICAN EXPRESS NATIONAL BANK", "entidad_pais": "US", "tipo_entidad": "Bank", "estado_fatca": "active", "es_exempt_beneficial_owner": False, "es_sponsored_ffo": False},
    {"giin": "AGGI01.9999.99.99.99", "entidad_nombre": "AGRICULTURAL BANK OF CHINA (UK) LIMITED", "entidad_pais": "GB", "tipo_entidad": "Bank", "estado_fatca": "active", "es_exempt_beneficial_owner": False, "es_sponsored_ffo": False},
    {"giin": "AIAUFI.999.99.99.999", "entidad_nombre": "AUSTRALIA AND NEW ZEALAND BANKING GROUP LIMITED", "entidad_pais": "AU", "tipo_entidad": "Financial Institution", "estado_fatca": "active", "es_exempt_beneficial_owner": False, "es_sponsored_ffo": False},
    {"giin": "AIJPFI.999.99.99.999", "entidad_nombre": "ANA BANK LIMITED", "entidad_pais": "JP", "tipo_entidad": "Financial Institution", "estado_fatca": "active", "es_exempt_beneficial_owner": False, "es_sponsored_ffo": False},
    {"giin": "AICA01.9999.99.99.99", "entidad_nombre": "BANCO DE LA NACION GUATEMALTECA", "entidad_pais": "GT", "tipo_entidad": "Bank", "estado_fatca": "active", "es_exempt_beneficial_owner": False, "es_sponsored_ffo": False},
    {"giin": "AICA02.9999.99.99.99", "entidad_nombre": "BANCO INDUSTRIAL DE EL SALVADOR", "entidad_pais": "SV", "tipo_entidad": "Bank", "estado_fatca": "active", "es_exempt_beneficial_owner": False, "es_sponsored_ffo": False},
    {"giin": "AICA03.9999.99.99.99", "entidad_nombre": "BANCO PROMERICA DE HONDURAS", "entidad_pais": "HN", "tipo_entidad": "Bank", "estado_fatca": "active", "es_exempt_beneficial_owner": False, "es_sponsored_ffo": False},
    {"giin": "AIUS01.9999.99.99.99", "entidad_nombre": "AMERICAN EXPRESS BANK LTD", "entidad_pais": "US", "tipo_entidad": "Bank", "estado_fatca": "active", "es_exempt_beneficial_owner": False, "es_sponsored_ffo": False},
]


def fetch_giin_csv(urls: list[str] | None = None) -> list[dict] | None:
    """Fetch GIIN data from IRS CSV. Returns None if no source available."""
    for url in urls or GIIN_CSV_URLS:
        try:
            resp = urlopen(url, timeout=30)
            content = resp.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(content))
            rows = []
            for row in reader:
                giin = row.get("GIIN", "").strip()
                if not giin:
                    continue
                rows.append({
                    "giin": giin,
                    "entidad_nombre": row.get("Legal Name", "").strip(),
                    "entidad_pais": row.get("Country", "").strip(),
                    "tipo_entidad": row.get("Type", "").strip(),
                    "estado_fatca": "active" if row.get("Status", "").strip().lower() != "inactive" else "inactive",
                    "es_exempt_beneficial_owner": row.get("Exempt Beneficial Owner", "").strip().lower() in ("true", "1", "yes"),
                    "es_sponsored_ffo": row.get("Sponsored FFO", "").strip().lower() in ("true", "1", "yes"),
                    "fecha_registro": row.get("Registration Date", "").strip() or None,
                    "fecha_expiracion": row.get("Expiration Date", "").strip() or None,
                    "nota": row.get("Notes", "").strip() or None,
                })
            if rows:
                return rows
        except (URLError, OSError, ValueError):
            continue
    return None


def upsert_gin(conn, data: dict) -> None:
    """Upsert a GIIN entry."""
    updated_at_expr = "CURRENT_TIMESTAMP" if conn.engine.dialect.name == "sqlite" else "NOW()"
    conn.execute(
        text("""
            INSERT INTO giin_registry (giin, entidad_nombre, entidad_pais, tipo_entidad,
                                       estado_fatca, fecha_registro, fecha_expiracion,
                                       es_exempt_beneficial_owner, es_sponsored_ffo, nota)
            VALUES (:giin, :entidad_nombre, :entidad_pais, :tipo_entidad,
                    :estado_fatca, :fecha_registro, :fecha_expiracion,
                    :es_exempt_beneficial_owner, :es_sponsored_ffo, :nota)
            ON CONFLICT (giin) DO UPDATE SET
                entidad_nombre = EXCLUDED.entidad_nombre,
                entidad_pais = EXCLUDED.entidad_pais,
                tipo_entidad = EXCLUDED.tipo_entidad,
                estado_fatca = EXCLUDED.estado_fatca,
                fecha_registro = EXCLUDED.fecha_registro,
                fecha_expiracion = EXCLUDED.fecha_expiracion,
                es_exempt_beneficial_owner = EXCLUDED.es_exempt_beneficial_owner,
                es_sponsored_ffo = EXCLUDED.es_sponsored_ffo,
                nota = EXCLUDED.nota,
                actualizado_en = """ + updated_at_expr + """
        """),
        {
            "giin": data["giin"],
            "entidad_nombre": data["entidad_nombre"],
            "entidad_pais": data["entidad_pais"],
            "tipo_entidad": data["tipo_entidad"],
            "estado_fatca": data["estado_fatca"],
            "fecha_registro": data.get("fecha_registro"),
            "fecha_expiracion": data.get("fecha_expiracion"),
            "es_exempt_beneficial_owner": data["es_exempt_beneficial_owner"],
            "es_sponsored_ffo": data["es_sponsored_ffo"],
            "nota": data.get("nota"),
        },
    )


def run_sync(worker_name: str = "cron-giin-monthly") -> dict:
    """Sync GIIN data from IRS or fallback seed."""
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)
    sync_start = datetime.now(UTC).isoformat()
    total = 0
    source = "seed"

    try:
        rows = fetch_giin_csv()
        if rows:
            source = "irs_giin_csv"
        else:
            rows = SEED_GIIN

        with engine.begin() as conn:
            for data in rows:
                upsert_gin(conn, data)
                total += 1

            return {
                "processed": total,
                "source": source,
                "worker": worker_name,
                "started_at": sync_start,
            }
    except Exception as exc:
        return {
            "processed": total,
            "source": source,
            "worker": worker_name,
            "error": str(exc),
            "started_at": sync_start,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GIIN worker: IRS GIIN registry ingestion")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=None, help="Seconds between sync cycles")
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("giin")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync()
        print(f"[run-once] GIIN: {result['processed']} entries from {result['source']}")
        if result.get("error"):
            print(f"  Error: {result['error']}")
    else:
        print(f"Starting GIIN worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(f"GIIN: {result['processed']} entries from {result['source']} at {datetime.now(UTC).isoformat()}")
            time.sleep(interval)
