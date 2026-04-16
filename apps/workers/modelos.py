#!/usr/bin/env python
"""
Worker: auto-scrape AEAT sede pages for model content.

Scrapes:
- Campaign detection (new campaign years)
- Instructions from AEAT sede HTML pages
- Casilla inventories from instruction pages
- Clave codes from instruction pages
- Normativa (BOE orders) from model pages

Runs continuously, checking each model on a schedule.
Changes are upserted to the database automatically.

Usage:
    python workers/modelos.py [--db-url URL] [--run-once] [--interval SECONDS]
"""

import os
import re
import time
from dataclasses import dataclass, field

import httpx
from sqlalchemy import create_engine, text

from runtime import configure_logging, get_bool_env, get_database_url, get_interval_seconds

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("MODELOS_SYNC_INTERVAL", 86400)
SSL_VERIFY = get_bool_env("DGT_SSL_VERIFY", False)

# AEAT sede base
AEAT_SEDE = "https://sede.agenciatributaria.gob.es"

logger = configure_logging("worker-modelos")


@dataclass
class SyncResult:
    models_checked: int = 0
    campaigns_created: int = 0
    casillas_upserted: int = 0
    instrucciones_upserted: int = 0
    claves_upserted: int = 0
    normativa_upserted: int = 0
    errors: list = field(default_factory=list)


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=AEAT_SEDE,
        follow_redirects=True,
        timeout=30,
        verify=SSL_VERIFY,
        headers={
            "User-Agent": "esdata-bot/1.0 (fiscal data infrastructure bot)",
        },
    )


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------


def scrape_casillas_from_page(html: str, modelo_codigo: str) -> list[dict]:
    """
    Extract casilla information from AEAT instruction HTML.

    AEAT instruction pages typically have tables with:
    - Casilla number (código)
    - Casilla label (etiqueta)
    - Description
    - Type (importe, texto, checkbox, numero)
    """
    casillas = []

    # Pattern 1: HTML tables with casilla data
    # Common pattern in AEAT sede: <td>0002</td><td>Rendimientos...</td>
    table_rows = re.findall(
        r"<td[^>]*>\s*(\d{1,4})\s*</td>\s*<td[^>]*>(.*?)</td>",
        html,
        re.DOTALL,
    )
    if table_rows:
        for i, (codigo, etiqueta_raw) in enumerate(table_rows):
            etiqueta = re.sub(r"<[^>]+>", "", etiqueta_raw).strip()
            if etiqueta and len(etiqueta) > 3:
                casillas.append(
                    {
                        "codigo": codigo.zfill(4) if len(codigo) < 4 else codigo,
                        "etiqueta": etiqueta,
                        "orden": i + 1,
                    }
                )
        return casillas

    # Pattern 2: Definition lists — <dt>0002</dt><dd>Label...</dd>
    def_rows = re.findall(
        r"<dt[^>]*>\s*(\d{1,4})\s*</dt>\s*<dd[^>]*>(.*?)</dd>",
        html,
        re.DOTALL,
    )
    if def_rows:
        for i, (codigo, desc_raw) in enumerate(def_rows):
            desc = re.sub(r"<[^>]+>", "", desc_raw).strip()
            if desc:
                casillas.append(
                    {
                        "codigo": codigo.zfill(4) if len(codigo) < 4 else codigo,
                        "etiqueta": desc[:100],
                        "descripcion": desc if len(desc) > 100 else None,
                        "orden": i + 1,
                    }
                )
        return casillas

    # Pattern 3: Structured lists — <li>0002 — Label</li>
    li_rows = re.findall(
        r"<li[^>]*>\s*(\d{1,4})\s*[-–—:]\s*(.*?)</li>",
        html,
        re.DOTALL,
    )
    if li_rows:
        for i, (codigo, etiqueta_raw) in enumerate(li_rows):
            etiqueta = re.sub(r"<[^>]+>", "", etiqueta_raw).strip()
            if etiqueta and len(etiqueta) > 3:
                casillas.append(
                    {
                        "codigo": codigo.zfill(4) if len(codigo) < 4 else codigo,
                        "etiqueta": etiqueta,
                        "orden": i + 1,
                    }
                )
        return casillas

    return casillas


def scrape_claves_from_page(html: str) -> list[dict]:
    """
    Extract clave codes from AEAT instruction HTML.

    Common patterns:
    - "Clave A: Dividendos"
    - "A - Dividendos"
    - <code>A</code>: description
    """
    claves = []

    # Pattern: single letter clave followed by description
    clave_rows = re.findall(
        r"(?:Clave\s*)?([A-Z])\s*[-–—:)\.]\s*([^\n<]{5,80})",
        html,
        re.MULTILINE,
    )
    for codigo, etiqueta in clave_rows:
        etiqueta = etiqueta.strip()
        if etiqueta and len(etiqueta) > 3 and not etiqueta.startswith("http"):
            claves.append(
                {
                    "codigo": codigo,
                    "etiqueta": etiqueta,
                }
            )

    # Pattern: numeric clave codes (for 303 regime codes)
    if not claves:
        num_claves = re.findall(
            r"(?:Clave\s*)?(\d{1,2})\s*[-–—:)\.]\s*([^\n<]{5,80})",
            html,
            re.MULTILINE,
        )
        for codigo, etiqueta in num_claves:
            etiqueta = etiqueta.strip()
            if etiqueta and len(etiqueta) > 3 and not etiqueta.startswith("http"):
                claves.append(
                    {
                        "codigo": codigo,
                        "etiqueta": etiqueta,
                    }
                )

    return claves


def scrape_instructions_from_page(html: str) -> list[dict]:
    """
    Extract instruction sections from AEAT HTML pages.

    Looks for sections like:
    - "Características" / "¿Qué es?"
    - "¿Quién debe presentar?"
    - "Cómo rellenar" / "Cómo cumplimentar"
    - "Plazo de presentación"
    """
    instrucciones = []

    section_patterns = [
        (r"Caracter[aí]sticas|¿Qu[eé] es\??", "caracteristicas"),
        (r"[¿Qq]ui[eé]n debe presentar|Obligados|Sujetos pasivos", "quien-debe"),
        (r"[Cc]ómo rellenar|[Cc]ómo cumplimentar|[Cc]ómo presentar", "como-rellenar"),
        (r"[Pp]lazo|[Ff]echa de presentaci[oó]n|[Cc]u[aá]ndo", "plazo"),
    ]

    for pattern, seccion in section_patterns:
        match = re.search(
            rf"(?:<h[23][^>]*>.*?{pattern}.*?</h[23]>|{pattern})",
            html,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            # Try to extract content after the heading
            start = match.end()
            # Get next 500 chars as content
            content_html = html[start : start + 2000]
            content = re.sub(r"<[^>]+>", "\n", content_html)
            content = re.sub(r"\n{3,}", "\n\n", content).strip()

            if len(content) > 50:
                instrucciones.append(
                    {
                        "seccion": seccion,
                        "titulo": match.group(0)
                        .replace("<", " ")
                        .replace(">", " ")
                        .strip()[:80],
                        "contenido": content[:5000],
                    }
                )

    return instrucciones


def upsert_instructions(conn, campana_id: int, instrucciones: list[dict]) -> int:
    """Upsert instruction sections for a campaign.

    Only replaces sections that were actually found in the scrape.
    Sections not found in the current scrape are left untouched,
    preventing data loss from partial scrapes.
    """
    count = 0
    for orden, inst in enumerate(instrucciones, start=1):
        conn.execute(
            text(
                """
                INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
                VALUES (:campana_id, :seccion, :titulo, :contenido, :orden)
                ON CONFLICT (campana_id, seccion, titulo) DO UPDATE SET
                    contenido = EXCLUDED.contenido,
                    orden = EXCLUDED.orden
                """
            ),
            {
                "campana_id": campana_id,
                "seccion": inst["seccion"],
                "titulo": inst["titulo"],
                "contenido": inst["contenido"],
                "orden": inst.get("orden", orden),
            },
        )
        count += 1
    return count


def detect_campaigns(html: str, modelo_codigo: str) -> list[str]:
    """
    Detect available campaign years from the model's AEAT page.

    Looks for links like:
    - /campana-2025/
    - /2025/
    - "Campaña 2025"
    - "Ejercicio 2025"
    """
    campaigns = set()

    # Pattern: year references (2020-2030)
    years = re.findall(r"(?:20[23]\d)", html)
    for year in years:
        if int(year) >= 2020 and int(year) <= 2030:
            campaigns.add(year)

    # Pattern: "Campaña 2025" or "Ejercicio 2025"
    camp_matches = re.findall(r"(?:[Cc]ampa[ñn]a|[Ee]jercicio)\s*(20[23]\d)", html)
    for year in camp_matches:
        campaigns.add(year)

    return sorted(campaigns, reverse=True)


def fetch_model_page(url_info: str) -> str | None:
    """Fetch the model's AEAT sede page and return HTML."""
    try:
        with _client() as c:
            resp = c.get(url_info)
            if resp.status_code == 200:
                return resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch {url_info}: {e}")
    return None


def fetch_instruction_page(url_instrucciones: str) -> str | None:
    """Fetch the model's instruction page and return HTML."""
    try:
        with _client() as c:
            resp = c.get(url_instrucciones)
            if resp.status_code == 200:
                return resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch instructions {url_instrucciones}: {e}")
    return None


# ---------------------------------------------------------------------------
# DB operations
# ---------------------------------------------------------------------------


def sync_model(
    engine,
    modelo_codigo: str,
    url_info: str,
    url_instrucciones: str | None,
    result: SyncResult,
):
    """Sync a single model's data from AEAT.

    Detects campaigns, creates any missing ones, then scrapes and persists
    content independently for EACH detected campaign using its own URL.
    """
    result.models_checked += 1

    # Get modelo_id
    with engine.connect() as conn:
        model_row = conn.execute(
            text("SELECT id FROM aeat_modelo WHERE codigo = :codigo"),
            {"codigo": modelo_codigo},
        ).fetchone()
        if not model_row:
            logger.warning(f"Modelo {modelo_codigo} not found in DB, skipping")
            result.errors.append(f"Modelo {modelo_codigo} not found")
            return
        modelo_id = model_row[0]
        conn.close()

    # Fetch main page to detect campaigns
    main_html = fetch_model_page(url_info) if url_info else None
    if not main_html:
        logger.warning(f"No HTML content for modelo {modelo_codigo}")
        result.errors.append(f"No content for {modelo_codigo}")
        return

    # --- Detect campaigns ---
    detected_campaigns = detect_campaigns(main_html, modelo_codigo)
    if not detected_campaigns:
        detected_campaigns = ["2025"]  # fallback

    # Create any missing campaigns
    with engine.connect() as conn:
        existing = conn.execute(
            text(
                """
                SELECT campana FROM modelo_campana
                WHERE modelo_id = :modelo_id
                """
            ),
            {"modelo_id": modelo_id},
        ).fetchall()
        existing_campaigns = {r[0] for r in existing}

        for camp in detected_campaigns:
            if camp not in existing_campaigns:
                url_instr = url_instrucciones if url_instrucciones else url_info
                # Deactivate all previous campaigns before inserting the new one
                conn.execute(
                    text(
                        """
                        UPDATE modelo_campana SET activo = false
                        WHERE modelo_id = :modelo_id
                        """
                    ),
                    {"modelo_id": modelo_id},
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, activo)
                        VALUES (:modelo_id, :campana, :url_instr, true)
                        ON CONFLICT (modelo_id, campana) DO UPDATE SET
                            url_instrucciones = EXCLUDED.url_instrucciones,
                            activo = true
                        """
                    ),
                    {
                        "modelo_id": modelo_id,
                        "campana": camp,
                        "url_instr": url_instr,
                    },
                )
                result.campaigns_created += 1
                logger.info(f"  New campaign created: {modelo_codigo} → {camp}")
        conn.commit()

    # Scrape and persist content for EACH campaign independently
    for camp in detected_campaigns:
        _scrape_campaign(
            engine, modelo_id, modelo_codigo, camp, url_info, url_instrucciones, result
        )


def _scrape_campaign(
    engine,
    modelo_id: int,
    modelo_codigo: str,
    campana: str,
    url_info: str,
    url_instrucciones_fallback: str | None,
    result: SyncResult,
):
    """Scrape and persist content for a single campaign."""
    with engine.connect() as conn:
        # Get this campaign's instruction URL (or fall back to the model default)
        camp_row = conn.execute(
            text(
                """
                SELECT id, url_instrucciones FROM modelo_campana
                WHERE modelo_id = :modelo_id AND campana = :campana
                """
            ),
            {"modelo_id": modelo_id, "campana": campana},
        ).fetchone()
        conn.close()

        if not camp_row:
            return

        campana_id = camp_row[0]
        camp_url_instr = camp_row[1]

        # Fetch HTML for this specific campaign
        url_to_fetch = camp_url_instr or url_instrucciones_fallback or url_info
        html = fetch_instruction_page(url_to_fetch) or fetch_model_page(url_info)
        if not html:
            logger.warning(f"  {modelo_codigo}/{campana}: no HTML to scrape")
            return

        # --- Scrape casillas ---
        scraped_casillas = scrape_casillas_from_page(html, modelo_codigo)
        if scraped_casillas:
            with engine.connect() as conn:
                for cas in scraped_casillas:
                    conn.execute(
                        text(
                            """
                            INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, orden)
                            VALUES (:campana_id, :codigo, :etiqueta, :descripcion, :orden)
                            ON CONFLICT (campana_id, codigo) DO UPDATE SET
                                etiqueta = EXCLUDED.etiqueta,
                                descripcion = COALESCE(EXCLUDED.descripcion, modelo_casilla.descripcion),
                                orden = EXCLUDED.orden
                            """
                        ),
                        {
                            "campana_id": campana_id,
                            "codigo": cas["codigo"],
                            "etiqueta": cas["etiqueta"],
                            "descripcion": cas.get("descripcion"),
                            "orden": cas.get("orden"),
                        },
                    )
                    result.casillas_upserted += 1
                conn.commit()
                logger.info(
                    f"  {modelo_codigo}/{campana}: {len(scraped_casillas)} casillas scraped"
                )

        # --- Scrape claves ---
        scraped_claves = scrape_claves_from_page(html)
        if scraped_claves:
            with engine.connect() as conn:
                for clave in scraped_claves:
                    conn.execute(
                        text(
                            """
                            INSERT INTO modelo_clave (campana_id, codigo, etiqueta)
                            VALUES (:campana_id, :codigo, :etiqueta)
                            ON CONFLICT (campana_id, codigo) DO UPDATE SET
                                etiqueta = EXCLUDED.etiqueta
                            """
                        ),
                        {
                            "campana_id": campana_id,
                            "codigo": clave["codigo"],
                            "etiqueta": clave["etiqueta"],
                        },
                    )
                    result.claves_upserted += 1
                conn.commit()
                logger.info(
                    f"  {modelo_codigo}/{campana}: {len(scraped_claves)} claves scraped"
                )

        # --- Scrape instructions ---
        scraped_instr = scrape_instructions_from_page(html)
        if scraped_instr:
            with engine.connect() as conn:
                count = upsert_instructions(conn, campana_id, scraped_instr)
                conn.commit()
                result.instrucciones_upserted += count
                logger.info(
                    f"  {modelo_codigo}/{campana}: {count} instructions upserted"
                )


def run_sync(engine, run_once: bool = False):
    """Main sync loop."""
    logger.info("Starting modelos worker...")

    while True:
        result = SyncResult()
        logger.info("=== Syncing model data from AEAT ===")

        try:
            with engine.connect() as conn:
                # Get all models with their URLs
                models = conn.execute(
                    text(
                        """
                        SELECT codigo, url_info,
                               (SELECT url_instrucciones FROM modelo_campana
                                WHERE modelo_id = aeat_modelo.id AND activo = true
                                ORDER BY campana DESC LIMIT 1) as url_instrucciones
                        FROM aeat_modelo
                        ORDER BY codigo
                        """
                    )
                ).fetchall()
                conn.close()

            logger.info(f"Found {len(models)} models to sync")

            for modelo_codigo, url_info, url_instr in models:
                url = url_instr or url_info
                if not url:
                    logger.warning(f"  SKIP {modelo_codigo}: no URL")
                    continue

                try:
                    logger.info(f"  Syncing {modelo_codigo}...")
                    sync_model(engine, modelo_codigo, url_info or "", url_instr, result)
                except Exception as e:
                    logger.error(f"  ERROR {modelo_codigo}: {e}")
                    result.errors.append(f"{modelo_codigo}: {e}")

            logger.info(
                f"Sync complete: {result.models_checked} checked, "
                f"{result.campaigns_created} new campaigns, "
                f"{result.casillas_upserted} casillas, "
                f"{result.claves_upserted} claves, "
                f"{result.instrucciones_upserted} instrucciones"
            )

            if result.errors:
                logger.warning(f"Errors: {result.errors}")

            # Log to sync_log
            try:
                with engine.connect() as conn:
                    conn.execute(
                        text(
                            """
                            INSERT INTO sync_log (
                                worker, started_at, finished_at, status,
                                bloques_processed, articulos_upserted,
                                documentos_processed, documentos_upserted,
                                doctrina_links_created, error_msg
                            ) VALUES (
                                'modelos', now(), now(),
                                CASE WHEN :errors = 0 THEN 'ok' ELSE 'error' END,
                                :models, :casillas, 0, 0, 0, :error_msg
                            )
                            """
                        ),
                        {
                            "errors": len(result.errors),
                            "models": result.models_checked,
                            "casillas": result.casillas_upserted,
                            "error_msg": "; ".join(result.errors)
                            if result.errors
                            else None,
                        },
                    )
                    conn.commit()
            except Exception as e:
                logger.warning(f"Failed to log to sync_log: {e}")

        except Exception as e:
            logger.error(f"Sync failed: {e}")

        if run_once:
            break

        logger.info(f"Next sync in {SYNC_INTERVAL_SECONDS}s")
        time.sleep(SYNC_INTERVAL_SECONDS)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scrape AEAT model content")
    parser.add_argument("--db-url", help="Database URL")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, help="Sync interval in seconds")
    args = parser.parse_args()

    global SYNC_INTERVAL_SECONDS

    db_url = args.db_url or os.getenv("DATABASE_URL", DATABASE_URL)
    interval = args.interval or SYNC_INTERVAL_SECONDS

    SYNC_INTERVAL_SECONDS = interval

    logger.info(f"DB: {db_url[:50]}...")
    logger.info(f"Interval: {SYNC_INTERVAL_SECONDS}s")
    logger.info(f"Run once: {args.run_once}")

    engine = create_engine(db_url)
    run_sync(engine, run_once=args.run_once)


if __name__ == "__main__":
    main()
