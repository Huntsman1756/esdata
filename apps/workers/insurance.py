#!/usr/bin/env python
"""Worker para IDD y Solvency II — seguros y supervision prudencial.

Fase 31.10 — Expansion regulatoria.

Ingesta desde:
- IDD: Directiva 2016/97/UE
- Solvency II: Directiva 2009/138/CE
- EIOPA reports
- ESAP

Usage:
    python insurance.py --run-once --domain idd
    python insurance.py --run-once --domain solvency
    python insurance.py --run-once --domain all
    python insurance.py
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
from runtime import get_database_url, get_interval_seconds
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

EURLEX_BASE = os.getenv(
    "EURLEX_BASE",
    "https://eur-lex.europa.eu",
)

IDD_NORMA = {
    "codigo": "IDD_2016_0097",
    "boe_id": "EUR-CELEX-32016L0097",
    "titulo": "Directiva 2016/97/UE sobre la distribucion de seguros (IDD)",
    "eli_uri": "https://eur-lex.europa.eu/eli/dir/2016/97/oj",
    "jurisdiccion": "ue",
    "tipo_fuente": "eurlex",
    "tipo_documento": "directiva",
    "ambito": "distribucion_seguros_ue",
    "estado_cobertura": "ingestada",
}

SOLVENCY_NORMA = {
    "codigo": "SOLVENCY_2009_0138",
    "boe_id": "EUR-CELEX-32009L0138",
    "titulo": "Directiva 2009/138/CE sobre el acceso y la ejecucion de la actividad de seguros y reaseguros (Solvency II)",
    "eli_uri": "https://eur-lex.europa.eu/eli/dir/2009/138/oj",
    "jurisdiccion": "ue",
    "tipo_fuente": "eurlex",
    "tipo_documento": "directiva",
    "ambito": "supervision_seguros_ue",
    "estado_cobertura": "ingestada",
}

DOMAIN_NORMAS = {
    "idd": IDD_NORMA,
    "solvency": SOLVENCY_NORMA,
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
            "regulacion": "insurance",
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
                "regulacion": "insurance",
            },
        )
        count += 1

    db.commit()
    return count


def run_once(domain):
    engine = create_engine(DATABASE_URL)
    total = 0

    with engine.begin() as conn:
        if domain in ("idd", "all"):
            norma = DOMAIN_NORMAS["idd"]
            changed = check_content_changed(conn, norma)
            if changed:
                count = fetch_eurlex_articles(norma, conn)
                record_revision(conn, norma, f"idd: {count} articulos")
                total += count
                invalidate_old_embeddings(conn, "insurance")

        if domain in ("solvency", "all"):
            norma = DOMAIN_NORMAS["solvency"]
            changed = check_content_changed(conn, norma)
            if changed:
                count = fetch_eurlex_articles(norma, conn)
                record_revision(conn, norma, f"solvency: {count} articulos")
                total += count
                invalidate_old_embeddings(conn, "insurance")

    return total


def main():
    parser = argparse.ArgumentParser(description="IDD/Solvency II worker")
    parser.add_argument("--run-once", action="store_true", help="Execute once and exit")
    parser.add_argument("--domain", default="all", choices=["idd", "solvency", "all"])
    args = parser.parse_args()

    if args.run_once:
        total = run_once(args.domain)
        print(f"Insurance worker: {total} articulos procesados")
        return

    while True:
        try:
            total = run_once(args.domain)
            print(f"Insurance worker: {total} articulos, next sync in {SYNC_INTERVAL_SECONDS}s")
        except Exception as e:
            print(f"Insurance worker error: {e}")

        time.sleep(SYNC_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
