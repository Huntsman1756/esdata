#!/usr/bin/env python
"""Worker para Consumer Credit — Directive 2008/48/EC.

Fase 31.10 — Expansion regulatoria.

Ingesta desde:
- EUR-Lex Directive 2008/48/EC
- ESAP
- Supervisor nacional (Banco de Espana)

Usage:
    python consumer_credit.py --run-once
    python consumer_credit.py
"""

import argparse
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from change_detection import (
    check_content_changed,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    record_revision,
)
from runtime import get_database_url, get_interval_seconds, ensure_database_connection
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

EURLEX_BASE = os.getenv(
    "EURLEX_BASE",
    "https://eur-lex.europa.eu",
)

CONSUMER_CREDIT_NORMA = {
    "codigo": "CONSUMER_CREDIT_2008_0048",
    "boe_id": "EUR-CELEX-32008L0048",
    "titulo": "Directiva 2008/48/CE sobre los contratos de credito al consumidor",
    "eli_uri": "https://eur-lex.europa.eu/eli/dir/2008/48/oj",
    "jurisdiccion": "ue",
    "tipo_fuente": "eurlex",
    "tipo_documento": "directiva",
    "ambito": "credito_consumo_ue",
    "estado_cobertura": "ingestada",
}


def ensure_norma(db, norma):
    existing = db.execute(
        text("SELECT id FROM normas WHERE codigo = :codigo"),
        {"codigo": norma["codigo"]},
    ).mappings().first()

    if existing:
        return existing["id"]

    db.execute(
        text(
            """INSERT INTO normas (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, regulacion_relacionada)
               VALUES (:codigo, :titulo, :boe_id, :eli_uri, :jurisdiccion, :tipo_fuente, :tipo_documento, :ambito, :estado_cobertura, :regulacion)
               ON CONFLICT (codigo) DO UPDATE SET titulo=EXCLUDED.titulo, estado_cobertura=EXCLUDED.estado_cobertura"""
        ),
        {
            "codigo": norma["codigo"],
            "titulo": norma["titulo"],
            "boe_id": norma["boe_id"],
            "eli_uri": norma["eli_uri"],
            "jurisdiccion": norma["jurisdiccion"],
            "tipo_fuente": norma["tipo_fuente"],
            "tipo_documento": norma["tipo_documento"],
            "ambito": norma["ambito"],
            "estado_cobertura": norma["estado_cobertura"],
            "regulacion": "consumer_credit",
        },
    )
    db.commit()
    return db.execute(
        text("SELECT id FROM normas WHERE codigo = :codigo"),
        {"codigo": norma["codigo"]},
    ).mappings().first()["id"]


def fetch_eurlex_articles(norma, db):
    celex = norma["boe_id"].replace("EUR-CELEX-", "")
    search_url = f"{EURLEX_BASE}/search?q={celex}&scope=EUROLX&type=html&lang=en"

    try:
        resp = httpx.get(search_url, timeout=30)
        if resp.status_code != 200:
            return 0
    except httpx.RequestError:
        return 0

    articles = []
    for line in resp.text.split("\n"):
        line = line.strip()
        if line and (line.startswith("Art") or line.startswith("Article")):
            articles.append(line[:200])

    if not articles:
        return 0

    norma_id = ensure_norma(db, norma)
    count = 0
    for i, text in enumerate(articles):
        db.execute(
            text(
                """INSERT INTO articulo (norma_id, numero, texto, fuente_origen, regulacion_relacionada)
                   VALUES (:norma_id, :numero, :texto, 'eurlex', :regulacion)
                   ON CONFLICT DO NOTHING"""
            ),
            {
                "norma_id": norma_id,
                "numero": str(i + 1),
                "texto": text,
                "regulacion": "consumer_credit",
            },
        )
        count += 1

    db.commit()
    return count


def run_once():
    engine = create_engine(DATABASE_URL)
    ensure_database_connection(engine)
    total = 0

    with engine.begin() as conn:
        norma = CONSUMER_CREDIT_NORMA
        changed = check_content_changed(conn, norma)
        if changed:
            count = fetch_eurlex_articles(norma, conn)
            record_revision(conn, norma, f"consumer_credit: {count} articulos")
            total += count
            invalidate_old_embeddings(conn, "consumer_credit")

    return total


def main():
    parser = argparse.ArgumentParser(description="Consumer Credit worker")
    parser.add_argument("--run-once", action="store_true", help="Execute once and exit")
    args = parser.parse_args()

    if args.run_once:
        total = run_once()
        print(f"Consumer Credit worker: {total} articulos procesados")
        return

    from runtime import handle_worker_failure
    from sqlalchemy import create_engine

    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata")
    engine = create_engine(db_url)
    ensure_database_connection(engine)

    while True:
        try:
            total = run_once()
            print(f"Consumer Credit worker: {total} articulos, next sync in {SYNC_INTERVAL_SECONDS}s")
        except Exception as exc:
            print(f"Consumer Credit worker error: {exc}")
            if not handle_worker_failure(engine, "consumer_credit", "loop", "main", exc):
                raise

        time.sleep(SYNC_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
