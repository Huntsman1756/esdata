"""Worker de doctrina DGT especifica para rendimientos mobiliarios.

Ingesta consultas vinculantes DGT relevantes para la sociedad de valores,
centradas en rendimientos del capital mobiliario (dividendos, intereses,
retenciones, imputacion temporal).

Seed URLs y consultas clave:
  - V0091-18: devoluciones bonos
  - V2424-20: imputacion temporal
  - V2965-17: retenciones 19%
  - Consultas adicionales sobre rendimientos mobiliarios

Reutiliza la infraestructura de `dgt.py` para scraping del portal Petete
de la DGT, pero filtra y almacena solo las consultas cuyo ambito de
normas objetivo incluye LIRPF (rendimientos mobiliarios) o IRNR.
"""

import argparse
import re
import time
from datetime import datetime

import httpx
from boe import _ensure_sync_log_table, auto_link_doctrina, log_sync
from change_detection import (
    check_content_changed,
    destination_row_exists,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    record_revision,
)
from runtime import ensure_database_connection, get_bool_env, get_database_url, get_interval_seconds
from sqlalchemy import create_engine

SEED_URLS = [
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0091-18",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2424-20",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2965-17",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1923-24",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1140-24",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2509-20",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0228-25",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2223-22",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0745-20",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1902-23",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2691-21",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1387-20",
]

DATABASE_URL = get_database_url()
DGT_SSL_VERIFY = get_bool_env("DGT_SSL_VERIFY", True)
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

# Normas objetivo especificas para rendimientos mobiliarios
RENDIMIENTO_MOBILIARIO_NORMAS = {"LIRPF", "IRNR", "LIS", "LIVA"}


def _extract_target_normas_rendimiento(texto: str | None, normativa: str | None) -> list[str]:
    """Extraer normas objetivo enfocadas en rendimientos mobiliarios.

    Amplia la logica de `dgt._extract_target_normas` para incluir
    deteccion de LIRPF (rendimientos capital mobiliario) e IRNR.
    """
    source = f"{normativa or ''} {texto or ''}".upper()
    normas = []
    # IRPF / rendimientos mobiliarios — solo si hay keywords especificas
    # de capital mobiliario, no cualquier referencia al IRPF
    rendimiento_keywords = [
        "RENDEMI",
        "CAPITAL MOBILIARIO",
        "RENDIMIENTO MOBILIARIO",
        "DIVIDENDO",
        "INTERES",
        "RENTA CAPITAL",
    ]
    has_rendimiento_keyword = any(kw in source for kw in rendimiento_keywords)
    if has_rendimiento_keyword:
        normas.append("LIRPF")
    # IRNR no residentes
    if (
        "RLD 435/1995" in source
        or "RIRNR" in source
        or "NO RESIDENTE" in source
        or "IRNR" in source
        or "RENDIMIENTO NO RESIDENTE" in source
    ):
        normas.append("IRNR")
    # LIS (sociedades)
    if (
        "LEY 27/2014" in source
        or re.search(r"\bLIS\b", source)
        or "SOCIEDADES" in source
    ):
        normas.append("LIS")
    # IVA
    if "LEY 37/1992" in source or "LIVA" in source or "IVA" in source:
        normas.append("LIVA")
    return normas


def run_sync(
    seed_urls: list[str] | None = None,
    worker_name: str = "worker-dgt-rendimiento",
) -> dict[str, int]:
    """Sincroniza consultas DGT relevantes para rendimientos mobiliarios."""
    urls = seed_urls or SEED_URLS
    processed = 0
    stored = 0
    links_created = 0
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)
    ssl_verify = get_bool_env("DGT_SSL_VERIFY", DGT_SSL_VERIFY)
    # Importamos la logica de scraping de dgt.py para reutilizar
    from dgt import (
        _build_document_payload,
        _extract_field,
        _extract_num_consulta,
        fetch_document_html,
        fetch_search_html,
        parse_search_results,
        start_session,
        upsert_documento_interpretativo,
    )
    from dgt import (
        parse_document_html as _parse_doc_html,
    )

    try:
        with httpx.Client(timeout=30.0, verify=ssl_verify) as client, engine.begin() as conn:
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)
            for url in urls:
                num_consulta = _extract_num_consulta(url)
                start_session(client)
                search_html = fetch_search_html(client, num_consulta)
                results = parse_search_results(search_html)
                if not results:
                    continue

                query, order, doc_id = _build_document_payload(results[0])
                document_html = fetch_document_html(client, query, order, doc_id)
                document = _parse_doc_html(document_html)

                # Ampliar el parsing con normas especificas de rendimiento
                normativa = _extract_field(document_html, "NORMATIVA")
                texto = document.get("texto")
                normas_objetivo = _extract_target_normas_rendimiento(texto, normativa)
                document["normas_objetivo"] = normas_objetivo

                processed += 1

                if not normas_objetivo:
                    continue

                change = check_content_changed(
                    conn, worker_name, "documento", document["referencia"], document_html
                )

                if not change.changed and destination_row_exists(
                    conn,
                    "documento_interpretativo",
                    "referencia",
                    document["referencia"],
                ):
                    print(f"  [SKIP] {document['referencia']} unchanged")
                    continue

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
                        "titulo": f"{document['referencia']} - {document.get('cuestion', 'Rendimientos mobiliarios')}",
                        "texto": texto,
                        "url_fuente": url,
                    },
                )
                record_revision(
                    conn,
                    worker_name,
                    "documento",
                    document["referencia"],
                    document_html,
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
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DGT Rendimiento worker: sync doctrine on rental income/dividends"
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
    init_sentry("dgt-rendimiento")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-dgt-rendimiento-weekly")
        print(
            f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}"
        )
    else:
        print(f"Starting DGT Rendimiento worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                "Synced "
                f"documentos={result['processed']}, "
                f"almacenados={result['stored']} "
                f"at {datetime.now().isoformat()}"
            )
            time.sleep(interval)
