import argparse
from datetime import UTC, datetime
from html import unescape
import os
import re
import time

import httpx
from sqlalchemy import create_engine, text

from boe import _ensure_sync_log_table, log_sync
from runtime import get_database_url, get_interval_seconds


def _parse_seed_urls(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


SEED_URLS = _parse_seed_urls(os.getenv("AEPD_SEED_URLS"))
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_reference(url: str, text_value: str) -> str:
    path_match = re.search(r"(/guias/|/docs/|/docs/)([^/]+)", url)
    if path_match:
        return f"AEPD-{path_match.group(2)}"
    text_match = re.search(r"(\d{4}/\d{2})", text_value)
    if text_match:
        return f"AEPD-{text_match.group(1).replace('/', '-')}"
    return f"AEPD-{datetime.now(UTC).date().isoformat().replace('-', '')}"


def _detect_document_type(text_value: str) -> str:
    lowered = text_value.lower()
    if "guía" in lowered or "guia" in lowered:
        return "guia_aepd"
    if "resolución" in lowered or "resolucion" in lowered:
        return "resolucion_aepd"
    if "instrucción" in lowered or "instruccion" in lowered:
        return "instruccion_aepd"
    if "acuerdo" in lowered:
        return "acuerdo_aepd"
    return "documento_aepd"


def _detect_ambito(text_value: str) -> str:
    lowered = text_value.lower()
    if "protección de datos" in lowered or "proteccion de datos" in lowered:
        return "proteccion_datos"
    if "derecho de acceso" in lowered or "derecho acceso" in lowered:
        return "derechos_ar"
    if "ficheros" in lowered or "ficheros de datos" in lowered:
        return "ficheros_datos"
    if "cookies" in lowered:
        return "cookies"
    return "proteccion_datos_general"


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
        raise ValueError(f"Could not extract text from AEPD document: {url}")

    referencia = _extract_reference(url, text_value)

    return {
        "referencia": referencia,
        "fecha": datetime.now(UTC).date().isoformat(),
        "titulo": f"{_detect_document_type(text_value)} - {referencia}",
        "texto": text_value,
        "url_fuente": url,
        "tipo_documento": _detect_document_type(text_value),
        "tipo_fuente": "aepd",
        "organismo_emisor": "AEPD",
        "ambito": _detect_ambito(text_value),
        "jurisdiccion": "es",
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
    worker_name: str = "worker-aepd",
) -> dict[str, int]:
    urls = seed_urls or SEED_URLS
    processed = 0
    stored = 0
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(timezone.utc).isoformat()

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            with engine.begin() as conn:
                _ensure_sync_log_table(conn)
                for url in urls:
                    response = client.get(url)
                    response.raise_for_status()
                    payload = build_document_payload(url, response.content)
                    processed += 1
                    upsert_documento_interpretativo(conn, payload)
                    stored += 1

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
        description="AEPD worker: sync public data protection documents"
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
    init_sentry("aepd")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-aepd-weekly")
        print(
            f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}"
        )
    else:
        print(f"Starting AEPD worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced documentos={result['processed']}, almacenados={result['stored']} at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
