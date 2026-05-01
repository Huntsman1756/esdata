#!/usr/bin/env python
"""Worker de descubrimiento y actualizacion de modelos AEAT desde la sede AEAT.

Descubre modelos desde el portal AEAT, actualiza metadata, y marca como
inactivos los modelos que ya no aparecen en el portal.

Uso:
    python aeat_models.py --run-once
    python aeat_models.py --interval 3600
    python aeat_models.py --force-playwright
"""

from __future__ import annotations

import argparse
import os
import re
import time
from typing import Protocol
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

from runtime import (
    configure_logging,
    get_database_url,
    get_interval_seconds,
)

logger = configure_logging("worker-aeat-modelos")

AEAT_SEDE = "https://sede.agenciatributaria.gob.es"
AEAT_MODELOS_PORTAL = (
    "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/"
    "modelos-informacion-y-declaraciones/"
)
AEAT_USER_AGENT = "Mozilla/5.0 (compatible; esdata-bot/1.0; fiscal data worker)"
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("AEAT_MODELS_SYNC_INTERVAL", 86400)


class FallbackRequired(RuntimeError):
    """Signal that the HTTP client cannot retrieve usable portal HTML."""


class AEATPortalClient(Protocol):
    def fetch_listing(self) -> str: ...

    def fetch_detail(self, url: str) -> str: ...

    def fetch_resource(self, url: str) -> bytes: ...


def _has_model_anchors(html: str) -> bool:
    return bool(re.search(r"href[^>]*modelo", html, flags=re.IGNORECASE))


class HttpxClient:
    def __init__(self, ssl_verify: bool = False):
        self.ssl_verify = ssl_verify

    def _build_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=AEAT_SEDE,
            follow_redirects=True,
            timeout=30,
            verify=self.ssl_verify,
            headers={"User-Agent": AEAT_USER_AGENT},
        )

    def _fetch_text(self, url: str, context: str) -> str:
        try:
            with self._build_client() as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.text
        except Exception as exc:
            raise FallbackRequired(f"HTTP fetch failed for {context} {url}: {exc}") from exc

    def fetch_listing(self) -> str:
        html = self._fetch_text(AEAT_MODELOS_PORTAL, "listing")
        if not _has_model_anchors(html):
            raise FallbackRequired("No anchors in listing; JS or geo-block likely required")
        return html

    def fetch_detail(self, url: str) -> str:
        return self._fetch_text(url, "detail")

    def fetch_resource(self, url: str) -> bytes:
        try:
            with self._build_client() as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.content
        except Exception as exc:
            raise FallbackRequired(f"HTTP resource fetch failed for {url}: {exc}") from exc


class PlaywrightClient:
    def __init__(self):
        from playwright.sync_api import sync_playwright

        self._sync_playwright = sync_playwright

    def _render_page(self, url: str, selector: str | None = None) -> str:
        with self._sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=AEAT_USER_AGENT)
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                if selector:
                    page.wait_for_selector(selector, timeout=15000)
                return page.content()
            finally:
                browser.close()

    def fetch_listing(self) -> str:
        return self._render_page(AEAT_MODELOS_PORTAL, "a[href*='modelo']")

    def fetch_detail(self, url: str) -> str:
        return self._render_page(url)

    def fetch_resource(self, url: str) -> bytes:
        with self._sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=AEAT_USER_AGENT)
                response = page.goto(url, wait_until="networkidle", timeout=30000)
                if response is None:
                    raise FallbackRequired(f"Playwright did not receive a response for {url}")
                return response.body()
            finally:
                browser.close()


def get_portal_client(force_playwright: bool = False) -> AEATPortalClient:
    if force_playwright:
        logger.info("Using Playwright client (forced)")
        return PlaywrightClient()

    http_client = HttpxClient()
    try:
        http_client.fetch_listing()
        logger.info("Using HTTP client for AEAT portal")
        return http_client
    except FallbackRequired as exc:
        logger.info("HTTP client insufficient for AEAT portal: %s", exc)
        logger.info("Falling back to Playwright")
        return PlaywrightClient()


def _discover_aeat_models(portal_client: AEATPortalClient | None = None) -> list[dict]:
    """Descubre modelos desde el portal AEAT.

    Retorna lista de dicts con:
      codigo, nombre, url_info
    """
    client = portal_client or get_portal_client()
    try:
        html = client.fetch_listing()
    except Exception as exc:
        logger.error("No HTML from AEAT portal: %s", exc)
        return []

    soup = BeautifulSoup(html, "html.parser")
    models = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        text = (a_tag.get_text(strip=True) or "").strip()

        codigo = None
        url_info = None

        match = re.search(r"modelo_(\d{3})_", href)
        if match:
            codigo = match.group(1)
            url_info = href if href.startswith("http") else urljoin(AEAT_MODELOS_PORTAL, href)

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

    seen = set()
    unique = []
    for model in models:
        if model["codigo"] not in seen:
            seen.add(model["codigo"])
            unique.append(model)

    logger.info("Discovered %d unique models from AEAT portal", len(unique))
    return unique


def _extract_model_name(raw_text: str, codigo: str) -> str:
    if raw_text:
        name = re.sub(r"<[^>]+>", " ", raw_text)
        name = re.sub(r"&nbsp;", " ", name)
        name = re.sub(r"[;\-–—:]+", " ", name).strip()
        if len(name) > 5:
            return name[:200]
    return f"Modelo {codigo}"


def _fetch_model_metadata(codigo: str, portal_client: AEATPortalClient | None = None) -> dict | None:
    client = portal_client or get_portal_client()
    try:
        html = client.fetch_listing()
    except Exception:
        return None

    soup = BeautifulSoup(html, "html.parser")
    url_info = None

    for a_tag in soup.find_all("a", href=True):
        if re.search(rf"modelo_{codigo}_", a_tag["href"]):
            href = a_tag["href"]
            url_info = href if href.startswith("http") else urljoin(AEAT_MODELOS_PORTAL, href)
            break

    if not url_info:
        logger.warning("Modelo %s not found on portal page", codigo)
        return None

    try:
        model_html = client.fetch_detail(url_info)
    except Exception:
        return {"codigo": codigo, "url_info": url_info}

    model_soup = BeautifulSoup(model_html, "html.parser")
    page_text = model_soup.get_text(" ", strip=True).lower()

    periodo = None
    if "mensual" in page_text:
        periodo = "mensual"
    elif "trimestral" in page_text:
        periodo = "trimestral"
    elif "anual" in page_text:
        periodo = "anual"

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


def _upsert_aeat_model(conn, codigo: str, nombre: str, url_info: str, periodo: str | None = None, impuesto: str | None = None) -> bool:
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
                    updated_at = CURRENT_TIMESTAMP
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
    try:
        if not discovered_codes:
            return 0
        codes = tuple(discovered_codes)
        placeholders = ",".join([f":c{i}" for i in range(len(codes))])
        params = {f"c{i}": code for i, code in enumerate(codes)}
        result = conn.execute(
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
        return result.rowcount or 0
    except Exception as exc:
        logger.warning("Failed to mark deprecated models: %s", exc)
        return 0


def _get_existing_codes(conn) -> set[str]:
    try:
        rows = conn.execute(text("SELECT codigo FROM aeat_modelo")).fetchall()
        return {row[0] for row in rows}
    except Exception:
        return set()


def run_sync(engine, run_once: bool = False, force_playwright: bool = False):
    logger.info("Starting AEAT models discovery worker...")
    portal_client = get_portal_client(force_playwright=force_playwright)

    while True:
        try:
            discovered = _discover_aeat_models(portal_client=portal_client)
            if not discovered:
                logger.warning("No models discovered, skipping sync")
                if run_once:
                    break
                time.sleep(SYNC_INTERVAL_SECONDS)
                continue

            discovered_codes = {model["codigo"] for model in discovered}
            logger.info(
                "Discovered %d models: %s",
                len(discovered_codes),
                ", ".join(sorted(discovered_codes)),
            )

            upserted = 0
            skipped = 0

            with engine.begin() as conn:
                _get_existing_codes(conn)

                for model in discovered:
                    codigo = model["codigo"]
                    nombre = model["nombre"]
                    url_info = model["url_info"]

                    metadata = _fetch_model_metadata(codigo, portal_client=portal_client)
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

                deprecated_count = _mark_deprecated_models(conn, discovered_codes)
                if deprecated_count:
                    logger.info("Marked %d models as deprecated", deprecated_count)

            logger.info(
                "Sync complete: %d upserted, %d skipped, %d deprecated",
                upserted,
                skipped,
                deprecated_count,
            )

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
    parser.add_argument(
        "--force-playwright",
        action="store_true",
        help="Use Playwright for AEAT portal scraping even if HTTP looks sufficient",
    )
    args = parser.parse_args()

    db_url = args.db_url or os.getenv("DATABASE_URL", DATABASE_URL)
    interval = args.interval or SYNC_INTERVAL_SECONDS

    logger.info("DB: %s...", db_url[:50])
    logger.info("Interval: %ds", interval)
    logger.info("Run once: %s", args.run_once)
    logger.info("Force Playwright: %s", args.force_playwright)

    engine = create_engine(db_url)
    run_sync(engine, run_once=args.run_once, force_playwright=args.force_playwright)


if __name__ == "__main__":
    main()
