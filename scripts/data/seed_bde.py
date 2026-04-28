#!/usr/bin/env python
"""Seed de documentos del Banco de Espana desde su files sitemap.

Descubre y almacena PDFs regulatorios (informes bancarios, circulares,
documentos de supervision) desde el files sitemap del BDE.

Uso:
    python scripts/data/seed_bde.py
    python scripts/data/seed_bde.py --limit 30
"""

import argparse
import re
import time
from datetime import UTC, datetime
from html import unescape
from io import BytesIO

import psycopg
import requests
from pypdf import PdfReader

DB_URL_DEFAULT = "postgresql://esdata:esdata_dev@localhost:5434/esdata"
BDE_BASE = "https://www.bde.es"
DELAY = 2.0
MIN_TEXT_LENGTH = 100  # PDFs can be short


def _normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_pdf_text(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        chunks = []
        for page in reader.pages:
            text_value = page.extract_text() or ""
            cleaned = _normalize_ws(text_value)
            if cleaned:
                chunks.append(cleaned)
        return "\n".join(chunks)
    except Exception:
        return ""


def extract_html_text(content: bytes) -> str:
    html = content.decode("utf-8", errors="ignore")
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", "\n", html)
    text_value = re.sub(r"\n\s*\n", "\n", html)
    return _normalize_ws(unescape(text_value))


def detect_document_type(text: str, url: str) -> str:
    lowered = text.lower()
    url_lower = url.lower()
    if "circular" in url_lower or "circular" in lowered:
        return "circular_bde"
    if "informe bancario" in lowered or "articulo 87" in lowered or "artículo 87" in lowered:
        return "informe_bancario_bde"
    if "memoria" in lowered:
        return "memoria_bde"
    if "boletin" in lowered:
        return "boletin_bde"
    if "revista" in lowered:
        return "revista_bde"
    if "documento trabajo" in lowered or "working paper" in lowered:
        return "documento_trabajo_bde"
    if "informe estudio" in lowered:
        return "informe_estudio_bde"
    if "informe" in lowered:
        return "informe_bde"
    if "comunicación" in lowered or "comunicacion" in lowered:
        return "comunicacion_bde"
    if "publicación" in lowered or "publicacion" in lowered:
        return "publicacion_bde"
    if "guía" in lowered or "guia" in lowered:
        return "guia_bde"
    return "documento_bde"


def detect_ambito(text: str) -> str:
    lowered = text.lower()
    if "estabilidad financiera" in lowered:
        return "estabilidad_financiera"
    if "politica monetaria" in lowered or "politica monetaria" in lowered:
        return "politica_monetaria"
    if "supervision bancaria" in lowered or "supervisión bancaria" in lowered:
        return "supervision_bancaria"
    if "sistemas de pago" in lowered or "sistemas de pagos" in lowered:
        return "sistemas_pago"
    if "macroprudencial" in lowered:
        return "regulacion_macroprudencial"
    if "blanqueo" in lowered or "financiacion terrorismo" in lowered or "financiación terrorismo" in lowered:
        return "prevencion_blanceo"
    if "creditos" in lowered or "entidades de credito" in lowered or "entidades de crédito" in lowered:
        return "entidades_credito"
    if "mercados" in lowered:
        return "mercados_financieros"
    if "pagos" in lowered:
        return "sistemas_pago"
    if "estadistica" in lowered or "estadística" in lowered:
        return "estadisticas"
    if "solvencia" in lowered or "capital" in lowered:
        return "solvencia_capital"
    if "liquidez" in lowered:
        return "liquidez"
    return "economia_espanola"


def extract_reference(url: str, text_value: str) -> str:
    # Try to extract from text first (e.g., "Circular 1/2024")
    text_match = re.search(r"(?:Circular|Informe|Comunicacion|Comunicación)[\s/]+(\d{1,3}/\d{4})", text_value, re.IGNORECASE)
    if text_match:
        return f"BDE-{text_match.group(1).replace('/', '-')}"

    # Try to extract from URL filename (BDE auto-generates filenames)
    file_match = re.search(r"/([^/]+)\.pdf", url)
    if file_match:
        fname = file_match.group(1)
        # Use a hash of the full URL for uniqueness
        return f"BDE-{abs(hash(url)) % 0xFFFFFFFF:08X}"

    return f"BDE-{datetime.now(UTC).date().isoformat().replace('-', '')}"


def build_payload(url: str, content: bytes) -> dict:
    if content[:5] == b"%PDF-":
        text_value = extract_pdf_text(content)
        if not text_value:
            raise ValueError(f"Could not extract text from BDE PDF: {url}")
    else:
        text_value = extract_html_text(content)
        if not text_value:
            raise ValueError(f"Could not extract text from BDE document: {url}")

    if len(text_value) < MIN_TEXT_LENGTH:
        raise ValueError(f"Text too short ({len(text_value)} chars): {url}")

    referencia = extract_reference(url, text_value)
    first_line = next((line.strip() for line in text_value.splitlines() if line.strip()), "")

    return {
        "referencia": referencia,
        "fecha": datetime.now(UTC).date().isoformat(),
        "titulo": first_line[:200] if first_line else referencia,
        "texto": text_value,
        "url_fuente": url,
        "tipo_documento": detect_document_type(text_value, url),
        "tipo_fuente": "bde",
        "organismo_emisor": "Banco de España",
        "ambito": detect_ambito(text_value),
        "jurisdiccion": "es",
    }


def upsert_documento(conn, payload: dict) -> None:
    conn.execute(
        psycopg.sql.SQL(
            """
            INSERT INTO documento_interpretativo (
                tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                ambito, referencia, fecha, titulo, texto, url_fuente
            ) VALUES (
                %(tipo_documento)s, 'Banco de España', 'es', 'bde',
                %(ambito)s, %(referencia)s, %(fecha)s, %(titulo)s, %(texto)s, %(url_fuente)s
            )
            ON CONFLICT (referencia) DO UPDATE SET
                tipo_documento = excluded.tipo_documento,
                ambito = excluded.ambito,
                fecha = excluded.fecha,
                titulo = excluded.titulo,
                texto = excluded.texto,
                url_fuente = excluded.url_fuente
            """
        ),
        payload,
    )


def fetch_url(url: str, session: requests.Session) -> bytes | None:
    try:
        resp = session.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        })
        if resp.status_code == 200:
            return resp.content
    except Exception:
        pass
    return None


def discover_from_sitemap(session: requests.Session) -> list[str]:
    """Discover URLs from BDE sitemaps."""
    all_urls = []

    # Fetch main sitemap index
    main_sitemap = "https://www.bde.es/sitemap.xml"
    resp = session.get(main_sitemap, timeout=10)
    if resp.status_code != 200:
        print("  [ERROR] Could not fetch main sitemap")
        return all_urls

    sitemap_locs = re.findall(r"<loc>([^<]+)</loc>", resp.text)
    print(f"  Found {len(sitemap_locs)} sub-sitemaps")

    # Fetch each sub-sitemap
    for sm_url in sitemap_locs:
        try:
            resp = session.get(sm_url, timeout=15)
            if resp.status_code != 200:
                continue
            locs = re.findall(r"<loc>([^<]+)</loc>", resp.text)
            print(f"  {sm_url}: {len(locs)} URLs")

            for loc in locs:
                if loc not in all_urls:
                    all_urls.append(loc)
        except Exception:
            continue

    return all_urls


def seed_from_pdfs(session: requests.Session, urls: list[str], limit: int, db_url: str) -> int:
    """Seed documents from PDF files."""
    stored = 0
    skipped = 0
    errors = 0

    engine = psycopg.connect(db_url, autocommit=True)
    try:
        with engine.cursor() as cur:
            for i, url in enumerate(urls[:limit]):
                fname = url.split("/")[-1][:80]
                print(f"  [{i+1}/{len(urls[:limit])}] {fname}")

                content = fetch_url(url, session)
                if not content:
                    skipped += 1
                    continue

                try:
                    payload = build_payload(url, content)
                    upsert_documento(cur, payload)
                    stored += 1
                    print(f"    [STORED] {payload['referencia']} ({payload['tipo_documento']})")
                except (ValueError, Exception) as e:
                    if "too short" in str(e):
                        skipped += 1
                    else:
                        errors += 1
                        print(f"    [ERROR] {e}")

                if i % 10 == 9:
                    time.sleep(DELAY)

    finally:
        engine.close()

    print(f"  PDFs: {stored} stored, {skipped} skipped, {errors} errors")
    return stored


def main():
    parser = argparse.ArgumentParser(description="Seed Banco de España documents from sitemaps")
    parser.add_argument("--limit", type=int, default=30, help="Max PDFs to process")
    parser.add_argument("--db-url", type=str, default=None, help="Database URL")
    args = parser.parse_args()

    db_url = args.db_url or DB_URL_DEFAULT

    print("=== Banco de España Seed ===")
    print(f"Limit: {args.limit} PDFs")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    })

    # Discover URLs from sitemaps
    print("\n--- Discovering URLs from sitemaps ---")
    all_urls = discover_from_sitemap(session)
    print(f"Total URLs discovered: {len(all_urls)}")

    # Filter PDF URLs
    pdf_urls = [u for u in all_urls if u.endswith(".pdf")]
    print(f"PDF URLs: {len(pdf_urls)}")

    print(f"\n--- Seeding PDFs ---")
    pdf_stored = seed_from_pdfs(session, pdf_urls, args.limit, db_url)

    print(f"\n=== Total stored: {pdf_stored} ===")


if __name__ == "__main__":
    main()
