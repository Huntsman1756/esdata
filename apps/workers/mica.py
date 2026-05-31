"""Ingest the official ESMA interim MiCA CASP CSV register."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import time
from datetime import UTC, date, datetime
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
MICA_REGISTER_CSV_FALLBACKS = {
    "white_papers_other": "https://www.esma.europa.eu/sites/default/files/2024-12/OTHER.csv",
    "art_issuers": "https://www.esma.europa.eu/sites/default/files/2024-12/ARTZZ.csv",
    "emt_issuers": "https://www.esma.europa.eu/sites/default/files/2024-12/EMTWP.csv",
    "non_compliant_entities": "https://www.esma.europa.eu/sites/default/files/2024-12/NCASP.csv",
}
MICA_REGISTER_LABELS = {
    "white_papers_other": "White papers for crypto-assets other than ART and EMT",
    "art_issuers": "Issuers of ART",
    "emt_issuers": "Issuers of EMT",
    "non_compliant_entities": "Non-compliant entities",
}
MICA_REGISTER_FILENAMES = {
    "white_papers_other": "OTHER.csv",
    "art_issuers": "ARTZZ.csv",
    "emt_issuers": "EMTWP.csv",
    "non_compliant_entities": "NCASP.csv",
}
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


def discover_esma_mica_register_csvs(page_url: str = ESMA_MICA_PAGE) -> dict[str, str]:
    """Discover official ESMA MiCA non-CASP register CSV links."""

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(page_url)
        response.raise_for_status()
    discovered: dict[str, str] = {}
    for register_type, filename in MICA_REGISTER_FILENAMES.items():
        match = re.search(rf'href="([^"]*{re.escape(filename)})"', response.text, re.IGNORECASE)
        if match:
            discovered[register_type] = urljoin(page_url, match.group(1))
    return {
        register_type: discovered.get(register_type, fallback_url)
        for register_type, fallback_url in MICA_REGISTER_CSV_FALLBACKS.items()
    }


def _csv_text_to_rows(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows = [dict(row) for row in reader]
    if not rows:
        raise RuntimeError("ESMA CASP CSV produced zero rows")
    return rows


def _csv_text_to_rows_allow_empty(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    return [dict(row) for row in reader]


def fetch_esma_casp(url: str | None = None) -> tuple[list[dict], str, str]:
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
    source_hash = hashlib.md5(response.content).hexdigest()
    source_url = str(response.url)
    logger.info("ESMA returned %d CASP rows from %s", len(rows), source_url)
    return rows, source_url, source_hash


def fetch_esma_mica_register(
    register_type: str,
    url: str | None = None,
) -> tuple[list[dict], str, str]:
    """Fetch one official ESMA MiCA non-CASP register CSV."""

    if register_type not in MICA_REGISTER_CSV_FALLBACKS:
        raise ValueError(f"Unsupported MiCA register type: {register_type}")
    source_url = url or discover_esma_mica_register_csvs()[register_type]
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(source_url)
        response.raise_for_status()
    rows = _csv_text_to_rows_allow_empty(response.content)
    source_hash = hashlib.md5(response.content).hexdigest()
    source_url = str(response.url)
    logger.info("ESMA returned %d %s rows from %s", len(rows), register_type, source_url)
    return rows, source_url, source_hash


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


def _first_present(raw: dict, *keys: str) -> str:
    for key in keys:
        value = (raw.get(key) or "").strip()
        if value:
            return value
    return ""


def _clean_raw_row(raw: dict) -> dict:
    return {
        str(key): value
        for key, value in raw.items()
        if key and str(key).strip() and value not in (None, "")
    }


def normalize_mica_register_row(register_type: str, raw: dict, index: int) -> dict:
    """Normalize a non-CASP ESMA MiCA register row without losing raw fields."""

    clean_raw = _clean_raw_row(raw)
    lei = _first_present(raw, "ae_lei")
    website = _first_present(raw, "wp_url", "ae_website")
    name = _first_present(raw, "ae_commercial_name", "ae_lei_name")
    entity_identifier = lei or website or name
    row_key_payload = {
        "register_type": register_type,
        "entity_identifier": entity_identifier,
        "home_member_state": _first_present(raw, "ae_homeMemberState"),
        "website": website,
        "index": index,
    }
    source_row_id = hashlib.sha256(
        json.dumps(row_key_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:32]
    status = "non_compliant" if register_type == "non_compliant_entities" else "active"
    if _first_present(raw, "ac_authorisationEndDate"):
        status = "revoked"

    return {
        "register_type": register_type,
        "register_label": MICA_REGISTER_LABELS[register_type],
        "source_row_id": source_row_id,
        "name": name,
        "entity_identifier": entity_identifier,
        "home_member_state": _first_present(raw, "ae_homeMemberState"),
        "status": status,
        "raw_data": clean_raw,
    }


def upsert_casp(db, casp: dict, source_url: str, source_hash: str) -> None:
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
        if "source_url" in casp_columns:
            update_parts.append("source_url = :source_url")
        if "source_hash" in casp_columns:
            update_parts.append("source_hash = :source_hash")
        if "capture_date" in casp_columns:
            update_parts.append("capture_date = :capture_date")
        if "verified" in casp_columns:
            update_parts.append("verified = true")
        if "completeness" in casp_columns:
            update_parts.append("completeness = 'completa'")
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
                "source_url": source_url,
                "source_hash": source_hash,
                "capture_date": date.today().isoformat(),
            },
        )
    else:
        insert_columns = [
            "name",
            "registration_number",
            "home_member_state",
            "passport_active",
            "services_offered",
            "status",
        ]
        insert_values = [
            ":name",
            ":registration_number",
            ":home_member_state",
            ":passport_active",
            ":services_offered",
            ":status",
        ]
        insert_params = {**casp, "services_offered": services_json}
        if "source_url" in casp_columns:
            insert_columns.append("source_url")
            insert_values.append(":source_url")
            insert_params["source_url"] = source_url
        if "source_hash" in casp_columns:
            insert_columns.append("source_hash")
            insert_values.append(":source_hash")
            insert_params["source_hash"] = source_hash
        if "capture_date" in casp_columns:
            insert_columns.append("capture_date")
            insert_values.append(":capture_date")
            insert_params["capture_date"] = date.today().isoformat()
        if "verified" in casp_columns:
            insert_columns.append("verified")
            insert_values.append("true")
        if "completeness" in casp_columns:
            insert_columns.append("completeness")
            insert_values.append("'completa'")
        db.execute(
            text(
                f"""
                INSERT INTO casp ({', '.join(insert_columns)})
                VALUES ({', '.join(insert_values)})
                """
            ),
            insert_params,
        )


def upsert_mica_register_entry(db, entry: dict, source_url: str, source_hash: str) -> None:
    """Insert or update a traced ESMA MiCA non-CASP register row."""

    raw_data_json = json.dumps(entry["raw_data"], ensure_ascii=False)
    raw_value_sql = "CAST(:raw_data AS JSONB)" if db.dialect.name == "postgresql" else ":raw_data"
    existing = db.execute(
        text(
            """
            SELECT id FROM mica_register_entry
            WHERE register_type = :register_type AND source_row_id = :source_row_id
            """
        ),
        {
            "register_type": entry["register_type"],
            "source_row_id": entry["source_row_id"],
        },
    ).mappings().first()

    params = {
        **entry,
        "raw_data": raw_data_json,
        "source_url": source_url,
        "source_hash": source_hash,
        "capture_date": date.today().isoformat(),
    }
    if existing:
        db.execute(
            text(
                f"""
                UPDATE mica_register_entry SET
                    register_label = :register_label,
                    name = :name,
                    entity_identifier = :entity_identifier,
                    home_member_state = :home_member_state,
                    status = :status,
                    raw_data = {raw_value_sql},
                    source_url = :source_url,
                    source_hash = :source_hash,
                    capture_date = :capture_date,
                    verified = true,
                    completeness = 'completa',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
            ),
            {**params, "id": existing["id"]},
        )
        return

    db.execute(
        text(
            f"""
            INSERT INTO mica_register_entry (
                register_type, register_label, source_row_id, name, entity_identifier,
                home_member_state, status, raw_data, source_url, source_hash,
                capture_date, verified, completeness
            )
            VALUES (
                :register_type, :register_label, :source_row_id, :name, :entity_identifier,
                :home_member_state, :status, {raw_value_sql}, :source_url, :source_hash,
                :capture_date, true, 'completa'
            )
            """
        ),
        params,
    )


def run_once() -> None:
    """Execute one ESMA MiCA sync."""

    logger.info("Starting MiCA sync from ESMA")
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine, logger=logger)
    sync_start = datetime.now(UTC).isoformat()
    synced = 0
    register_synced = 0

    try:
        casps_raw, source_url, source_hash = fetch_esma_casp()
        register_urls = discover_esma_mica_register_csvs()
        with engine.begin() as conn:
            for raw in casps_raw:
                normalized = normalize_casp(raw)
                if not normalized["name"] or not normalized["registration_number"]:
                    logger.warning("Skipping CASP entry with empty name: %s", raw)
                    continue
                upsert_casp(conn, normalized, source_url, source_hash)
                synced += 1
            for register_type, register_url in register_urls.items():
                rows, register_source_url, register_source_hash = fetch_esma_mica_register(
                    register_type,
                    register_url,
                )
                for index, raw in enumerate(rows):
                    normalized_entry = normalize_mica_register_row(register_type, raw, index)
                    if not normalized_entry["name"] and not normalized_entry["entity_identifier"]:
                        logger.warning("Skipping MiCA register entry with empty identity: %s", raw)
                        continue
                    upsert_mica_register_entry(
                        conn,
                        normalized_entry,
                        register_source_url,
                        register_source_hash,
                    )
                    register_synced += 1
            _ensure_sync_log_table(conn)
            log_sync(
                conn,
                "cron-mica-weekly",
                "ok",
                documentos_processed=len(casps_raw) + register_synced,
                documentos_upserted=synced + register_synced,
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

    logger.info(
        "MiCA sync complete: %d CASPs and %d non-CASP register rows synced from ESMA",
        synced,
        register_synced,
    )


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
