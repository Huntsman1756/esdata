"""Load ESMA FIRDS file metadata without downloading instrument payloads."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent))

from boe import _ensure_sync_log_table, log_sync
from runtime import (
    assert_table_exists,
    configure_logging,
    ensure_database_connection,
    get_database_url,
    get_interval_seconds,
    handle_worker_failure,
    init_sentry,
)

logger = configure_logging("workers.esma_firds")
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("ESMA_FIRDS_SYNC_INTERVAL_SECONDS", 86400)

FIRDS_SOLR_URL = "https://registers.esma.europa.eu/solr/esma_registers_firds_files/select"
FIRDS_REGISTER_URL = "https://registers.esma.europa.eu/publication/searchRegister?core=esma_registers_firds"


@dataclass(frozen=True)
class FirdsFile:
    tipo: str
    fecha: date
    url_esma: str
    file_name: str
    checksum: str | None
    size_bytes: int | None = None


def _to_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def search_dltins_files(days: int = 7) -> list[FirdsFile]:
    end = date.today()
    start = end - timedelta(days=days)
    response = httpx.get(
        FIRDS_SOLR_URL,
        params={
            "q": "*",
            "fq": [
                f"publication_date:[{start.isoformat()}T00:00:00Z TO {end.isoformat()}T23:59:59Z]",
                "file_type:DLTINS",
            ],
            "wt": "json",
            "start": "0",
            "rows": "100",
        },
        timeout=60.0,
    )
    response.raise_for_status()
    docs = response.json().get("response", {}).get("docs", [])
    files: list[FirdsFile] = []
    for doc in docs:
        publication_date = _to_date(doc.get("publication_date"))
        if not publication_date or not doc.get("download_link"):
            continue
        files.append(
            FirdsFile(
                tipo=doc.get("file_type", "DLTINS"),
                fecha=publication_date,
                url_esma=doc["download_link"],
                file_name=doc.get("file_name", Path(doc["download_link"]).name),
                checksum=doc.get("checksum"),
            )
        )
    return sorted(files, key=lambda item: (item.fecha, item.file_name), reverse=True)


def assert_firds_tables(conn) -> None:
    assert_table_exists(
        conn,
        "esma_firds_file",
        required_columns=("tipo", "fecha", "url_esma", "source_hash", "downloaded", "processed", "capture_date"),
    )


def upsert_firds_files(conn, files: list[FirdsFile]) -> dict[str, int]:
    ids: dict[str, int] = {}
    for firds_file in files:
        file_id = conn.execute(
            text(
                """
                INSERT INTO esma_firds_file (
                    tipo, fecha, url_esma, size_bytes, source_hash,
                    downloaded, processed, capture_date, verified,
                    completeness, updated_at
                )
                VALUES (
                    :tipo, :fecha, :url_esma, :size_bytes, :source_hash,
                    false, false, :capture_date, false,
                    'parcial', now()
                )
                ON CONFLICT (tipo, fecha, url_esma) DO UPDATE SET
                    size_bytes = COALESCE(EXCLUDED.size_bytes, esma_firds_file.size_bytes),
                    source_hash = EXCLUDED.source_hash,
                    capture_date = EXCLUDED.capture_date,
                    completeness = EXCLUDED.completeness,
                    updated_at = now()
                RETURNING id
                """
            ),
            {
                "tipo": firds_file.tipo,
                "fecha": firds_file.fecha,
                "url_esma": firds_file.url_esma,
                "size_bytes": firds_file.size_bytes,
                "source_hash": firds_file.checksum,
                "capture_date": date.today().isoformat(),
            },
        ).scalar_one()
        ids[firds_file.url_esma] = file_id
    return ids


def run_once(worker_name: str = "worker-esma-firds") -> dict:
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine, logger=logger)
    sync_start = datetime.now(UTC).isoformat()
    try:
        files = search_dltins_files(days=7)
        if not files:
            raise RuntimeError("No recent ESMA DLTINS files found")
        with engine.begin() as conn:
            assert_firds_tables(conn)
            upsert_firds_files(conn, files)
            _ensure_sync_log_table(conn)
            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=len(files),
                articulos=0,
                started_at=sync_start,
            )
    except Exception as exc:
        if not handle_worker_failure(engine, "esma_firds", "DLTINS", "sync_firds", exc):
            logger.warning("ESMA FIRDS sync moved to dead-letter")
        try:
            with engine.begin() as conn:
                _ensure_sync_log_table(conn)
                log_sync(conn, worker_name, "error", error_msg=str(exc)[:500], started_at=sync_start)
        except Exception as log_exc:
            logger.warning("Failed to write ESMA FIRDS error log: %s", log_exc)
        raise
    return {"worker": worker_name, "files": len(files), "instruments": 0, "mode": "metadata_only"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Load ESMA FIRDS DLTINS file metadata only")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=None, help="Sync interval in seconds")
    args = parser.parse_args()

    init_sentry("esma_firds")
    interval = args.interval or SYNC_INTERVAL_SECONDS
    if args.run_once:
        result = run_once()
        print(
            "[run-once] ESMA FIRDS: "
            f"files={result['files']} instruments={result['instruments']} mode={result['mode']}"
        )
        return

    while True:
        try:
            result = run_once()
            logger.info("ESMA FIRDS sync complete: %s", result)
        except Exception:
            logger.exception("Error in ESMA FIRDS sync cycle")
        time.sleep(interval)


if __name__ == "__main__":
    main()
