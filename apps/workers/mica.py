"""Ingest the official ESMA interim MiCA CASP CSV register."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import httpx
from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parent))

from boe import _ensure_sync_log_table, log_sync
from runtime import (
    configure_logging,
    ensure_database_connection,
    get_database_url,
    get_interval_seconds,
    handle_worker_failure,
    init_sentry,
)

logger = configure_logging("workers.mica")

ESMA_MICA_PAGE = "https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/markets-crypto-assets-regulation-mica"
ESMA_CASP_CSV_FALLBACK = "https://www.esma.europa.eu/sites/default/files/2024-12/CASPS.csv"
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("MICA_SYNC_INTERVAL_SECONDS", 604800)


def discover_esma_casp_csv(page_url: str = ESMA_MICA_PAGE) -> str:
    """Discover the current CASP CSV from ESMA's official MiCA page."""

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(page_url)
        response.raise_for_status()
    match = re.search(r'href="([^"]*CASPS\.csv)"', response.text, re.IGNORECASE)
    if not match:
        raise RuntimeError("No CASPS.csv link found on ESMA MiCA page")
    return urljoin(page_url, match.group(1))


def _csv_text_to_rows(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows = [dict(row) for row in reader]
    if not rows:
        raise RuntimeError("ESMA CASP CSV produced zero rows")
    return rows


def fetch_esma_casp(url: str | None = None) -> tuple[list[dict], str]:
    """Fetch CASP rows from the official ESMA interim MiCA CSV."""

    source_url = url or discover_esma_casp_csv()
    try:
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            response = client.get(source_url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        if url:
            raise
        logger.warning("ESMA CASP discovery URL failed, trying fallback CSV: %s", exc)
        source_url = ESMA_CASP_CSV_FALLBACK
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            response = client.get(source_url)
            response.raise_for_status()

    rows = _csv_text_to_rows(response.content)
    logger.info("ESMA returned %d CASP rows from %s", len(rows), source_url)
    return rows, source_url


def normalize_casp(raw: dict) -> dict:
    """Normalize an ESMA CASP CSV row to the local DB schema."""

    services_text = (raw.get("ac_serviceCode") or raw.get("services") or "").strip()
    services = [part.strip() for part in services_text.split("|") if part.strip()]
    commercial_name = (raw.get("ae_commercial_name") or "").strip()
    lei_name = (raw.get("ae_lei_name") or raw.get("name") or "").strip()
    lei = (raw.get("ae_lei") or raw.get("registration_number") or "").strip()
    state = (raw.get("ae_homeMemberState") or raw.get("home_member_state") or "").strip()
    passport_countries = (raw.get("ac_serviceCode_cou") or "").strip()
    end_date = (raw.get("ac_authorisationEndDate") or "").strip()

    return {
        "name": commercial_name or lei_name,
        "registration_number": lei or f"{state}:{commercial_name or lei_name}",
        "home_member_state": state,
        "passport_active": bool(passport_countries),
        "services_offered": services,
        "status": "revoked" if end_date else "active",
    }


def upsert_casp(db, casp: dict) -> None:
    """Insertar o actualizar un CASP en la BD."""
    services_json = json.dumps(casp["services_offered"])
    casp_columns = {column["name"] for column in inspect(db).get_columns("casp")}
    existing = db.execute(
        text(
            "SELECT id FROM casp WHERE registration_number = :reg AND home_member_state = :state"
        ),
        {
            "reg": casp["registration_number"],
            "state": casp["home_member_state"],
        },
    ).mappings().first()

    if existing:
        update_parts = [
            "name = :name",
            "passport_active = :passport_active",
            "services_offered = :services_offered",
            "status = :status",
        ]
        if "updated_at" in casp_columns:
            update_parts.append("updated_at = CURRENT_TIMESTAMP")
        db.execute(
            text(
                f"UPDATE casp SET {', '.join(update_parts)} WHERE id = :id"
            ),
            {
                "id": existing["id"],
                "name": casp["name"],
                "passport_active": casp["passport_active"],
                "services_offered": services_json,
                "status": casp["status"],
            },
        )
    else:
        db.execute(
            text(
                """
                INSERT INTO casp (name, registration_number, home_member_state,
                                  passport_active, services_offered, status)
                VALUES (:name, :registration_number, :home_member_state,
                        :passport_active, :services_offered, :status)
                """
            ),
            {**casp, "services_offered": services_json},
        )


def run_once() -> None:
    """Execute one ESMA CASP sync."""

    logger.info("Starting MiCA CASP sync from ESMA")
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine, logger=logger)
    sync_start = datetime.now(UTC).isoformat()
    synced = 0

    try:
        casps_raw, source_url = fetch_esma_casp()
        with engine.begin() as conn:
            for raw in casps_raw:
                normalized = normalize_casp(raw)
                if not normalized["name"] or not normalized["registration_number"]:
                    logger.warning("Skipping CASP entry with empty name: %s", raw)
                    continue
                upsert_casp(conn, normalized)
                synced += 1
            _ensure_sync_log_table(conn)
            log_sync(
                conn,
                "cron-mica-weekly",
                "ok",
                documentos_processed=len(casps_raw),
                documentos_upserted=synced,
                started_at=sync_start,
            )
    except Exception as exc:
        if not handle_worker_failure(engine, "mica", "ESMA_CASP", "sync_registry", exc):
            logger.warning("MiCA CASP sync moved to dead-letter")
        try:
            with engine.begin() as conn:
                _ensure_sync_log_table(conn)
                log_sync(
                    conn,
                    "cron-mica-weekly",
                    "error",
                    error_msg=str(exc)[:500],
                    started_at=sync_start,
                )
        except Exception as log_exc:
            logger.warning("Failed to write MiCA sync error log: %s", log_exc)
        raise

    logger.info("MiCA CASP sync complete: %d CASPs synced from %s", synced, source_url)


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker MiCA CASP sync from ESMA")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=None, help="Sync interval in seconds")
    args = parser.parse_args()

    init_sentry("mica")
    interval = args.interval or SYNC_INTERVAL_SECONDS

    if args.run_once:
        run_once()
        return

    logger.info("MiCA CASP worker starting, interval=%ds", interval)
    while True:
        try:
            run_once()
        except Exception:
            logger.exception("Error in MiCA CASP sync cycle")
        logger.info("Next sync in %ds", interval)
        time.sleep(interval)


if __name__ == "__main__":
    main()
