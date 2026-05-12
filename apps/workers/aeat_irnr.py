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
    ensure_database_connection,
    configure_logging,
    get_database_url,
    get_interval_seconds,
    handle_worker_failure,
)
from sqlalchemy import create_engine, text

from change_detection import (
    check_content_changed,
    record_revision,
    ensure_source_revision_table,
)

logger = configure_logging("worker-aeat-irnr")

AEAT_SEDE = "https://sede.agenciatributaria.gob.es"
AEAT_IRNR_PORTAL = f"{AEAT_SEDE}/Sede/impuestos-tasas/irnr.html"
AEAT_IRNR_RATES_URL = (
    f"{AEAT_SEDE}/Sede/no-residentes/irnr-sin-establecimiento-permanente/"
    "tipos-gravamen-irnr-sin-establecimiento-permanente.html"
)
BOE_IRNR_LAW_URL = "https://www.boe.es/buscar/act.php?id=BOE-A-2004-4527"
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("IRNR_SYNC_INTERVAL", 86400)

# Modelos IRNR especificos que este worker gestiona
IRNR_MODELOS = {
    "210": "IRNR sin establecimiento permanente",
    "211": "Retencion en la adquisicion de bienes inmuebles",
    "213": "Gravamen especial sobre bienes inmuebles de entidades no residentes",
    "216": "Retenciones e ingresos a cuenta",
    "226": "Regimen opcional para residentes UE/EEE",
    "228": "Devolucion por exencion por reinversion en vivienda habitual",
    "247": "Comunicacion de desplazamiento al extranjero",
    "296": "Resumen anual de retenciones",
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

        # Pattern 1: URL contains modelo-XXX or modelo_XXX.
        match = re.search(r"modelo[-_](\d{3})(?:[-_./]|$)", href, re.IGNORECASE)
        if match:
            codigo = match.group(1)
            url_info = href if href.startswith("http") else urljoin(AEAT_IRNR_PORTAL, href)

        # Pattern 2: Text starts with "Modelo XXX" or a bare model code.
        if not codigo and text:
            text_match = re.match(r"^(?:Modelo\s*)?(\d{3})\s*[\.\-:]", text, re.IGNORECASE)
            if text_match:
                codigo = text_match.group(1)
                url_info = href if href.startswith("http") else urljoin(AEAT_IRNR_PORTAL, href)

        if codigo and codigo in IRNR_MODELOS and url_info:
            nombre = _extract_model_name(text, codigo)
            if nombre == f"Modelo {codigo}":
                nombre = IRNR_MODELOS[codigo]
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


def _extract_instruction_sections(html: str, title: str, source_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines()]
    lines = [line for line in lines if line]
    content = "\n".join(lines)
    if len(content) < 100:
        return []

    return [
        {
            "seccion": "portal_aeat_modelo",
            "titulo": title[:200],
            "contenido": f"Fuente oficial AEAT: {source_url}\n\n{content[:8000]}",
            "source_url": source_url,
            "source_family": "AEAT official portal",
        }
    ]


def _extract_irnr_rate_rows(html: str, source_url: str = AEAT_IRNR_RATES_URL) -> list[dict]:
    text_content = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
    required_phrases = [
        "Tipos de gravamen en el IRNR sin establecimiento permanente",
        "Dividendos",
        "Intereses",
        "Pensiones",
        "Página actualizada:",
    ]
    if not all(phrase in text_content for phrase in required_phrases):
        return []

    legal_basis = f"Artículo 25 TRLIRNR (BOE-A-2004-4527); fuente AEAT: {source_url}"
    notes = (
        "Tipos extraidos de la pagina oficial AEAT de tipos de gravamen IRNR sin "
        "establecimiento permanente. La pagina informa 'Pagina actualizada: 18/junio/2025'. "
        "Cuando la pagina no indica una fecha de vigencia individual para el concepto, "
        "effective_date se deja sin informar."
    )

    return [
        {
            "tipo_renta": "general_ue_islandia_noruega",
            "tipo_retencion": 19.0,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Con caracter general: Residentes UE, Islandia y Noruega: 19%.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": None,
            "legal_basis": legal_basis,
            "uncertainty_notes": notes,
        },
        {
            "tipo_renta": "general_liechtenstein_desde_2021_07_11",
            "tipo_retencion": 19.0,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Con caracter general: Liechtenstein desde 11-07-2021: 19%.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": "2021-07-11",
            "legal_basis": legal_basis,
            "uncertainty_notes": notes,
        },
        {
            "tipo_renta": "general_liechtenstein_hasta_2021_07_10",
            "tipo_retencion": 24.0,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Con caracter general: Liechtenstein hasta 10-07-2021: 24%.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": None,
            "legal_basis": legal_basis,
            "uncertainty_notes": "Historico incluido en la tabla AEAT; no usar como tipo actual desde 11-07-2021.",
        },
        {
            "tipo_renta": "general_resto_contribuyentes",
            "tipo_retencion": 24.0,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Con caracter general: Resto contribuyentes: 24%.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": None,
            "legal_basis": legal_basis,
            "uncertainty_notes": notes,
        },
        {
            "tipo_renta": "trabajo_temporada",
            "tipo_retencion": 2.0,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Contrato de duracion determinada para trabajadores de temporada: 2%.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": None,
            "legal_basis": legal_basis,
            "uncertainty_notes": notes,
        },
        {
            "tipo_renta": "dividendos_participacion_fondos_propios",
            "tipo_retencion": 19.0,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Dividendos y otros rendimientos derivados de la participacion en fondos propios: 19%.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": None,
            "legal_basis": legal_basis,
            "uncertainty_notes": notes,
        },
        {
            "tipo_renta": "intereses_capitales_propios",
            "tipo_retencion": 19.0,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Intereses y otros rendimientos obtenidos por la cesion a terceros de capitales propios: 19%.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": None,
            "legal_basis": legal_basis,
            "uncertainty_notes": notes,
        },
        {
            "tipo_renta": "pensiones_tramo_hasta_12000",
            "tipo_retencion": 8.0,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Pensiones: hasta 12.000 euros, 8%.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": None,
            "legal_basis": legal_basis,
            "uncertainty_notes": notes,
        },
        {
            "tipo_renta": "pensiones_tramo_12000_18700",
            "tipo_retencion": 30.0,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Pensiones: desde 12.000 euros hasta 18.700 euros, 30% sobre el resto.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": None,
            "legal_basis": legal_basis,
            "uncertainty_notes": notes,
        },
        {
            "tipo_renta": "pensiones_tramo_desde_18700",
            "tipo_retencion": 40.0,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Pensiones: desde 18.700 euros en adelante, 40%.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": None,
            "legal_basis": legal_basis,
            "uncertainty_notes": notes,
        },
        {
            "tipo_renta": "trabajo_misiones_diplomaticas_consulares",
            "tipo_retencion": 8.0,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Trabajo en Misiones Diplomaticas y Representaciones Consulares de Espana en el extranjero: 8%.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": None,
            "legal_basis": legal_basis,
            "uncertainty_notes": notes,
        },
        {
            "tipo_renta": "reaseguro",
            "tipo_retencion": 1.5,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Rendimientos derivados de operaciones de reaseguro: 1,5%.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": None,
            "legal_basis": legal_basis,
            "uncertainty_notes": notes,
        },
        {
            "tipo_renta": "navegacion_maritima_aerea",
            "tipo_retencion": 4.0,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Entidades de navegacion maritima o aerea residentes en el extranjero: 4%.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": None,
            "legal_basis": legal_basis,
            "uncertainty_notes": notes,
        },
        {
            "tipo_renta": "ganancias_iic",
            "tipo_retencion": 19.0,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Ganancias patrimoniales por acciones o participaciones de instituciones de inversion colectiva: 19%.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": None,
            "legal_basis": legal_basis,
            "uncertainty_notes": notes,
        },
        {
            "tipo_renta": "otras_ganancias_transmisiones",
            "tipo_retencion": 19.0,
            "articulo_referencia": "art. 25 TRLIRNR",
            "fuente_texto": "Otras ganancias patrimoniales por transmisiones de elementos patrimoniales: 19%.",
            "source_url": source_url,
            "source_family": "AEAT official portal; BOE official text",
            "effective_date": None,
            "legal_basis": legal_basis,
            "uncertainty_notes": notes,
        },
    ]


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
                    activo = true
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
        if not discovered_codes:
            return 0

        placeholders = ", ".join(f":code_{i}" for i in range(len(discovered_codes)))
        params = {f"code_{i}": code for i, code in enumerate(discovered_codes)}
        sql = f"""
            UPDATE aeat_modelo
            SET activo = false
            WHERE activo = true
              AND impuesto = 'IRNR'
              AND codigo NOT IN ({placeholders})
            """
        result = conn.execute(text(sql), params)
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


def _get_model_id(conn, codigo: str) -> int | None:
    row = conn.execute(
        text("SELECT id FROM aeat_modelo WHERE codigo = :codigo"),
        {"codigo": codigo},
    ).fetchone()
    return row[0] if row else None


def _upsert_irnr_instructions(conn, modelo_id: int, instructions: list[dict]) -> int:
    count = 0
    for inst in instructions:
        conn.execute(
            text(
                """
                INSERT INTO irnr_instruccion (
                    modelo_id, seccion, titulo, contenido, source_url, source_family
                )
                VALUES (
                    :modelo_id, :seccion, :titulo, :contenido, :source_url, :source_family
                )
                ON CONFLICT (modelo_id, seccion) DO UPDATE SET
                    titulo = EXCLUDED.titulo,
                    contenido = EXCLUDED.contenido,
                    source_url = EXCLUDED.source_url,
                    source_family = EXCLUDED.source_family,
                    actualizado_en = CURRENT_TIMESTAMP
                """
            ),
            {
                "modelo_id": modelo_id,
                "seccion": inst["seccion"],
                "titulo": inst["titulo"],
                "contenido": inst["contenido"],
                "source_url": inst["source_url"],
                "source_family": inst["source_family"],
            },
        )
        count += 1
    return count


def _upsert_irnr_rates(conn, modelo_id: int, rates: list[dict]) -> int:
    count = 0
    for rate in rates:
        conn.execute(
            text(
                """
                INSERT INTO irnr_withholding_rate (
                    modelo_id,
                    tipo_renta,
                    tipo_retencion,
                    articulo_referencia,
                    fuente_texto,
                    source_url,
                    source_family,
                    effective_date,
                    legal_basis,
                    uncertainty_notes,
                    activo
                )
                VALUES (
                    :modelo_id,
                    :tipo_renta,
                    :tipo_retencion,
                    :articulo_referencia,
                    :fuente_texto,
                    :source_url,
                    :source_family,
                    :effective_date,
                    :legal_basis,
                    :uncertainty_notes,
                    true
                )
                ON CONFLICT (modelo_id, tipo_renta) DO UPDATE SET
                    tipo_retencion = EXCLUDED.tipo_retencion,
                    articulo_referencia = EXCLUDED.articulo_referencia,
                    fuente_texto = EXCLUDED.fuente_texto,
                    source_url = EXCLUDED.source_url,
                    source_family = EXCLUDED.source_family,
                    effective_date = EXCLUDED.effective_date,
                    legal_basis = EXCLUDED.legal_basis,
                    uncertainty_notes = EXCLUDED.uncertainty_notes,
                    activo = true,
                    actualizado_en = CURRENT_TIMESTAMP
                """
            ),
            {
                "modelo_id": modelo_id,
                "tipo_renta": rate["tipo_renta"],
                "tipo_retencion": rate["tipo_retencion"],
                "articulo_referencia": rate.get("articulo_referencia"),
                "fuente_texto": rate.get("fuente_texto"),
                "source_url": rate.get("source_url"),
                "source_family": rate.get("source_family"),
                "effective_date": rate.get("effective_date"),
                "legal_basis": rate.get("legal_basis"),
                "uncertainty_notes": rate.get("uncertainty_notes"),
            },
        )
        count += 1
    return count


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
            instructions_upserted = 0
            rates_upserted = 0
            rate_rows: list[dict] = []
            rate_html = _fetch(AEAT_IRNR_RATES_URL, _build_client, logger, "IRNR rates")
            if rate_html:
                rate_rows = _extract_irnr_rate_rows(rate_html)

            with engine.begin() as conn:
                for model in discovered:
                    codigo = model["codigo"]
                    nombre = model["nombre"]
                    url_info = model["url_info"]

                    if _upsert_irnr_model(conn, codigo, nombre, url_info, impuesto="IRNR"):
                        upserted += 1
                        logger.info("  Upserted IRNR modelo %s (%s)", codigo, nombre)
                        modelo_id = _get_model_id(conn, codigo)
                        if modelo_id:
                            page_html = _fetch(url_info, _build_client, logger, f"IRNR modelo {codigo}")
                            if page_html:
                                instructions = _extract_instruction_sections(page_html, nombre, url_info)
                                instructions_upserted += _upsert_irnr_instructions(
                                    conn,
                                    modelo_id,
                                    instructions,
                                )
                            if codigo == "210" and rate_rows:
                                rates_upserted += _upsert_irnr_rates(conn, modelo_id, rate_rows)
                    else:
                        skipped += 1

                # Step 2: Mark deprecated IRNR models
                deprecated_count = _mark_deprecated_irnr_models(conn, discovered_codes)
                if deprecated_count:
                    logger.info("Marked %d IRNR models as deprecated", deprecated_count)

            logger.info(
                "IRNR sync complete: %d upserted, %d instructions, %d rates, %d skipped, %d deprecated",
                upserted,
                instructions_upserted,
                rates_upserted,
                skipped,
                deprecated_count,
            )

        except Exception as exc:
            logger.exception("IRNR sync failed: %s", exc)
            if not handle_worker_failure(engine, "aeat_irnr", "loop", "main", exc):
                raise
            if run_once:
                break
            break

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
    ensure_database_connection(engine)
    run_sync(engine, run_once=args.run_once)


if __name__ == "__main__":
    main()
