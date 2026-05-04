"""Worker CENDOJ — Centro de Documentacion Judicial (CGPJ).

Fuente: jurisprudencia publicada via buscador CENDOJ
(https://www.poderjudicial.es/search/). Persistencia: `documento_interpretativo`
con `tipo_fuente='cendoj'`. Conflict key: `referencia` UNIQUE (ROJ).

Sync intervalo: semanal (cuando habilitado). Auditoria via `sync_log`.

Limitaciones conocidas / [BLOCKED]:
- Acceso programatico restringido (SSO/captcha en upstream); el worker
  esta gateado por flag `CENDOJ_ENABLED` y no se ejecuta por defecto.
- Licencia de reuso restrictiva: revisar terminos antes de redistribuir.
"""

import argparse
import os
import re
import time
from datetime import UTC, datetime
from html import unescape
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
from runtime import (
    ensure_database_connection,
    get_database_url,
    get_interval_seconds,
    sleep_with_heartbeat,
    touch_heartbeat,
)
from sqlalchemy import create_engine, text


def _parse_seed_urls(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


SEED_URLS = _parse_seed_urls(os.getenv("CENDOJ_SEED_URLS"))
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_reference(url: str, text_value: str) -> str:
    path = urlparse(url).path.rstrip("/").split("/")[-1]
    if path and path.lower() not in {"", "index.html"}:
        cleaned = re.sub(r"[^A-Za-z0-9_-]", "-", path)
        return f"CENDOJ-{cleaned}"

    match = re.search(r"(\d{5})/(\d{4})", text_value)
    if match:
        return f"CENDOJ-{match.group(1)}-{match.group(2)}"
    return f"CENDOJ-{datetime.now(UTC).date().isoformat().replace('-', '')}"


def _detect_court(text_value: str) -> str:
    lowered = text_value.lower()
    if "tribunal supremo" in lowered:
        return "tribunal_supremo"
    if "audiencia nacional" in lowered:
        return "audiencia_nacional"
    if "tsj" in lowered or "tribunal superior de justicia" in lowered:
        return "tsj"
    return "otro_tribunal"


def _detect_document_type(text_value: str) -> str:
    lowered = text_value.lower()
    if "sentencia" in lowered:
        return "sentencia"
    if "auto" in lowered:
        return "auto"
    if "providencia" in lowered:
        return "providencia"
    return "resolucion"


def _detect_ambito(text_value: str) -> str:
    lowered = text_value.lower()
    if "tributari" in lowered or "iva" in lowered or "irpf" in lowered or "impuesto" in lowered:
        return "jurisprudencia_tributaria"
    if "blanqueo de capitales" in lowered or "financiacion del terrorismo" in lowered or "financiación del terrorismo" in lowered:
        return "jurisprudencia_pbcft"
    if "mercado de valores" in lowered or "cnmv" in lowered or "servicios de inversion" in lowered or "servicios de inversión" in lowered:
        return "jurisprudencia_mercantil_regulatoria"
    return "jurisprudencia"


def _detect_organismo(text_value: str) -> str:
    lowered = text_value.lower()
    if "tribunal supremo" in lowered:
        return "Tribunal Supremo"
    if "audiencia nacional" in lowered:
        return "Audiencia Nacional"
    if "tsj" in lowered:
        return "TSJ"
    return "CENDOJ"


def extract_text(content: bytes) -> str:
    html = content.decode("utf-8", errors="ignore")
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", "\n", html)
    text_value = re.sub(r"\n\s*\n", "\n", html)
    return _normalize_whitespace(unescape(text_value))


def build_document_payload(url: str, content: bytes) -> dict[str, str]:
    text_value = extract_text(content)
    if not text_value:
        raise ValueError(f"Could not extract text from CENDOJ document: {url}")

    referencia = _extract_reference(url, text_value)
    court = _detect_court(text_value)
    doc_type = _detect_document_type(text_value)
    organismo = _detect_organismo(text_value)

    return {
        "referencia": referencia,
        "fecha": datetime.now(UTC).date().isoformat(),
        "titulo": f"{doc_type} - {court} - {referencia}",
        "texto": text_value,
        "url_fuente": url,
        "tipo_documento": doc_type,
        "tipo_fuente": "cendoj",
        "organismo_emisor": organismo,
        "ambito": _detect_ambito(text_value),
        "jurisdiccion": "es",
        "court": court,
    }


def upsert_documento_interpretativo(conn, payload: dict[str, str]) -> None:
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
                tipo_documento = excluded.tipo_documento,
                organismo_emisor = excluded.organismo_emisor,
                ambito = excluded.ambito,
                fecha = excluded.fecha,
                titulo = excluded.titulo,
                texto = excluded.texto,
                url_fuente = excluded.url_fuente
            """
        ),
        payload,
    )


def run_sync(
    seed_urls: list[str] | None = None,
    worker_name: str = "worker-cendoj",
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
        description="CENDOJ worker: sync public jurisprudence from CENDOJ"
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
    init_sentry("cendoj")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-cendoj-weekly")
        print(
            f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}"
        )
    else:
        print(f"Starting CENDOJ worker in continuous mode (interval={interval}s)")
        while True:
            touch_heartbeat()
            result = run_sync()
            print(
                f"Synced documentos={result['processed']}, almacenados={result['stored']} at {datetime.now(UTC).isoformat()}"
            )
            sleep_with_heartbeat(interval)
