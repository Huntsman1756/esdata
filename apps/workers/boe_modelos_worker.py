"""Worker BOE -> casillas  orchestrator.


Descarga Ordenes HAC del BOE, parsea metadata/casillas/tablas/PDF,
y almacena los resultados en la base de datos via modelos_support.


Pattern de ejecucin:
- Ciclo continuo con intervalo configurable (default 86400s).
- Advisory lock para evitar ejecuciones concurrentes.
- Heartbeat para monitoreo.
- DLQ para fallos persistentes.
- Log de resultados en sync_log.


Ejemplo de uso::


    from boe_modelos_worker import run_sync


    run_sync(run_once=True)

"""


from __future__ import annotations



import logging

import os

import sys

from dataclasses import dataclass, field

from datetime import UTC, datetime



import httpx

from boe_modelos import (
    parse_anexo_casilla_references,

    parse_boe_table_fields,

    parse_orden_hac_metadata,

)

from boe_pdf_parser import download_and_parse_boe_pdf

from modelos_support import upsert_casillas, upsert_instructions

from runtime import (
    ensure_database_connection,

    handle_worker_failure,

    sleep_with_heartbeat,

    touch_heartbeat,

)

from sqlalchemy import create_engine, text




logger = logging.getLogger(__name__)




logging.basicConfig(

    level=logging.INFO,

    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",

    stream=sys.stdout,

)


BOE_MODELOS_API_BASE = os.getenv(

    "BOE_MODELOS_API_BASE",

    "https://www.boe.es/datosabiertos/api/legislacion-consolidada",

)

DATABASE_URL = os.getenv(

    "DATABASE_URL",

    "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata",

)

SYNC_INTERVAL_SECONDS = int(os.getenv("BOE_MODELOS_SYNC_INTERVAL", "86400"))

BOE_HAC_NORMAS = [

    "LIVA",

    "LIRPF",

    "LIS",

    "LGT",

    "ITPAJD",

    "IRNR",

    "IIEE",

    "HL",

    "DAC6",

    "DAC6RD",

    "DAC6EU",

]

BOE_MODELOS_LOCK_KEY = 88420033


@dataclass
class ModeloSyncResult:
    syncs_attempted: int = 0
    syncs_success: int = 0
    syncs_error: int = 0
    casillas_upserted: int = 0
    instrucciones_upserted: int = 0


@dataclass
class OrdenSyncResult:
    success: bool
    boe_id: str
    modelo_codigos: list[str] = field(default_factory=list)
    casillas_parsed: list[dict] = field(default_factory=list)
    pdf_casillas: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    campana_id: int | None = None


def _clean_html_text(value: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", value).strip()


def _normalize_casilla_code(codigo: str) -> str:
    return codigo.zfill(4) if codigo.isdigit() else codigo


def _ensure_sync_log_table(conn) -> None:
    """Ensure sync_log table exists. Uses session-level operations only."""
    try:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id SERIAL PRIMARY KEY,
                worker VARCHAR(100) NOT NULL,
                started_at TIMESTAMP NOT NULL,
                finished_at TIMESTAMP,
                status VARCHAR(50),
                bloques_processed INTEGER DEFAULT 0,
                articulos_upserted INTEGER DEFAULT 0,
                filas_procesadas INTEGER DEFAULT 0,
                errores INTEGER DEFAULT 0,
                documentos_procesados INTEGER DEFAULT 0,
                documentos_insertados INTEGER DEFAULT 0,
                doctrina_enlaces INTEGER DEFAULT 0,
                error_msg TEXT
            )
        """))
    except Exception:
        pass


def _log_sync(conn, worker: str, status: str, stats: dict, error_msg: str = None) -> None:
    """Log a sync entry matching the actual sync_log table schema."""
    try:
        conn.execute(text("""
            INSERT INTO sync_log (
                worker, started_at, finished_at, status,
                bloques_processed, articulos_upserted,
                documentos_processed, documentos_upserted,
                doctrina_links_created, rows_processed,
                errors, error_msg
            ) VALUES (
                :worker, :started_at, :finished_at, :status,
                :bloques_processed, :articulos_upserted,
                :documentos_processed, :documentos_upserted,
                :doctrina_links_created, :rows_processed,
                :errors, :error_msg
            )
        """), {
            "worker": worker,
            "started_at": stats.get('started_at', datetime.now(UTC)),
            "finished_at": datetime.now(UTC),
            "status": status,
            "bloques_processed": stats.get("bloques_processed", 0),
            "articulos_upserted": stats.get("articulos_upserted", 0),
            "documentos_processed": stats.get("documentos_procesados", 0),
            "documentos_upserted": stats.get("documentos_insertados", 0),
            "doctrina_links_created": stats.get("doctrina_enlaces", 0),
            "rows_processed": stats.get("filas_procesadas", 0),
            "errors": stats.get("errores", 0),
            "error_msg": error_msg,
        })
    except Exception as e:
        logger.error("Failed to write sync_log: %s", e)


@dataclass
class _OrdenHAC:
    orden: str
    boe_id: str
    modelo_codigos: list
    url_eli: str | None = None
    titulo: str = ""


def _fetch_boe_xml(boe_id: str) -> str:
    with httpx.Client(timeout=30.0) as client:
        return _get_hac_xml_text(client, boe_id)


def _pdf_url_for_boe_id(boe_id: str) -> str:
    import re

    match = re.fullmatch(r"BOE-A-(\d{4})-(\d+)", boe_id)
    if not match:
        return f"https://www.boe.es/diario_boe/txt.php?id={boe_id}"
    year, number = match.groups()
    return f"https://www.boe.es/boe/dias/{year}/01/01/pdfs/{boe_id}.pdf"


def _pdf_url_from_xml(xml_text: str, boe_id: str) -> str:
    from xml.etree import ElementTree as ET

    try:
        root = ET.fromstring(xml_text)
        url_pdf = root.findtext("./metadatos/url_pdf")
        if url_pdf:
            return f"https://www.boe.es{url_pdf}" if url_pdf.startswith("/") else url_pdf
    except Exception:
        pass
    return _pdf_url_for_boe_id(boe_id)


def _campaign_from_boe_id(boe_id: str) -> str:
    import re

    match = re.search(r"BOE-A-(\d{4})-", boe_id)
    return match.group(1) if match else str(datetime.now(UTC).year)


def _casillas_for_upsert(casillas: list[dict]) -> list[dict]:
    normalized = []
    for idx, casilla in enumerate(casillas, start=1):
        descripcion = casilla.get("descripcion") or casilla.get("etiqueta") or ""
        normalized.append(
            {
                "codigo": _normalize_casilla_code(str(casilla["codigo"])),
                "etiqueta": str(casilla.get("etiqueta") or descripcion)[:100] or "Casilla BOE",
                "descripcion": descripcion or None,
                "orden": casilla.get("orden", idx),
            }
        )
    return normalized


def _ensure_model_campaign(conn, modelo_codigo: str, campana: str) -> int:
    row = conn.execute(
        text("SELECT id FROM aeat_modelo WHERE codigo = :codigo"),
        {"codigo": modelo_codigo},
    ).mappings().first()
    if row:
        modelo_id = row["id"]
    else:
        row = conn.execute(
            text(
                """
                INSERT INTO aeat_modelo (codigo, nombre, activo)
                VALUES (:codigo, :nombre, true)
                ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre
                RETURNING id
                """
            ),
            {"codigo": modelo_codigo, "nombre": f"Modelo {modelo_codigo}"},
        ).mappings().first()
        modelo_id = row["id"]

    row = conn.execute(
        text(
            """
            INSERT INTO modelo_campana (modelo_id, campana, activo)
            VALUES (:modelo_id, :campana, false)
            ON CONFLICT (modelo_id, campana) DO UPDATE SET updated_at = now()
            RETURNING id
            """
        ),
        {"modelo_id": modelo_id, "campana": campana},
    ).mappings().first()
    return row["id"]


def sync_orden_hac_to_db(boe_id: str, db_url: str | None = None) -> OrdenSyncResult:
    result = OrdenSyncResult(success=False, boe_id=boe_id)
    try:
        xml_text = _fetch_boe_xml(boe_id)
        metadata = parse_orden_hac_metadata(xml_text)
        modelo_codigos = metadata.get("modelo_codigos") or []
        result.modelo_codigos = modelo_codigos

        all_casillas = []
        for modelo_codigo in modelo_codigos:
            for casilla in parse_anexo_casilla_references(xml_text, modelo_codigo):
                all_casillas.append(
                    {
                        "codigo": casilla["codigo"],
                        "etiqueta": casilla["descripcion"][:100],
                        "descripcion": casilla["descripcion"],
                    }
                )

        for field in parse_boe_table_fields(xml_text):
            all_casillas.append(
                {
                    "codigo": field["codigo"],
                    "etiqueta": field["descripcion"][:100],
                    "descripcion": field["descripcion"],
                }
            )

        pdf_result = download_and_parse_boe_pdf(_pdf_url_from_xml(xml_text, boe_id))
        if pdf_result.get("success"):
            result.pdf_casillas = pdf_result.get("casillas", [])

        result.casillas_parsed = all_casillas
        engine = create_engine(db_url or DATABASE_URL)
        campana = _campaign_from_boe_id(boe_id)
        with engine.begin() as conn:
            for modelo_codigo in modelo_codigos:
                campana_id = _ensure_model_campaign(conn, modelo_codigo, campana)
                result.campana_id = campana_id
                upsert_casillas(conn, campana_id, _casillas_for_upsert(all_casillas))
                if result.pdf_casillas:
                    upsert_casillas(conn, campana_id, _casillas_for_upsert(result.pdf_casillas))

        result.success = True
    except httpx.HTTPStatusError as exc:
        result.errors.append(f"{exc.response.status_code} {exc}")
    except Exception as exc:  # noqa: BLE001
        result.errors.append(str(exc))
    return result


def _fetch_hac_normas_xml(client: httpx.Client, normas: list[str]) -> list[_OrdenHAC]:
    """Fetch all HAC order XMLs and parse metadata. Returns list of parsed HAC orders."""
    results = []
    for codigo in normas:
        boe_id_match = None
        known_boe_ids = {
            "LIVA": "BOE-A-1992-28740",
            "LIRPF": "BOE-A-2006-20764",
            "LIS": "BOE-A-2014-12328",
            "LGT": "BOE-A-2003-23186",
            "ITPAJD": "BOE-A-1993-253",
        }
        if codigo in known_boe_ids:
            boe_id_match = known_boe_ids[codigo]

        if not boe_id_match:
            logger.info("SKIP %s: no BOE ID mapping", codigo)
            continue

        try:
            response = client.get(
                f"https://www.boe.es/diario_boe/xml.php?id={boe_id_match}",
                timeout=30.0,
            )
            response.raise_for_status()
            xml_text = response.text

            metadata = parse_orden_hac_metadata(xml_text)
            # The boe_id may not be in the XML metadata, use the known one
            if not metadata["boe_id"]:
                metadata["boe_id"] = boe_id_match
            results.append(_OrdenHAC(
                orden=metadata["orden"],
                boe_id=metadata["boe_id"],
                modelo_codigos=metadata["modelo_codigos"],
                url_eli=metadata.get("url_eli"),
                titulo=metadata["titulo"],
            ))
        except Exception as e:
            logger.error("Failed to fetch XML for %s: %s", codigo, e)
    return results


def find_orden_boe_ids(client: httpx.Client | None = None) -> list[str]:
    if client is not None:
        return [order.boe_id for order in _fetch_hac_normas_xml(client, BOE_HAC_NORMAS)]
    with httpx.Client(timeout=30.0) as local_client:
        return [order.boe_id for order in _fetch_hac_normas_xml(local_client, BOE_HAC_NORMAS)]


def _get_hac_xml_text(client: httpx.Client, boe_id: str) -> str:
    """Get XML text for a BOE ID."""
    response = client.get(
        f"https://www.boe.es/diario_boe/xml.php?id={boe_id}",
        timeout=30.0,
    )
    response.raise_for_status()
    return response.text


def _try_acquire_sync_lock(conn) -> bool:
    try:
        row = conn.execute(
            text("SELECT pg_try_advisory_xact_lock(:lock_key)"),
            {"lock_key": BOE_MODELOS_LOCK_KEY},
        ).fetchone()
        return bool(row[0]) if row else False
    except Exception as e:
        logger.warning("Failed to acquire sync lock: %s", e)
        return False


def run_sync(engine, run_once: bool = False):
    logger.info("Starting BOE->models worker...")

    total_synced = 0
    total_errors = 0

    while True:
        touch_heartbeat()
        started_at = datetime.now(UTC)

        lock_acquired = False
        with engine.begin() as conn:
            lock_acquired = _try_acquire_sync_lock(conn)

        if not lock_acquired:
            logger.warning("Another BOE models sync already in progress, skipping")
            with engine.begin() as conn:
                _log_sync(conn, "worker-boe-modelos", "skipped", {
                    "started_at": started_at,
                    "bloques_processed": 0,
                    "articulos_upserted": 0,
                    "filas_procesadas": 0,
                    "errores": 0,
                    "documentos_procesados": 0,
                    "documentos_insertados": 0,
                    "doctrina_enlaces": 0,
                })
            if run_once:
                break
            logger.info("Next sync in %ds", SYNC_INTERVAL_SECONDS)
            sleep_with_heartbeat(SYNC_INTERVAL_SECONDS)
            continue

        with httpx.Client(timeout=30.0) as client:
            try:
                boe_ids = find_orden_boe_ids(client)
                logger.info("Found %d HAC orders to process", len(boe_ids))

                for boe_id in boe_ids:
                    touch_heartbeat()
                    try:
                        db_url = engine.url.render_as_string(hide_password=False)
                        order_result = sync_orden_hac_to_db(boe_id, db_url)
                        if not order_result.success:
                            raise RuntimeError("; ".join(order_result.errors) or "unknown sync error")

                        with engine.begin() as conn:
                            _log_sync(conn, "worker-boe-modelos", "ok", {
                                "started_at": started_at,
                                "bloques_processed": 1,
                                "articulos_upserted": len(order_result.casillas_parsed) + len(order_result.pdf_casillas),
                                "filas_procesadas": 1,
                                "errores": 0,
                                "documentos_procesados": 1,
                                "documentos_insertados": 0,
                                "doctrina_enlaces": 0,
                            })

                        total_synced += 1
                        logger.info(
                            "Processed %s: %d XML casillas, %d PDF casillas",
                            boe_id,
                            len(order_result.casillas_parsed),
                            len(order_result.pdf_casillas),
                        )
                    except Exception as e:
                        total_errors += 1
                        logger.error("Failed to process order %s: %s", boe_id, e)
                        with engine.begin() as conn:
                            _log_sync(conn, "worker-boe-modelos", "error", {
                                "started_at": started_at,
                                "bloques_processed": 1,
                                "articulos_upserted": 0,
                                "filas_procesadas": 0,
                                "errores": 1,
                                "documentos_procesados": 1,
                                "documentos_insertados": 0,
                                "doctrina_enlaces": 0,
                                "error_msg": str(e)[:500],
                            })
            except Exception as exc:
                logger.exception("Sync loop failed")
                handle_worker_failure(
                    engine,
                    "worker-boe-modelos",
                    "sync_loop",
                    "orchestrator",
                    exc,
                )

        if run_once:
            break

        logger.info("Next sync in %ds", SYNC_INTERVAL_SECONDS)
        sleep_with_heartbeat(SYNC_INTERVAL_SECONDS)

    return {"synced": total_synced, "errors": total_errors}


if __name__ == "__main__":
    import argparse


    parser = argparse.ArgumentParser(description="BOE->casillas worker")
    parser.add_argument("--db-url", help="Database URL")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, help="Sync interval in seconds")
    args = parser.parse_args()


    db_url = args.db_url or os.getenv("DATABASE_URL", DATABASE_URL)
    interval = args.interval or SYNC_INTERVAL_SECONDS


    logger.info("DB: %s...", db_url[:50])
    logger.info("Interval: %ds", interval)


    engine = create_engine(db_url)
    ensure_database_connection(engine, logger=logger)
    run_sync(engine, run_once=args.run_once)
