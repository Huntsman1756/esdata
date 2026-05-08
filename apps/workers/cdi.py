#!/usr/bin/env python
"""Worker CDI — Convenios de Doble Imposición (DTA).

Fuentes:
  1. https://sede.agenciatributaria.gob.es/.../convenios-doble-imposicion...
     ← listado alfabético con enlaces a páginas por país (rubrica, firma, BOE, PDFs)
  2. https://www.hacienda.gob.es/.../CDI/Paginas/CDI_Alfa.aspx
     ← tabla complementaria (rubrica, firma, publicación BOCG, BOE)

Persistencia: tabla `irs_dta_convention` con `pais`, `fecha_firma`,
`fecha_vigencia`, `boe_referencia`, `pdf_urls`, `texto_completo`.

Uso:
    python cdi.py --run-once
    python cdi.py --interval 604800
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from runtime import (
    configure_logging,
    ensure_database_connection,
    finalize_partial_sync_status,
    get_database_url,
    get_interval_seconds,
    handle_worker_failure,
    sleep_with_heartbeat,
    touch_heartbeat,
)
from sqlalchemy import create_engine, inspect, text

logger = configure_logging("worker-cdi")

# ── Configuration ──────────────────────────────────────────────────

AEAT_SEDE = "https://sede.agenciatributaria.gob.es"
CDI_LISTING_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/"
    "normativa-criterios-interpretativos/fiscalidad-internacional/"
    "convenios-doble-imposicion-firmados-espana.html"
)

HACIENDA_TABLE_URL = (
    "https://www.hacienda.gob.es"
    "/es-ES/Normativa%20y%20doctrina/Normativa/CDI/Paginas/CDI_Alfa.aspx"
)

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("CDI_SYNC_INTERVAL_SECONDS", 604800)  # 1 week

USER_AGENT = "Mozilla/5.0 (compatible; esdata/cdi-worker/1.0; fiscal compliance)"

HEADERS = {"User-Agent": USER_AGENT}

# ── Helpers ─────────────────────────────────────────────────────────

def _safe_fetch(client: httpx.Client, url: str, retries: int = 3) -> Optional[str]:
    """GET with retries, returns text or None."""
    for attempt in range(retries):
        try:
            resp = client.get(url, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            logger.warning("Fetch failed for %s (attempt %d): %s", url, attempt + 1, exc)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    logger.error("All retries exhausted for %s", url)
    return None


def _parse_date(text: str) -> Optional[datetime]:
    """Simple date parser: MM/DD/YY or YYYY or other formats."""
    text = text.strip().replace("\\u00a0", " ").replace("&nbsp;", " ")
    # Try MM/DD/YY
    m = re.search(r"(\d{1,2})[\s/](\d{1,2})[\s/](\d{2,4})", text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day)
        except ValueError:
            pass
    return None


def _clean_text(text: str) -> str:
    """Clean HTML/Unicode from scraped text."""
    return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)


# ── Country extraction ─────────────────────────────────────────────

def extract_countries_from_listing(html: str) -> list[dict]:
    """Extract country list from AEAT CDI listing page.

    Returns: [{codigo, nombre, detalle_url, ...}]
    """
    soup = BeautifulSoup(html, "html.parser")
    countries = []

    # The page has links to individual country pages like:
    # /Sede/normativa-criterios-interpretativos/fiscalidad-internacional/...-albania.html
    country_links = soup.find_all("a", href=True)

    # Countries we know the listing should have (alphabetical list from scraped content)
    KNOWN_COUNTRIES = {
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

    # Country code map: page slug -> standard country code
    COUNTRY_CODES = {
        "albania": "ALB",
        "alemania": "DEU",
        "andorra": "AND",
        "arabia-saudi": "SAU",
        "argelia": "DZA",
        "argentina": "ARG",
        "austria": "AUT",
        "australia": "AUS",
        "armenia": "ARM",
        "azerbaian": "AZE",
        "bielorrusia": "BLR",
        "barbados": "BRB",
        "belgica": "BEL",
        "bolivia": "BOL",
        "bosnia-y-herzegovina": "BIH",
        "brasil": "BRA",
        "bulgaria": "BGR",
        "cabo-verde": "CPV",
        "canada": "CAN",
        "catar": "QAT",
        "chequia": "CZE",
        "chile": "CHL",
        "china": "CHN",
        "chipre": "CYP",
        "colombia": "COL",
        "corea-del-sur": "KOR",
        "costa-rica": "CRI",
        "croacia": "HRV",
        "cuba": "CUB",
        "dinamarca": "DNK",
        "ecuador": "ECU",
        "egipto": "EGY",
        "emirates-arabes-unidos": "ARE",
        "eslovaquia": "SVK",
        "eslovenia": "SVN",
        "estados-unidos": "USA",
        "estonia": "EST",
        "filipinas": "PHL",
        "finlandia": "FIN",
        "francia": "FRA",
        "georgia": "GEO",
        "grecia": "GRC",
        "hungria": "HUN",
        "india": "IND",
        "indonesia": "IDN",
        "iran": "IRN",
        "irlanda": "IRL",
        "islandia": "ISL",
        "israel": "ISR",
        "italia": "ITA",
        "jamaica": "JAM",
        "japon": "JPN",
        "kazajstan": "KAZ",
        "kuwait": "KWT",
        "letonia": "LVA",
        "lituanía": "LTU",
        "luxemburgo": "LUX",
        "macedonia": "MKD",
        "malasia": "MYS",
        "malta": "MLT",
        "marruecos": "MAR",
        "mexico": "MEX",
        "moldavia": "MDA",
        "nigeria": "NGA",
        "noruega": "NOR",
        "nueva-zelanda": "NZL",
        "oman": "OMN",
        "paises-bajos": "NLD",
        "pakistan": "PAK",
        "panama": "PAN",
        "paraguay": "PRY",
        "polonia": "POL",
        "portugal": "PRT",
        "reino-unido": "GBR",
        "republica-dominicana": "DOM",
        "rumania": "ROU",
        "rusia": "RUS",
        "el-salvador": "SLV",
        "senegal": "SEN",
        "serbia": "SRB",
        "singapur": "SGP",
        "sudafrica": "ZAF",
        "suecia": "SWE",
        "suiza": "CHE",
        "tailandia": "THA",
        "trinidad-y-tobago": "TTO",
        "tunéz": "TUN",
        "turquia": "TUR",
        "uruguay": "URY",
        "uzbekistan": "UZB",
        "venezuela": "VEN",
        "vietnam": "VNM",
    }

    for link in country_links:
        href = link["href"]
        text_content = _clean_text(link.get_text())

        # Only interested in CDI/convenio country detail links
        if not any(kw in href.lower() for kw in ["cdi", "convenio"]):
            continue

        # Extract country name from text
        country_name = None
        for known in KNOWN_COUNTRIES:
            if known.lower() in text_content.lower():
                country_name = known
                break

        if not country_name:
            continue

        # Derive country code from URL slug
        code_slug = os.path.basename(href).replace(".html", "").replace(".htm", "").lower()
        country_code = COUNTRY_CODES.get(code_slug, country_name[:3].upper())

        countries.append({
            "codigo": country_code,
            "nombre": country_name,
            "detalle_url": AEAT_SEDE + href if not href.startswith("http") else href,
            "url_slug": code_slug,
        })

    return countries


# ── Sync engine ────────────────────────────────────────────────────

def discover_and_sync() -> dict:
    """Main sync: discover countries, fetch details, upsert conventions."""
    stats = {
        "countries_discovered": 0,
        "conventions_upserted": 0,
        "conventions_skipped": 0,
        "conventions_deprecated": 0,
        "errors": 0,
    }

    try:
        from sqlalchemy import create_engine as _create_engine
        engine = _create_engine(DATABASE_URL, pool_pre_ping=True)
        ensure_database_connection(engine)

        with httpx.Client(
            timeout=30,
            follow_redirects=True,
            headers=HEADERS,
        ) as client:
            # 1. Fetch listing page
            listing_html = _safe_fetch(client, CDI_LISTING_URL)
            if not listing_html:
                logger.error("Could not fetch CDI listing page")
                return stats

            # 2. Extract country links from AEAT page
            countries = extract_countries_from_listing(listing_html)
            stats["countries_discovered"] = len(countries)
            logger.info("Discovered %d CDI countries from AEAT listing", len(countries))

            # 3. For each country, fetch details and upsert
            for country in countries:
                try:
                    touch_heartbeat()
                    detail_html = _safe_fetch(client, country["detalle_url"])
                    if not detail_html:
                        logger.warning("Skipping %s - no details page", country["nombre"])
                        stats["conventions_skipped"] += 1
                        continue

                    convention = _parse_country_convention(country, detail_html)
                    _upsert_convention(engine, convention)
                    stats["conventions_upserted"] += 1

                except Exception as exc:
                    logger.error("Error processing %s: %s", country["nombre"], exc, exc_info=True)
                    stats["errors"] += 1

            # 4. Mark conventions as deprecated if not in current list
            current_codes = {c["codigo"] for c in countries}
            deprecated = _cleanup_deprecated(engine, current_codes)
            stats["conventions_deprecated"] = deprecated
            logger.info("Deprecated %d conventions not in listing", deprecated)

        return stats

    except Exception as exc:
        logger.error("CDI sync failed: %s", exc, exc_info=True)
        stats["errors"] += 1
        return stats


def _parse_country_convention(country: dict, html: str) -> dict:
    """Extract CDI details from country detail page."""
    soup = BeautifulSoup(html, "html.parser")

    # Extract PDF links
    pdf_urls = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        text = _clean_text(link.get_text())
        if href.endswith((".pdf", ".PDF")) or "pdf" in text.lower():
            url = AEAT_SEDE + href if not href.startswith("http") else href
            pdf_urls.append(url)

    # Extract dates and BOE references from the page text
    text_content = soup.get_text()

    fecha_firma = None
    fecha_vigencia = None
    boe_referencia = ""

    # Look for firma dates
    firma_patterns = [
        r"[Ff]irma\s*[:\.]?\s?([0-9]{1,2}[/\s-][0-9]{1,2}[/\s-][0-9]{2,4})",
        r"Firma.*?(\d{1,2}/\d{1,2}/\d{4})",
    ]
    for pat in firma_patterns:
        m = re.search(pat, text_content)
        if m:
            fecha_firma = _parse_date(m.group(1))
            break

    # Look for vigencia dates (BOE entry into force)
    vigencia_patterns = [
        r"[Vv]igencia\s*[:\.]?\s?([0-9]{1,2}[/\s-][0-9]{1,2}[/\s-][0-9]{2,4})",
        r"vigor.*?(\d{1,2}/\d{1,2}/\d{4})",
    ]
    for pat in vigencia_patterns:
        m = re.search(pat, text_content)
        if m:
            fecha_vigencia = _parse_date(m.group(1))
            break

    # Look for BOE reference
    boe_patterns = [
        r"BOE\s*[:\.]?\s?(\d{4})\s*(?:\d{1,2}[/\s-][A-Za-z]{3}[/\s-][0-9]{1,2})?",
        r"Boletín\s*Oficial.*?BOE.*?(\d{4})",
        r"BOE\s+(\d{4})",
    ]
    for pat in boe_patterns:
        m = re.search(pat, text_content)
        if m:
            boe_referencia = f"BOE-{m.group(1)}"
            break

    # Get full page text
    texto_completo = soup.get_text(separator="\n", strip=True)

    convention = {
        "codigo_pais": country["codigo"],
        "pais": country["nombre"],
        "fecha_firma": fecha_firma,
        "fecha_vigencia": fecha_vigencia,
        "boe_referencia": boe_referencia,
        "pdf_urls": list(set(pdf_urls)),  # deduplicate
        "articulos": {},
        "estado": "vigente",
        "texto_completo": texto_completo,
    }

    logger.info(
        "Parsed %s: firma=%s vigencia=%s BOE=%s PDFs=%d",
        country["nombre"], fecha_firma, fecha_vigencia, boe_referencia, len(convention["pdf_urls"])
    )

    return convention


def _upsert_convention(engine, data: dict) -> None:
    """Insert or update a CDI convention in irs_dta_convention."""
    sql = """
    INSERT INTO irs_dta_convention (
        codigo, pais_origen, pais_destino, titulo, fecha_firma, fecha_vigencia, tipo_acuerdo,
        boe_referencia, articulos, texto_completo, estado, creado_en, actualizado_en
    ) VALUES (
        :codigo, :pais, 'España', 'Convenio de doble imposición con ' || :pais, :fecha_firma, :fecha_vigencia, 'convencion_doble_imposicion',
        :boe_ref, :articulos, :texto, 'vigente', NOW(), NOW()
    )
    ON CONFLICT (codigo)
    DO UPDATE SET
        pais_origen = EXCLUDED.pais_origen,
        fecha_firma = EXCLUDED.fecha_firma,
        fecha_vigencia = EXCLUDED.fecha_vigencia,
        boe_referencia = EXCLUDED.boe_referencia,
        articulos = EXCLUDED.articulos,
        texto_completo = EXCLUDED.texto_completo,
        estado = EXCLUDED.estado,
        actualizado_en = NOW()
    """

    with engine.connect() as conn:
        conn.execute(text(sql), {
            "codigo": data["codigo_pais"],
            "pais": data["pais"],
            "fecha_firma": data["fecha_firma"],
            "fecha_vigencia": data["fecha_vigencia"],
            "boe_ref": data["boe_referencia"],
            "articulos": json.dumps(data["articulos"], ensure_ascii=False),
            "texto": data["texto_completo"][:50000],  # prevent oversized text
        })
        conn.commit()
        logger.debug("Upserted convention for %s", data["pais"])


def _cleanup_deprecated(engine, current_codes: set) -> int:
    """Mark conventions as deprecated if not in current list."""
    if not current_codes:
        return 0

    current_codes_list = list(current_codes)
    if not current_codes_list:
        return 0

    codes_param = ','.join(repr(c) for c in current_codes_list)
    sql = f"""
    UPDATE irs_dta_convention
    SET estado = 'derogado', actualizado_en = NOW()
    WHERE estado = 'vigente'
    AND codigo NOT IN ({codes_param})
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), {"current_codes": tuple(current_codes)})
            deprecated = result.rowcount
            conn.commit()
            return deprecated
    except Exception as exc:
        logger.warning("Could not cleanup deprecated: %s", exc)
        return 0


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CDI Worker — Fetch and store Double Taxation Treaties from AEAT/Hacienda"
    )
    parser.add_argument("--run-once", action="store_true", help="Sync once and exit")
    parser.add_argument("--interval", type=int, help="Sync interval in seconds")
    args = parser.parse_args()

    if args.run_once:
        logger.info("Starting CDI worker (single run)")
        stats = discover_and_sync()
        logger.info("CDI sync complete: %s", json.dumps(stats, indent=2))
    else:
        interval = args.interval or SYNC_INTERVAL_SECONDS
        logger.info("Starting CDI worker (interval=%ds)", interval)
        while True:
            try:
                stats = discover_and_sync()
                logger.info("CDI sync complete: %s", json.dumps(stats, indent=2))
            except Exception as exc:
                logger.error("CDI sync error: %s", exc, exc_info=True)

            time.sleep(interval)


if __name__ == "__main__":
    main()
