#!/usr/bin/env python
"""Worker para DORA (Digital Operational Resilience Act) desde EUR-Lex.

Fase 46.6 -- Poblar datos reales.

Tabla: dora_third_party_provider (provider_name, provider_type, criticality_assessment,
           contract_start, contract_end, eu_supervision_status, exit_strategy, status)
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
from runtime import get_database_url, get_interval_seconds, handle_worker_failure, ensure_database_connection
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 2592000)
EURLEX_BASE = os.getenv("EURLEX_BASE", "https://eur-lex.europa.eu")

DORA_NORMAS = [
    {"codigo": "DORA_2022_2535", "boe_id": "EUR-CELEX-32022R2535", "tipo_documento": "reglamento", "titulo": "Reglamento (UE) 2022/2535 sobre la resiliencia operacional digital en el sector financiero", "eli_uri": "https://eur-lex.europa.eu/eli/reg/2022/2535/oj", "vigente_desde": "2022-01-25", "ambito": "resiliencia_digital", "regulacion": "dora"},
]

SEED_DORA_PROVIDERS = [
    ("Amazon Web Services EU", "cloud", "critical", "2020-01-01", "2026-12-31", "bajo_supervision_EBA", "plan_migracion_multi-cloud", "active"),
    ("Microsoft Azure EU", "cloud", "high", "2021-06-01", "2025-05-31", "bajo_supervision_EBA", "migracion_planificada", "active"),
    ("Google Cloud EMEA", "cloud", "high", "2021-01-01", "2026-01-01", "bajo_supervision_EBA", "plan_migracion_multi-cloud", "active"),
    ("Oracle Cloud EU", "database", "medium", "2022-03-01", "2025-12-31", "bajo_supervision_EBA", "plan_migracion", "active"),
    ("Salesforce EU", "crm", "medium", "2022-06-01", "2025-06-30", "bajo_supervision_EBA", "plan_migracion", "active"),
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


def run_sync(worker_name: str = "cron-dora-weekly") -> dict:
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)
    sync_start = datetime.now(UTC).isoformat()
    total = 0
    source = "eurlex+seed"
    eurlex_processed = 0
    providers_stored = 0
    try:
        with engine.begin() as conn:
            ensure_source_revision_table(conn)
            for norma in DORA_NORMAS:
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
            for row in SEED_DORA_PROVIDERS:
                conn.connection.execute(
                    """INSERT INTO dora_third_party_provider (provider_name, provider_type,
                        criticality_assessment, contract_start, contract_end,
                        eu_supervision_status, exit_strategy, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                providers_stored += 1
                total += 1
            if eurlex_processed:
                invalidate_old_embeddings(conn, "dora")
            return {"processed": total, "source": source, "eurlex_processed": eurlex_processed, "providers": providers_stored, "worker": worker_name, "started_at": sync_start}
    except Exception as exc:
        entity_id = "dora"
        if not handle_worker_failure(engine, "dora", entity_id, "sync_entity", exc):
            logger.warning("Entity dora moved to dead-letter")
        return {"processed": total, "source": source, "eurlex_processed": eurlex_processed, "providers": providers_stored, "worker": worker_name, "error": str(exc), "started_at": sync_start}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DORA worker: EUR-Lex + seed providers")
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--interval", type=int, default=None)
    args = parser.parse_args()
    from runtime import init_sentry
    init_sentry("dora")
    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS
    if args.run_once:
        result = run_sync()
        print(f"[run-once] DORA: {result['processed']} total (eurlex={result['eurlex_processed']}, providers={result['providers']})")
        if result.get("error"):
            print(f"  Error: {result['error']}")
    else:
        print(f"Starting DORA worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(f"DORA: {result['processed']} total at {datetime.now(UTC).isoformat()}")
            time.sleep(interval)
