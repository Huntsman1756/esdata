#!/usr/bin/env python
"""CDI Worker v7 — Convenios de Doble Imposición (DTA).

Fuentes:
  1. Hacienda tabla: BOE dates (col 4), entry into force (col 7), PDFs
  2. AEAT listing + detail pages: firma date, BOE refs

Persistencia: `irs_dta_convention` — fecha_firma, fecha_vigencia, boe_links,
pdf_urls, textos_sinteticos.

Uso:
    docker compose exec worker-cdi python cdi.py --run-once
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup, Tag
from runtime import (
    configure_logging,
    ensure_database_connection,
    get_database_url,
    get_interval_seconds,
    handle_worker_failure,
    sleep_with_heartbeat,
    touch_heartbeat,
)
from sqlalchemy import create_engine, text

logger = configure_logging("worker-cdi")

# ── Configuration ──────────────────────────────────────────────────

AEAT_SEDE = "https://sede.agenciatributaria.gob.es"
CDI_LISTING_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/"
    "normativa-criterios-interpretativos/fiscalidad-internacional/"
    "convenios-doble-imposicion-firmados-espana.html"
)

HACIENDA_URL = (
    "https://www.hacienda.gob.es"
    "/es-ES/Normativa%20y%20doctrina/Normativa/CDI/Paginas/CDI_Alfa.aspx"
)

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("CDI_SYNC_INTERVAL_SECONDS", 604800)
USER_AGENT = "Mozilla/5.0 (compatible; esdata/cdi-worker/7.0; fiscal compliance)"
HEADERS = {"User-Agent": USER_AGENT}

KNOWN_COUNTRIES_CLEAN = {
    "Albania", "Alemania", "Andorra", "Arabia Saudi", "Argelia", "Argentina",
    "Austria", "Australia", "Armenia", "Azerbaiyán", "Bielorrusia", "Barbados",
    "Bélgica", "Bolivia", "Bosnia y Herzegovina", "Brasil", "Bulgaria",
    "Cabo Verde", "Canadá", "Catar", "Chequia", "Chile", "China",
    "Chipre", "Colombia", "Corea del Sur", "Costa Rica", "Croacia", "Cuba",
    "Dinamarca", "Ecuador", "Egipto", "Emiratos Árabes Unidos", "Eslovaquia",
    "Eslovenia", "Estados Unidos", "Estonia", "Filipinas", "Finlandia", "Francia",
    "Georgia", "Grecia", "Hungría", "India", "Indonesia", "Irán", "Irlanda",
    "Islandia", "Israel", "Italia", "Jamaica", "Japón", "Kazajstán", "Kuwait",
    "Letonia", "Lituania", "Luxemburgo", "Macedonia", "Malasia", "Malta",
    "Marruecos", "México", "Moldavia", "Nigeria", "Noruega", "Nueva Zelanda",
    "Omán", "Países Bajos", "Pakistan", "Panamá", "Paraguay", "Polonia",
    "Portugal", "Reino Unido", "República Dominicana", "Rumanía", "Federación Rusa",
    "El Salvador", "Senegal", "Serbia", "Singapur", "Sudáfrica", "Suecia",
    "Suiza", "Tailandia", "Trinidad y Tobago", "Túnez", "Turquía",
    "Uruguay", "Uzbekistán", "Venezuela", "Vietnam",
}

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "jun": 6, "jul": 7, "ago": 8,
    "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}


def _parse_date_str(date_str: str) -> Optional[datetime]:
    """Parse a date string like '12/06/97', '1/06/22', '10 de octubre de 1995', '2 de julio de 2010'."""
    date_str = date_str.strip()
    
    # Format: DD/MM/YY or DD/MM/YYYY
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", date_str)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day)
        except ValueError:
            pass
    
    # Format: "2 de julio de 2010" or "10 de octubre de 1995"
    m = re.match(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", date_str)
    if m:
        day = int(m.group(1))
        month = MONTHS.get(m.group(2).lower())
        year = int(m.group(3))
        if month:
            try:
                return datetime(year, month, day)
            except ValueError:
                pass
    
    # Format: DD-MMM-YYYY or DD MMM YYYY (with hyphens or spaces)
    m = re.match(r"(\d{1,2})[-/\s]+(\w+)[-/\s]+(\d{4})", date_str)
    if m:
        day = int(m.group(1))
        month = MONTHS.get(m.group(2).lower())
        year = int(m.group(3))
        if month:
            try:
                return datetime(year, month, day)
            except ValueError:
                pass
    
    return None


def _normalize_country_name(raw: str) -> str:
    """Normalize country name: strip parenthetical suffixes."""
    name = re.sub(r'\s*\(.*?\)', '', raw).strip()
    for known in KNOWN_COUNTRIES_CLEAN:
        if known.lower() == name.lower():
            return known
    for known in KNOWN_COUNTRIES_CLEAN:
        if known.lower() in name.lower():
            return known
    return name


def _safe_fetch(client: httpx.Client, url: str, retries: int = 3) -> Optional[str]:
    for attempt in range(retries):
        try:
            resp = client.get(url, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    logger.error("All retries exhausted for %s", url)
    return None


def parse_hacienda_table(html: str) -> list[dict]:
    """Parse the CDI table from hacienda.gob.es."""
    soup = BeautifulSoup(html, "html.parser")
    conventions = []
    
    table = soup.find("table")
    if not table:
        logger.warning("No table found on Hacienda CDI page")
        return conventions
    
    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 5:
            continue
        
        # Column 0: Country name
        country_raw = cells[0].get_text(separator=" ", strip=True)
        country_raw = re.sub(r'Convenios\s*', '', country_raw).strip()
        country_raw = re.sub(r'\s+', ' ', country_raw).strip()
        
        if not country_raw or len(country_raw) < 2:
            continue
        
        country_name = _normalize_country_name(country_raw)
        if country_name not in KNOWN_COUNTRIES_CLEAN:
            continue
        
        # Column 4: BOE — extract ALL dates and PDF links
        boe_dates = []
        boe_pdf_urls = []
        boe_refs = []
        if len(cells) > 4:
            for a in cells[4].find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                
                if text:
                    d = _parse_date_str(text)
                    if d and 1950 <= d.year <= 2040:
                        boe_dates.append(d)
                
                if href.endswith(".pdf"):
                    full_url = href if href.startswith("http") else "https://www.hacienda.gob.es" + href
                    boe_pdf_urls.append(full_url)
                
                if "boe.es" in href:
                    boe_ref = re.search(r"BOE-A-(\d+-\d+)", href)
                    boe_refs.append({
                        "url": href,
                        "boe_reference": boe_ref.group(0) if boe_ref else text,
                    })
            
            # Also get direct text dates from the cell
            direct_dates = re.findall(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", cells[4].get_text(strip=True))
            for day, month, year in direct_dates:
                year = int(year)
                if year < 100:
                    year += 2000
                try:
                    d = datetime(int(year), int(month), int(day))
                    if 1950 <= d.year <= 2040 and d not in boe_dates:
                        boe_dates.append(d)
                except ValueError:
                    pass
        
        # Column 7: Textos sintéticos — dates + PDFs
        sinteticos_pdf_urls = []
        sinteticos_dates = []
        if len(cells) > 7:
            for a in cells[7].find_all("a", href=True):
                href = a["href"]
                span = a.find("span")
                if span:
                    d = _parse_date_str(span.get_text(strip=True))
                    if d and 1950 <= d.year <= 2040:
                        sinteticos_dates.append(d)
                if href.endswith(".pdf"):
                    full_url = href if href.startswith("http") else "https://www.hacienda.gob.es" + href
                    sinteticos_pdf_urls.append(full_url)
        
        convention = {
            "pais": country_name,
            "boe_dates": boe_dates,
            "boe_pdf_urls": boe_pdf_urls,
            "boe_refs": boe_refs,
            "sinteticos_pdf_urls": sinteticos_pdf_urls,
            "sinteticos_dates": sinteticos_dates,
        }
        
        conventions.append(convention)
    
    logger.info("Parsed %d conventions from Hacienda table", len(conventions))
    return conventions


def extract_countries_from_listing(html: str) -> list[dict]:
    """Extract country list from AEAT CDI listing page."""
    soup = BeautifulSoup(html, "html.parser")
    countries = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        text_content = link.get_text(strip=True)

        if not any(kw in href.lower() for kw in ["cdi", "convenio"]):
            continue

        country_name = None
        for known in KNOWN_COUNTRIES_CLEAN:
            if known.lower() in text_content.lower():
                country_name = known
                break

        if not country_name:
            continue

        countries.append({
            "nombre": country_name,
            "detalle_url": AEAT_SEDE + href if not href.startswith("http") else href,
        })

    return countries


def parse_aeat_country_page(html: str, country: dict) -> dict:
    """Extract firma date and other infos from AEAT page."""
    soup = BeautifulSoup(html, "html.parser")
    
    boe_links = []
    firma_date = None
    ratification_text = ""
    
    main_content = soup.find("main")
    if main_content:
        ratification_text = main_content.get_text(separator="\n", strip=True)[:50000]
        
        # Search for "DD de Month de YYYY" pattern
        all_matches = re.findall(
            r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})",
            ratification_text
        )
        if not all_matches:
            all_matches = re.findall(
                r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})",
                html
            )
        
        for day_str, month_str, year_str in all_matches:
            day = int(day_str)
            month = MONTHS.get(month_str.lower())
            year = int(year_str)
            if month and 1950 <= year <= 2040:
                try:
                    firma_date = datetime(year, month, day)
                    break
                except ValueError:
                    pass
        
        for link in main_content.find_all("a", href=True):
            if "boe.es" in link["href"]:
                br = re.search(r"BOE-A-(\d+-\d+)", link["href"])
                text = link.get_text(strip=True)
                boe_links.append({
                    "url": link["href"],
                    "text": text,
                    "boe_reference": br.group(0) if br else text,
                })
    
    # Extract vigencia from AEAT page links and text
    vigencia_date = None
    
    # Pattern 1: "vigente a partir de DD de Month de YYYY" or "DD de Month YYYY"
    vig_patterns = [
        r'vigente\s+(?:a partir de|desde)\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
        r'vigente\s+(?:a partir de|desde)\s+(\d{1,2})\s+de\s+(\w+)\s+(\d{4})',
        r'vigente\s+(?:a partir de|desde)\s+(\d{1,2})\s+de\s+(\w+)\s+(\d{2})',
    ]
    for pat in vig_patterns:
        m = re.search(pat, ratification_text, re.IGNORECASE)
        if m:
            day = int(m.group(1))
            month = MONTHS.get(m.group(2).lower())
            year = int(m.group(3))
            if len(m.group(3)) == 2 and year > 50:
                year += 1900
            elif len(m.group(3)) == 2:
                year += 2000
            if month and 1950 <= year <= 2040:
                try:
                    vigencia_date = datetime(year, month, day)
                    break
                except ValueError:
                    pass
    
    # Pattern 2: Try extracting from link hrefs like "convenio-vigente-partir-1-enero-2013.html"
    if not vigencia_date:
        for link in main_content.find_all("a", href=True):
            href = link.get_text(strip=True)
            if "vigente" in href.lower() and "pdf" not in href.lower():
                # Try to parse "Convenio vigente a partir de 1 de enero 2013"
                m = re.search(r'vigente\s+(?:a partir de|desde)\s+(\d{1,2})\s+de\s+(\w+)\s+(\d{2,4})', href, re.IGNORECASE)
                if m:
                    day = int(m.group(1))
                    month = MONTHS.get(m.group(2).lower())
                    year = int(m.group(3))
                    if len(m.group(3)) == 2 and year > 50:
                        year += 1900
                    elif len(m.group(3)) == 2:
                        year += 2000
                    if month and 1950 <= year <= 2040:
                        try:
                            vigencia_date = datetime(year, month, day)
                            break
                        except ValueError:
                            pass
    
    return {
        "firma_date": firma_date,
        "boe_links": boe_links,
        "ratification_text": ratification_text,
        "vigencia_date": vigencia_date,
    }


def discover_and_sync() -> dict:
    """Main sync: parse Hacienda table, supplement with AEAT pages, update DB."""
    stats = {
        "conventions_upserted": 0,
        "errors": 0,
        "with_firma": 0,
        "with_vigencia": 0,
        "with_pdfs": 0,
        "with_boe": 0,
    }

    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        ensure_database_connection(engine)

        with httpx.Client(timeout=30, follow_redirects=True, headers=HEADERS) as client:
            # Clear all existing data
            logger.info("Clearing existing CDI data...")
            with engine.connect() as conn:
                conn.execute(text("DELETE FROM irs_dta_convention"))
                conn.commit()
            logger.info("Cleared existing CDI data")

            # 1. Parse Hacienda table
            hacienda_html = _safe_fetch(client, HACIENDA_URL)
            if not hacienda_html:
                logger.error("Could not fetch Hacienda CDI table")
                stats["errors"] += 1
                return stats

            conventions = parse_hacienda_table(hacienda_html)
            logger.info("Parsed %d conventions from Hacienda", len(conventions))

            # 2. For each, supplement with AEAT page for firma date
            for conv in conventions:
                try:
                    touch_heartbeat()
                    
                    # Entry into force: prefer first valid sinteticos date, fallback to latest BOE date
                    entrada_vigor = None
                    
                    # Priority 1: sinteticos dates
                    for d in conv["sinteticos_dates"]:
                        if 1950 <= d.year <= 2040:
                            entrada_vigor = d
                            break
                    
                    # Priority 2: latest BOE date as proxy
                    if not entrada_vigor and conv["boe_dates"]:
                        entrada_vigor = max(conv["boe_dates"])
                    
                    # Merge
                    merged = {
                        "pais": conv["pais"],
                        "fecha_vigencia": entrada_vigor,
                        "boe_pdf_urls": conv["boe_pdf_urls"],
                        "boe_refs": conv["boe_refs"],
                        "sinteticos_pdf_urls": conv["sinteticos_pdf_urls"],
                    }
                    
                    # Try to get firma date from AEAT page
                    aeat_data = _find_and_parse_aeat_page(client, conv["pais"])
                    if conv["pais"] == "Argentina":
                        logger.info("DEBUG Argentina: aeat_data=%s vigencia_date=%s", aeat_data is not None, aeat_data.get("vigencia_date") if aeat_data else None)
                    if aeat_data:
                        merged["fecha_firma"] = aeat_data["firma_date"]
                        merged["boe_links"] = aeat_data["boe_links"]
                        merged["ratification_text"] = aeat_data["ratification_text"]
                        if aeat_data["firma_date"]:
                            stats["with_firma"] += 1
                        
                        # Priority 3: vigent date from AEAT page (extracted in parse_aeat_country_page)
                        if not entrada_vigor and aeat_data.get("vigencia_date"):
                            entrada_vigor = aeat_data["vigencia_date"]
                            merged["fecha_vigencia"] = entrada_vigor
                    else:
                        merged["fecha_firma"] = None
                        merged["boe_links"] = []
                        merged["ratification_text"] = ""
                    
                    _upsert_convention(engine, merged)
                    stats["conventions_upserted"] += 1
                    
                    if merged["fecha_vigencia"]:
                        stats["with_vigencia"] += 1
                    if merged["boe_pdf_urls"] or merged["sinteticos_pdf_urls"]:
                        stats["with_pdfs"] += 1
                    if merged["boe_refs"] or merged["boe_links"]:
                        stats["with_boe"] += 1
                    
                    if stats["conventions_upserted"] % 10 == 0:
                        logger.info("Progress: %d/%d", stats["conventions_upserted"], len(conventions))

                except Exception as exc:
                    logger.error("Error processing %s: %s", conv["pais"], exc, exc_info=True)
                    stats["errors"] += 1

        return stats

    except Exception as exc:
        logger.error("CDI sync failed: %s", exc, exc_info=True)
        stats["errors"] += 1
        return stats


def _find_and_parse_aeat_page(client: httpx.Client, country_name: str) -> Optional[dict]:
    """Find and parse the AEAT country page for a given country."""
    listing_html = _safe_fetch(client, CDI_LISTING_URL)
    if not listing_html:
        return None

    countries = extract_countries_from_listing(listing_html)
    target = None
    for c in countries:
        if c["nombre"].lower() == country_name.lower():
            target = c
            break

    if not target:
        return None

    page_html = _safe_fetch(client, target["detalle_url"])
    if not page_html:
        return None

    return parse_aeat_country_page(page_html, target)


def _upsert_convention(engine, data: dict) -> None:
    """INSERT or UPDATE irs_dta_convention by pais_origen."""
    pais = data["pais"]
    
    all_pdfs = list(data.get("boe_pdf_urls", []))
    all_pdfs.extend(data.get("sinteticos_pdf_urls", []))
    all_pdfs = list(set(all_pdfs))
    
    all_boe = list(data.get("boe_refs", []))
    all_boe.extend(data.get("boe_links", []))
    
    boe_referencia = ""
    for ref in all_boe:
        if ref.get("boe_reference"):
            boe_referencia += ref["boe_reference"] + "; "
    boe_referencia = boe_referencia.strip().rstrip("; ")
    
    textos = ""
    for link in data.get("sinteticos_pdf_urls", []):
        textos += "Textos sintéticos: " + link + "\n"
    for ref in all_boe:
        if ref.get("url"):
            textos += "BOE: " + ref["url"] + "\n"
    
    if data.get("ratification_text"):
        textos += "\n---\nRatificación:\n" + data["ratification_text"]
    
    sql = """
    INSERT INTO irs_dta_convention (
        codigo, pais_origen, pais_destino, titulo, fecha_firma, fecha_vigencia,
        tipo_acuerdo, boe_referencia, boe_links, articulos, pdf_urls,
        textos_sinteticos, texto_completo, estado, creado_en, actualizado_en
    ) VALUES (
        :codigo, :pais, 'España', 'Convenio de doble imposición con ' || :pais,
        :fecha_firma, :fecha_vigencia,
        'convencion_doble_imposicion', :boe_ref, :boe_links, :articulos, :pdfs,
        :textos, :rat_text, 'vigente', NOW(), NOW()
    )
    ON CONFLICT (pais_origen) DO UPDATE SET
        fecha_firma = EXCLUDED.fecha_firma,
        fecha_vigencia = EXCLUDED.fecha_vigencia,
        boe_referencia = EXCLUDED.boe_referencia,
        boe_links = EXCLUDED.boe_links,
        articulos = EXCLUDED.articulos,
        pdf_urls = EXCLUDED.pdf_urls,
        textos_sinteticos = EXCLUDED.textos_sinteticos,
        texto_completo = EXCLUDED.texto_completo,
        estado = EXCLUDED.estado,
        actualizado_en = NOW()
    """

    with engine.connect() as conn:
        conn.execute(text(sql), {
            "codigo": pais[:10],
            "pais": pais,
            "fecha_firma": data.get("fecha_firma"),
            "fecha_vigencia": data.get("fecha_vigencia"),
            "boe_ref": boe_referencia,
            "boe_links": json.dumps(all_boe, ensure_ascii=False),
            "articulos": "{}",
            "pdfs": json.dumps(all_pdfs, ensure_ascii=False),
            "textos": textos[:50000],
            "rat_text": data.get("ratification_text", "")[:20000],
        })
        conn.commit()
        logger.debug("Upserted: %s (firma=%s vigencia=%s pdfs=%d)",
                     pais, data.get("fecha_firma"), data.get("fecha_vigencia"), len(all_pdfs))


def main():
    parser = argparse.ArgumentParser(description="CDI Worker — DTA conventions from AEAT/Hacienda")
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--interval", type=int)
    args = parser.parse_args()

    if args.run_once:
        logger.info("Starting CDI worker (single run)")
        stats = discover_and_sync()
        logger.info("CDI sync complete: %s", json.dumps(stats, indent=2))
    else:
        interval = args.interval or SYNC_INTERVAL_SECONDS
        logger.info("Starting CDI worker (interval=%ds)", interval)
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        while True:
            touch_heartbeat()
            try:
                stats = discover_and_sync()
                logger.info("CDI sync complete: %s", json.dumps(stats, indent=2))
            except Exception as exc:
                logger.error("CDI sync error: %s", exc, exc_info=True)
                handle_worker_failure(
                    engine,
                    "worker-cdi",
                    "full_sync",
                    "discovery",
                    exc,
                )
            sleep_with_heartbeat(interval)


if __name__ == "__main__":
    main()
