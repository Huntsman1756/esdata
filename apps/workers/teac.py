import argparse
from datetime import datetime, timezone
from html import unescape
import os
import re
import time

import httpx
from sqlalchemy import create_engine, text

from boe import _ensure_sync_log_table, auto_link_doctrina, log_sync
from runtime import get_database_url, get_interval_seconds


def _parse_seed_urls(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


SEED_URLS = _parse_seed_urls(os.getenv("TEAC_SEED_URLS"))
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)


def _clean_html_text(value: str) -> str:
    text_value = re.sub(r"<[^>]+>", " ", value)
    text_value = unescape(text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def _extract(pattern: str, html: str) -> str | None:
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return None
    return _clean_html_text(match.group(1))


def _extract_first(patterns: list[str], html: str) -> str | None:
    for pattern in patterns:
        value = _extract(pattern, html)
        if value:
            return value
    return None


def parse_resolution_html(html: str) -> dict[str, str]:
    referencia = _extract_first(
        [
            r"Resolucion TEAC\s+([0-9/]+)",
            r"resoluci(?:o|ó)n:\s*<span class=['\"]criterioNegrita['\"]>([0-9/]+)</span>",
        ],
        html,
    )
    fecha = _extract_first(
        [
            r'<div class="fecha">Fecha:\s*(.*?)</div>',
            r"Fecha de la resoluci(?:o|ó)n:\s*<span class=['\"]criterioNegrita['\"]>(.*?)</span>",
        ],
        html,
    )
    organo = _extract_first(
        [
            r'<div class="organo">(.*?)</div>',
            r"Unidad resolutoria:\s*<span class=['\"]criterioNegrita['\"]>(.*?)</span>",
        ],
        html,
    )
    titulo = _extract_first(
        [
            r'<div class="titulo">(.*?)</div>',
            r"<div id=['\"]criterioDatosAsunto['\"][^>]*>.*?<p>(.*?)</p>",
        ],
        html,
    )
    texto = _extract_first(
        [
            r'<div class="texto">(.*?)</div>',
            r"<div id=['\"]criterioDatosContenido['\"][^>]*>.*?<p>(.*?)</p>",
        ],
        html,
    )

    return {
        "referencia": referencia,
        "fecha": datetime.strptime(fecha, "%d/%m/%Y").date().isoformat(),
        "organo": organo,
        "titulo": titulo,
        "texto": texto,
    }


def fetch_resolution_html(url: str) -> str:
    response = httpx.get(url, timeout=30.0)
    response.raise_for_status()
    return response.text


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
                'resolucion_teac',
                'TEAC',
                'es',
                'teac',
                'fiscal',
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
        payload,
    )


def run_sync(
    seed_urls: list[str] | None = None,
    worker_name: str = "worker-teac",
) -> dict[str, int]:
    urls = seed_urls or SEED_URLS
    processed = 0
    stored = 0
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(timezone.utc).isoformat()

    try:
        with httpx.Client(timeout=30.0) as client:
            with engine.begin() as conn:
                _ensure_sync_log_table(conn)
                for url in urls:
                    html = fetch_resolution_html(url)
                    data = parse_resolution_html(html)
                    processed += 1
                    upsert_documento_interpretativo(
                        conn,
                        {
                            "referencia": data["referencia"],
                            "fecha": data["fecha"],
                            "titulo": data["titulo"],
                            "texto": data["texto"],
                            "url_fuente": url,
                        },
                    )
                    stored += 1

                if stored:
                    links_created = auto_link_doctrina(conn)

                log_sync(
                    conn,
                    worker_name,
                    "ok",
                    documentos_processed=processed,
                    documentos_upserted=stored,
                    doctrina_links_created=links_created,
                )

            return {"processed": processed, "stored": stored}

    except Exception:
        logger.exception("TEAC sync failed")
        return {"processed": processed, "stored": stored}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="TEAC worker: sync doctrine from TEAC resolutions"
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
    init_sentry("teac")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-teac-weekly")
        print(
            f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}"
        )
    else:
        print(f"Starting TEAC worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced resoluciones={result['processed']}, almacenadas={result['stored']} at {datetime.now().isoformat()}"
            )
            time.sleep(interval)
