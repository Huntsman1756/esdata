import argparse
import json
import logging
import os
import re
import time
from datetime import UTC, date, datetime, timedelta
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
DYCTEA_ROOT_URL = "https://serviciostelematicosext.hacienda.gob.es/TEAC/DYCTEA/"
DEFAULT_TEAC_FECHA_DESDE = "2018-01-01"


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


def _extract_hidden_inputs(html: str) -> dict[str, str]:
    inputs: dict[str, str] = {}
    for match in re.finditer(r"<input\b[^>]*>", html, flags=re.IGNORECASE | re.DOTALL):
        tag = match.group(0)
        name_match = re.search(r'name=["\']([^"\']+)["\']', tag, flags=re.IGNORECASE)
        if not name_match:
            continue
        value_match = re.search(r'value=["\']([^"\']*)["\']', tag, flags=re.IGNORECASE)
        inputs[unescape(name_match.group(1))] = unescape(value_match.group(1)) if value_match else ""
    return inputs


def _parse_span_value(label: str, text_value: str) -> str | None:
    match = re.search(
        rf"{label}\s*:\s*(.*?)(?=\s+(?:Unidad resolutoria|Sala|Concepto|Materia):|$)",
        text_value,
        re.IGNORECASE,
    )
    if not match:
        return None
    value = _clean_html_text(match.group(1))
    return value or None


def _parse_teac_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", value)
    if not match:
        return None
    day, month, year = match.groups()
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def _format_teac_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_dyctea_search_results(html: str, base_url: str) -> list[dict[str, str | None]]:
    """Parse DYCTEA HTML search result rows into official resolution metadata."""
    item_matches = re.findall(
        r"<li\b[^>]*class=['\"][^'\"]*resultadoCriterio[^'\"]*['\"][^>]*>(.*?)</li>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not item_matches:
        item_matches = [
            match.group(0)
            for match in re.finditer(
                r"<a\b[^>]+href=['\"]criterio\.aspx\?id=[^'\"]+['\"][^>]*>.*?</a>",
                html,
                flags=re.IGNORECASE | re.DOTALL,
            )
        ]

    results: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for item_html in item_matches:
        link_match = re.search(
            r"<a\b[^>]+href=['\"](criterio\.aspx\?id=[^'\"]+)['\"][^>]*>(.*?)</a>",
            item_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not link_match:
            continue
        href = unescape(link_match.group(1))
        url = urljoin(base_url, href)
        title = _clean_html_text(link_match.group(2))
        item_text = _clean_html_text(item_html)
        referencia_match = re.search(r"\b(\d{2}/\d{5}/\d{4}/\d{2}/\d{2})\b", item_text)
        if not referencia_match:
            referencia_match = re.search(r"\b(\d{2}/\d{5}/\d{4}/\d{2}/\d/\d)\b", href)
        referencia = referencia_match.group(1) if referencia_match else url
        fecha = _parse_teac_date(item_text)
        sala = _parse_span_value("Unidad resolutoria", item_text) or _parse_span_value("Sala", item_text)
        materia = _parse_span_value("Concepto", item_text) or _parse_span_value("Materia", item_text)
        key = f"{referencia}|{url}"
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "referencia": referencia,
                "fecha": fecha,
                "sala": sala,
                "materia": materia,
                "titulo": title,
                "url_oficial": url,
            }
        )
    return results


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


def _search_dyctea_metadata(
    fecha_desde: date,
    fecha_hasta: date,
    *,
    page_url: str = DYCTEA_ROOT_URL,
) -> list[dict[str, str | None]]:
    html = fetch_resolution_html(page_url)
    hidden_inputs = _extract_hidden_inputs(html)
    if "__VIEWSTATE" not in hidden_inputs:
        return []

    data = {
        **hidden_inputs,
        "ctl00$contentBody$tbFechaDesde": _format_teac_date(fecha_desde),
        "ctl00$contentBody$tbFechaHasta": _format_teac_date(fecha_hasta),
        "ctl00$contentBody$ddlUnidad": "00",
        "ctl00$contentBody$rbCriterio": "2",
        "ctl00$contentBody$cbCriterios": "on",
        "ctl00$contentBody$cbResoluciones": "on",
        "ctl00$contentBody$btSearch": "Buscar",
    }
    response = httpx.post(
        page_url,
        data=data,
        timeout=30.0,
        follow_redirects=True,
    )
    response.raise_for_status()
    return parse_dyctea_search_results(response.text, str(response.url))


def discover_dyctea_bulk(
    *,
    fecha_desde: str,
    fecha_hasta: str | None = None,
    max_results: int | None = None,
    request_delay: float = 1.0,
) -> list[dict[str, str | None]]:
    """Discover DYCTEA resolutions over date windows using the official HTML form."""
    start = _parse_iso_date(fecha_desde)
    end = _parse_iso_date(fecha_hasta) if fecha_hasta else datetime.now(UTC).date()
    if start > end:
        return []

    results: list[dict[str, str | None]] = []
    seen_urls: set[str] = set()
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=30), end)
        for item in _search_dyctea_metadata(cursor, window_end):
            url = str(item.get("url_oficial") or "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            results.append(item)
            if max_results and len(results) >= max_results:
                return results
        cursor = window_end + timedelta(days=1)
        if cursor <= end:
            time.sleep(request_delay)
    return results


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
        "texto": texto or "",
    }


def fetch_resolution_html(url: str) -> str:
    response = httpx.get(url, timeout=30.0)
    response.raise_for_status()
    return response.text


def _documento_columns(conn) -> set[str]:
    if conn.engine.dialect.name == "sqlite":
        return {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(documento_interpretativo)"))
        }
    return {
        row[0]
        for row in conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'documento_interpretativo'
                """
            )
        )
    }


def upsert_documento_interpretativo(conn, payload: dict[str, str]) -> None:
    metadata_payload = {
        "verified": bool(payload.get("verified")),
        "sala": payload.get("sala") or payload.get("organo"),
        "materia": payload.get("materia"),
        "url_oficial": payload.get("url_oficial") or payload.get("url_fuente"),
    }
    metadata_payload = {
        key: value for key, value in metadata_payload.items() if value is not None
    }
    record = sanitize_documento_payload(
        {
            "tipo_documento": payload.get("tipo_documento", "resolucion_teac"),
            "organismo_emisor": payload.get("organismo_emisor", "TEAC"),
            "jurisdiccion": payload.get("jurisdiccion", "es"),
            "tipo_fuente": payload.get("tipo_fuente", "teac"),
            "ambito": payload.get("ambito", "fiscal"),
            "referencia": payload["referencia"],
            "fecha": payload["fecha"],
            "titulo": payload["titulo"],
            "texto": payload["texto"],
            "url_fuente": payload["url_fuente"],
            "metadata": json.dumps(metadata_payload, ensure_ascii=True, sort_keys=True),
            "row_completeness": payload.get("row_completeness", "partial"),
            "row_provenance": payload.get("row_provenance", "official_best_effort"),
        }
    )
    columns = [
        "tipo_documento",
        "organismo_emisor",
        "jurisdiccion",
        "tipo_fuente",
        "ambito",
        "referencia",
        "fecha",
        "titulo",
        "texto",
        "url_fuente",
        "metadata",
        "row_completeness",
        "row_provenance",
    ]
    columns = [column for column in columns if column in _documento_columns(conn)]
    cols_sql = ", ".join(columns)
    values_sql = ", ".join(f":{column}" for column in columns)
    update_sql = ", ".join(
        f"{column} = excluded.{column}" for column in columns if column != "referencia"
    )
    conn.execute(
        text(
            f"""
            INSERT INTO documento_interpretativo ({cols_sql})
            VALUES ({values_sql})
            ON CONFLICT (referencia) DO UPDATE SET
                {update_sql}
            """
        ),
        record,
    )


def _effective_fecha_desde(
    conn,
    max_results: int | None,
    explicit_fecha_desde: str | None,
) -> str:
    if explicit_fecha_desde:
        return explicit_fecha_desde
    if max_results:
        return DEFAULT_TEAC_FECHA_DESDE
    try:
        row = conn.execute(
            text(
                """
                SELECT MAX(fecha)
                FROM documento_interpretativo
                WHERE tipo_documento = 'resolucion_teac'
                """
            )
        ).fetchone()
    except Exception:
        return DEFAULT_TEAC_FECHA_DESDE
    return row[0] or DEFAULT_TEAC_FECHA_DESDE


def run_sync(
    seed_urls: list[str] | None = None,
    worker_name: str = "worker-teac",
    *,
    max_results: int | None = None,
    dry_run: bool = False,
    fecha_desde: str | None = None,
) -> dict[str, int]:
    if seed_urls == []:
        logger.error(
            "SEED_URLS vacío en %s — worker abortado sin ingestión. "
            "Configura la variable de entorno correspondiente.",
            worker_name,
        )
        return {"processed": 0, "stored": 0}

    request_delay = float(os.environ.get("WORKER_REQUEST_DELAY", "1.0"))
    processed = 0
    stored = 0
    links_created = 0
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)

    try:
        urls = seed_urls if seed_urls is not None else SEED_URLS
        metadata_by_url: dict[str, dict[str, str | None]] = {}
        prefetched_html: dict[str, str] = {}
        if urls:
            target_urls, prefetched_html = _expand_seed_urls(list(urls))
            if max_results:
                target_urls = target_urls[:max_results]
        else:
            with engine.begin() as conn:
                effective_fecha_desde = _effective_fecha_desde(
                    conn,
                    max_results,
                    fecha_desde or os.environ.get("TEAC_FECHA_DESDE"),
                )
            candidates = discover_dyctea_bulk(
                fecha_desde=effective_fecha_desde,
                max_results=max_results,
                request_delay=request_delay,
            )
            target_urls = [
                str(candidate["url_oficial"])
                for candidate in candidates
                if candidate.get("url_oficial")
            ]
            metadata_by_url = {
                str(candidate["url_oficial"]): candidate
                for candidate in candidates
                if candidate.get("url_oficial")
            }

        if dry_run:
            print(f"[dry-run] TEAC candidate resolutions: {len(target_urls)}")
            return {"processed": 0, "stored": 0}

        with engine.begin() as conn:
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)
            for url in target_urls:
                html = prefetched_html.get(url) or fetch_resolution_html(url)
                data = parse_resolution_html(html)
                metadata = metadata_by_url.get(url, {})
                if metadata.get("titulo") and not data.get("titulo"):
                    data["titulo"] = str(metadata["titulo"])
                if metadata.get("fecha") and not data.get("fecha"):
                    data["fecha"] = str(metadata["fecha"])
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
                        "texto": data["texto"]
                        or (
                            "[PARTIAL] Metadata oficial TEAC sin texto completo parseable. "
                            f"Referencia: {data['referencia']}. URL oficial: {url}"
                        ),
                        "url_fuente": url,
                        "url_oficial": url,
                        "sala": metadata.get("sala") or data.get("organo"),
                        "materia": metadata.get("materia"),
                        "row_completeness": "complete" if data["texto"] else "partial",
                        "row_provenance": "official_exact"
                        if data["texto"]
                        else "official_best_effort",
                        "verified": bool(
                            data["texto"] and "hacienda.gob.es" in url.lower()
                        ),
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
                time.sleep(request_delay)

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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover candidate DYCTEA resolutions without DB writes",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=None,
        help="Maximum TEAC resolutions to process in this run",
    )
    parser.add_argument(
        "--fecha-desde",
        default=None,
        help="Initial DYCTEA fecha desde in YYYY-MM-DD format (defaults to TEAC_FECHA_DESDE or delta)",
    )
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("teac")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(
            worker_name="cron-teac-weekly",
            max_results=args.max_results,
            dry_run=args.dry_run,
            fecha_desde=args.fecha_desde,
        )
        print(
            f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}"
        )
    else:
        print(f"Starting TEAC worker in continuous mode (interval={interval}s)")
        while True:
            touch_heartbeat()
            try:
                result = run_sync(max_results=args.max_results, fecha_desde=args.fecha_desde)
                print(
                    f"Synced resoluciones={result['processed']}, almacenadas={result['stored']} at {datetime.now().isoformat()}"
                )
            except Exception as exc:
                print(f"[ERROR] TEAC sync failed: {exc} at {datetime.now().isoformat()}")
            sleep_with_heartbeat(interval)
