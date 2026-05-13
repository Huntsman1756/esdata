"""Load ESMA authorised DLT market infrastructures from the official PDF."""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
from pypdf import PdfReader
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


logger = configure_logging("workers.esma_dlt")
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("ESMA_DLT_SYNC_INTERVAL_SECONDS", 604800)

DLT_PILOT_PAGE_URL = "https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/dlt-pilot-regime"
AUTHORISED_DLT_PDF_URL = (
    "https://www.esma.europa.eu/sites/default/files/2026-01/"
    "Authorised_DLT_Market_Infrastructures.pdf"
)


@dataclass(frozen=True)
class DltInfrastructure:
    operator: str
    infrastructure_name: str
    tipo: str
    pais: str
    autoridad_competente: str
    fecha_autorizacion: date
    source_date_label: str
    exemptions: tuple[str, ...]

    @property
    def nombre(self) -> str:
        return f"{self.operator} - {self.infrastructure_name}"


@dataclass(frozen=True)
class PdfDownload:
    source_url: str
    source_hash: str
    content: bytes


COMMON_CSDR_FULL_EXEMPTIONS = (
    "MiFID II Article 53(3) and Article 19(2) on access to an MTF",
    "CSDR Article 2(1) point 4 on dematerialised form",
    "CSDR Article 2(1) point 9 on transfer order",
    "CSDR Article 2(1) point 19 on participant",
    "CSDR Article 2(1) point 28 on securities account",
    "CSDR Article 3 on book-entry form",
    "CSDR Article 6 on measures to prevent settlement fails",
    "CSDR Article 7 on measures to address settlement fails",
    "CSDR Article 33 on requirements for participation",
    "CSDR Article 34 on transparency",
    "CSDR Article 35 on communication procedures with participants and other market infrastructures",
    "CSDR Article 37 on integrity of the issue",
    "CSDR Article 38 on account segregation",
    "CSDR Article 39 on settlement finality",
    "CSDR Article 40 on cash settlement",
    "CSDR Article 50 on standard link access",
    "CSDR Article 51 on customised link access",
    "CSDR Article 53 on access between a CSD and another market infrastructure",
)


AUTHORISED_DLT_INFRASTRUCTURES: tuple[DltInfrastructure, ...] = (
    DltInfrastructure(
        operator="CSD Prague (Centrální depozitář cenných papírů, a.s.)",
        infrastructure_name="DLT Register",
        tipo="DLT Settlement System",
        pais="CZE",
        autoridad_competente="Czech National Bank",
        fecha_autorizacion=date(2024, 10, 11),
        source_date_label="11 October 2024",
        exemptions=(
            "CSDR Article 6 on measures to prevent settlement fails",
            "CSDR Article 7 on measures to address settlement fails",
            "CSDR Article 35 on communication procedures with participants and other market infrastructures",
            "CSDR Article 38 on the segregation of assets",
            "CSDR Article 39 on settlement finality",
            "CSDR Article 40 on cash settlement",
        ),
    ),
    DltInfrastructure(
        operator="21X AG",
        infrastructure_name="21X DLT-TSS",
        tipo="DLT Trading & Settlement System",
        pais="DEU",
        autoridad_competente="Federal Financial Supervisory Authority (BaFin)",
        fecha_autorizacion=date(2024, 12, 3),
        source_date_label="3 December 2024",
        exemptions=COMMON_CSDR_FULL_EXEMPTIONS,
    ),
    DltInfrastructure(
        operator="360X AG",
        infrastructure_name="360X DLT MTF",
        tipo="DLT Multilateral Trading Facility",
        pais="DEU",
        autoridad_competente="Federal Financial Supervisory Authority (BaFin)",
        fecha_autorizacion=date(2025, 4, 29),
        source_date_label="29 April 2025",
        exemptions=(),
    ),
    DltInfrastructure(
        operator="UAB Axiology DLT",
        infrastructure_name="Axiology DLT TSS",
        tipo="DLT Trading & Settlement System",
        pais="LTU",
        autoridad_competente="Lietuvos bankas (Bank of Lithuania)",
        fecha_autorizacion=date(2025, 7, 9),
        source_date_label="9 July 2025",
        exemptions=(
            "CSDR Article 2(1) point 4 on dematerialised form",
            "CSDR Article 2(1) point 9 on transfer order",
            "CSDR Article 2(1) point 28 on securities account",
            "CSDR Article 3 on book-entry form",
            "CSDR Article 6 on measures to prevent settlement fails",
            "CSDR Article 7 on measures to address settlement fails",
            "CSDR Article 35 on communication procedures with participants and other market infrastructures",
            "CSDR Article 37 on integrity of the issue",
            "CSDR Article 38 on account segregation",
            "CSDR Article 39 on settlement finality",
            "CSDR Article 40 on cash settlement",
            "CSDR Article 50 on standard link access",
            "CSDR Article 51 on customised link access",
            "CSDR Article 53 on access between a CSD and another market infrastructure",
        ),
    ),
    DltInfrastructure(
        operator="LISE SA",
        infrastructure_name="LISE DLT TSS",
        tipo="DLT Trading & Settlement System",
        pais="FRA",
        autoridad_competente="Autorité de Contrôle Prudentiel et de Résolution (ACPR)",
        fecha_autorizacion=date(2025, 10, 13),
        source_date_label="13 October 2025",
        exemptions=(
            "MiFID II Article 53(3) and Article 19(2) on access to an MTF",
            "MiFIR Article 26 on transaction reporting",
            *COMMON_CSDR_FULL_EXEMPTIONS[1:],
        ),
    ),
    DltInfrastructure(
        operator="Securitize Europe Brokerage and Markets SV SA",
        infrastructure_name="Securitize Europe DLT TSS",
        tipo="DLT Trading & Settlement System",
        pais="ESP",
        autoridad_competente="Comisión Nacional del Mercado de Valores (CNMV)",
        fecha_autorizacion=date(2025, 11, 26),
        source_date_label="26 November 2025",
        exemptions=COMMON_CSDR_FULL_EXEMPTIONS,
    ),
)


def fetch_authorised_dlt_pdf(url: str = AUTHORISED_DLT_PDF_URL) -> PdfDownload:
    response = httpx.get(url, follow_redirects=True, timeout=60.0)
    response.raise_for_status()
    return PdfDownload(source_url=str(response.url), source_hash=hashlib.md5(response.content).hexdigest(), content=response.content)


def extract_pdf_text(pdf_content: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def validate_pdf_contains_official_rows(pdf_text: str, records: tuple[DltInfrastructure, ...]) -> None:
    normalized_pdf_text = _normalize_text(pdf_text)
    missing: list[str] = []
    for record in records:
        for expected in (
            record.operator,
            record.infrastructure_name,
            record.source_date_label,
            record.autoridad_competente.split(" (", 1)[0],
        ):
            if expected and _normalize_text(expected) not in normalized_pdf_text:
                missing.append(f"{record.operator}: {expected}")
    if missing:
        raise RuntimeError("Official ESMA DLT PDF no longer matches expected rows: " + "; ".join(missing))


def assert_dlt_tables(conn) -> None:
    assert_table_exists(
        conn,
        "esma_dlt_market_infrastructure",
        required_columns=(
            "nombre",
            "pais",
            "tipo",
            "autoridad_competente",
            "fecha_autorizacion",
            "url_esma",
            "source_hash",
            "capture_date",
            "verified",
            "completeness",
        ),
    )
    assert_table_exists(
        conn,
        "esma_dlt_exemption",
        required_columns=("infrastructure_id", "tipo_exencion", "articulo_referencia", "source_url", "source_hash", "capture_date"),
    )
    assert_table_exists(
        conn,
        "esma_reporting_document",
        required_columns=("tipo", "titulo", "referencia", "url_esma", "source_hash", "capture_date", "dominio"),
    )


def upsert_dlt_reporting_document(conn, download: PdfDownload) -> None:
    conn.execute(text("DELETE FROM esma_reporting_document WHERE url_esma = :url_esma"), {"url_esma": download.source_url})
    conn.execute(
        text(
            """
            INSERT INTO esma_reporting_document (
                tipo, titulo, referencia, url_esma, fecha_publicacion,
                source_hash, capture_date, dominio, verified,
                completeness, updated_at
            )
            VALUES (
                'REGISTER',
                'List of Authorised DLT Market Infrastructures',
                'DLT Pilot Regime Articles 8(11), 9(11) and 10(11)',
                :url_esma,
                NULL,
                :source_hash,
                :capture_date,
                'DLT',
                true,
                'completa',
                now()
            )
            """
        ),
        {"url_esma": download.source_url, "source_hash": download.source_hash, "capture_date": date.today().isoformat()},
    )


def upsert_dlt_infrastructures(conn, download: PdfDownload, records: tuple[DltInfrastructure, ...]) -> tuple[int, int]:
    infra_count = 0
    exemption_count = 0
    for record in records:
        infrastructure_id = conn.execute(
            text(
                """
                INSERT INTO esma_dlt_market_infrastructure (
                    nombre, pais, tipo, autoridad_competente,
                    fecha_autorizacion, url_esma, source_hash,
                    capture_date, verified, completeness, updated_at
                )
                VALUES (
                    :nombre, :pais, :tipo, :autoridad_competente,
                    :fecha_autorizacion, :url_esma, :source_hash,
                    :capture_date, true, 'completa', now()
                )
                ON CONFLICT (nombre, pais, tipo) DO UPDATE SET
                    autoridad_competente = EXCLUDED.autoridad_competente,
                    fecha_autorizacion = EXCLUDED.fecha_autorizacion,
                    url_esma = EXCLUDED.url_esma,
                    source_hash = EXCLUDED.source_hash,
                    capture_date = EXCLUDED.capture_date,
                    verified = EXCLUDED.verified,
                    completeness = EXCLUDED.completeness,
                    updated_at = now()
                RETURNING id
                """
            ),
            {
                "nombre": record.nombre,
                "pais": record.pais,
                "tipo": record.tipo,
                "autoridad_competente": record.autoridad_competente,
                "fecha_autorizacion": record.fecha_autorizacion,
                "url_esma": download.source_url,
                "source_hash": download.source_hash,
                "capture_date": date.today().isoformat(),
            },
        ).scalar_one()
        infra_count += 1
        conn.execute(
            text("DELETE FROM esma_dlt_exemption WHERE infrastructure_id = :infrastructure_id"),
            {"infrastructure_id": infrastructure_id},
        )
        for exemption in record.exemptions:
            conn.execute(
                text(
                    """
                    INSERT INTO esma_dlt_exemption (
                        infrastructure_id, tipo_exencion, articulo_referencia,
                        fecha_concesion, source_url, source_hash,
                        capture_date, updated_at
                    )
                    VALUES (
                        :infrastructure_id, :tipo_exencion, :articulo_referencia,
                        NULL, :source_url, :source_hash,
                        :capture_date, now()
                    )
                    """
                ),
                {
                    "infrastructure_id": infrastructure_id,
                    "tipo_exencion": exemption,
                    "articulo_referencia": exemption.split(" on ", 1)[0],
                    "source_url": download.source_url,
                    "source_hash": download.source_hash,
                    "capture_date": date.today().isoformat(),
                },
            )
            exemption_count += 1
    return infra_count, exemption_count


def run_once(worker_name: str = "worker-esma-dlt") -> dict:
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine, logger=logger)
    sync_start = datetime.now(UTC).isoformat()
    try:
        download = fetch_authorised_dlt_pdf()
        pdf_text = extract_pdf_text(download.content)
        validate_pdf_contains_official_rows(pdf_text, AUTHORISED_DLT_INFRASTRUCTURES)
        with engine.begin() as conn:
            assert_dlt_tables(conn)
            upsert_dlt_reporting_document(conn, download)
            infra_count, exemption_count = upsert_dlt_infrastructures(conn, download, AUTHORISED_DLT_INFRASTRUCTURES)
            _ensure_sync_log_table(conn)
            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=1,
                articulos=infra_count + exemption_count,
                started_at=sync_start,
            )
    except Exception as exc:
        if not handle_worker_failure(engine, "esma_dlt", "DLT", "sync_authorised_infrastructures", exc):
            logger.warning("ESMA DLT sync moved to dead-letter")
        try:
            with engine.begin() as conn:
                _ensure_sync_log_table(conn)
                log_sync(conn, worker_name, "error", error_msg=str(exc)[:500], started_at=sync_start)
        except Exception as log_exc:
            logger.warning("Failed to write ESMA DLT error log: %s", log_exc)
        raise
    return {
        "worker": worker_name,
        "infrastructures": infra_count,
        "exemptions": exemption_count,
        "source_hash": download.source_hash,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Load ESMA authorised DLT market infrastructures")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=None, help="Sync interval in seconds")
    args = parser.parse_args()

    init_sentry("esma_dlt")
    interval = args.interval or SYNC_INTERVAL_SECONDS
    if args.run_once:
        result = run_once()
        print(
            "[run-once] ESMA DLT: "
            f"infrastructures={result['infrastructures']} "
            f"exemptions={result['exemptions']} source_hash={result['source_hash']}"
        )
        return

    while True:
        try:
            result = run_once()
            logger.info("ESMA DLT sync complete: %s", result)
        except Exception:
            logger.exception("Error in ESMA DLT sync cycle")
        time.sleep(interval)


if __name__ == "__main__":
    main()
