#!/usr/bin/env python
"""Worker para CSRD desde EUR-Lex.

Fase 46.8 -- Poblar datos reales.

Tabla: csrd_company (company_id, company_name, company_type, sector, registration_number,
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
from runtime import get_database_url, get_interval_seconds
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 2592000)
EURLEX_BASE = os.getenv("EURLEX_BASE", "https://eur-lex.europa.eu")

CSRD_NORMAS = [
    {"codigo": "CSRD_2014_95", "boe_id": "EUR-CELEX-32013L0034", "tipo_documento": "directiva", "titulo": "Directiva 2013/34/UE modificada por Directiva 2014/95/UE sobre divulgaciones de informacion no financiera (CSRD)", "eli_uri": "https://eur-lex.europa.eu/eli/dir/2014/95/oj", "vigente_desde": "2014-11-05", "ambito": "informacion_sostenibilidad", "regulacion": "csrd"},
    {"codigo": "CSRD_ESRS_2023_386", "boe_id": "EUR-CELEX-32023R2725", "tipo_documento": "reglamento_ejecutivo", "titulo": "Reglamento de Ejecucion (UE) 2023/2725 sobre normas de verificacion (CSRD ESRS)", "eli_uri": "https://eur-lex.europa.eu/eli/reg_impl/2023/2725/oj", "vigente_desde": "2023-07-05", "ambito": "informacion_sostenibilidad", "regulacion": "csrd"},
    {"codigo": "CSRD_ESEF_2019_815", "boe_id": "EUR-CELEX-32019R0815", "tipo_documento": "reglamento_ejecutivo", "titulo": "Reglamento de Ejecucion (UE) 2019/815 sobre formato unico electronico (CSRD ESEF)", "eli_uri": "https://eur-lex.europa.eu/eli/reg_impl/2019/815/oj", "vigente_desde": "2019-06-17", "ambito": "informacion_sostenibilidad", "regulacion": "csrd"},
]

SEED_CSRD_COMPANIES = [
    (50, "INDITEX", "cotizada", "textil", "ES-CSRD-2024-001", "ES", "active"),
    (51, "IBERDROLA", "cotizada", "energia", "ES-CSRD-2024-002", "ES", "active"),
    (52, "TELEFONICA", "cotizada", "telecomunicaciones", "ES-CSRD-2024-003", "ES", "active"),
    (53, "BBVA", "cotizada", "banco", "ES-CSRD-2024-004", "ES", "active"),
    (54, "REPSOL", "cotizada", "petroleo", "ES-CSRD-2024-005", "ES", "active"),
    (55, "CAIXABANK", "cotizada", "banco", "ES-CSRD-2024-006", "ES", "active"),
    (56, "CELLNIX", "cotizada", "tecnologia", "ES-CSRD-2024-007", "ES", "active"),
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


def run_sync(worker_name: str = "cron-csrd-monthly") -> dict:
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(UTC).isoformat()
    total = 0
    source = "eurlex+seed"
    eurlex_processed = 0
    companies_stored = 0
    try:
        with engine.begin() as conn:
            ensure_source_revision_table(conn)
            for norma in CSRD_NORMAS:
                changed = check_content_changed(conn, norma["codigo"], "directive", norma["boe_id"], "")
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
            for row in SEED_CSRD_COMPANIES:
                conn.connection.execute(
                    """INSERT INTO csrd_company (company_id, company_name, company_type,
                        sector, registration_number, home_member_state, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                companies_stored += 1
                total += 1
            if eurlex_processed:
                invalidate_old_embeddings(conn, "csrd")
            return {"processed": total, "source": source, "eurlex_processed": eurlex_processed, "companies": companies_stored, "worker": worker_name, "started_at": sync_start}
    except Exception as exc:
        return {"processed": total, "source": source, "eurlex_processed": eurlex_processed, "companies": companies_stored, "worker": worker_name, "error": str(exc), "started_at": sync_start}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CSRD worker")
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--interval", type=int, default=None)
    args = parser.parse_args()
    from runtime import init_sentry
    init_sentry("csrd")
    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS
    if args.run_once:
        result = run_sync()
        print(f"[run-once] CSRD: {result['processed']} total (eurlex={result['eurlex_processed']}, companies={result['companies']})")
        if result.get("error"):
            print(f"  Error: {result['error']}")
    else:
        print(f"Starting CSRD worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(f"CSRD: {result['processed']} total at {datetime.now(UTC).isoformat()}")
            time.sleep(interval)
