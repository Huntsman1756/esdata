#!/usr/bin/env python
"""Seed de documentos SEPBLAC desde su portal web.

Descubre y almacena guías, informes y publicaciones del SEPBLAC.

Uso:
    python scripts/data/seed_sepblac.py
"""

import argparse
import re
import time
from datetime import datetime

import psycopg
import requests

DB_URL_DEFAULT = "postgresql://esdata:esdata_dev@localhost:5434/esdata"
SEPBLAC_BASE = "https://www.sepblac.es"
DELAY = 2.5  # seconds between requests to respect rate limits


def fetch_sitemap() -> list[str]:
    """Descubre URLs del sitemap de SEPBLAC."""
    try:
        resp = requests.get(f"{SEPBLAC_BASE}/sitemap.xml", timeout=15)
        if resp.status_code != 200:
            return []
        urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
        # Strip CDATA wrappers from sitemap URLs
        urls = [re.sub(r"^<!\[CDATA\[|\]\]>$", "", u) for u in urls]
        return urls
    except Exception:
        return []


def discover_sepblac_pages() -> list[dict]:
    """Descubre páginas relevantes del SEPBLAC desde el sitemap."""
    urls = fetch_sitemap()
    filters = [
        "guia", "informe", "recomendacion", "memoria-de-actividades",
        "convenio", "actualizacion", "paquete-legislativo",
        "datos-actividad", "guia-dd", "guia-hidro",
    ]
    # Skip category/archive pages (not individual documents)
    category_pages = [
        "/es/publicaciones/",
        "/es/sobre-el-sepblac/transparencia/",
        "/es/sujetos-obligados/recomendaciones/",
        "/es/registro-de-actividades/",
    ]
    skip = ["wp-", "xmlrpc", "feed", "css", "js", "jpg", "png", "svg", "ca/", "/en/", "/gl/", "/va/", "/eu/"]

    pages = []
    seen = set()
    for url in urls:
        url_lower = url.lower()
        if any(f in url_lower for f in filters) and not any(s in url_lower for s in skip):
            # Skip category/archive pages
            if any(cat in url_lower for cat in category_pages):
                continue
            if url not in seen:
                seen.add(url)
                year_match = re.search(r"/(\d{4})/", url)
                pages.append({"url": url, "year": int(year_match.group(1)) if year_match else 0})

    # Sort by year descending (newest first)
    pages.sort(key=lambda p: p["year"], reverse=True)
    return pages[:40]  # Limit to most recent 40


def extract_page_content(url: str) -> dict | None:
    """Extrae contenido de una página del SEPBLAC."""
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return None

        html = resp.text
        soup_text = _html_to_text(html)

        if not soup_text or len(soup_text) < 200:
            return None

        title_match = re.search(r"<title>(.*?)</title>", html)
        titulo = title_match.group(1).strip() if title_match else "Documento SEPBLAC"

        # Extract full date from URL (YYYY/MM/DD pattern)
        date_match = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
        if date_match:
            fecha = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        else:
            # Fallback: use current date
            fecha = datetime.now().strftime("%Y-%m-%d")

        return {
            "titulo": titulo,
            "texto": soup_text,
            "fecha": fecha,
            "url": url,
        }
    except Exception:
        return None


def _html_to_text(html: str) -> str:
    """Convierte HTML a texto limpio."""
    import re as _re

    # Remove scripts and styles
    html = _re.sub(r"<script[\s\S]*?</script>", " ", html, flags=_re.IGNORECASE)
    html = _re.sub(r"<style[\s\S]*?</style>", " ", html, flags=_re.IGNORECASE)
    # Remove HTML tags but keep paragraphs
    html = _re.sub(r"<br\s*/?>", "\n", html, flags=_re.IGNORECASE)
    html = _re.sub(r"</p>", "\n\n", html, flags=_re.IGNORECASE)
    html = _re.sub(r"<[^>]+>", " ", html)
    # Clean whitespace
    lines = [line.strip() for line in html.splitlines()]
    lines = [l for l in lines if l]
    return "\n".join(lines)


def detect_sepblac_type(text: str) -> str:
    """Detecta el tipo de documento SEPBLAC."""
    lowered = text.lower()
    if "guía" in lowered or "guia" in lowered:
        return "guia_sepblac"
    if "informe" in lowered or "memoria" in lowered:
        return "informe_sepblac"
    if "recomendación" in lowered or "recomendacion" in lowered:
        return "recomendacion_sepblac"
    if "datos de actividad" in lowered or "actividad" in lowered:
        return "datos_actividad_sepblac"
    if "convenio" in lowered or "memorándum" in lowered or "memorando" in lowered:
        return "convenio_sepblac"
    if "obligado" in lowered or "declaración" in lowered or "declaracion" in lowered:
        return "tramite_sepblac"
    return "documento_sepblac"


def detect_ambito(text: str) -> str:
    """Detecta el ámbito del documento."""
    lowered = text.lower()
    if "pbc" in lowered or "blanqueo de capitales" in lowered or "financiación del terrorismo" in lowered or "financiacion del terrorismo" in lowered:
        return "aml_cft"
    if "supervisión" in lowered or "supervision" in lowered:
        return "supervision_sepblac"
    if "transparencia" in lowered:
        return "transparencia_sepblac"
    return "pbcft_general"


def seed_sepblac(db_url: str) -> dict:
    """Ingerir documentos SEPBLAC desde su portal."""
    discovered = discover_sepblac_pages()
    print(f"Descubiertas {len(discovered)} páginas del SEPBLAC")

    processed = 0
    stored = 0
    skipped = 0
    errors = 0

    conn_str = db_url.replace("postgres://", "postgresql://")
    conn = psycopg.connect(conn_str, autocommit=True)

    try:
        for i, page in enumerate(discovered):
            url = page["url"]
            processed += 1

            print(f"  [{i+1}/{len(discovered)}] {url}")

            content = extract_page_content(url)
            if not content:
                print(f"    [SKIP] No se pudo extraer contenido")
                skipped += 1
                time.sleep(DELAY)
                continue

            referencia = f"SEPBLAC-{re.sub(r'[^a-zA-Z0-9]', '-', content['titulo'][:50])}"
            referencia = referencia[:80]

            event_type = detect_sepblac_type(content["texto"])
            ambito = detect_ambito(content["texto"])

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
                        'SEPBLAC',
                        'es',
                        'sepblac',
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    ON CONFLICT (referencia) DO UPDATE SET
                        tipo_documento = excluded.tipo_documento,
                        ambito = excluded.ambito,
                        fecha = excluded.fecha,
                        titulo = excluded.titulo,
                        texto = excluded.texto,
                        url_fuente = excluded.url_fuente
                    """,
                    (event_type, ambito, referencia, content["fecha"], content["titulo"], content["texto"], url),
                )
                stored += 1
                print(f"    [OK] {referencia} ({event_type})")

            except Exception as e:
                print(f"    [ERROR] {referencia}: {e}")
                errors += 1

            time.sleep(DELAY)

        print(f"\nResumen: {processed} descubiertas, {stored} almacenadas, {skipped} saltadas, {errors} errores")
        return {
            "discovered": processed,
            "stored": stored,
            "skipped": skipped,
            "errors": errors,
        }

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed SEPBLAC documents from portal")
    parser.add_argument(
        "--db-url",
        default=DB_URL_DEFAULT,
        help=f"Database URL (default: {DB_URL_DEFAULT})",
    )
    args = parser.parse_args()

    result = seed_sepblac(args.db_url)
