"""Worker de ingestion del RIRNR (Reglamento del IRNR, RD 435/1995).

Ingesta el texto consolidado del Reglamento del Impuesto sobre la Renta
de no Residentes desde la API de legislacion consolidada del BOE,
centrado en articulos sobre:

- Retenciones en dividendos (15% UE / 24% no UE)
- Retenciones en intereses
- Ganancias patrimoniales
- Convenios de doble imposicion bilateral

Relacion con IRNR (Ley 35/2006, ya cubierta en boe.py)
Relacion con modelos: 123, 124, 216, 296
Relacion con convenios DTA: ES-US, ES-DE, ES-FR

Reutiliza la infraestructura de `boe.py` para scraping del BOE API
de legislacion consolidada.
"""

import argparse
import time
from datetime import UTC, datetime

import httpx
from boe import (
    _ensure_schema,
    _ensure_sync_log_table,
    fetch_block,
    fetch_index,
    parse_metadata,
    upsert_articulo,
    upsert_norma,
)
from change_detection import (
    check_content_changed,
    destination_row_exists,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    record_revision,
)
from runtime import ensure_database_connection, get_bool_env, get_database_url, get_interval_seconds, handle_worker_failure
from sqlalchemy import create_engine, text

# RIRNR = Real Decreto 435/1995, de 27 de marzo
RIRNR_BOE_ID = "BOE-A-1995-7256"
RIRNR_CODIGO = "RIRNR"

DATABASE_URL = get_database_url()
RIRNR_SSL_VERIFY = get_bool_env("RIRNR_SSL_VERIFY", False)
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)


def run_sync(
    seed_norma: str | None = None,
    worker_name: str = "worker-rirnr",
) -> dict[str, int]:
    """Sincroniza el texto consolidado del RIRNR desde el BOE API."""
    boe_id = seed_norma or RIRNR_BOE_ID
    processed = 0
    articulos_upserted = 0
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)
    sync_start = datetime.now(UTC).isoformat()
    ssl_verify = get_bool_env("RIRNR_SSL_VERIFY", RIRNR_SSL_VERIFY)

    try:
        with httpx.Client(timeout=60.0, verify=ssl_verify) as client, engine.begin() as conn:
            _ensure_schema(conn)
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)

            # 1. Fetch metadata
            metadata = parse_metadata(
                RIRNR_CODIGO, boe_id,
                client.get(
                    f"https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{boe_id}/metadatos",
                    headers={"Accept": "application/json"},
                ).json()
            )
            upsert_norma(conn, metadata)
            processed += 1

            # 2. Fetch index
            index = fetch_index(client, boe_id)
            if not index:
                raise ValueError(f"No blocks found for {boe_id} in BOE API")

            # 3. Process each block
            for block_info in index:
                bloque = fetch_block(client, boe_id, block_info.id)

                # Solo procesar articulos (no titulos, capitulos, etc.)
                if not bloque.numero or bloque.tipo_articulo not in (
                    "articulo",
                    "articulo_transitorio",
                    "articulo_disposicion_adicional",
                    "articulo_disposicion_derogatoria",
                    "articulo_disposicion_final",
                ):
                    continue

                change = check_content_changed(
                    conn, worker_name, "bloque", bloque.bloque_id, bloque.texto
                )

                if not change.changed and destination_row_exists(
                    conn,
                    "version_articulo",
                    "boe_bloque_id",
                    bloque.bloque_id,
                ):
                    continue

                invalidated = invalidate_old_embeddings(conn, bloque.bloque_id)
                if invalidated:
                    print(
                        f"  [INVALIDATE] {invalidated} old embeddings for {bloque.bloque_id}"
                    )

                upsert_articulo(conn, RIRNR_CODIGO, bloque)
                record_revision(
                    conn,
                    worker_name,
                    "bloque",
                    bloque.bloque_id,
                    bloque.texto,
                )
                articulos_upserted += 1

            # 4. Link matters
            links_created = 0  # RIRNR doesn't use auto_link_doctrina

            # 5. Log
            log_sync(
                conn,
                worker_name,
                "ok",
                bloques_processed=processed,
                articulos_upserted=articulos_upserted,
                doctrina_links_created=links_created,
                started_at=sync_start,
            )

        return {"processed": processed, "articulos_upserted": articulos_upserted}
    except Exception as exc:
        entity_id = "rirnr"
        if not handle_worker_failure(engine, "rirnr", entity_id, "sync_entity", exc):
            logger.warning("Entity rirnr moved to dead-letter")
            return {"processed": 0, "articulos_upserted": 0}
        with engine.begin() as conn:
            _ensure_sync_log_table(conn)
            log_sync(
                conn,
                worker_name,
                "error",
                bloques_processed=processed,
                articulos_upserted=articulos_upserted,
                error_msg=str(exc),
                started_at=sync_start,
            )
        raise


def log_sync(conn, worker_name, status, **kwargs):
    """Escribe un registro en sync_log."""
    _ensure_sync_log_table(conn)
    started_at = kwargs.get("started_at") or datetime.now(UTC).isoformat()
    finished_at = datetime.now(UTC).isoformat()
    duration_ms = max(0, int((datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at)).total_seconds() * 1000))
    if conn.engine.dialect.name == "sqlite":
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(sync_log)"))}
    else:
        columns = {
            row[0]
            for row in conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = 'sync_log'")
            )
        }

    values = {
        "worker": worker_name,
        "started_at": started_at,
        "finished_at": finished_at,
        "status": status,
        "bloques_processed": kwargs.get("bloques_processed", 0),
        "articulos_upserted": kwargs.get("articulos_upserted", 0),
        "documentos_processed": kwargs.get("documentos_processed", 0),
        "documentos_upserted": kwargs.get("documentos_upserted", 0),
        "doctrina_links_created": kwargs.get("doctrina_links_created", 0),
        "error_msg": kwargs.get("error_msg"),
        "rows_processed": max(
            kwargs.get("bloques_processed", 0),
            kwargs.get("articulos_upserted", 0),
            kwargs.get("documentos_processed", 0),
            kwargs.get("documentos_upserted", 0),
            kwargs.get("doctrina_links_created", 0),
        ),
        "errors": 0 if not kwargs.get("error_msg") else 1,
        "duration_ms": duration_ms,
    }

    ordered_columns = [
        "worker",
        "started_at",
        "finished_at",
        "status",
        "bloques_processed",
        "articulos_upserted",
        "documentos_processed",
        "documentos_upserted",
        "doctrina_links_created",
        "error_msg",
        "rows_processed",
        "errors",
        "duration_ms",
    ]
    insert_columns = [column for column in ordered_columns if column in columns]
    placeholders = ", ".join(f":{column}" for column in insert_columns)
    conn.execute(
        text(
            f"INSERT INTO sync_log ({', '.join(insert_columns)}) VALUES ({placeholders})"
        ),
        {column: values[column] for column in insert_columns},
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="RIRNR worker: ingest Reglamento IRNR from BOE API"
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
        "--boe-id",
        type=str,
        default=None,
        help=f"BOE ID to ingest (default: {RIRNR_BOE_ID})",
    )
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("rirnr")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(seed_norma=args.boe_id, worker_name="cron-rirnr-weekly")
        print(
            f"[run-once] Procesados: {result['processed']}, articulos: {result['articulos_upserted']}"
        )
    else:
        print(f"Starting RIRNR worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced procesados={result['processed']}, articulos={result['articulos_upserted']} at {datetime.now().isoformat()}"
            )
            time.sleep(interval)
