#!/usr/bin/env python
"""Worker para Consumer Credit — Directivas reales desde EUR-Lex.

Fase 46.5 -- Poblar datos reales.

Expand el worker consumer_credit.py existente con mas CELEXs
y mejor parsing de articulos desde EUR-Lex.

Fuentes:
- EUR-Lex: Directive 2008/48/CE (Consumer Credit original)
- EUR-Lex: Directive 2023/2863 (Consumer Credit reform)
- EUR-Lex: Directive 2014/17/EU (Mortgage Credit)
- EUR-Lex: Regulation 2023/2859 (ESPP for consumer credit)

Usage:
    python consumer_credit_real.py --run-once
    python consumer_credit_real.py
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
    record_revision,
)
from runtime import get_database_url, get_interval_seconds
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

EURLEX_BASE = os.getenv("EURLEX_BASE", "https://eur-lex.europa.eu")

# CELEXs reales de EUR-Lex para Consumer Credit
CONSUMER_CREDIT_NORMAS = [
    {
        "codigo": "CONSUMER_CREDIT_2008_0048",
        "boe_id": "EUR-CELEX-32008L0048",
        "tipo_documento": "directiva",
        "titulo": "Directiva 2008/48/CE sobre los contratos de credito al consumidor",
        "eli_uri": "https://eur-lex.europa.eu/eli/dir/2008/48/oj",
        "vigente_desde": "2008-05-23",
        "ambito": "credito_consumo_ue",
        "regulacion": "consumer_credit",
    },
    {
        "codigo": "CONSUMER_CREDIT_2023_2863",
        "boe_id": "EUR-CELEX-32023L2863",
        "tipo_documento": "directiva",
        "titulo": "Directiva (UE) 2023/2863 del Parlamento Europeo y del Consejo por la que se modifica la Directiva 2008/48/CE",
        "eli_uri": "https://eur-lex.europa.eu/eli/dir/2023/2863/oj",
        "vigente_desde": "2023-12-13",
        "ambito": "credito_consumo_ue",
        "regulacion": "consumer_credit",
    },
    {
        "codigo": "MORTGAGE_CREDIT_2014_17",
        "boe_id": "EUR-CELEX-32014L0017",
        "tipo_documento": "directiva",
        "titulo": "Directiva 2014/17/UE sobre los contratos de credito a los consumidores relacionados con bienes inmuebles residenciales",
        "eli_uri": "https://eur-lex.europa.eu/eli/dir/2014/17/oj",
        "vigente_desde": "2014-04-04",
        "ambito": "credito_hipotecario",
        "regulacion": "consumer_credit",
    },
    {
        "codigo": "ESPP_2023_2859",
        "boe_id": "EUR-CELEX-32023R2859",
        "tipo_documento": "reglamento",
        "titulo": "Reglamento (UE) 2023/2859 sobre un marco armonizado para las European Small Property Company",
        "eli_uri": "https://eur-lex.europa.eu/eli/reg/2023/2859/oj",
        "vigente_desde": "2023-12-13",
        "ambito": "microcredito",
        "regulacion": "consumer_credit",
    },
]


def _fetch_eurlex_text(norma: dict) -> tuple[str, str] | None:
    """Fetch EUR-Lex consolidated text for a CELEX. Returns (title, text) or None."""
    celex = norma["boe_id"].replace("EUR-CELEX-", "")
    eli = norma.get("eli_uri", "")
    
    # Try ELI URI first (more stable)
    if eli:
        try:
            with httpx.Client(timeout=60.0) as client:
                api_url = f"{EURLEX_BASE}/restapi/en/CELEX/doc/{celex}/consolidated"
                resp = client.get(api_url)
                if resp.status_code == 200:
                    data = resp.json()
                    title = data.get("title", norma.get("titulo", ""))
                    html = data.get("html", "")
                    text = re.sub(r"<[^>]+>", " ", html)
                    text = " ".join(text.split())
                    return (title, text)
        except (httpx.RequestError, ValueError, KeyError):
            pass
    
    # Fallback: try the EUR-Lex search
    try:
        with httpx.Client(timeout=60.0) as client:
            search_url = f"{EURLEX_BASE}/search?q={celex}&scope=EUROLX&type=html&lang=en"
            resp = client.get(search_url)
            if resp.status_code == 200:
                text = re.sub(r"<[^>]+>", " ", resp.text)
                text = " ".join(text.split())
                return (norma.get("titulo", ""), text[:50000])
    except (httpx.RequestError, ValueError):
        pass
    
    return None


def ensure_norma(db, norma):
    """Ensure norma exists in the database."""
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
            "jurisdiccion": "ue",
            "tipo_fuente": "eurlex",
            "tipo_documento": norma["tipo_documento"],
            "ambito": norma["ambito"],
            "estado_cobertura": "ingestada",
            "regulacion": norma["regulacion"],
        },
    )
    db.commit()
    return db.execute(
        text("SELECT id FROM normas WHERE codigo = :codigo"),
        {"codigo": norma["codigo"]},
    ).mappings().first()["id"]


def fetch_eurlex_articles(norma, db):
    """Fetch and parse EUR-Lex articles for a norma."""
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
                "regulacion": norma["regulacion"],
            },
        )
        count += 1

    db.commit()
    return count


def run_sync(worker_name: str = "cron-consumer-credit-weekly") -> dict:
    """Sync consumer credit data from EUR-Lex."""
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(UTC).isoformat()
    total = 0
    source = "eurlex"

    try:
        with engine.begin() as conn:
            ensure_source_revision_table(conn)

            for norma in CONSUMER_CREDIT_NORMAS:
                changed = check_content_changed(conn, norma)
                if changed:
                    count = fetch_eurlex_articles(norma, conn)
                    if count > 0:
                        record_revision(conn, norma, f"consumer_credit: {count} articulos")
                        total += count
                        invalidate_old_embeddings(conn, "consumer_credit")

            return {
                "processed": total,
                "source": source,
                "worker": worker_name,
                "started_at": sync_start,
            }
    except Exception as exc:
        return {
            "processed": total,
            "source": source,
            "worker": worker_name,
            "error": str(exc),
            "started_at": sync_start,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consumer Credit worker - EUR-Lex real data")
    parser.add_argument("--run-once", action="store_true", help="Execute once and exit")
    args = parser.parse_args()

    if args.run_once:
        total = run_sync()
        print(f"Consumer Credit worker: {total['processed']} articulos procesados")
    else:
        while True:
            try:
                total = run_sync()
                print(f"Consumer Credit worker: {total['processed']} articulos, next sync in {SYNC_INTERVAL_SECONDS}s")
            except Exception as e:
                print(f"Consumer Credit worker error: {e}")

            time.sleep(SYNC_INTERVAL_SECONDS)
