#!/usr/bin/env python
"""Ingest official IRS FATCA FFI/GIIN data.

The GIIN registry must be populated only from official IRS sources. Historical
seed fallback data is intentionally forbidden because a stale or synthetic GIIN
answer is unsafe in compliance workflows.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import time
import zipfile
from datetime import UTC, datetime
from urllib.error import URLError
from urllib.request import urlopen

from boe import _ensure_sync_log_table, log_sync
from runtime import (
    configure_logging,
    ensure_database_connection,
    get_database_url,
    get_interval_seconds,
    handle_worker_failure,
)
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 2592000)
logger = configure_logging("worker-giin")

IRS_FATCA_DOWNLOADS_URL = "https://www.irs.gov/downloads/fatca"
IRS_FATCA_BASE_URL = "https://www.irs.gov"
IRS_FFI_CSV_ZIP_RE = re.compile(
    r'href="([^"]*fatca-foreign-financial-institution[^"]*ffi[^"]*csv\.zip)"',
    re.IGNORECASE,
)

# Legacy direct CSV URLs are kept as official fallback only; no seed fallback.
GIIN_CSV_URLS = [
    "https://www.irs.gov/pub/irs-fatca/english_giin.csv",
    "https://www.irs.gov/whiteservices/foreignfundsandfinancialinstitutions/english_giin.csv",
]


def discover_latest_irs_csv_zip(downloads_url: str = IRS_FATCA_DOWNLOADS_URL) -> str:
    """Return the latest IRS FATCA FFI CSV ZIP link from the official listing."""

    html = urlopen(downloads_url, timeout=60).read().decode("utf-8", errors="replace")
    match = IRS_FFI_CSV_ZIP_RE.search(html)
    if not match:
        raise RuntimeError("No IRS FATCA FFI CSV ZIP link found on downloads page")
    href = match.group(1)
    if href.startswith(("http://", "https://")):
        return href
    return IRS_FATCA_BASE_URL + href


def _row_value(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _parse_giin_csv_text(content: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content))
    rows: list[dict] = []
    for row in reader:
        giin = _row_value(row, "GIIN")
        entity_name = _row_value(row, "FINm", "Legal Name", "Financial Institution Name")
        country = _row_value(row, "CountryNm", "Country", "Country/Jurisdiction")
        if not giin or not entity_name or not country:
            continue
        status = _row_value(row, "Status").lower()
        rows.append(
            {
                "giin": giin,
                "entidad_nombre": entity_name,
                "entidad_pais": country,
                "tipo_entidad": _row_value(row, "Type") or "FFI",
                "estado_fatca": "inactivo" if status == "inactive" else "activo",
                "es_exempt_beneficial_owner": _row_value(
                    row, "Exempt Beneficial Owner"
                ).lower()
                in ("true", "1", "yes"),
                "es_sponsored_ffo": _row_value(row, "Sponsored FFO").lower()
                in ("true", "1", "yes"),
                "fecha_registro": _row_value(row, "Registration Date") or None,
                "fecha_expiracion": _row_value(row, "Expiration Date") or None,
                "nota": _row_value(row, "Notes") or None,
            }
        )
    return rows


def fetch_giin_zip(url: str | None = None) -> tuple[list[dict], str]:
    """Fetch and parse the current official IRS FATCA FFI CSV ZIP."""

    source_url = url or discover_latest_irs_csv_zip()
    archive = urlopen(source_url, timeout=180).read()
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        csv_names = [name for name in zipped.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            raise RuntimeError(f"No CSV file found inside IRS FATCA ZIP: {source_url}")
        with zipped.open(csv_names[0]) as handle:
            content = handle.read().decode("utf-8-sig")
    rows = _parse_giin_csv_text(content)
    if not rows:
        raise RuntimeError(f"IRS FATCA CSV produced zero GIIN rows: {source_url}")
    return rows, source_url


def fetch_giin_csv(urls: list[str] | None = None) -> list[dict] | None:
    """Fetch legacy direct IRS CSV URLs. Returns None if unavailable."""

    for url in urls or GIIN_CSV_URLS:
        try:
            resp = urlopen(url, timeout=30)
            rows = _parse_giin_csv_text(resp.read().decode("utf-8-sig"))
            if rows:
                return rows
        except (URLError, OSError, ValueError):
            continue
    return None


def upsert_gin(conn, data: dict) -> None:
    """Upsert a GIIN entry."""

    updated_at_expr = "CURRENT_TIMESTAMP" if conn.engine.dialect.name == "sqlite" else "NOW()"
    conn.execute(
        text(
            """
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
                actualizado_en = """
            + updated_at_expr
            + """
        """
        ),
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
    """Sync GIIN data from official IRS sources only."""

    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine, logger=logger)
    sync_start = datetime.now(UTC).isoformat()
    total = 0
    source = "irs_fatca_ffi_csv_zip"

    try:
        try:
            rows, source_url = fetch_giin_zip()
        except Exception as zip_exc:
            logger.warning("IRS FATCA ZIP fetch failed, trying legacy CSV URLs: %s", zip_exc)
            rows = fetch_giin_csv()
            if not rows:
                raise RuntimeError(f"No official IRS GIIN source available: {zip_exc}") from zip_exc
            source = "irs_legacy_giin_csv"
            source_url = ";".join(GIIN_CSV_URLS)

        with engine.begin() as conn:
            for data in rows:
                upsert_gin(conn, data)
                total += 1
            _ensure_sync_log_table(conn)
            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=len(rows),
                documentos_upserted=total,
                started_at=sync_start,
            )

        return {
            "processed": total,
            "source": source,
            "source_url": source_url,
            "worker": worker_name,
            "started_at": sync_start,
        }
    except Exception as exc:
        entity_id = "giin"
        if not handle_worker_failure(engine, "giin", entity_id, "sync_entity", exc):
            logger.warning("Entity giin moved to dead-letter")
        try:
            with engine.begin() as conn:
                _ensure_sync_log_table(conn)
                log_sync(
                    conn,
                    worker_name,
                    "error",
                    error_msg=str(exc)[:500],
                    started_at=sync_start,
                )
        except Exception as log_exc:
            logger.warning("Failed to write GIIN sync error log: %s", log_exc)
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
        if result.get("source_url"):
            print(f"  Source: {result['source_url']}")
        if result.get("error"):
            print(f"  Error: {result['error']}")
    else:
        print(f"Starting GIIN worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"GIIN: {result['processed']} entries from {result['source']} "
                f"at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
