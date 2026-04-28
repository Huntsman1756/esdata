#!/usr/bin/env python
"""Worker de descubrimiento y actualizacion de modelos AEAT desde la sede AEAT.

Descubre modelos desde el portal AEAT, actualiza metadata, y marca como
inactivos los modelos que ya no aparecen en el portal.

Uso:
    python aeat_models.py --run-once
    python aeat_models.py --interval 3600
"""

import argparse
import os
import re
import time
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

from runtime import (
    configure_logging,
    get_database_url,
    get_interval_seconds,
)

logger = configure_logging("worker-aead-modelos")

AEAT_SEDE = "https://sede.agenciatributaria.gob.es"
AEAT_MODELOS_PORTAL = (
    "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/"
    "modelos-informacion-y-declaraciones/"
)
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("AEAT_MODELS_SYNC_INTERVAL", 86400)


def _build_client(ssl_verify: bool = False) -> httpx.Client:
    return httpx.Client(
        base_url=AEAT_SEDE,
        follow_redirects=True,
        timeout=30,
        verify=ssl_verify,
        headers={
            "User-Agent": "esdata-bot/1.0 (fiscal data infrastructure bot)",
        },
    )


def _fetch(url: str, client_fn, logger, context: str = "page") -> str | None:
    try:
        with client_fn() as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp.text
    except Exception as exc:
        logger.warning("Failed to fetch %s %s: %s", context, url, exc)
    return None


# -------------------------------------------------------------------
# Discovery
# -------------------------------------------------------------------

def _discover_aeat_models() -> list[dict]:
    """Descubre modelos desde el portal AEAT.

    Retorna lista de dicts con:
      codigo, nombre, url_info
    """
    client = _build_client()
    html = _fetch(AEAT_MODELOS_PORTAL, lambda: client, logger, "portal")
    if not html:
        logger.error("No HTML from AEAT portal")
        return []

    soup = BeautifulSoup(html, "html.parser")
    models = []

    # The AEAT portal uses links to individual model pages.
    # Pattern: href containing "modelo_" and ending in .html
    # Also look for data attributes or link text containing model codes.
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        text = (a_tag.get_text(strip=True) or "").strip()

        # Extract model code from URL or text
        codigo = None
        url_info = None

        # Pattern 1: URL contains modelo_XXXX_...
        match = re.search(r"modelo_(\d{3})_", href)
        if match:
            codigo = match.group(1)
            url_info = href if href.startswith("http") else urljoin(AEAT_MODELOS_PORTAL, href)

        # Pattern 2: Text starts with model code
        if not codigo and text:
            text_match = re.match(r"^(\d{3})\s*[-–—:]", text)
            if text_match:
                codigo = text_match.group(1)
                url_info = AEAT_MODELOS_PORTAL

        if codigo and url_info:
            nombre = _extract_model_name(text, codigo)
            models.append({
                "codigo": codigo,
                "nombre": nombre,
                "url_info": url_info,
            })

    # Deduplicate by codigo, keeping first occurrence
    seen = set()
    unique = []
    for m in models:
        if m["codigo"] not in seen:
            seen.add(m["codigo"])
            unique.append(m)

    logger.info("Discovered %d unique models from AEAT portal", len(unique))
    return unique


def _extract_model_name(raw_text: str, codigo: str) -> str:
    """Extract a human-readable name from the raw link text or code."""
    if raw_text:
        # Clean HTML entities and trim
        name = re.sub(r"<[^>]+>", " ", raw_text)
        name = re.sub(r"&nbsp;", " ", name)
        name = re.sub(r"[;\-–—:]+", " ", name).strip()
        if len(name) > 5:
            return name[:200]
    return f"Modelo {codigo}"


# -------------------------------------------------------------------
# Metadata fetching
# -------------------------------------------------------------------

def _fetch_model_metadata(codigo: str) -> dict | None:
    """Obtiene metadata basica desde la pagina oficial de cada modelo."""
    # Try to find the model page URL from the portal
    client = _build_client()
    html = _fetch(AEAT_MODELOS_PORTAL, lambda: client, logger, "portal")
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    url_info = None

    for a_tag in soup.find_all("a", href=True):
        if re.search(rf"modelo_{codigo}_", a_tag["href"]):
            url_info = a_tag["href"] if a_tag["href"].startswith("http") else urljoin(AEAT_MODELOS_PORTAL, a_tag["href"])
            break

    if not url_info:
        logger.warning("Modelo %s not found on portal page", codigo)
        return None

    # Fetch the model page to extract additional metadata
    model_html = _fetch(url_info, lambda: client, logger, "model page")
    if not model_html:
        return {"codigo": codigo, "url_info": url_info}

    model_soup = BeautifulSoup(model_html, "html.parser")

    # Try to extract periodo from page content
    periodo = None
    page_text = model_soup.get_text(" ", strip=True).lower()
    if "mensual" in page_text:
        periodo = "mensual"
    elif "trimestral" in page_text:
        periodo = "trimestral"
    elif "anual" in page_text:
        periodo = "anual"

    # Try to extract impuesto
    impuesto = None
    if "irpf" in page_text:
        impuesto = "IRPF"
    elif "iva" in page_text:
        impuesto = "IVA"
    elif "is" in page_text or "impuesto sociedades" in page_text:
        impuesto = "IS"
    elif "irnr" in page_text:
        impuesto = "IRNR"
    elif "informacion" in page_text or "informativo" in page_text:
        impuesto = "informacion"

    return {
        "codigo": codigo,
        "nombre": _extract_model_name(model_soup.get_text(" ", strip=True)[:150], codigo),
        "url_info": url_info,
        "periodo": periodo,
        "impuesto": impuesto,
    }


# -------------------------------------------------------------------
# Database operations
# -------------------------------------------------------------------

def _upsert_aeat_model(conn, codigo: str, nombre: str, url_info: str, periodo: str | None = None, impuesto: str | None = None) -> bool:
    """Upsert un modelo en aeat_modelo por codigo."""
    try:
        conn.execute(
            text(
                """
                INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info, activo)
                VALUES (:codigo, :nombre, :periodo, :impuesto, :url_info, true)
                ON CONFLICT (codigo) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    periodo = COALESCE(EXCLUDED.periodo, aeat_modelo.periodo),
                    impuesto = COALESCE(EXCLUDED.impuesto, aeat_modelo.impuesto),
                    url_info = EXCLUDED.url_info,
                    activo = true,
                    actualizado_at = datetime('now')
                """
            ),
            {
                "codigo": codigo,
                "nombre": nombre,
                "periodo": periodo,
                "impuesto": impuesto,
                "url_info": url_info,
            },
        )
        return True
    except Exception as exc:
        logger.error("Failed to upsert modelo %s: %s", codigo, exc)
        return False


def _mark_deprecated_models(conn, discovered_codes: set[str]) -> int:
    """Marca como inactivos los modelos en DB que no aparecen en el portal."""
    try:
        if not discovered_codes:
            return 0
        codes = tuple(discovered_codes)
        placeholders = ",".join([f":c{i}" for i in range(len(codes))])
        params = {f"c{i}": code for i, code in enumerate(codes)}
        conn.execute(
            text(
                f"""
                UPDATE aeat_modelo
                SET activo = false
                WHERE activo = true
                  AND codigo NOT IN ({placeholders})
                """
            ),
            params,
        )
        return conn.execute(text("SELECT changes()")).scalar() or 0
    except Exception as exc:
        logger.warning("Failed to mark deprecated models: %s", exc)
        return 0


def _get_existing_codes(conn) -> set[str]:
    """Returns set of codigo values currently in aeat_modelo."""
    try:
        rows = conn.execute(
            text("SELECT codigo FROM aeat_modelo")
        ).fetchall()
        return {row[0] for row in rows}
    except Exception:
        return set()


# -------------------------------------------------------------------
# Main sync loop
# -------------------------------------------------------------------

def run_sync(engine, run_once: bool = False):
    logger.info("Starting AEAT models discovery worker...")

    while True:
        try:
            # Step 1: Discover models from AEAT portal
            discovered = _discover_aeat_models()
            if not discovered:
                logger.warning("No models discovered, skipping sync")
                if run_once:
                    break
                time.sleep(SYNC_INTERVAL_SECONDS)
                continue

            discovered_codes = {m["codigo"] for m in discovered}
            logger.info("Discovered %d models: %s", len(discovered_codes), ", ".join(sorted(discovered_codes)))

            upserted = 0
            skipped = 0

            with engine.begin() as conn:
                existing_codes = _get_existing_codes(conn)

                for model in discovered:
                    codigo = model["codigo"]
                    nombre = model["nombre"]
                    url_info = model["url_info"]

                    # Try to enrich with metadata
                    metadata = _fetch_model_metadata(codigo)
                    if metadata:
                        nombre = metadata.get("nombre", nombre)
                        url_info = metadata.get("url_info", url_info)
                        periodo = metadata.get("periodo")
                        impuesto = metadata.get("impuesto")
                    else:
                        periodo = None
                        impuesto = None

                    if _upsert_aeat_model(conn, codigo, nombre, url_info, periodo, impuesto):
                        upserted += 1
                        logger.info("  Upserted modelo %s (%s)", codigo, nombre)
                    else:
                        skipped += 1

                # Step 2: Mark deprecated models
                deprecated_count = _mark_deprecated_models(conn, discovered_codes)
                if deprecated_count:
                    logger.info("Marked %d models as deprecated", deprecated_count)

            logger.info("Sync complete: %d upserted, %d skipped, %d deprecated", upserted, skipped, deprecated_count)

        except Exception as exc:
            logger.error("Sync failed: %s", exc, exc_info=True)

        if run_once:
            break

        logger.info("Next sync in %ds", SYNC_INTERVAL_SECONDS)
        time.sleep(SYNC_INTERVAL_SECONDS)


def main():
    parser = argparse.ArgumentParser(
        description="Discover and update AEAT models from the official portal"
    )
    parser.add_argument("--db-url", help="Database URL")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, help="Sync interval in seconds")
    args = parser.parse_args()

    db_url = args.db_url or os.getenv("DATABASE_URL", DATABASE_URL)
    interval = args.interval or SYNC_INTERVAL_SECONDS

    logger.info("DB: %s...", db_url[:50])
    logger.info("Interval: %ds", interval)
    logger.info("Run once: %s", args.run_once)

    engine = create_engine(db_url)
    run_sync(engine, run_once=args.run_once)


if __name__ == "__main__":
    main()
