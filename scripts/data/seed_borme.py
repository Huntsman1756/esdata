#!/usr/bin/env python
"""Seed de documentos BORME reales desde indices HTML del BOE.

Ingerir BORME de los ultimos dias laborables, extrayendo referencias
de los indices HTML publicos y almacenando en documento_interpretativo.

Uso:
    python scripts/data/seed_borme.py
    python scripts/data/seed_borme.py --db-url postgresql://user:pass@host:5432/db
"""

import argparse
import re
import time
from datetime import UTC, datetime
from io import BytesIO

import psycopg
import requests
from pypdf import PdfReader

DB_URL_DEFAULT = "postgresql://esdata:esdata_dev@localhost:5434/esdata"

# Ultimos dias laborables con BORME publicado (2025-04-25 = viernes)
BORME_DATES = [
    "2025-04-25",
    "2025-04-24",
    "2025-04-23",
    "2025-04-22",
    "2025-04-21",
]


def extract_borme_urls(html: str) -> list[str]:
    """Extraer URLs de PDFs BORME desde el HTML del indice."""
    pattern = r'href="(/borme/dias/\d{4}/\d{2}/\d{2}/pdfs/BORME-[A-Z]-\d{4}-\d+(?:-\d+)?\.pdf)"'
    return [f"https://www.boe.es{url}" for url in re.findall(pattern, html)]


def extract_borme_date_from_url(url: str) -> str:
    """Extraer la fecha YYYY-MM-DD de la URL del BORME."""
    match = re.search(r'/borme/dias/(\d{4})/(\d{2})/(\d{2})/pdfs/', url)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return datetime.now(UTC).date().isoformat()


def fetch_borme_pdf(url: str, max_retries: int = 3) -> bytes | None:
    """Descargar un PDF BORME con reintentos y backoff."""
    for attempt in range(max_retries):
        try:
            resp = requests.get(
                url,
                timeout=30.0,
                headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
            )
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "pdf" not in content_type.lower():
                return None
            return resp.content
        except requests.HTTPError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return None


def detect_event_type(text: str) -> str:
    """Detectar tipo de evento societario desde el texto del BORME."""
    patterns = [
        ("nombramiento", r"\bNombramientos?\b"),
        ("cese", r"\bCeses?\b"),
        ("constitucion", r"\bConstituci[oó]n\b"),
        ("cambio_domicilio", r"\bDomicilio\b"),
        ("ampliacion_capital", r"\bAmpliaci[oó]n de capital\b"),
        ("reduccion_capital", r"\bReducci[oó]n de capital\b"),
        ("disolucion", r"\bDisoluci[oó]n\b"),
        ("concurso", r"\bConcurso\b"),
    ]
    for event_type, pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return event_type
    return "acto_societario"


def extract_company_name(text: str) -> str | None:
    """Extraer nombre de la empresa principal del BORME."""
    patterns = [
        r"\bConstituci[oó]n\.\s*([A-Z0-9\u00c1\u00c9\u00cd\u00d3\u00da\u00d1 .,\-]+?\s+(?:S\.L\.|SL|S\.A\.|SA|SOCIEDAD LIMITADA|SOCIEDAD ANONIMA))\b",
        r"\b([A-Z0-9\u00c1\u00c9\u00cd\u00d3\u00DA\u00d1 .,\-]+?\s+(?:S\.L\.|SL|S\.A\.|SA|SOCIEDAD LIMITADA|SOCIEDAD ANONIMA))\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            name = re.sub(r"\s+", " ", match.group(1)).strip(" .,")
            if len(name) > 3:
                return name
    return None


def extract_pdf_text(content: bytes) -> str:
    """Extraer texto de un PDF BORME."""
    reader = PdfReader(BytesIO(content))
    text_parts = []
    for page in reader.pages:
        t = page.extract_text() or ""
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            text_parts.append(t)
    return "\n".join(text_parts)


def seed_borme(db_url: str, seed_dates: list[str] | None = None) -> dict:
    """Ingerir BORME desde indices HTML y almacenar en documento_interpretativo."""
    dates = seed_dates or BORME_DATES
    processed = 0
    stored = 0
    skipped = 0
    errors = 0
    urls_discovered = 0

    conn_str = db_url.replace("postgres://", "postgresql://")
    conn = psycopg.connect(conn_str, autocommit=True)

    try:
        # Discover URLs from HTML indices
        all_urls: list[tuple[str, str]] = []  # (url, date)
        for date_str in dates:
            index_url = f"https://www.boe.es/borme/dias/{date_str.replace('-', '/')}/"
            try:
                # Fresh session per request to avoid CDN caching issues
                session = requests.Session()
                session.headers.update({
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                })
                resp = session.get(index_url, timeout=15.0)
                if resp.status_code == 200 and "BORME-S" in resp.text:
                    urls = extract_borme_urls(resp.text)
                    # Limit to first 20 per day to avoid excessive processing
                    for url in urls[:20]:
                        all_urls.append((url, date_str))
                    urls_discovered += len(urls)
                    print(f"  [{date_str}] {len(urls)} BORMEs descubiertos")
                time.sleep(2.0)  # rate limit BOE
            except requests.HTTPError as e:
                print(f"  [{date_str}] Error discovering: {e}")

        print(f"\nTotal BORMEs descubiertos: {urls_discovered}")

        # Process each BORME PDF
        for url, date_str in all_urls:
            processed += 1
            pdf_code = re.search(r'(BORME-[A-Z]-\d{4}-\d+(?:-\d+)?)\.pdf$', url)
            referencia = pdf_code.group(1) if pdf_code else f"BORME-{date_str}"

            content = fetch_borme_pdf(url)
            if not content:
                print(f"  [SKIP] {referencia} — no PDF content")
                skipped += 1
                continue

            # Extract text from PDF
            text_value = extract_pdf_text(content)

            if not text_value or len(text_value) < 50:
                print(f"  [SKIP] {referencia} — insufficient text ({len(text_value)} chars)")
                skipped += 1
                continue

            event_type = detect_event_type(text_value)
            company_name = extract_company_name(text_value)
            first_line = next(
                (line.strip() for line in text_value.splitlines() if line.strip()),
                "",
            )
            titulo = f"{referencia} — {first_line[:200]}" if first_line else referencia

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
                        'BORME',
                        'es',
                        'borme',
                        'mercantil',
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
                    (event_type, referencia, date_str, titulo, text_value, url),
                )
                stored += 1

                # Upsert empresa if extracted
                if company_name:
                    conn.execute(
                        """
                        INSERT INTO empresa (nombre, nif, domicilio, fuente_inicial)
                        VALUES (%s, NULL, NULL, 'BORME')
                        ON CONFLICT (nombre) DO UPDATE SET
                            domicilio = COALESCE(excluded.domicilio, empresa.domicilio)
                        """,
                        (company_name,),
                    )

                print(f"  [OK] {referencia} ({event_type}) empresa={company_name}")

            except Exception as e:
                print(f"  [ERROR] {referencia}: {e}")
                errors += 1

            time.sleep(0.5)  # rate limit

        print(f"\nResumen: {processed} procesados, {stored} almacenados, {skipped} saltados, {errors} errores")
        return {
            "processed": processed,
            "stored": stored,
            "skipped": skipped,
            "errors": errors,
            "urls_discovered": urls_discovered,
        }

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed BORME documents from BOE HTML indices")
    parser.add_argument(
        "--db-url",
        default=DB_URL_DEFAULT,
        help=f"Database URL (default: {DB_URL_DEFAULT})",
    )
    parser.add_argument(
        "--dates",
        nargs="+",
        default=None,
        help="Override BORME dates (YYYY-MM-DD format, space-separated)",
    )
    args = parser.parse_args()

    result = seed_borme(args.db_url, args.dates)
