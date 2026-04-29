import argparse
import logging
import re
import time
from datetime import UTC, datetime
from html import unescape

import httpx
from boe import _ensure_sync_log_table, auto_link_doctrina, log_sync
from change_detection import (
    check_content_changed,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    record_revision,
)
from runtime import get_bool_env, get_database_url, get_interval_seconds
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


SEED_URLS = [
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2274-22",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1923-24",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2691-21",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1387-20",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1140-24",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2509-20",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0228-25",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2223-22",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0745-20",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1902-23",
]


BASE_URL = "https://petete.tributos.hacienda.gob.es"
DATABASE_URL = get_database_url()
DGT_SSL_VERIFY = get_bool_env("DGT_SSL_VERIFY", False)
DGT_DISCOVERY = get_bool_env("DGT_DISCOVERY", False)
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)


def build_search_payload(num_consulta: str) -> dict[str, str]:
    return {
        "type2": "on",
        "NMCMP_1": "NUM-CONSULTA",
        "VLCMP_1": num_consulta,
        "OPCMP_1": ".Y",
        "cmpOrder": "NUM-CONSULTA",
        "dirOrder": "0",
        "tab": "2",
        "page": "1",
        "auto": "true",
    }


def start_session(client: httpx.Client) -> None:
    client.get("/consultas/").raise_for_status()
    client.headers.update(
        {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{BASE_URL}/consultas/",
            "Origin": BASE_URL,
        }
    )


def fetch_search_html(client: httpx.Client, num_consulta: str) -> str:
    response = client.post(
        "/consultas/do/search",
        data=build_search_payload(num_consulta),
    )
    response.raise_for_status()
    return response.text


def fetch_document_html(
    client: httpx.Client, query: str, order: str, doc_id: str, tab: str = "2"
) -> str:
    match = re.search(r"V\d{4}-\d{2}", query)
    if match:
        client.headers["Referer"] = (
            f"{BASE_URL}/consultas/?num_consulta={match.group(0)}"
        )

    response = client.post(
        "/consultas/do/document",
        data={
            "query": query,
            "order": order,
            "doc": doc_id,
            "tab": tab,
        },
    )
    response.raise_for_status()
    return response.text


def _clean_html_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_search_results(html: str) -> list[dict[str, str]]:
    results = []
    pattern = re.compile(
        r'<td id="doc_(?P<doc_id>\d+)"[^>]*>.*?<span class="NUM-CONSULTA">.*?(?P<referencia>V\d{4}-\d{2}).*?'
        r'<span class="DESCRIPCION-HECHOS">(?P<hechos>.*?)</span>.*?'
        r'<span class="CUESTION-PLANTEADA"><i>(?P<cuestion>.*?)</i></span>',
        re.DOTALL,
    )

    for match in pattern.finditer(html):
        results.append(
            {
                "doc_id": match.group("doc_id"),
                "referencia": match.group("referencia"),
                "hechos": _clean_html_text(match.group("hechos")),
                "cuestion": _clean_html_text(match.group("cuestion")),
            }
        )

    return results


def _extract_field(html: str, field_class: str) -> str | None:
    pattern = re.compile(
        rf'<tr class="{re.escape(field_class)}">.*?<td class="value">(?P<value>.*?)</td>',
        re.DOTALL,
    )
    match = pattern.search(html)
    if not match:
        return None
    return _clean_html_text(match.group("value"))


def _extract_target_normas(normativa: str | None, text_value: str) -> list[str]:
    source = f"{normativa or ''} {text_value}".upper()
    normas = []
    if "LEY 37/1992" in source or "LIVA" in source or "IVA" in source:
        normas.append("LIVA")
    if (
        "LEY 27/2014" in source
        or re.search(r"\bLIS\b", source)
        or "SOCIEDADES" in source
    ):
        normas.append("LIS")
    return normas


def parse_document_html(html: str) -> dict[str, str | list[str]]:
    referencia = _extract_field(html, "NUM-CONSULTA")
    fecha = _extract_field(html, "FECHA-SALIDA")
    normativa = _extract_field(html, "NORMATIVA")
    cuestion = _extract_field(html, "CUESTION-PLANTEADA")
    texto = _extract_field(html, "CONTESTACION-COMPL")

    return {
        "referencia": referencia,
        "organo": _extract_field(html, "ORGANO"),
        "fecha": datetime.strptime(fecha, "%d/%m/%Y").date().isoformat()
        if fecha
        else None,
        "normativa": normativa,
        "cuestion": cuestion,
        "texto": texto,
        "normas_objetivo": _extract_target_normas(normativa, texto or ""),
    }


def _extract_num_consulta(url: str) -> str:
    match = re.search(r"[?&]num_consulta=(V\d{4}-\d{2})", url)
    if not match:
        raise ValueError(f"Could not extract num_consulta from {url}")
    return match.group(1)


def _build_document_payload(search_result: dict[str, str]) -> tuple[str, str, str]:
    referencia = search_result["referencia"]
    return (
        f".EN NUM-CONSULTA ({referencia})",
        "NUM-CONSULTA|0",
        search_result["doc_id"],
    )


def _build_titulo(document: dict[str, str | list[str]]) -> str:
    cuestion = document.get("cuestion") or "Consulta DGT"
    return f"{document['referencia']} - {cuestion}"


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
                'consulta_vinculante',
                'DGT',
                'es',
                'dgt',
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


def discover_dgt_consultas(
    start_year: int = 2017,
    max_consecutive_404: int = 3,
    end_year: int | None = None,
) -> list[str]:
    discovered: list[str] = []
    if end_year is None:
        end_year = datetime.now(UTC).year

    for year in range(start_year, end_year + 1):
        year_str = f"{year % 100:02d}"
        consecutive_404 = 0

        for num in range(1, 10000):
            num_str = f"{num:04d}"
            num_consulta = f"V{num_str}-{year_str}"
            url = f"{BASE_URL}/consultas/?num_consulta={num_consulta}"

            search_html = fetch_search_html_for_discovery(num_consulta)

            if search_html is None:
                consecutive_404 += 1
                if consecutive_404 >= max_consecutive_404:
                    logger.info(
                        "DGT discovery: %d consecutive 404s for year %s, stopping number iteration",
                        max_consecutive_404,
                        year_str,
                    )
                    break
                continue

            consecutive_404 = 0

            results = parse_search_results(search_html)
            if results:
                discovered.append(url)
                logger.info("DGT discovery: found %s (%d results)", num_consulta, len(results))
            else:
                logger.debug("DGT discovery: %s returned no search results", num_consulta)

        logger.info("DGT discovery: year %s complete, %d URLs found so far", year_str, len(discovered))

    logger.info("DGT discovery complete: %d total URLs", len(discovered))
    return discovered


def fetch_search_html_for_discovery(num_consulta: str) -> str | None:
    try:
        with httpx.Client(
            base_url=BASE_URL,
            timeout=30.0,
            verify=DGT_SSL_VERIFY,
        ) as client:
            start_session(client)
            response = client.post(
                "/consultas/do/search",
                data=build_search_payload(num_consulta),
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.text
    except (httpx.HTTPStatusError, httpx.RequestError):
        return None


def run_sync(
    seed_urls: list[str] | None = None,
    worker_name: str = "worker-dgt",
) -> dict[str, int]:
    urls = list(seed_urls or SEED_URLS)

    if DGT_DISCOVERY:
        logger.info("DGT discovery enabled, running discovery phase")
        discovered = discover_dgt_consultas()
        known = {u for u in urls}
        urls.extend(u for u in discovered if u not in known)
        logger.info("DGT discovery: %d seed + %d discovered = %d total URLs", len(seed_urls or SEED_URLS), len(discovered), len(urls))
    processed = 0
    stored = 0
    links_created = 0
    engine = create_engine(DATABASE_URL, future=True)

    try:
        with httpx.Client(
            base_url=BASE_URL,
            timeout=30.0,
            verify=DGT_SSL_VERIFY,
        ) as client, engine.begin() as conn:
            start_session(client)
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)
            for url in urls:
                num_consulta = _extract_num_consulta(url)
                search_html = fetch_search_html(client, num_consulta)
                results = parse_search_results(search_html)
                if not results:
                    continue

                query, order, doc_id = _build_document_payload(results[0])
                document_html = fetch_document_html(client, query, order, doc_id)
                document = parse_document_html(document_html)
                processed += 1

                if not document["normas_objetivo"]:
                    continue

                change = check_content_changed(
                    conn, worker_name, "consulta", document["referencia"], document_html
                )

                if change.changed:
                    invalidated = invalidate_old_embeddings(conn, document["referencia"])
                    if invalidated:
                        print(
                            f"  [INVALIDATE] {invalidated} old embeddings for {document['referencia']}"
                        )

                    upsert_documento_interpretativo(
                        conn,
                        {
                            "referencia": document["referencia"],
                            "fecha": document["fecha"],
                            "titulo": _build_titulo(document),
                            "texto": document["texto"],
                            "url_fuente": url,
                        },
                    )
                    record_revision(
                        conn,
                        worker_name,
                        "consulta",
                        document["referencia"],
                        document_html,
                    )
                    stored += 1
                else:
                    print(f"  [SKIP] {document['referencia']} unchanged")

                time.sleep(1)

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
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DGT worker: sync doctrine from DGT Petete"
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
    init_sentry("dgt")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-dgt-weekly")
        print(
            f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}"
        )
    else:
        print(f"Starting DGT worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced documentos={result['processed']}, almacenados={result['stored']} at {datetime.now().isoformat()}"
            )
            time.sleep(interval)
