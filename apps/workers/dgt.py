"""Worker DGT — Direccion General de Tributos (Ministerio de Hacienda).

Fuente: https://petete.tributos.hacienda.gob.es/ (consultas vinculantes y
no vinculantes). Discovery via `dgt_doctrina.py` (queue persistente en
`dgt_queue`). Persistencia: tabla `documento_interpretativo` con
`tipo_fuente='dgt'`, `tipo_documento='consulta_dgt'`.

Conflict key: `documento_interpretativo.referencia` UNIQUE
(formato `V<num>-<anio>` o `<num>-<anio>` segun tipo).

Sync intervalo: diario via cron. Auditoria: `sync_log` (worker='worker-dgt').

Limitaciones conocidas:
- Sitio sin API publica; scraping HTML sujeto a cambios de marca.
- TLS upstream: `DGT_SSL_VERIFY=true` por defecto; bajar solo en entorno
  controlado y nunca en produccion.
- Enlace a articulos (doctrina↔articulado) en `documento_articulo` es
  best-effort segun `metodo_enlace` (regex, manual, llm).
"""

import argparse
import logging
import os
import re
import ssl
import sys
import time
from datetime import UTC, datetime
from html import unescape
from pathlib import Path

import httpx
from boe import _ensure_sync_log_table, auto_link_doctrina, log_sync
from change_detection import (
    check_content_changed,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    record_revision,
)
from runtime import (
    ensure_database_connection,
    finalize_partial_sync_status,
    get_bool_env,
    get_database_url,
    get_interval_seconds,
    sleep_with_heartbeat,
    touch_heartbeat,
)
from sqlalchemy import create_engine, text
from vocabulary_validation import sanitize_documento_payload

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)

_DGT_QUEUE_BOOTSTRAP_LOGGED: set[str] = set()


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
DGT_SSL_VERIFY = get_bool_env("DGT_SSL_VERIFY", True)
DGT_DISCOVERY = get_bool_env("DGT_DISCOVERY", False)
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)
FNMT_INTERMEDIATE_CHAIN = (
    Path(__file__).resolve().parent / "certs" / "fnmt-ac-componentes-informaticos.pem"
)


def build_dgt_tls_verify() -> bool | ssl.SSLContext:
    if not DGT_SSL_VERIFY:
        return False

    context = ssl.create_default_context()
    if FNMT_INTERMEDIATE_CHAIN.exists():
        context.load_verify_locations(cafile=str(FNMT_INTERMEDIATE_CHAIN))
    return context


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
    query_match = re.search(
        r'<input type="hidden" name="query" id="query" value="(?P<query>[^"]+)"',
        html,
        re.DOTALL,
    )
    order_match = re.search(
        r'<input type="hidden" name="order" id="order" value="(?P<order>[^"]+)"',
        html,
        re.DOTALL,
    )
    query_value = unescape(query_match.group("query")) if query_match else None
    order_value = unescape(order_match.group("order")) if order_match else None

    pattern = re.compile(
        r'<td id="doc_(?P<doc_id>\d+)"[^>]*(?:onClick="return viewDocument\(\d+,\s*(?P<tab>\d+)\);")?[^>]*>.*?<span class="NUM-CONSULTA">.*?(?P<referencia>V\d{4}-\d{2}).*?'
        r'<span class="DESCRIPCION-HECHOS">(?P<hechos>.*?)</span>.*?'
        r'<span class="CUESTION-PLANTEADA"><i>(?P<cuestion>.*?)</i></span>',
        re.DOTALL,
    )

    return [
        {
            "doc_id": match.group("doc_id"),
            "query": query_value,
            "order": order_value,
            "tab": match.group("tab") or "2",
            "referencia": match.group("referencia"),
            "hechos": _clean_html_text(match.group("hechos")),
            "cuestion": _clean_html_text(match.group("cuestion")),
        }
        for match in pattern.finditer(html)
    ]


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
    query = search_result.get("query")
    order = search_result.get("order")
    if query and order:
        return (query, order, search_result["doc_id"])

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
    payload = dict(payload)

    if conn.engine.dialect.name == "sqlite":
        table_columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(documento_interpretativo)"))
        }
    else:
        table_columns = {
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

    payload.setdefault("tipo_documento", "consulta_vinculante")
    payload.setdefault("organismo_emisor", "DGT")
    payload.setdefault("jurisdiccion", "es")
    payload.setdefault("tipo_fuente", "dgt")
    payload.setdefault("ambito", "fiscal")
    payload.setdefault("row_completeness", "complete")
    payload.setdefault("row_provenance", "official_exact")
    payload = sanitize_documento_payload(payload)

    ordered_columns = [
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
        "row_completeness",
        "row_provenance",
    ]
    insert_columns = [column for column in ordered_columns if column in table_columns]
    update_columns = [
        column
        for column in ("fecha", "titulo", "texto", "url_fuente")
        if column in insert_columns
    ]
    assignments = [f"{column} = excluded.{column}" for column in update_columns]

    conn.execute(
        text(
            f"""
            INSERT INTO documento_interpretativo ({', '.join(insert_columns)})
            VALUES ({', '.join(f':{column}' for column in insert_columns)})
            ON CONFLICT (referencia) DO UPDATE SET
                {', '.join(assignments)}
            """
        ),
        {column: payload[column] for column in insert_columns},
    )


def fetch_search_html_for_discovery(num_consulta: str) -> str | None:
    """Deprecated — replaced by numeric discovery via POST /consultas/do/search."""
    return None


def ensure_dgt_queue_table(conn) -> None:
    """Garantiza que `dgt_queue` existe en SQLite/tests.

    En Postgres la tabla es propiedad de la migracion
    `20260504_0057_dgt_queue_split`, asi que este helper degrada a no-op
    defensivo y solo conserva bootstrap local para SQLite.
    """
    dialect_name = conn.engine.dialect.name
    if dialect_name != "sqlite":
        if dialect_name not in _DGT_QUEUE_BOOTSTRAP_LOGGED:
            logger.debug(
                "ensure_dgt_queue_table: no-op en %s; schema owned por Alembic "
                "(20260504_0057_dgt_queue_split)",
                dialect_name,
            )
            _DGT_QUEUE_BOOTSTRAP_LOGGED.add(dialect_name)
        return

    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS dgt_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_name TEXT NOT NULL,
                source_entity_id TEXT NOT NULL,
                dgt_url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'processed', 'empty')),
                queued_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                processed_at TIMESTAMP,
                UNIQUE(worker_name, source_entity_id)
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_dgt_queue_pending
                ON dgt_queue(worker_name, status, id)
            """
        )
    )


def _ensure_dgt_queue(conn, worker_name: str, seed_urls: list[str]) -> None:
    """Insert seed URLs into `dgt_queue` as pending queue entries."""
    ensure_dgt_queue_table(conn)
    for url in seed_urls:
        num_consulta = _extract_num_consulta(url)
        conn.execute(
            text("""
                INSERT INTO dgt_queue (
                    worker_name, source_entity_id, dgt_url, status
                ) VALUES (:worker, :entity_id, :url, 'pending')
                ON CONFLICT (worker_name, source_entity_id) DO NOTHING
            """),
            {
                "worker": worker_name,
                "entity_id": num_consulta,
                "url": url,
            },
        )


def _get_pending_urls(conn, worker_name: str, limit: int = 100) -> list[tuple[str, str]]:
    """Get pending URLs from the queue. Returns [(url, entity_id), ...]."""
    result = conn.execute(
        text("""
            SELECT dgt_url, source_entity_id
            FROM dgt_queue
            WHERE worker_name = :worker
              AND status = 'pending'
            ORDER BY id ASC
            LIMIT :limit
        """),
        {"worker": worker_name, "limit": limit},
    )
    return result.fetchall()


def _mark_done(conn, worker_name: str, entity_id: str, status: str) -> None:
    """Mark a queue entry as processed or empty."""
    if status not in {"processed", "empty"}:
        raise ValueError(f"Unsupported DGT queue status: {status}")

    conn.execute(
        text("""
            UPDATE dgt_queue
            SET status = :status,
                processed_at = :ts
            WHERE worker_name = :worker
              AND source_entity_id = :entity_id
              AND status = 'pending'
        """),
        {
            "worker": worker_name,
            "status": status,
            "entity_id": entity_id,
            "ts": datetime.now(UTC).isoformat(),
        },
    )


def run_sync(  # noqa: C901
    seed_urls: list[str] | None = None,
    worker_name: str = "worker-dgt",
    batch_size: int = 100,
) -> dict[str, int]:
    seed_list = list(seed_urls or SEED_URLS)
    total_processed = 0
    total_stored = 0
    total_discovered = 0
    links_created = 0
    missing_document_failures = 0
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine, logger=logger)

    try:
        with httpx.Client(
            base_url=BASE_URL,
            timeout=60.0,
            verify=build_dgt_tls_verify(),
        ) as client:
            start_session(client)

            # Phase 1: Ensure seed URLs are in the queue
            with engine.begin() as conn:
                _ensure_sync_log_table(conn)
                ensure_source_revision_table(conn)
                ensure_dgt_queue_table(conn)
                _ensure_dgt_queue(conn, worker_name, seed_list)

            # Phase 2: Discovery — insert new URLs into pending queue
            if DGT_DISCOVERY:
                logger.info("DGT discovery enabled, starting numeric iteration")

                # Load existing entity IDs into memory to avoid per-URL DB queries
                with engine.begin() as conn:
                    existing_ids = set(
                        row[0] for row in conn.execute(
                            text("""
                                SELECT source_entity_id
                                FROM dgt_queue
                                WHERE worker_name = :worker
                            """),
                            {"worker": worker_name},
                        ).fetchall()
                    )

                for year in range(2026, 2016, -1):
                    year_str = f"{year % 100:02d}"
                    consecutive_404 = 0
                    year_discovered = 0
                    batch_inserts = []

                    for num in range(1, 10000):
                        num_str = f"{num:04d}"
                        num_consulta = f"V{num_str}-{year_str}"

                        # Skip if already in queue (from prior run)
                        if num_consulta in existing_ids:
                            continue

                        try:
                            search_html = fetch_search_html(client, num_consulta)
                        except (httpx.HTTPStatusError, httpx.RequestError):
                            consecutive_404 += 1
                            if consecutive_404 >= 3:
                                logger.info(
                                    "DGT discovery: 3 consecutive errors for year %s, stopping",
                                    year_str,
                                )
                                break
                            continue

                        results = parse_search_results(search_html)
                        if not results:
                            consecutive_404 += 1
                            if consecutive_404 >= 3:
                                logger.info(
                                    "DGT discovery: 3 consecutive 404s for year %s, stopping",
                                    year_str,
                                )
                                break
                            continue

                        consecutive_404 = 0
                        year_discovered += 1
                        total_discovered += 1
                        existing_ids.add(num_consulta)
                        batch_inserts.append({
                            "worker": worker_name,
                            "entity_id": num_consulta,
                            "url": f"{BASE_URL}/consultas/?num_consulta={num_consulta}",
                        })

                        time.sleep(float(os.environ.get("WORKER_REQUEST_DELAY", "1.0")))
                        logger.info(
                            "DGT discovery: found %s (%d total discovered)",
                            num_consulta,
                            total_discovered,
                        )

                    # Batch insert discovered URLs
                    if batch_inserts:
                        with engine.begin() as conn:
                            conn.execute(
                                text("""
                                    INSERT INTO dgt_queue (
                                        worker_name, source_entity_id, dgt_url, status
                                    ) VALUES (:worker, :entity_id, :url, 'pending')
                                    ON CONFLICT (worker_name, source_entity_id) DO NOTHING
                                """),
                                batch_inserts,
                            )

                    logger.info("DGT discovery: year %s complete, %d URLs found", year_str, year_discovered)

                logger.info("DGT discovery complete: %d new URLs discovered", total_discovered)

            # Phase 3: Processing — incremental from persistent queue
            with engine.begin() as conn:
                _ensure_sync_log_table(conn)
                ensure_source_revision_table(conn)
                ensure_dgt_queue_table(conn)

            while True:
                start_session(client)

                with engine.begin() as conn:
                    pending = _get_pending_urls(conn, worker_name, limit=batch_size)

                if not pending:
                    logger.info("DGT queue empty, sync complete")
                    break

                batch_processed = 0
                batch_stored = 0
                batch_links = 0
                batch_missing_documents = 0

                for url, entity_id in pending:
                    touch_heartbeat()
                    try:
                        num_consulta = _extract_num_consulta(url)
                        search_html = fetch_search_html(client, num_consulta)
                        results = parse_search_results(search_html)
                        if not results:
                            batch_missing_documents += 1
                            with engine.begin() as conn:
                                _mark_done(conn, worker_name, entity_id, "empty")
                            continue

                        query, order, doc_id = _build_document_payload(results[0])
                        document_html = fetch_document_html(
                            client,
                            query,
                            order,
                            doc_id,
                            results[0].get("tab", "2"),
                        )
                        document = parse_document_html(document_html)
                        batch_processed += 1

                        if not document["normas_objetivo"]:
                            with engine.begin() as conn:
                                _mark_done(conn, worker_name, entity_id, "empty")
                            continue

                        # Check content change
                        with engine.begin() as conn:
                            change = check_content_changed(
                                conn, worker_name, "consulta", document["referencia"], document_html
                            )

                        if change.changed:
                            with engine.begin() as conn:
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
                                batch_stored += 1

                            # Mark queue entry as done
                            with engine.begin() as conn:
                                _mark_done(conn, worker_name, entity_id, "processed")
                        else:
                            print(f"  [SKIP] {document['referencia']} unchanged")
                            # Mark queue entry as done (already processed)
                            with engine.begin() as conn:
                                _mark_done(conn, worker_name, entity_id, "processed")

                        time.sleep(1)

                    except Exception as e:
                        logger.error("Error processing %s: %s", url, e)
                        # Don't mark as done — will retry next batch
                        continue

                if batch_stored:
                    with engine.begin() as conn:
                        batch_links = auto_link_doctrina(conn)
                        links_created += batch_links

                total_processed += batch_processed
                total_stored += batch_stored
                missing_document_failures += batch_missing_documents
                logger.info(
                    "DGT batch: %d processed, %d stored, %d pending remaining",
                    batch_processed, batch_stored,
                    len(pending) - batch_processed,
                )

            with engine.begin() as conn:
                _ensure_sync_log_table(conn)
                final_status, final_error_msg = finalize_partial_sync_status(
                    base_status="ok",
                    missing_count=missing_document_failures,
                    source_label="DGT documents",
                )
                log_sync(
                    conn,
                    worker_name,
                    final_status,
                    documentos_processed=total_processed,
                    documentos_upserted=total_stored,
                    doctrina_links_created=links_created,
                    error_msg=final_error_msg,
                )

        return {
            "processed": total_processed,
            "stored": total_stored,
            "discovered": total_discovered,
        }
    except Exception as exc:
        with engine.begin() as conn:
            _ensure_sync_log_table(conn)
            log_sync(
                conn,
                worker_name,
                "error",
                documentos_processed=total_processed,
                documentos_upserted=total_stored,
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
            touch_heartbeat()
            try:
                result = run_sync()
                discovered = result.get("discovered", 0)
                print(
                    f"Synced documentos={result['processed']}, almacenados={result['stored']}, "
                    f"descubiertos={discovered} at {datetime.now().isoformat()}"
                )
            except Exception as exc:
                print(f"[ERROR] DGT sync failed: {exc} at {datetime.now().isoformat()}")
            sleep_with_heartbeat(interval)
