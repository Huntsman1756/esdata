#!/usr/bin/env python
"""Worker principal para sincronizar campanas y contenido de modelos AEAT."""

import os
import time

from sqlalchemy import create_engine

from modelos_support import (
    derive_campaign_operativa,
    SyncResult,
    build_client,
    detect_campaigns,
    ensure_campaigns,
    fetch_page,
    get_campaign_row,
    get_model_id,
    get_model_metadata,
    get_model_rows,
    get_previous_campaign_casillas_count,
    log_sync_result,
    scrape_casillas_from_page,
    scrape_claves_from_page,
    scrape_instructions_from_page,
    upsert_campaign_operativa,
    upsert_casillas,
    upsert_claves,
    upsert_instructions,
)
from runtime import configure_logging, get_bool_env, get_database_url, get_interval_seconds

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("MODELOS_SYNC_INTERVAL", 86400)
SSL_VERIFY = get_bool_env("DGT_SSL_VERIFY", False)

logger = configure_logging("worker-modelos")


def _client():
    return build_client(SSL_VERIFY)


def _fetch_model_page(url_info: str | None) -> str | None:
    return fetch_page(_client, logger, url_info, "model page")


def _fetch_instruction_page(url_instrucciones: str | None) -> str | None:
    return fetch_page(_client, logger, url_instrucciones, "instructions")


def _scrape_campaign(engine, modelo_id: int, modelo_codigo: str, campana: str, url_info: str, url_instrucciones_fallback: str | None, result: SyncResult):
    with engine.begin() as conn:
        campaign_row = get_campaign_row(conn, modelo_id, campana)
        if not campaign_row:
            return

        campana_id, campaign_instruction_url = campaign_row
        previous_casillas_count = get_previous_campaign_casillas_count(conn, modelo_id, campana)

    url_to_fetch = campaign_instruction_url or url_instrucciones_fallback or url_info
    html = _fetch_instruction_page(url_to_fetch) or _fetch_model_page(url_info)
    if not html:
        logger.warning(f"  {modelo_codigo}/{campana}: no HTML to scrape")
        return

    scraped_casillas = scrape_casillas_from_page(html, modelo_codigo)
    if not scraped_casillas and previous_casillas_count > 0:
        message = (
            f"DRIFT_AEAT: modelo {modelo_codigo} campana {campana} devolvio 0 casillas "
            f"tras scraping, pero existen {previous_casillas_count} casillas en campanas previas. "
            "Verificar HTML de AEAT manualmente y no sustituir datos previos con vacio."
        )
        logger.error(message)
        result.errors.append(message)
        return

    if scraped_casillas:
        with engine.begin() as conn:
            count = upsert_casillas(conn, campana_id, scraped_casillas)
        result.casillas_upserted += count
        logger.info(f"  {modelo_codigo}/{campana}: {count} casillas scraped")

    scraped_claves = scrape_claves_from_page(html)
    if scraped_claves:
        with engine.begin() as conn:
            count = upsert_claves(conn, campana_id, scraped_claves)
        result.claves_upserted += count
        logger.info(f"  {modelo_codigo}/{campana}: {count} claves scraped")

    scraped_instr = scrape_instructions_from_page(html)
    if scraped_instr:
        operativa_status = "sin metadato operativo"
        with engine.begin() as conn:
            count = upsert_instructions(conn, campana_id, scraped_instr)
            metadata = get_model_metadata(conn, modelo_codigo)
            if metadata:
                operativa_payload = derive_campaign_operativa(
                    modelo_codigo=modelo_codigo,
                    impuesto=metadata["impuesto"],
                    periodo=metadata["periodo"],
                    instrucciones=scraped_instr,
                )
                operativa_payload["norma_base"] = None
                operativa_payload["nota"] = (
                    "Borrador derivado automaticamente desde instrucciones AEAT."
                )
                if upsert_campaign_operativa(conn, campana_id, operativa_payload):
                    result.operativa_upserted += 1
                    operativa_status = "operativa derivada guardada"
                else:
                    result.operativa_skipped += 1
                    operativa_status = "operativa curada preservada"
        result.instrucciones_upserted += count
        logger.info(
            f"  {modelo_codigo}/{campana}: {count} instructions upserted, "
            f"{operativa_status}"
        )


def sync_model(engine, modelo_codigo: str, url_info: str, url_instrucciones: str | None, result: SyncResult):
    result.models_checked += 1

    with engine.begin() as conn:
        modelo_id = get_model_id(conn, modelo_codigo)
        if not modelo_id:
            logger.warning(f"Modelo {modelo_codigo} not found in DB, skipping")
            result.errors.append(f"Modelo {modelo_codigo} not found")
            return

    main_html = _fetch_model_page(url_info) if url_info else None
    if not main_html:
        logger.warning(f"No HTML content for modelo {modelo_codigo}")
        result.errors.append(f"No content for {modelo_codigo}")
        return

    detected_campaigns = detect_campaigns(main_html, modelo_codigo) or ["2025"]

    with engine.begin() as conn:
        ensure_campaigns(
            conn,
            modelo_id,
            modelo_codigo,
            detected_campaigns,
            url_instrucciones,
            url_info,
            result,
            logger,
        )

    for campana in detected_campaigns:
        _scrape_campaign(
            engine,
            modelo_id,
            modelo_codigo,
            campana,
            url_info,
            url_instrucciones,
            result,
        )


def _log_sync(engine, result: SyncResult) -> None:
    try:
        with engine.begin() as conn:
            log_sync_result(conn, result)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to log to sync_log: {exc}")


def _list_models(engine):
    with engine.begin() as conn:
        return get_model_rows(conn)


def run_sync(engine, run_once: bool = False):
    logger.info("Starting modelos worker...")

    while True:
        result = SyncResult()
        logger.info("=== Syncing model data from AEAT ===")

        try:
            models = _list_models(engine)
            logger.info(f"Found {len(models)} models to sync")

            for modelo_codigo, url_info, url_instr in models:
                url = url_instr or url_info
                if not url:
                    logger.warning(f"  SKIP {modelo_codigo}: no URL")
                    continue

                try:
                    logger.info(f"  Syncing {modelo_codigo}...")
                    sync_model(engine, modelo_codigo, url_info or "", url_instr, result)
                except Exception as exc:  # noqa: BLE001
                    logger.error(f"  ERROR {modelo_codigo}: {exc}")
                    result.errors.append(f"{modelo_codigo}: {exc}")

            logger.info(
                f"Sync complete: {result.models_checked} checked, "
                f"{result.campaigns_created} new campaigns, "
                f"{result.casillas_upserted} casillas, "
                f"{result.claves_upserted} claves, "
                f"{result.instrucciones_upserted} instrucciones, "
                f"{result.operativa_upserted} operativas, "
                f"{result.operativa_skipped} preservadas"
            )
            if result.errors:
                logger.warning(f"Errors: {result.errors}")

            _log_sync(engine, result)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Sync failed: {exc}")

        if run_once:
            break

        logger.info(f"Next sync in {SYNC_INTERVAL_SECONDS}s")
        time.sleep(SYNC_INTERVAL_SECONDS)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scrape AEAT model content")
    parser.add_argument("--db-url", help="Database URL")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, help="Sync interval in seconds")
    args = parser.parse_args()

    global SYNC_INTERVAL_SECONDS

    db_url = args.db_url or os.getenv("DATABASE_URL", DATABASE_URL)
    SYNC_INTERVAL_SECONDS = args.interval or SYNC_INTERVAL_SECONDS

    logger.info(f"DB: {db_url[:50]}...")
    logger.info(f"Interval: {SYNC_INTERVAL_SECONDS}s")
    logger.info(f"Run once: {args.run_once}")

    engine = create_engine(db_url)
    run_sync(engine, run_once=args.run_once)


if __name__ == "__main__":
    main()
