import argparse
import logging
import os
import re
import time
from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse

import httpx
from boe import _ensure_sync_log_table, log_sync
from change_detection import (
    check_content_changed,
    destination_row_exists,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    record_revision,
)
from pypdf import PdfReader
from runtime import (
    ensure_database_connection,
    get_database_url,
    get_interval_seconds,
    handle_worker_failure,
    sleep_with_heartbeat,
    touch_heartbeat,
)
from sqlalchemy import create_engine, text
from vocabulary_validation import sanitize_documento_payload

logger = logging.getLogger(__name__)


def _parse_seed_urls(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


SEED_URLS = _parse_seed_urls(os.getenv("BDNS_SEED_URLS"))
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)


def _extract_convocatoria_id(url: str) -> str | None:
    match = re.search(r"/convocatoria/(\d+)", url)
    if not match:
        return None
    return match.group(1)


def _extract_document_id(url: str) -> str | None:
    match = re.search(r"/document/(\d+)", url)
    if not match:
        return None
    return match.group(1)


def _build_referencia(url: str) -> str:
    convocatoria_id = _extract_convocatoria_id(url)
    document_id = _extract_document_id(url)
    if convocatoria_id and document_id:
        return f"BDNS-{convocatoria_id}-{document_id}"
    if convocatoria_id:
        return f"BDNS-{convocatoria_id}"

    path = urlparse(url).path.rstrip("/").split("/")[-1]
    return f"BDNS-{path or 'seed'}"


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    chunks = []
    for page in reader.pages:
        text_value = page.extract_text() or ""
        cleaned = _normalize_whitespace(text_value)
        if cleaned:
            chunks.append(cleaned)
    return "\n".join(chunks)


def build_document_payload(url: str, content: bytes) -> dict[str, str]:
    text_value = extract_pdf_text(content)
    if not text_value:
        raise ValueError(f"Could not extract text from BDNS document: {url}")

    first_line = next((line.strip() for line in text_value.splitlines() if line.strip()), "")
    referencia = _build_referencia(url)
    convocatoria_id = _extract_convocatoria_id(url)
    title_bits = [bit for bit in [f"Convocatoria {convocatoria_id}" if convocatoria_id else None, first_line] if bit]

    return {
        "referencia": referencia,
        "fecha": datetime.utcnow().date().isoformat(),
        "titulo": " - ".join(title_bits) or referencia,
        "texto": text_value,
        "url_fuente": url,
    }


def upsert_documento_interpretativo(conn, payload: dict[str, str]) -> None:
    record = sanitize_documento_payload(
        {
            "tipo_documento": payload.get("tipo_documento", "convocatoria_subvencion"),
            "organismo_emisor": payload.get("organismo_emisor", "BDNS"),
            "jurisdiccion": payload.get("jurisdiccion", "es"),
            "tipo_fuente": payload.get("tipo_fuente", "bdns"),
            "ambito": payload.get("ambito", "subvenciones"),
            "referencia": payload["referencia"],
            "fecha": payload["fecha"],
            "titulo": payload["titulo"],
            "texto": payload["texto"],
            "url_fuente": payload["url_fuente"],
        }
    )
    conn.execute(
        text(
            """
            INSERT INTO documento_interpretativo (
                tipo_documento,
                organismo_emisor,
                jurisdiccion,
                tipo_fuente,
                ambito,
                referencia,
                fecha,
                titulo,
                texto,
                url_fuente
            )
            VALUES (
                :tipo_documento,
                :organismo_emisor,
                :jurisdiccion,
                :tipo_fuente,
                :ambito,
                :referencia,
                :fecha,
                :titulo,
                :texto,
                :url_fuente
            )
            ON CONFLICT (referencia) DO UPDATE SET
                fecha = excluded.fecha,
                titulo = excluded.titulo,
                texto = excluded.texto,
                url_fuente = excluded.url_fuente
            """
        ),
        record,
    )


def run_sync(
    seed_urls: list[str] | None = None,
    worker_name: str = "worker-bdns",
) -> dict[str, int]:
    import logging
    import os

    logger = logging.getLogger(__name__)
    urls = seed_urls or SEED_URLS
    if not urls:
        logger.error(
            "SEED_URLS vacío en %s — worker abortado sin ingestión. "
            "Configura la variable de entorno correspondiente.",
            worker_name,
        )
        return {"processed": 0, "stored": 0}

    request_delay = float(os.environ.get("WORKER_REQUEST_DELAY", "1.0"))
    processed = 0
    stored = 0
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client, engine.begin() as conn:
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)
            for url in urls:
                response = client.get(url)
                response.raise_for_status()
                payload = build_document_payload(url, response.content)
                processed += 1

                change = check_content_changed(
                    conn, worker_name, "documento", payload["referencia"], response.content
                )

                if not change.changed and destination_row_exists(
                    conn,
                    "documento_interpretativo",
                    "referencia",
                    payload["referencia"],
                ):
                    print(f"  [SKIP] {payload['referencia']} unchanged")
                    continue

                invalidated = invalidate_old_embeddings(conn, payload["referencia"])
                if invalidated:
                    print(
                        f"  [INVALIDATE] {invalidated} old embeddings for {payload['referencia']}"
                    )

                upsert_documento_interpretativo(conn, payload)
                record_revision(
                    conn,
                    worker_name,
                    "documento",
                    payload["referencia"],
                    response.content,
                )
                stored += 1
                time.sleep(request_delay)

            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=processed,
                documentos_upserted=stored,
            )

        return {"processed": processed, "stored": stored}
    except Exception as exc:
        entity_id = "bdns"
        if not handle_worker_failure(engine, "bdns", entity_id, "sync_entity", exc):
            logger.warning("Entity bdns moved to dead-letter")
            return {"processed": 0, "stored": 0}
        with engine.begin() as conn:
            log_sync(
                conn,
                worker_name,
                "error",
                documentos_processed=processed,
                documentos_upserted=stored,
                error_msg=str(exc),
            )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BDNS worker: sync public subsidy calls from BDNS documents"
    )
    parser.add_argument(
        "--run-once", action="store_true", help="Run a single sync cycle and exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=f"Seconds between sync cycles in continuous mode (default: {SYNC_INTERVAL_SECONDS})",
    )
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("bdns")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-bdns-weekly")
        print(
            f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}"
        )
    else:
        print(f"Starting BDNS worker in continuous mode (interval={interval}s)")
        while True:
            touch_heartbeat()
            result = run_sync()
            print(
                f"Synced convocatorias={result['processed']}, almacenadas={result['stored']} at {datetime.utcnow().isoformat()}"
            )
            sleep_with_heartbeat(interval)
