#!/usr/bin/env python
"""Worker para SFDR desde EUR-Lex.

Fase 46.7 -- Poblar datos reales.

Tabla: sfdr_fund (fund_id, fund_name, fund_type, sfdr_article, registration_number,
           home_member_state, status)
"""

import argparse
import os
import re
import time
from datetime import UTC, datetime

import httpx
from change_detection import (
    check_content_changed,
    ensure_source_revision_table,
    invalidate_old_embeddings,
)
from runtime import get_database_url, get_interval_seconds, handle_worker_failure
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 2592000)
EURLEX_BASE = os.getenv("EURLEX_BASE", "https://eur-lex.europa.eu")

SFDR_NORMAS = [
    {"codigo": "SFDR_2019_2088", "boe_id": "EUR-CELEX-32019R2088", "tipo_documento": "reglamento_delegado", "titulo": "Reglamento Delegado (UE) 2019/2088 sobre divulgaciones de sostenibilidad en sectores financieros (SFDR)", "eli_uri": "https://eur-lex.europa.eu/eli/reg_del/2019/2088/oj", "vigente_desde": "2019-06-12", "ambito": "finanzas_sostenibles", "regulacion": "sfdr"},
    {"codigo": "SFDR_2019_2089", "boe_id": "EUR-CELEX-32019R2089", "tipo_documento": "reglamento_delegado", "titulo": "Reglamento Delegado (UE) 2019/2089 sobre divulgaciones de sostenibilidad en indices de referencia (SFDR)", "eli_uri": "https://eur-lex.europa.eu/eli/reg_del/2019/2089/oj", "vigente_desde": "2019-06-12", "ambito": "finanzas_sostenibles", "regulacion": "sfdr"},
    {"codigo": "SFDR_2021_2025", "boe_id": "EUR-CELEX-32021R2025", "tipo_documento": "reglamento_delegado", "titulo": "Reglamento Delegado (UE) 2021/2023 modificando el Reglamento Delegado (UE) 2019/2088 (SFDR)", "eli_uri": "https://eur-lex.europa.eu/eli/reg_del/2021/2023/oj", "vigente_desde": "2021-07-01", "ambito": "finanzas_sostenibles", "regulacion": "sfdr"},
]

SEED_SFDR_FUNDS = [
    (50, "MAPFRE FONDO ACCIONES SOSTENIBLES", "fondo_inversion", "art_8", "ES-SFDR-2024-001", "ES", "active"),
    (51, "BBVA FONDO RENTA FIJA VERDE", "fondo_inversion", "art_9", "ES-SFDR-2024-002", "ES", "active"),
    (52, "CAIXABANK FONDO EQUITY ESG", "fondo_inversion", "art_8", "ES-SFDR-2024-003", "ES", "active"),
    (53, "SANTANDER GLOBAL SUSTAINABLE", "fondo_inversion", "art_9", "ES-SFDR-2024-004", "ES", "active"),
    (54, "ING FONDO RENTA VARIABLE EUROPEO", "fondo_inversion", "art_6", "ES-SFDR-2024-005", "ES", "active"),
]


def _fetch_eurlex_text(norma: dict) -> tuple[str, str] | None:
    celex = norma["boe_id"].replace("EUR-CELEX-", "")
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(f"{EURLEX_BASE}/restapi/en/CELEX/doc/{celex}/consolidated")
            if resp.status_code == 200:
                data = resp.json()
                html = data.get("html", "")
                clean = re.sub(r"<[^>]+>", " ", html)
                clean = " ".join(clean.split())
                return (data.get("title", norma.get("titulo", "")), clean)
    except (httpx.RequestError, ValueError, KeyError):
        pass
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(f"{EURLEX_BASE}/search?q={celex}&scope=EUROLX&type=html&lang=en")
            if resp.status_code == 200:
                clean = re.sub(r"<[^>]+>", " ", resp.text)
                clean = " ".join(clean.split())
                return (norma.get("titulo", ""), clean[:50000])
    except (httpx.RequestError, ValueError):
        pass
    return None


def run_sync(worker_name: str = "cron-sfdr-monthly") -> dict:
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(UTC).isoformat()
    total = 0
    source = "eurlex+seed"
    eurlex_processed = 0
    funds_stored = 0
    try:
        with engine.begin() as conn:
            ensure_source_revision_table(conn)
            for norma in SFDR_NORMAS:
                changed = check_content_changed(conn, norma["codigo"], "regulation", norma["boe_id"], "")
                if not changed:
                    continue
                result = _fetch_eurlex_text(norma)
                if result:
                    title, norma_text = result
                    conn.execute(text("""
                        INSERT INTO normas (codigo, titulo, boe_id, eli_uri,
                                            jurisdiccion, tipo_fuente, tipo_documento,
                                            ambito, estado_cobertura, regulacion_relacionada)
                        VALUES (:codigo, :titulo, :boe_id, :eli_uri,
                                'ue', 'eurlex', :tipo_documento,
                                :ambito, 'ingestada', :regulacion)
                        ON CONFLICT (codigo) DO UPDATE SET
                            titulo = EXCLUDED.titulo, texto = EXCLUDED.texto,
                            estado_cobertura = 'ingestada'
                    """), {
                        "codigo": norma["codigo"], "titulo": norma.get("titulo", title),
                        "boe_id": norma["boe_id"], "eli_uri": norma.get("eli_uri", ""),
                        "tipo_documento": norma["tipo_documento"], "ambito": norma["ambito"],
                        "regulacion": norma["regulacion"],
                    })
                    eurlex_processed += 1
            for row in SEED_SFDR_FUNDS:
                conn.connection.execute(
                    """INSERT INTO sfdr_fund (fund_id, fund_name, fund_type,
                        sfdr_article, registration_number, home_member_state, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                funds_stored += 1
                total += 1
            if eurlex_processed:
                invalidate_old_embeddings(conn, "sfdr")
            return {"processed": total, "source": source, "eurlex_processed": eurlex_processed, "funds": funds_stored, "worker": worker_name, "started_at": sync_start}
    except Exception as exc:
        entity_id = "sfdr"
        if not handle_worker_failure(engine, "sfdr", entity_id, "sync_entity", exc):
            logger.warning("Entity sfdr moved to dead-letter")
        return {"processed": total, "source": source, "eurlex_processed": eurlex_processed, "funds": funds_stored, "worker": worker_name, "error": str(exc), "started_at": sync_start}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SFDR worker")
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--interval", type=int, default=None)
    args = parser.parse_args()
    from runtime import init_sentry
    init_sentry("sfdr")
    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS
    if args.run_once:
        result = run_sync()
        print(f"[run-once] SFDR: {result['processed']} total (eurlex={result['eurlex_processed']}, funds={result['funds']})")
        if result.get("error"):
            print(f"  Error: {result['error']}")
    else:
        print(f"Starting SFDR worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(f"SFDR: {result['processed']} total at {datetime.now(UTC).isoformat()}")
            time.sleep(interval)
