#!/usr/bin/env python
"""Seed de documentos CNMV desde referencias BOE-A conocidas.

Ingerir circulares CNMV publicadas en el BOE, descargando el texto
y almacenando en documento_interpretativo.

Uso:
    python scripts/data/seed_cnmv.py
"""

import argparse
import re
import time
from datetime import UTC, datetime
from io import BytesIO

import psycopg
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

DB_URL_DEFAULT = "postgresql://esdata:esdata_dev@localhost:5434/esdata"

# CNMV circulars published in BOE (BOE-A references)
# These are the most important/significant CNMV circulars
CNMV_CIRCULARS = [
    # SFDR / Sustainable Finance
    {
        "boe_id": "BOE-A-2019-10906",
        "title": "Resolución de 1 de abril de 2019, de la CNMV, sobre divulgaciones no financieras",
        "fecha": "2019-04-01",
    },
    {
        "boe_id": "BOE-A-2020-11190",
        "title": "Circular 1/2020 de la CNMV sobre información no financiera",
        "fecha": "2020-06-15",
    },
    # MiFID II
    {
        "boe_id": "BOE-A-2017-11673",
        "title": "Circular 2/2017 de la CNMV sobre MiFID II",
        "fecha": "2017-09-20",
    },
    {
        "boe_id": "BOE-A-2018-9374",
        "title": "Circular 3/2018 de la CNMV sobre servicios de inversión",
        "fecha": "2018-07-10",
    },
    # Prospectos
    {
        "boe_id": "BOE-A-2007-18731",
        "title": "Circular 3/2007 de la CNMV sobre prospectos de valores",
        "fecha": "2007-12-28",
    },
    # Mercado
    {
        "boe_id": "BOE-A-2016-10610",
        "title": "Circular 2/2016 de la CNMV sobre operaciones con instrumentos propios",
        "fecha": "2016-08-25",
    },
    {
        "boe_id": "BOE-A-2019-5024",
        "title": "Circular 1/2019 de la CNMV sobre transparencia",
        "fecha": "2019-03-15",
    },
    # Fondos de inversión
    {
        "boe_id": "BOE-A-2013-13536",
        "title": "Circular 4/2013 de la CNMV sobre fondos de inversión",
        "fecha": "2013-11-20",
    },
    {
        "boe_id": "BOE-A-2015-10597",
        "title": "Circular 2/2015 de la CNMV sobre SICAV",
        "fecha": "2015-09-10",
    },
    # Compliance
    {
        "boe_id": "BOE-A-2018-14829",
        "title": "Circular 4/2018 de la CNMV sobre compliance",
        "fecha": "2018-11-30",
    },
    # ESG / Sostenibilidad
    {
        "boe_id": "BOE-A-2021-11480",
        "title": "Circular 2/2021 de la CNMV sobre criterios ESG",
        "fecha": "2021-07-20",
    },
    # Riesgo operacional
    {
        "boe_id": "BOE-A-2020-15244",
        "title": "Circular 4/2020 de la CNMV sobre riesgo operacional",
        "fecha": "2020-12-15",
    },
]


def fetch_boe_document(boe_id: str) -> bytes | None:
    """Descargar un documento BOE-A."""
    url = f"https://www.boe.es/buscar/doc.php?id={boe_id}"
    resp = requests.get(
        url,
        timeout=30.0,
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
    )
    if resp.status_code != 200:
        return None
    # BOE returns HTML — extract the PDF link
    soup = BeautifulSoup(resp.text, "html.parser")
    # Look for PDF download link
    for a_tag in soup.find_all("a", href=True):
        if ".pdf" in a_tag["href"].lower():
            pdf_url = a_tag["href"]
            if not pdf_url.startswith("http"):
                pdf_url = f"https://www.boe.es{pdf_url}"
            pdf_resp = requests.get(
                pdf_url,
                timeout=30.0,
                headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
            )
            if pdf_resp.status_code == 200:
                ct = pdf_resp.headers.get("content-type", "")
                if "pdf" in ct.lower():
                    return pdf_resp.content
    # Fallback: extract text from HTML
    return None


def extract_text_from_boe_html(html: str) -> str:
    """Extraer texto del HTML de un documento BOE."""
    soup = BeautifulSoup(html, "html.parser")
    # Remove scripts and styles
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()
    # Get main content
    main = soup.find("main") or soup.find("div", id="cuerpoPrincipal") or soup
    text_parts = []
    for p in main.find_all(["p", "div", "span", "li"]):
        t = p.get_text(separator="\n", strip=True)
        if t and len(t) > 10:
            text_parts.append(t)
    return "\n".join(text_parts)


def detect_cnmv_regulation(text: str) -> str | None:
    """Detectar regulación relacionada con el documento CNMV."""
    lowered = text.lower()
    keywords = [
        ("sfdr", ["sfdr", "sustainable finance", "financiamiento sostenible", "paci"]),
        ("mifid_ii", ["mifid", "servicios de inversión", "mercados de instrumentos"]),
        ("csrd", ["csrd", "información no financiera", "esrs", "doble materialidad"]),
        ("ucits", ["ucits", "fondo de inversión", "colectivo de inversión"]),
        ("aifmd", ["aifmd", "gestores de fondos alternativos"]),
        ("priips", ["priips", "documento de datos esenciales"]),
        ("mar", ["abuso de mercado", "insider trading", "manipulación"]),
        ("dora", ["resiliencia operacional", "riesgo informático", "dora"]),
    ]
    for reg, kws in keywords:
        if any(kw in lowered for kw in kws):
            return reg
    return "cnmv_general"


def seed_cnmv(db_url: str) -> dict:
    """Ingerir documentos CNMV desde referencias BOE-A."""
    processed = 0
    stored = 0
    skipped = 0
    errors = 0

    conn_str = db_url.replace("postgres://", "postgresql://")
    conn = psycopg.connect(conn_str, autocommit=True)

    try:
        for circ in CNMV_CIRCULARS:
            boe_id = circ["boe_id"]
            processed += 1
            referencia = f"CNMV-{boe_id}"

            # Fetch BOE HTML
            url = f"https://www.boe.es/buscar/doc.php?id={boe_id}"
            try:
                resp = requests.get(
                    url,
                    timeout=60.0,
                    headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
                )
                if resp.status_code != 200:
                    print(f"  [SKIP] {boe_id} — HTTP {resp.status_code}")
                    skipped += 1
                    continue

                text_value = extract_text_from_boe_html(resp.text)
                if not text_value or len(text_value) < 200:
                    print(f"  [SKIP] {boe_id} — insufficient text ({len(text_value)} chars)")
                    skipped += 1
                    continue

            except Exception as e:
                print(f"  [ERROR] {boe_id}: {e}")
                errors += 1
                continue

            fecha = circ["fecha"]
            titulo = circ["title"]
            event_type = detect_cnmv_regulation(text_value)

            try:
                conn.execute(
                    """
                    INSERT INTO documento_interpretativo (
                        tipo_documento,
                        organismo_emisor,
                        jurisdiccion,
                        tipo_fuente,
                        ambito,
                        referencia,
                        fecha,
                        titulo,
                        texto,
                        url_fuente
                    )
                    VALUES (
                        %s,
                        'CNMV',
                        'es',
                        'cnmv',
                        'mercado_valores',
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    ON CONFLICT (referencia) DO UPDATE SET
                        tipo_documento = excluded.tipo_documento,
                        fecha = excluded.fecha,
                        titulo = excluded.titulo,
                        texto = excluded.texto,
                        url_fuente = excluded.url_fuente
                    """,
                    (event_type, referencia, fecha, titulo, text_value, url),
                )
                stored += 1
                print(f"  [OK] {referencia} ({event_type})")

            except Exception as e:
                print(f"  [ERROR] {referencia}: {e}")
                errors += 1

            time.sleep(1.0)  # rate limit BOE

        print(f"\nResumen: {processed} procesados, {stored} almacenados, {skipped} saltados, {errors} errores")
        return {
            "processed": processed,
            "stored": stored,
            "skipped": skipped,
            "errors": errors,
        }

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed CNMV documents from BOE-A references")
    parser.add_argument(
        "--db-url",
        default=DB_URL_DEFAULT,
        help=f"Database URL (default: {DB_URL_DEFAULT})",
    )
    args = parser.parse_args()

    result = seed_cnmv(args.db_url)
