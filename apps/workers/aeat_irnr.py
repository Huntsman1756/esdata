#!/usr/bin/env python
"""Worker de descubrimiento y actualizacion de modelos IRNR desde la sede AEAT.

Descubre modelos IRNR desde el portal AEAT de no residentes, actualiza metadata,
y marca como inactivos los modelos que ya no aparecen en el portal.

Uso:
    python aeat_irnr.py --run-once
    python aeat_irnr.py --interval 3600
"""

import argparse
import os
import re
import time
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from runtime import (
    configure_logging,
    get_database_url,
    get_interval_seconds,
)
from sqlalchemy import create_engine, text

logger = configure_logging("worker-aeat-irnr")

AEAT_SEDE = "https://sede.agenciatributaria.gob.es"
AEAT_IRNR_PORTAL = (
    "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/"
    "modelos-informacion-y-declaraciones/no_residentes/"
)
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("IRNR_SYNC_INTERVAL", 86400)

# Modelos IRNR especificos que este worker gestiona
IRNR_MODELOS = {
    "116": "Actividades economicas (periodo trimestral)",
    "123": "Rendimientos sin establecimiento permanente",
    "124": "Dividendos y rentas del capital mobiliario",
    "212": "Dividendos y rentas del capital (empresas)",
    "216": "FactA a terceros (no residentes)",
    "296": "Resumen anual de retenciones",
    "878": "Relacion de pagos a proveedores no residentes",
}


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

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

def _discover_irnr_models() -> list[dict]:
    """Descubre modelos IRNR desde el portal AEAT de no residentes.

    Retorna lista de dicts con:
      codigo, nombre, url_info, periodo, impuesto
    """
    client = _build_client()
    html = _fetch(AEAT_IRNR_PORTAL, lambda: client, logger, "IRNR portal")
    if not html:
        logger.error("No HTML from AEAT IRNR portal")
        return []

    soup = BeautifulSoup(html, "html.parser")
    models = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        text = (a_tag.get_text(strip=True) or "").strip()
        codigo = None
        url_info = None

        # Pattern 1: URL contains modelo_XXXX_
        match = re.search(r"modelo_(\d{3})_", href)
        if match:
            codigo = match.group(1)
            url_info = href if href.startswith("http") else urljoin(AEAT_IRNR_PORTAL, href)

        # Pattern 2: Text starts with model code
        if not codigo and text:
            text_match = re.match(r"^(\d{3})\s*[-—:]", text)
            if text_match:
                codigo = text_match.group(1)
                url_info = AEAT_IRNR_PORTAL

        if codigo and codigo in IRNR_MODELOS and url_info:
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

    logger.info("Discovered %d IRNR models from AEAT portal", len(unique))
    return unique


def _extract_model_name(raw_text: str, codigo: str) -> str:
    """Extract a human-readable name from the raw link text or code."""
    if raw_text:
        # Clean HTML entities and trim
        name = re.sub(r"<[^>]+>", " ", raw_text)
        name = re.sub(r"&nbsp;", " ", name)
        name = re.sub(r"[;\-—:]+", " ", name).strip()
        if len(name) > 5:
            return name[:200]
    return f"Modelo {codigo}"


# -------------------------------------------------------------------
# Database operations
# -------------------------------------------------------------------

def _upsert_irnr_model(conn, codigo: str, nombre: str, url_info: str, periodo: str | None = None, impuesto: str | None = None) -> bool:
    """Upsert un modelo IRNR en aeat_modelo por codigo."""
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
        logger.error("Failed to upsert IRNR modelo %s: %s", codigo, exc)
        return False


def _mark_deprecated_irnr_models(conn, discovered_codes: set[str]) -> int:
    """Marca como inactivos los modelos IRNR en DB que no aparecen en el portal."""
    try:
        if discovered_codes:
            placeholders = ", ".join(f":code_{i}" for i in range(len(discovered_codes)))
            params = {f"code_{i}": code for i, code in enumerate(discovered_codes)}
            params["now"] = None
            sql = f"""
                UPDATE aeat_modelo
                SET activo = false, actualizado_at = datetime('now')
                WHERE activo = true
                  AND impuesto = 'IRNR'
                  AND codigo NOT IN ({placeholders})
                """
            result = conn.execute(text(sql), params)
        else:
            result = conn.execute(
                text(
                    """
                    UPDATE aeat_modelo
                    SET activo = false, actualizado_at = datetime('now')
                    WHERE activo = true
                      AND impuesto = 'IRNR'
                      AND codigo NOT IN ('__none__')
                    """
                )
            )
        return result.rowcount
    except Exception as exc:
        logger.warning("Failed to mark deprecated IRNR models: %s", exc)
        return 0


def _get_existing_codes(conn) -> set[str]:
    """Returns set of codigo values currently in aeat_modelo for IRNR models."""
    try:
        rows = conn.execute(
            text("SELECT codigo FROM aeat_modelo WHERE impuesto = 'IRNR'")
        ).fetchall()
        return {row[0] for row in rows}
    except Exception:
        return set()


# -------------------------------------------------------------------
# Main sync loop
# -------------------------------------------------------------------

def run_sync(engine, run_once: bool = False):
    logger.info("Starting IRNR models discovery worker...")

    while True:
        try:
            # Step 1: Discover IRNR models from AEAT portal
            discovered = _discover_irnr_models()
            if not discovered:
                logger.warning("No IRNR models discovered, skipping sync")
                if run_once:
                    break
                time.sleep(SYNC_INTERVAL_SECONDS)
                continue

            discovered_codes = {m["codigo"] for m in discovered}
            logger.info("Discovered %d IRNR models: %s", len(discovered_codes), ", ".join(sorted(discovered_codes)))

            upserted = 0
            skipped = 0

            with engine.begin() as conn:
                for model in discovered:
                    codigo = model["codigo"]
                    nombre = model["nombre"]
                    url_info = model["url_info"]

                    if _upsert_irnr_model(conn, codigo, nombre, url_info):
                        upserted += 1
                        logger.info("  Upserted IRNR modelo %s (%s)", codigo, nombre)
                    else:
                        skipped += 1

                # Step 2: Mark deprecated IRNR models
                deprecated_count = _mark_deprecated_irnr_models(conn, discovered_codes)
                if deprecated_count:
                    logger.info("Marked %d IRNR models as deprecated", deprecated_count)

            logger.info("IRNR sync complete: %d upserted, %d skipped, %d deprecated", upserted, skipped, deprecated_count)

        except Exception as exc:
            logger.exception("IRNR sync failed: %s", exc)

        if run_once:
            break

        logger.info("Next IRNR sync in %ds", SYNC_INTERVAL_SECONDS)
        time.sleep(SYNC_INTERVAL_SECONDS)


def main():
    parser = argparse.ArgumentParser(
        description="Discover and update IRNR models from the AEAT portal"
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
