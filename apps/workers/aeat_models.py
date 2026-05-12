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
from contextlib import contextmanager
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import urljoin, urlparse

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

logger = configure_logging("worker-aeat-modelos")

AEAT_SEDE = "https://sede.agenciatributaria.gob.es"
AEAT_MODELOS_PORTAL = (
    "https://sede.agenciatributaria.gob.es/Sede/"
    "presentacion-declaraciones-calendario-contribuyente.html"
)
AEAT_USER_AGENT = "Mozilla/5.0 (compatible; esdata-bot/1.0; fiscal data worker)"
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("AEAT_MODELS_SYNC_INTERVAL", 86400)
DEFAULT_CAMPAIGN = "current"
PLAYWRIGHT_BROWSERS_PATH = "/tmp/ms-playwright"
AEAT_SYNC_LOCK_KEY = 88420031
AEAT_RESOURCE_FETCH_RETRIES = 3

MODEL_TAX_OVERRIDES = {
    "100": "IRPF",
    "102": "IRPF",
    "111": "IRPF",
    "115": "IRPF",
    "123": "IRPF/IS/IRNR",
    "124": "IRNR",
    "130": "IRPF",
    "156": "INFORMATIVO",
    "159": "INFORMATIVO",
    "165": "INFORMATIVO",
    "170": "INFORMATIVO",
    "171": "INFORMATIVO",
    "172": "INFORMATIVO",
    "173": "INFORMATIVO",
    "179": "INFORMATIVO",
    "180": "IRPF",
    "181": "INFORMATIVO",
    "182": "INFORMATIVO",
    "184": "INFORMATIVO",
    "185": "INFORMATIVO",
    "186": "INFORMATIVO",
    "187": "IRPF",
    "188": "INFORMATIVO",
    "189": "IRPF",
    "190": "IRPF",
    "192": "INFORMATIVO",
    "193": "IRPF",
    "194": "IRPF/IS",
    "195": "INFORMATIVO",
    "196": "IRPF",
    "198": "IRPF",
    "199": "INFORMATIVO",
    "200": "IS/IRNR",
    "202": "IS/IRNR",
    "206": "IS/IRNR",
    "210": "IRNR",
    "211": "IRNR",
    "213": "IRNR",
    "216": "IRNR",
    "231": "INFORMATIVO",
    "233": "INFORMATIVO",
    "234": "INFORMATIVO",
    "238": "INFORMATIVO",
    "239": "INFORMATIVO",
    "240": "INFORMATIVO",
    "241": "INFORMATIVO",
    "247": "IRNR",
    "270": "INFORMATIVO",
    "280": "INFORMATIVO",
    "281": "INFORMATIVO",
    "283": "INFORMATIVO",
    "289": "INFORMATIVO",
    "290": "INFORMATIVO",
    "291": "IRNR",
    "294": "INFORMATIVO",
    "295": "INFORMATIVO",
    "296": "IRNR",
    "299": "INFORMATIVO",
    "303": "IVA",
    "347": "INFORMATIVO",
    "349": "IVA",
    "390": "IVA",
}

MODEL_METADATA_OVERRIDES = {
    "102": {
        "nombre": "Modelo 102. IRPF. Segundo plazo del fraccionamiento de la declaracion anual.",
        "periodo": "anual",
        "impuesto": "IRPF",
        "url_info": (
            "https://sede.agenciatributaria.gob.es/Sede/impuestos-tasas/"
            "impuesto-sobre-renta-personas-fisicas/"
            "modelo-100-mode-declaracion-documentos-devolucion_/"
            "descarga-modelo-102.html"
        ),
    },
    "206": {
        "nombre": (
            "Modelo 206. IS/IRNR. Documento de ingreso o devolucion. "
            "(Modelo 200 y 206)."
        ),
        "periodo": "anual",
        "impuesto": "IS/IRNR",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GE04.shtml",
    },
}


class FallbackRequired(RuntimeError):
    """Signal that the HTTP client cannot retrieve usable portal HTML."""


def _ensure_playwright_browser_installation() -> None:
    browser_root = Path(os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", PLAYWRIGHT_BROWSERS_PATH))
    if browser_root.exists():
        return

    browser_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["playwright", "install", "chromium"], check=True)


class AEATPortalClient(Protocol):
    def fetch_listing(self) -> str: ...

    def fetch_detail(self, url: str) -> str: ...

    def fetch_resource(self, url: str) -> bytes | None: ...


def _has_model_anchors(html: str) -> bool:
    return bool(
        re.search(
            r"href[^>]*(modelo_\d{3}_|procedimientoini/)|>\s*modelo\s+[0-9A-Z]{2,4}",
            html,
            flags=re.IGNORECASE,
        )
    )


def _normalize_html(html: str) -> bytes:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    normalized = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()
    return normalized.encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _normalize_aeat_url(url: str) -> str:
    normalized = url.strip()
    if normalized.startswith("ttps://"):
        normalized = "h" + normalized
    elif normalized.startswith("http://www1.agenciatributaria.gob.es/"):
        normalized = "https://" + normalized[len("http://") :]
    elif normalized.startswith("//"):
        normalized = "https:" + normalized
    elif not normalized.startswith(("http://", "https://")):
        normalized = "https://" + normalized.lstrip("/")
    return normalized


def _is_official_model_resource(url: str) -> bool:
    host = urlparse(_normalize_aeat_url(url)).netloc.lower()
    return host in {
        "sede.agenciatributaria.gob.es",
        "www1.agenciatributaria.gob.es",
        "www.boe.es",
    }


def _is_protected_transactional_resource(url: str) -> bool:
    normalized = _normalize_aeat_url(url)
    parsed = urlparse(normalized)
    if parsed.netloc.lower() != "www1.agenciatributaria.gob.es":
        return False

    return parsed.path.startswith("/wlpl/") and "fTramite=" in parsed.query


def _is_valid_aeat_page(html: str) -> bool:
    lowered = html.lower()
    return "erro4033.html" not in lowered and "acceso denegado" not in lowered


def _infer_campaign(page_text: str, url_info: str | None = None) -> str:
    if url_info:
        match = re.search(r"(?:19|20)\d{2}", url_info)
        if match:
            return match.group(0)

    match = re.search(r"(?:campa(?:n|ñ)a|ejercicio)\s*(?:de\s*)?((?:19|20)\d{2})", page_text, re.IGNORECASE)
    if match:
        return match.group(1)

    bare_years = re.findall(r"(?:19|20)\d{2}", page_text)
    if bare_years:
        return bare_years[0]

    return DEFAULT_CAMPAIGN


def _classify_resource(anchor_text: str, url: str) -> tuple[str, str]:
    lowered_text = anchor_text.lower()
    lowered_url = url.lower()
    resource_hint = f"{lowered_text} {lowered_url}"

    if lowered_url.endswith(".pdf"):
        formato = "pdf"
    elif lowered_url.endswith(".zip"):
        formato = "zip"
    elif lowered_url.endswith(".xml"):
        formato = "xml"
    elif lowered_url.endswith(".html") or lowered_url.endswith(".htm"):
        formato = "html"
    else:
        formato = "other"

    if "instrucc" in resource_hint:
        return ("instrucciones", formato)
    if "dise" in resource_hint or "registro" in resource_hint:
        return ("diseno_registro", formato)
    if "normativa" in resource_hint or "orden" in resource_hint or "boe" in resource_hint:
        return ("normativa", formato)
    if "ayuda" in resource_hint:
        return ("ayuda", formato)
    if "modelo" in resource_hint or "formulario" in resource_hint:
        return ("formulario_pdf" if formato == "pdf" else "formulario_html", formato)
    return ("recurso_oficial", formato)


def _extract_model_resources(detail_html: str, detail_url: str) -> list[dict]:
    soup = BeautifulSoup(detail_html, "html.parser")
    resources = [
        {
            "tipo_recurso": "pagina_modelo",
            "formato": "html",
            "url_recurso": detail_url,
            "payload": _normalize_html(detail_html),
            "metadata": {"origin": "detail_page"},
        }
    ]
    seen = {(resources[0]["tipo_recurso"], resources[0]["url_recurso"])}

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith("javascript:") or href.startswith("#"):
            continue

        url_recurso = _normalize_aeat_url(href if href.startswith("http") else urljoin(detail_url, href))
        if not _is_official_model_resource(url_recurso):
            continue
        anchor_text = a_tag.get_text(" ", strip=True)
        tipo_recurso, formato = _classify_resource(anchor_text, url_recurso)
        key = (tipo_recurso, url_recurso)
        if key in seen:
            continue
        seen.add(key)
        resources.append(
            {
                "tipo_recurso": tipo_recurso,
                "formato": formato,
                "url_recurso": url_recurso,
                "metadata": {"anchor_text": anchor_text[:200]},
            }
        )

    return resources


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
            soup = BeautifulSoup(html, "html.parser")
            next_link = soup.find("a", href=re.compile(r"todas-declaraciones-modelo\.html", re.IGNORECASE))
            if next_link and next_link.get("href"):
                html = self._fetch_text(urljoin(AEAT_SEDE, next_link["href"]), "listing-index")

        if not _has_model_anchors(html):
            soup = BeautifulSoup(html, "html.parser")
            next_link = soup.find(
                "a",
                href=re.compile(r"presentar-consultar-declaraciones-modelo\.html", re.IGNORECASE),
            )
            if next_link and next_link.get("href"):
                html = self._fetch_text(urljoin(AEAT_SEDE, next_link["href"]), "listing-catalog")

        if not _has_model_anchors(html):
            raise FallbackRequired("No anchors in listing; JS or geo-block likely required")
        return html

    def fetch_detail(self, url: str) -> str:
        return self._fetch_text(url, "detail")

    def fetch_resource(self, url: str) -> bytes | None:
        last_exc: Exception | None = None
        for attempt in range(1, AEAT_RESOURCE_FETCH_RETRIES + 1):
            try:
                with self._build_client() as client:
                    resp = client.get(url)
                    resp.raise_for_status()
                    return resp.content
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "AEAT resource fetch failed for %s on attempt %d/%d: %s",
                    url,
                    attempt,
                    AEAT_RESOURCE_FETCH_RETRIES,
                    exc,
                )
                if attempt < AEAT_RESOURCE_FETCH_RETRIES:
                    time.sleep(2 ** (attempt - 1))

        logger.error(
            "AEAT resource fetch exhausted retries for %s: %s",
            url,
            last_exc,
        )
        return None


class PlaywrightClient:
    def __init__(self):
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", PLAYWRIGHT_BROWSERS_PATH)
        _ensure_playwright_browser_installation()
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

    def fetch_resource(self, url: str) -> bytes | None:
        with self._sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=AEAT_USER_AGENT)
                try:
                    response = page.goto(url, wait_until="networkidle", timeout=30000)
                    if response is None:
                        raise FallbackRequired(f"Playwright did not receive a response for {url}")
                    return response.body()
                except Exception:
                    return HttpxClient().fetch_resource(url)
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
            url_info = href if href.startswith("http") else urljoin(AEAT_SEDE, href)

        if not codigo:
            match = re.search(r'/procedimientoini/[^"\s>]+', href, re.IGNORECASE)
            text_match = re.search(r"modelo\s+([0-9A-Z]{2,4})", text, re.IGNORECASE)
            if match and text_match:
                codigo = text_match.group(1).zfill(3)
                url_info = href if href.startswith("http") else urljoin(AEAT_SEDE, href)

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
        # Strip AEAT site-chrome that leaks into page titles when scraping
        # without JavaScript. These strings are always present regardless of
        # the actual model name and would otherwise contaminate aeat_modelo.nombre
        # (detected by audit 2026-05-09 in 217/219 rows).
        chrome_patterns = [
            r"\bSaltar al contenido principal\b.*$",
            r"\bLogotipo del Gobierno de España\b.*$",
            r"\bLogotipo Organismo\b.*$",
            r"\bMenú móvil\b.*$",
            r"\bMenu\b\s*$",
            r"^\s*Agencia Tributaria\s+Agencia Tributaria\s+",
            r"^\s*Agencia Tributaria\s+",
        ]
        for pattern in chrome_patterns:
            name = re.sub(pattern, " ", name, flags=re.IGNORECASE)
        name = re.sub(r"\s+", " ", name)
        name = re.sub(r"[;\-–—:]+", " ", name).strip()
        if len(name) > 5:
            return name[:200]
    return f"Modelo {codigo}"


def _extract_model_code_from_name(nombre: str) -> str | None:
    match = re.search(r"\bModelo\s+([0-9]{3})\b", nombre or "", re.IGNORECASE)
    return match.group(1) if match else None


def _infer_impuesto(codigo: str, page_text: str, url_info: str, nombre: str) -> str | None:
    """Infer the tax family from the model detail page without trusting nav noise."""

    if codigo in MODEL_TAX_OVERRIDES:
        return MODEL_TAX_OVERRIDES[codigo]

    compact = re.sub(r"\s+", " ", " ".join((codigo, url_info or "", nombre or "")).lower())
    is_sociedades = (
        "impuesto sobre sociedades" in compact
        or "impuesto sociedades" in compact
        or "/is/" in compact
        or "modelo 200" in compact
    )
    is_irnr = (
        "impuesto sobre la renta de no residentes" in compact
        or "renta de no residentes" in compact
        or "irnr" in compact
        or "/no-residentes/" in compact
    )
    if is_sociedades and is_irnr:
        return "IS/IRNR"
    if is_sociedades:
        return "IS"
    if is_irnr:
        return "IRNR"
    if "irpf" in compact or "impuesto sobre la renta de las personas fisicas" in compact:
        return "IRPF"
    if "declaracion informativa" in compact or "declaración informativa" in compact or "informativo" in compact:
        return "INFORMATIVO"
    if "iva" in compact or "impuesto sobre el valor anadido" in compact or "impuesto sobre el valor añadido" in compact:
        return "IVA"
    return None


def _apply_model_metadata_override(codigo: str, metadata: dict) -> dict:
    override = MODEL_METADATA_OVERRIDES.get(codigo)
    if not override:
        return metadata
    merged = {**metadata, **override}
    merged["metadata_override"] = True
    return merged


def _fetch_model_metadata(
    codigo: str,
    url_info: str | None = None,
    portal_client: AEATPortalClient | None = None,
) -> dict | None:
    client = portal_client or get_portal_client()
    if not url_info:
        try:
            html = client.fetch_listing()
        except Exception:
            return None

        soup = BeautifulSoup(html, "html.parser")

        for a_tag in soup.find_all("a", href=True):
            if re.search(rf"modelo_{codigo}_", a_tag["href"]):
                href = a_tag["href"]
                url_info = href if href.startswith("http") else urljoin(AEAT_MODELOS_PORTAL, href)
                break

    if not url_info:
        logger.warning("Modelo %s not found on portal page", codigo)
        return None

    url_info = _normalize_aeat_url(url_info)

    try:
        model_html = client.fetch_detail(url_info)
    except Exception:
        return {"codigo": codigo, "url_info": url_info}

    if not _is_valid_aeat_page(model_html):
        logger.warning("AEAT blocked detail page for modelo %s: %s", codigo, url_info)
        return None

    model_soup = BeautifulSoup(model_html, "html.parser")
    page_text = model_soup.get_text(" ", strip=True).lower()

    periodo = None
    if "mensual" in page_text:
        periodo = "mensual"
    elif "trimestral" in page_text:
        periodo = "trimestral"
    elif "anual" in page_text:
        periodo = "anual"

    nombre = _extract_model_name(model_soup.get_text(" ", strip=True)[:150], codigo)
    embedded_code = _extract_model_code_from_name(nombre)
    if embedded_code and embedded_code != codigo and codigo not in MODEL_METADATA_OVERRIDES:
        logger.warning(
            "AEAT detail page for modelo %s appears to describe modelo %s; keeping discovered metadata",
            codigo,
            embedded_code,
        )
        return None

    impuesto = _infer_impuesto(codigo, page_text, url_info, nombre)

    return _apply_model_metadata_override(codigo, {
        "codigo": codigo,
        "nombre": nombre,
        "url_info": url_info,
        "periodo": periodo,
        "impuesto": impuesto,
        "campana": _infer_campaign(model_soup.get_text(" ", strip=True), url_info),
        "detail_html": model_html,
        "recursos": _extract_model_resources(model_html, url_info),
    })


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


def _get_modelo_id(conn, codigo: str) -> int | None:
    row = conn.execute(
        text("SELECT id FROM aeat_modelo WHERE codigo = :codigo"),
        {"codigo": codigo},
    ).fetchone()
    return row[0] if row else None


def _upsert_modelo_campana(
    conn,
    modelo_id: int,
    campana: str,
    metadata: dict,
) -> tuple[int | None, bool]:
    conn.execute(
        text(
            """
            UPDATE modelo_campana
            SET activo = false
            WHERE modelo_id = :modelo_id
              AND campana != :campana
              AND activo = true
            """
        ),
        {"modelo_id": modelo_id, "campana": campana},
    )

    existing = conn.execute(
        text(
            "SELECT id FROM modelo_campana WHERE modelo_id = :modelo_id AND campana = :campana"
        ),
        {"modelo_id": modelo_id, "campana": campana},
    ).fetchone()

    conn.execute(
        text(
            """
            INSERT INTO modelo_campana (
                modelo_id,
                campana,
                version_form,
                url_instrucciones,
                url_normativa,
                url_formato,
                activo,
                fecha_publicacion_portal,
                fecha_actualizacion_portal,
                estado_publicacion,
                updated_at
            )
            VALUES (
                :modelo_id,
                :campana,
                :version_form,
                :url_instrucciones,
                :url_normativa,
                :url_formato,
                true,
                :fecha_publicacion_portal,
                :fecha_actualizacion_portal,
                :estado_publicacion,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (modelo_id, campana) DO UPDATE SET
                version_form = COALESCE(EXCLUDED.version_form, modelo_campana.version_form),
                url_instrucciones = COALESCE(EXCLUDED.url_instrucciones, modelo_campana.url_instrucciones),
                url_normativa = COALESCE(EXCLUDED.url_normativa, modelo_campana.url_normativa),
                url_formato = COALESCE(EXCLUDED.url_formato, modelo_campana.url_formato),
                activo = true,
                fecha_publicacion_portal = COALESCE(EXCLUDED.fecha_publicacion_portal, modelo_campana.fecha_publicacion_portal),
                fecha_actualizacion_portal = COALESCE(EXCLUDED.fecha_actualizacion_portal, modelo_campana.fecha_actualizacion_portal),
                estado_publicacion = COALESCE(EXCLUDED.estado_publicacion, modelo_campana.estado_publicacion),
                updated_at = CURRENT_TIMESTAMP
            """
        ),
        {
            "modelo_id": modelo_id,
            "campana": campana,
            "version_form": metadata.get("version_form"),
            "url_instrucciones": metadata.get("url_instrucciones"),
            "url_normativa": metadata.get("url_normativa"),
            "url_formato": metadata.get("url_formato"),
            "fecha_publicacion_portal": metadata.get("fecha_publicacion_portal"),
            "fecha_actualizacion_portal": metadata.get("fecha_actualizacion_portal"),
            "estado_publicacion": metadata.get("estado_publicacion"),
        },
    )

    row = conn.execute(
        text(
            "SELECT id FROM modelo_campana WHERE modelo_id = :modelo_id AND campana = :campana"
        ),
        {"modelo_id": modelo_id, "campana": campana},
    ).fetchone()
    return (row[0] if row else None, existing is None)


def _touch_modelo_recurso(conn, recurso_id: int, metadata: dict | None = None) -> None:
    conn.execute(
        text(
            """
            UPDATE modelo_recurso
            SET last_seen_at = CURRENT_TIMESTAMP,
                etag = COALESCE(:etag, etag),
                last_modified = COALESCE(:last_modified, last_modified),
                content_length = COALESCE(:content_length, content_length),
                metadata = CAST(:metadata AS JSON)
            WHERE id = :recurso_id
            """
        ),
        {
            "recurso_id": recurso_id,
            "etag": metadata.get("etag") if metadata else None,
            "last_modified": metadata.get("last_modified") if metadata else None,
            "content_length": metadata.get("content_length") if metadata else None,
            "metadata": json.dumps(metadata or {}),
        },
    )


def _reactivate_modelo_recurso(conn, recurso_id: int, metadata: dict | None = None) -> None:
    conn.execute(
        text(
            """
            UPDATE modelo_recurso
            SET activa = true,
                url_recurso = COALESCE(:url_recurso, url_recurso),
                formato = COALESCE(:formato, formato),
                last_seen_at = CURRENT_TIMESTAMP,
                etag = COALESCE(:etag, etag),
                last_modified = COALESCE(:last_modified, last_modified),
                content_length = COALESCE(:content_length, content_length),
                metadata = CAST(:metadata AS JSON)
            WHERE id = :recurso_id
            """
        ),
        {
            "recurso_id": recurso_id,
            "url_recurso": metadata.get("url_recurso") if metadata else None,
            "formato": metadata.get("formato") if metadata else None,
            "etag": metadata.get("etag") if metadata else None,
            "last_modified": metadata.get("last_modified") if metadata else None,
            "content_length": metadata.get("content_length") if metadata else None,
            "metadata": json.dumps(metadata or {}),
        },
    )


def _try_acquire_sync_lock(conn) -> bool:
    dialect = getattr(getattr(conn, "engine", None), "dialect", None)
    if getattr(dialect, "name", None) != "postgresql":
        return True

    row = conn.execute(
        text("SELECT pg_try_advisory_lock(:lock_key)"),
        {"lock_key": AEAT_SYNC_LOCK_KEY},
    ).fetchone()
    return bool(row[0]) if row else False


@contextmanager
def _hold_sync_lock(engine):
    if engine.dialect.name != "postgresql":
        with engine.connect() as conn:
            yield _try_acquire_sync_lock(conn)
        return

    lock_conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    acquired = False
    try:
        acquired = _try_acquire_sync_lock(lock_conn)
        yield acquired
    finally:
        try:
            if acquired:
                lock_conn.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": AEAT_SYNC_LOCK_KEY},
                )
        finally:
            lock_conn.close()


def _store_modelo_recurso_version(
    conn,
    campana_id: int,
    tipo_recurso: str,
    formato: str,
    url_recurso: str,
    payload: bytes,
    metadata: dict | None = None,
) -> str:
    sha256 = _sha256_bytes(payload)
    existing = conn.execute(
        text(
            """
            SELECT id, sha256_contenido
            FROM modelo_recurso
            WHERE campana_id = :campana_id
              AND tipo_recurso = :tipo_recurso
              AND activa = true
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"campana_id": campana_id, "tipo_recurso": tipo_recurso},
    ).fetchone()

    if existing and existing.sha256_contenido == sha256:
        _touch_modelo_recurso(conn, existing.id, metadata)
        return "unchanged"

    historical = conn.execute(
        text(
            """
            SELECT id
            FROM modelo_recurso
            WHERE campana_id = :campana_id
              AND tipo_recurso = :tipo_recurso
              AND sha256_contenido = :sha256
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"campana_id": campana_id, "tipo_recurso": tipo_recurso, "sha256": sha256},
    ).fetchone()

    if existing:
        conn.execute(
            text(
                """
                UPDATE modelo_recurso
                SET activa = false,
                    last_seen_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
            ),
            {"id": existing.id},
        )

    if historical:
        _reactivate_modelo_recurso(
            conn,
            historical.id,
            {
                **(metadata or {}),
                "url_recurso": url_recurso,
                "formato": formato,
            },
        )
        return "unchanged"

    conn.execute(
        text(
            """
            INSERT INTO modelo_recurso (
                campana_id,
                tipo_recurso,
                formato,
                url_recurso,
                sha256_contenido,
                row_completeness,
                row_provenance,
                etag,
                last_modified,
                content_length,
                metadata,
                activa,
                first_seen_at,
                last_seen_at
            )
            VALUES (
                :campana_id,
                :tipo_recurso,
                :formato,
                :url_recurso,
                :sha256,
                :row_completeness,
                :row_provenance,
                :etag,
                :last_modified,
                :content_length,
                CAST(:metadata AS JSON),
                true,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "campana_id": campana_id,
            "tipo_recurso": tipo_recurso,
            "formato": formato,
            "url_recurso": url_recurso,
            "sha256": sha256,
            "row_completeness": "complete",
            "row_provenance": "official_exact",
            "etag": metadata.get("etag") if metadata else None,
            "last_modified": metadata.get("last_modified") if metadata else None,
            "content_length": metadata.get("content_length") if metadata else None,
            "metadata": json.dumps(metadata or {}),
        },
    )
    return "rotated" if existing else "inserted"


def _record_sync_log(conn, started_at: datetime, finished_at: datetime, status: str, stats: dict, error_msg: str | None = None) -> None:
    inspector = inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("sync_log")}
    payload = {
        "worker": os.getenv("WORKER_NAME", "worker-aeat-modelos").strip() or "worker-aeat-modelos",
        "started_at": started_at,
        "finished_at": finished_at,
        "status": status,
        "bloques_processed": stats["recursos_descargados"],
        "articulos_upserted": stats["versiones_nuevas"],
        "documentos_processed": stats["modelos_descubiertos"],
        "documentos_upserted": stats["campanas_upserted"],
        "error_msg": error_msg,
    }
    if "rows_processed" in columns:
        payload["rows_processed"] = stats["sin_cambios"]
    if "errors" in columns:
        payload["errors"] = stats["errores"]

    insert_columns = ", ".join(payload.keys())
    insert_values = ", ".join(f":{key}" for key in payload)
    conn.execute(
        text(
            f"INSERT INTO sync_log ({insert_columns}) VALUES ({insert_values})"
        ),
        payload,
    )


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


def _get_seeded_models(conn) -> list[dict]:
    try:
        rows = conn.execute(
            text(
                """
                SELECT codigo, nombre, url_info
                FROM aeat_modelo
                WHERE activo = true
                  AND url_info IS NOT NULL
                ORDER BY codigo
                """
            )
        ).fetchall()
    except Exception as exc:
        logger.warning("Failed to load seeded AEAT models: %s", exc)
        return []
    return [
        {"codigo": row.codigo, "nombre": row.nombre or f"Modelo {row.codigo}", "url_info": row.url_info}
        for row in rows
    ]


def run_sync(engine, run_once: bool = False, force_playwright: bool = False):
    logger.info("Starting AEAT models discovery worker...")
    portal_client = get_portal_client(force_playwright=force_playwright)

    while True:
        touch_heartbeat()
        started_at = datetime.now(UTC)
        stats = {
            "modelos_descubiertos": 0,
            "campanas_upserted": 0,
            "recursos_descargados": 0,
            "versiones_nuevas": 0,
            "sin_cambios": 0,
            "errores": 0,
        }
        skipped_resource_failures = 0
        try:
            with _hold_sync_lock(engine) as lock_acquired:
                if not lock_acquired:
                    logger.warning("DEADLOCK_RISK: another AEAT sync already in progress, skipping")
                    try:
                        with engine.begin() as conn:
                            _record_sync_log(
                                conn,
                                started_at,
                                datetime.now(UTC),
                                "partial",
                                stats,
                                "AEAT sync already in progress",
                            )
                    except Exception:
                        pass
                    if run_once:
                        break
                    logger.info("Next sync in %ds", SYNC_INTERVAL_SECONDS)
                    sleep_with_heartbeat(SYNC_INTERVAL_SECONDS)
                    continue

                with engine.begin() as conn:
                    discovered = _discover_aeat_models(portal_client=portal_client)
                    if not discovered:
                        discovered = _get_seeded_models(conn)

                        if discovered:
                            logger.warning(
                                "No models discovered from AEAT portal; falling back to %d seeded models",
                                len(discovered),
                            )
                        else:
                            logger.warning("No models discovered, skipping sync")
                            stats["modelos_descubiertos"] = 0
                            _record_sync_log(conn, started_at, datetime.now(UTC), "partial", stats, "No models discovered")
                            if run_once:
                                break
                            logger.info("Next sync in %ds", SYNC_INTERVAL_SECONDS)
                            sleep_with_heartbeat(SYNC_INTERVAL_SECONDS)
                            continue

                    discovered_codes = {model["codigo"] for model in discovered}
                    stats["modelos_descubiertos"] = len(discovered_codes)
                    logger.info(
                        "Discovered %d models: %s",
                        len(discovered_codes),
                        ", ".join(sorted(discovered_codes)),
                    )

                    upserted = 0
                    skipped = 0
                    skipped_resource_failures = 0

                    _get_existing_codes(conn)

                    for model in discovered:
                        touch_heartbeat()
                        try:
                            codigo = model["codigo"]
                            nombre = model["nombre"]
                            url_info = model["url_info"]

                            metadata = _fetch_model_metadata(codigo, url_info=url_info, portal_client=portal_client)
                            if metadata:
                                nombre = metadata.get("nombre", nombre)
                                url_info = metadata.get("url_info", url_info)
                                periodo = metadata.get("periodo")
                                impuesto = metadata.get("impuesto")
                            else:
                                periodo = None
                                impuesto = None

                            if not _upsert_aeat_model(conn, codigo, nombre, url_info, periodo, impuesto):
                                skipped += 1
                                stats["errores"] += 1
                                continue

                            upserted += 1
                            modelo_id = _get_modelo_id(conn, codigo)
                            if modelo_id is None:
                                skipped += 1
                                stats["errores"] += 1
                                continue

                            campana, campana_inserted = _upsert_modelo_campana(
                                conn,
                                modelo_id,
                                (metadata or {}).get("campana", DEFAULT_CAMPAIGN),
                                metadata or {},
                            )
                            if campana is None:
                                skipped += 1
                                stats["errores"] += 1
                                continue
                            stats["campanas_upserted"] += 1 if campana_inserted else 0

                            for recurso in (metadata or {}).get("recursos", []):
                                if recurso["tipo_recurso"] == "pagina_modelo":
                                    resource_url = _normalize_aeat_url(recurso["url_recurso"])
                                    payload = recurso["payload"]
                                else:
                                    if not _is_official_model_resource(recurso["url_recurso"]):
                                        logger.info(
                                            "Skipping non-official resource %s for modelo %s",
                                            recurso["url_recurso"],
                                            codigo,
                                        )
                                        continue
                                    resource_url = _normalize_aeat_url(recurso["url_recurso"])
                                    payload = portal_client.fetch_resource(resource_url)
                                    if payload is None:
                                        if not _is_protected_transactional_resource(resource_url):
                                            skipped_resource_failures += 1
                                        logger.warning(
                                            "Skipping official resource %s for modelo %s after fetch failures",
                                            resource_url,
                                            codigo,
                                        )
                                        continue
                                    stats["recursos_descargados"] += 1

                                outcome = _store_modelo_recurso_version(
                                    conn,
                                    campana,
                                    recurso["tipo_recurso"],
                                    recurso["formato"],
                                    resource_url,
                                    payload,
                                    recurso.get("metadata"),
                                )
                                if outcome == "unchanged":
                                    stats["sin_cambios"] += 1
                                else:
                                    stats["versiones_nuevas"] += 1

                            logger.info("  Upserted modelo %s (%s)", codigo, nombre)
                        except Exception as exc:
                            stats["errores"] += 1
                            logger.error("Failed to process modelo %s: %s", model.get("codigo"), exc)
                            raise

                    deprecated_count = _mark_deprecated_models(conn, discovered_codes)
                    if deprecated_count:
                        logger.info("Marked %d models as deprecated", deprecated_count)

                    final_status, final_error_msg = finalize_partial_sync_status(
                        base_status="ok" if stats["errores"] == 0 else "partial",
                        missing_count=skipped_resource_failures,
                        source_label="AEAT official resources",
                    )

                    _record_sync_log(
                        conn,
                        started_at,
                        datetime.now(UTC),
                        final_status,
                        stats,
                        final_error_msg,
                    )

                logger.info(
                    "Sync complete: %d upserted, %d skipped, %d deprecated",
                    upserted,
                    skipped,
                    deprecated_count,
                )

        except Exception as exc:
            entity_id = "aeat_models"
            if not handle_worker_failure(engine, "aeat_models", entity_id, "sync_entity", exc):
                logger.warning("Entity aeat_models moved to dead-letter")
                return
            logger.error("Sync failed: %s", exc, exc_info=True)
            try:
                with engine.begin() as conn:
                    _record_sync_log(
                        conn,
                        started_at,
                        datetime.now(UTC),
                        "error",
                        stats,
                        str(exc)[:500],
                    )
            except Exception as log_exc:
                logger.error("Failed to write sync_log: %s", log_exc)

        if run_once:
            break

        logger.info("Next sync in %ds", SYNC_INTERVAL_SECONDS)
        sleep_with_heartbeat(SYNC_INTERVAL_SECONDS)


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
    ensure_database_connection(engine, logger=logger)
    run_sync(engine, run_once=args.run_once, force_playwright=args.force_playwright)


if __name__ == "__main__":
    main()
