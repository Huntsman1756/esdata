import argparse
import logging
import os
import re
import time
from datetime import UTC, datetime
from html import unescape
from urllib.parse import urljoin

import httpx
from boe import _ensure_sync_log_table, auto_link_doctrina, log_sync
from change_detection import (
    check_content_changed,
    destination_row_exists,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    record_revision,
)
from runtime import get_database_url, get_interval_seconds
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)
DYCTEA_ROOT_URL = "https://serviciostelematicosext.hacienda.gob.es/TEAC/DYCTEA/"


def _is_direct_resolution_url(url: str) -> bool:
    normalized = url.lower()
    return "criterio.aspx?id=" in normalized or bool(
        re.search(r"/teac/\d{2}-\d{4,}-\d{4}$", normalized)
    )


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


def _extract_resolution_links(html: str, base_url: str) -> list[str]:
    matches = re.findall(
        r"href=['\"](criterio\.aspx\?id=[^'\"]+)['\"]",
        html,
        re.IGNORECASE,
    )
    links: list[str] = []
    seen: set[str] = set()
    for href in matches:
        resolved_url = urljoin(base_url, unescape(href))
        if resolved_url in seen:
            continue
        seen.add(resolved_url)
        links.append(resolved_url)
    return links


def _extract_hidden_input(name: str, html: str) -> str | None:
    match = re.search(
        rf'name=["\']{re.escape(name)}["\'][^>]*value=["\']([^"\']*)["\']',
        html,
    )
    if not match:
        return None
    return unescape(match.group(1))


def _search_dyctea(base_url: str, html: str) -> list[str]:
    viewstate = _extract_hidden_input("__VIEWSTATE", html)
    viewstate_generator = _extract_hidden_input("__VIEWSTATEGENERATOR", html)
    if not viewstate or not viewstate_generator:
        return []

    response = httpx.post(
        base_url,
        data={
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstate_generator,
            "ctl00$contentBody$ddlUnidad": "00",
            "ctl00$contentBody$cbCriterios": "on",
            "ctl00$contentBody$cbResoluciones": "on",
            "ctl00$contentBody$btSearch": "Buscar",
        },
        timeout=30.0,
        follow_redirects=True,
    )
    response.raise_for_status()
    return _extract_resolution_links(response.text, str(response.url))


def discover_resolution_urls(seed_url: str, html: str) -> list[str]:
    direct_links = _extract_resolution_links(html, seed_url)
    if direct_links:
        return direct_links

    if "ctl00$contentBody$btSearch" in html and "__VIEWSTATE" in html:
        search_results = _search_dyctea(seed_url, html)
        if search_results:
            return search_results

    if "Bases de datos de los Tribunales Econ" in html or "Base de datos Doctrina y Criterios" in html:
        dyctea_response = httpx.get(DYCTEA_ROOT_URL, timeout=30.0, follow_redirects=True)
        dyctea_response.raise_for_status()
        search_results = _search_dyctea(DYCTEA_ROOT_URL, dyctea_response.text)
        if search_results:
            return search_results

    return []


def _expand_seed_urls(seed_urls: list[str]) -> tuple[list[str], dict[str, str]]:
    expanded_urls: list[str] = []
    prefetched_html: dict[str, str] = {}
    seen: set[str] = set()

    for seed_url in seed_urls:
        html = fetch_resolution_html(seed_url)
        if _is_direct_resolution_url(seed_url):
            candidates = [seed_url]
            prefetched_html[seed_url] = html
        else:
            candidates = discover_resolution_urls(seed_url, html)
            if not candidates:
                raise ValueError(
                    f"TEAC seed URL did not yield resolution links: {seed_url}"
                )

        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            expanded_urls.append(candidate)

    return expanded_urls, prefetched_html


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
    if not fecha:
        logger.warning("TEAC: fecha not found in HTML, using ingestion date as fallback")
        fecha = datetime.now(UTC).date().isoformat()

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

    if not referencia:
        raise ValueError("TEAC: referencia not found in resolution HTML")

    try:
        parsed_fecha = datetime.strptime(fecha, "%d/%m/%Y").date().isoformat()
    except ValueError:
        parsed_fecha = fecha

    return {
        "referencia": referencia,
        "fecha": parsed_fecha,
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
    links_created = 0
    engine = create_engine(DATABASE_URL, future=True)

    try:
        target_urls, prefetched_html = _expand_seed_urls(list(urls))

        with engine.begin() as conn:
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)
            for url in target_urls:
                html = prefetched_html.get(url) or fetch_resolution_html(url)
                data = parse_resolution_html(html)
                processed += 1

                change = check_content_changed(
                    conn, worker_name, "documento", data["referencia"], html
                )

                if not change.changed and destination_row_exists(
                    conn,
                    "documento_interpretativo",
                    "referencia",
                    data["referencia"],
                ):
                    print(f"  [SKIP] {data['referencia']} unchanged")
                    continue

                invalidated = invalidate_old_embeddings(conn, data["referencia"])
                if invalidated:
                    print(
                        f"  [INVALIDATE] {invalidated} old embeddings for {data['referencia']}"
                    )

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
                record_revision(
                    conn,
                    worker_name,
                    "documento",
                    data["referencia"],
                    html,
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

    except Exception as exc:
        with engine.begin() as conn:
            _ensure_sync_log_table(conn)
            log_sync(
                conn,
                worker_name,
                "error",
                documentos_processed=processed,
                documentos_upserted=stored,
                doctrina_links_created=links_created,
                error_msg=str(exc),
            )
        logger.exception("TEAC sync failed")
        raise


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
