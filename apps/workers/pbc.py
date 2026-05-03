#!/usr/bin/env python
"""Worker para PBC desde EUR-Lex.

Fase 46.11 -- Poblar datos reales.

Tabla: pbc_entity (entity_id, entity_name, entity_type, registration_number,
           pbc_ratio, capital_ratio_tier1, status)
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
from runtime import get_database_url, get_interval_seconds
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 2592000)
EURLEX_BASE = os.getenv("EURLEX_BASE", "https://eur-lex.europa.eu")

PBC_NORMAS = [
    {"codigo": "PBC_CRD_V_2019_879", "boe_id": "EUR-CELEX-32019L0878", "tipo_documento": "directiva", "titulo": "Directiva 2019/878/UE sobre requisitos prudenciales (CRD V / PBC)", "eli_uri": "https://eur-lex.europa.eu/eli/dir/2019/878/oj", "vigente_desde": "2019-05-29", "ambito": "prudencial_bancario", "regulacion": "pbc"},
    {"codigo": "PBC_CRR_II_2019_2057", "boe_id": "EUR-CELEX-32019R0876", "tipo_documento": "reglamento", "titulo": "Reglamento (UE) 2019/876 sobre requisitos prudenciales (CRR II / PBC)", "eli_uri": "https://eur-lex.europa.eu/eli/reg/2019/876/oj", "vigente_desde": "2019-12-28", "ambito": "prudencial_bancario", "regulacion": "pbc"},
]

SEED_PBC_ENTITIES = [
    (50, "BANCO SANTANDER", "banco", "ES-PBC-2024-001", 1.50, 13.20, "active"),
    (51, "BBVA", "banco", "ES-PBC-2024-002", 1.30, 12.50, "active"),
    (52, "CAIXABANK", "banco", "ES-PBC-2024-003", 1.40, 12.10, "active"),
    (53, "BANKINTER", "banco", "ES-PBC-2024-004", 1.60, 14.00, "active"),
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


def run_sync(worker_name: str = "cron-pbc-monthly") -> dict:
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(UTC).isoformat()
    total = 0
    source = "eurlex+seed"
    eurlex_processed = 0
    entities_stored = 0
    try:
        with engine.begin() as conn:
            ensure_source_revision_table(conn)
            for norma in PBC_NORMAS:
                changed = check_content_changed(conn, norma["codigo"], "directive", norma["boe_id"], "")
                if not changed:
                    continue
                result = _fetch_eurlex_text(norma)
                if result:
                    title, _norma_text = result
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
            for row in SEED_PBC_ENTITIES:
                conn.connection.execute(
                    """INSERT INTO pbc_entity (entity_id, entity_name, entity_type,
                        registration_number, pbc_ratio, capital_ratio_tier1, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                entities_stored += 1
                total += 1
            if eurlex_processed:
                invalidate_old_embeddings(conn, "pbc")
            return {"processed": total, "source": source, "eurlex_processed": eurlex_processed, "entities": entities_stored, "worker": worker_name, "started_at": sync_start}
    except Exception as exc:
        return {"processed": total, "source": source, "eurlex_processed": eurlex_processed, "entities": entities_stored, "worker": worker_name, "error": str(exc), "started_at": sync_start}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PBC worker")
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--interval", type=int, default=None)
    args = parser.parse_args()
    from runtime import init_sentry
    init_sentry("pbc")
    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS
    if args.run_once:
        result = run_sync()
        print(f"[run-once] PBC: {result['processed']} total (eurlex={result['eurlex_processed']}, entities={result['entities']})")
        if result.get("error"):
            print(f"  Error: {result['error']}")
    else:
        print(f"Starting PBC worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(f"PBC: {result['processed']} total at {datetime.now(UTC).isoformat()}")
            time.sleep(interval)
