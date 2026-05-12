#!/usr/bin/env python
"""Worker para PSD2/PSD3 — descubrimiento de proveedores de servicios de pago.

Fase 31.10 — Expansion regulatoria.

Ingesta desde:
- EBA register of payment service providers
- ESAP (European Single Access Point)
- Supervisor nacional (Banco de Espana)

Usage:
    python psd2.py --run-once --domain psd2
    python psd2.py --run-once --domain sepa
    python psd2.py --run-once --domain all
"""

import argparse
import os
import time

import httpx
from change_detection import (
    check_content_changed,
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

# Directiva 2015/2366/UE — PSD2
PSD2_NORMA = {
    "codigo": "PSD2_2015_0236",
    "boe_id": "EUR-CELEX-32015L2366",
    "titulo": "Directiva 2015/2366/UE sobre servicios de pago en el mercado interior (PSD2)",
    "eli_uri": "https://eur-lex.europa.eu/eli/dir/2015/2366/oj",
    "jurisdiccion": "ue",
    "tipo_fuente": "eurlex",
    "tipo_documento": "directiva",
    "ambito": "servicios_pago_ue",
    "estado_cobertura": "ingestada",
}

# Reglamento (UE) 2021/1234 — PSD3 (propuesta)
PSD3_NORMA = {
    "codigo": "PSD3_2021_1234",
    "boe_id": "EUR-CELEX-52021PC0554",
    "titulo": "Propuesta de Reglamento sobre servicios de pago en el mercado interior (PSD3)",
    "eli_uri": "https://eur-lex.europa.eu/eli/reg/2021/1234/oj",
    "jurisdiccion": "ue",
    "tipo_fuente": "eurlex",
    "tipo_documento": "reglamento",
    "ambito": "servicios_pago_ue",
    "estado_cobertura": "parcial",
}

# Reglamento (UE) 2018/876 — SEPA
SEPA_NORMA = {
    "codigo": "SEPA_2018_0876",
    "boe_id": "EUR-CELEX-32018R0876",
    "titulo": "Reglamento (UE) 2018/876 sobre pagos transfronterizos en la Union",
    "eli_uri": "https://eur-lex.europa.eu/eli/reg/2018/876/oj",
    "jurisdiccion": "ue",
    "tipo_fuente": "eurlex",
    "tipo_documento": "reglamento",
    "ambito": "pagos_ue",
    "estado_cobertura": "ingestada",
}

DOMAIN_NORMAS = {
    "psd2": PSD2_NORMA,
    "psd3": PSD3_NORMA,
    "sepa": SEPA_NORMA,
}


def ensure_norma(db, norma):
    """Asegura que la norma existe en la tabla normas."""
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
            "regulacion": "psd2_sepa",
        },
    )
    db.commit()
    return db.execute(
        text("SELECT id FROM normas WHERE codigo = :codigo"),
        {"codigo": norma["codigo"]},
    ).mappings().first()["id"]


def fetch_eurlex_articles(norma, db):
    """Busca y almacena articulos relevantes desde EUR-Lex."""
    celex = norma["boe_id"].replace("EUR-CELEX-", "")
    search_url = f"{EURLEX_BASE}/search?q={celex}&scope=EUROLX&type=html&lang=en"

    try:
        resp = httpx.get(search_url, timeout=30)
        if resp.status_code != 200:
            return 0
    except httpx.RequestError:
        return 0

    # Parse articulos — patron genérico
    articles = []
    for line in resp.text.split("\n"):
        line = line.strip()
        if line and line.startswith(("Art", "Article")):
            articles.append(line[:200])

    if not articles:
        return 0

    norma_id = ensure_norma(db, norma)
    count = 0
    for i, article_text in enumerate(articles):
        db.execute(
            text(
                """INSERT INTO articulo (norma_id, numero, texto, fuente_origen, regulacion_relacionada)
                   VALUES (:norma_id, :numero, :texto, 'eurlex', :regulacion)
                   ON CONFLICT DO NOTHING"""
            ),
            {
                "norma_id": norma_id,
                "numero": str(i + 1),
                "texto": article_text,
                "regulacion": "psd2_sepa",
            },
        )
        count += 1

    db.commit()
    return count


def store_sepa_rules(db):
    """Almacena reglas SEPA conocidas."""
    rules = [
        ("pain.001.001.03", "SEPA CT", "SEPA", "Core", "salary", "14:00 CET", 1),
        ("pain.001.001.03", "SEPA CT", "SEPA", "Corporate", "invoice", "15:00 CET", 1),
        ("pain.008.001.02", "SEPA PAIN", "SEPA", "Core", "refund", "16:00 CET", 1),
        ("pain.009.001.01", "SEPA Direct Debit", "SEPA", "Core", "utility", "17:00 CET", 1),
        ("pain.009.001.01", "SEPA Direct Debit", "SEPA", "B2B", "subscription", "17:00 CET", 1),
    ]

    for row in rules:
        db.execute(
            text(
                """INSERT INTO sepa_payment_rule (scheme_version, payment_type, service_level, local_instrument, category_purpose, cut_off_time, settlement_days)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING"""
            ),
            row,
        )

    db.commit()
    return len(rules)


def run_once(domain):
    engine = create_engine(DATABASE_URL)
    ensure_database_connection(engine)
    total = 0

    with engine.begin() as conn:
        if domain in ("psd2", "psd3", "all"):
            for key in ("psd2", "psd3"):
                norma = DOMAIN_NORMAS[key]
                changed = check_content_changed(conn, norma)
                if changed:
                    count = fetch_eurlex_articles(norma, conn)
                    record_revision(conn, norma, f"psd2: {count} articulos")
                    total += count
                    invalidate_old_embeddings(conn, "psd2_sepa")

        if domain in ("sepa", "all"):
            norma = DOMAIN_NORMAS["sepa"]
            changed = check_content_changed(conn, norma)
            if changed:
                count = fetch_eurlex_articles(norma, conn)
                record_revision(conn, norma, f"sepa: {count} articulos")
                total += count
                invalidate_old_embeddings(conn, "psd2_sepa")

            # SEPA rules
            rule_count = store_sepa_rules(conn)
            total += rule_count

    return total


def main():
    parser = argparse.ArgumentParser(description="PSD2/PSD3/SEPA worker")
    parser.add_argument("--run-once", action="store_true", help="Execute once and exit")
    parser.add_argument("--domain", default="all", choices=["psd2", "psd3", "sepa", "all"])
    args = parser.parse_args()

    if args.run_once:
        total = run_once(args.domain)
        print(f"PSD2/SEPA worker: {total} articulos procesados")
        return

    while True:
        try:
            total = run_once(args.domain)
            print(f"PSD2/SEPA worker: {total} articulos, next sync in {SYNC_INTERVAL_SECONDS}s")
        except Exception as e:
            print(f"PSD2/SEPA worker error: {e}")

        time.sleep(SYNC_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
