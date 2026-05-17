"""Worker CNMV — Comision Nacional del Mercado de Valores.

Fuente: comunicados, hechos relevantes, criterios y guias publicadas en
https://www.cnmv.es/. Persistencia: `documento_interpretativo` con
`tipo_fuente='cnmv'`. Conflict key: `referencia` UNIQUE.

Sync intervalo: semanal (cron-cnmv-weekly). Auditoria via `sync_log`.

Limitaciones conocidas:
- Tipologia heterogenea (HR, criterios, FAQs); `tipo_documento` se infiere
  desde la URL/listado y puede requerir reclasificacion manual.
- Algunos PDFs requieren parsing OCR no incluido por defecto.
"""

import argparse
import json
import logging
import os
import re
import time
import unicodedata
from datetime import UTC, datetime
from io import BytesIO
from urllib.parse import urlparse

import httpx
from boe import _ensure_sync_log_table, log_sync
from bs4 import BeautifulSoup
from change_detection import (
    check_content_changed,
    destination_row_exists,
    ensure_source_revision_table,
    invalidate_old_embeddings_by_entity,
    record_revision,
)
from pypdf import PdfReader
from runtime import (
    ensure_database_connection,
    finalize_partial_sync_status,
    get_database_url,
    get_interval_seconds,
    handle_worker_failure,
    sleep_with_heartbeat,
    touch_heartbeat,
)
from sqlalchemy import create_engine, text
from vocabulary_validation import sanitize_documento_payload

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_seed_urls(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SEED_URLS = _parse_seed_urls(os.getenv("CNMV_SEED_URLS"))
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

# Portal CNMV URLs for discovery
CNMV_CIRCULARES_MAIN_URL = "https://www.cnmv.es/portal/Legislacion/Circulares.aspx"
CNMV_GUIAS_TECNICAS_URL = "https://www.cnmv.es/portal/legislacion/guias-tecnicas?lang=es"
CNMV_CONSULTAS_CNMV_URL = "https://www.cnmv.es/portal/publicaciones/Documentos-Fase-Consulta?tDoc=1"
CNMV_CIRCULARES_PATTERN = re.compile(
    r"/Portal/Legislacion/Circulares-(\d{4})-(\d{4})\.aspx", re.IGNORECASE
)
CNMV_SEED_URLS_FALLBACK = [
    "https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133",
]
CNMV_FAMILY_ALIASES = {
    "circulares": "circulares",
    "guias_tecnicas": "guias_tecnicas",
    "documentos_consulta": "documentos_consulta_cnmv",
    "documentos_consulta_cnmv": "documentos_consulta_cnmv",
}


# ---------------------------------------------------------------------------
# Regulation mapping (23.7)
# ---------------------------------------------------------------------------

REGULACION_MAP = {
    # MiFID II (Directive 2014/65/EU)
    "mifid_ii": [
        "mifid ii", "mifid2", "directiva mifid", "directiva 2014/65/ue",
        "servicios de inversión", "servicios de inversion", "mercados de instrumentos financieros",
        "transparencia mercados", "best execution", "mejor ejecucion",
        "apropiadez", "suitability", "apropiada", "conocimiento y experiencia",
    ],
    # MiFIR (Regulation 600/2014/EU)
    "mifir": [
        "directiva mifir", "reglamento mifir", "reglamento 600/2014/ue",
        "datos de mercado", "informacion de mercado", "transacción ejecutada",
    ],
    # MAR (Market Abuse Regulation 596/2014/EU)
    "mar": [
        "reglamento mar", "abuso de mercado", "insider trading",
        "manipulación de mercados", "manipulacion de mercados",
        "operaciones con instrumentos propios", "programas de compra",
        "directiva 2014/57/ue", "reglamento 596/2014/ue",
    ],
    # DORA (Digital Operational Resilience Act CRR 2022/2554)
    "dora": [
        "directiva dora", "resiliencia operacional digital",
        "reglamento 2022/2554", "riesgo informatico", "riesgo informático",
        "incidentes TIC", "pruebas de resistencia",
    ],
    # PRIIPs (Regulation 1286/2014/EU)
    "priips": [
        "reglamento priips", "productos de inversión",
        "documento de datos esenciales", "drei",
        "reglamento 1286/2014/ue",
    ],
    # LIVMC (Markets in Crypto-Assets Regulation 2023/1114)
    "livmc": [
        "reglamento micar", "mercados de criptoactivos",
        "reglamento 2023/1114", "activos electrónicos",
        "criptoactivos", "asset token", "e-money token",
    ],
    # SFDR (Sustainable Finance Disclosure Regulation 2019/2088)
    "sfdr": [
        "reglamento sfdr", "reglamento 2019/2088", "sfdr",
        "sustainable finance disclosure regulation", "financiamiento sostenible",
        "financiamiento sostenible", "sostenibilidad", "impacto adverso principal",
        "paci", "paci aggregated", "paci indicator", "artículo 8", "artículo 9",
        "art 8", "art 9", "art.8", "art.9", "sfdr disclosure",
        "inversion sostenible", "criterios ambientales", "criterios sociales",
        "cambio climático", "transición climática", "transicion climatica",
        "económicas sostenibles", "economicas sostenibles", "pa", "pi",
    ],
    # CSRD (Corporate Sustainability Reporting Directive 2022/2464)
    "csrd": [
        "directiva csrd", "reglamento csrd", "reglamento 2022/2464",
        "directiva 2022/2464", "información no financiera", "informacion no financiera",
        "información de sostenibilidad", "informacion de sostenibilidad",
        "esrs", "european sustainability reporting standards",
        "doble materialidad", "doble materiality", "informe de sostenibilidad",
        "corporate sustainability reporting", "csr directive",
        "esg data", "esg data point", "esg",
    ],
    # AIFMD (Alternative Investment Fund Managers Directive 2011/61/EU)
    "aifmd": [
        "directiva aifmd", "reglamento aifmd", "2011/61/ue",
        "gestores de fondos de inversion alternativos", "gestores de fondos de inversion alternativos",
        "aifmd", "aif manager", "fondo alternativo", "aif",
        "leverage", "apalancamiento", "depositary", "depositario",
        "aifmd regulatory report", "liquidity management", "gestion de liquidez",
    ],
    # UCITS (Undertakings for Collective Investment in Transferable Securities)
    "ucits": [
        "directiva ucits", "reglamento ucits", "ucits",
        "undertakings for collective investment", "colectivo de inversion",
        "fondo ucits", "ucits fund", "ucits v", "directiva 2009/65/ce",
        "ucits regulatory report", "prospecto ucits",
    ],
    # CRD/CRR (Capital Requirements Directive/Regulation)
    "crd": [
        "directiva crd", "reglamento crd", "crd v", "directiva 2013/36/ue",
        "reglamento crr", "reglamento 575/2014/ue", "capital requirements",
        "requisitos de capital", "ratio de capital", "cet1", "tier 1",
        "tier 2", "ratio de apalancamiento", "leverage ratio",
        "requisitos prudenciales", "crd/crr", "capital position",
        "stress test", "prueba de resistencia", "pilar 1", "pilar 2",
        "icaap", "srep", "requisitos de capital",
    ],
    # BRRD (Bank Recovery and Resolution Directive 2014/59/EU)
    "brrd": [
        "directiva brrd", "recuperacion y resolucion", "2014/59/ue",
        "brrd", "bail-in", "resolucion bancaria", "directiva de recuperacion",
        "directiva de recuperacion y resolucion", "mrel",
        "total loss absorbing capacity", "requisitos de pasivos",
        "requisitos de capacidad de absorcion de perdidas",
        "requisitos de capacidad de absorción de pérdidas",
    ],
    # EMIR (European Market Infrastructure Regulation 648/2012)
    "emir": [
        "reglamento emir", "reglamento 648/2012", "emir",
        "european market infrastructure regulation", "derivados",
        "o tc", "otc derivatives", "contratos derivados",
        "clearing", "compensacion", "compensación",
        "reporting de derivados", "trade report", "clearing member",
        "counterparty", "central counterparty", "ccp",
        "trade repository", "repositor de operaciones",
    ],
}


def _detect_regulacion_relacionada(text_value: str) -> str | None:
    """Detect related EU/ES regulation from document text (23.7)."""
    lowered = text_value.lower()
    for regulacion, keywords in REGULACION_MAP.items():
        if any(kw in lowered for kw in keywords):
            return regulacion
    return None


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _ascii_fold(value: str) -> str:
    return (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def _slug(value: str, max_length: int = 80) -> str:
    folded = _ascii_fold(value).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
    return slug[:max_length].strip("-") or "documento"


def _absolute_cnmv_url(base_url: str, href: str) -> str:
    if href.startswith("//"):
        return "https:" + href
    return str(httpx.URL(base_url).join(href))


def _metadata_json(metadata: dict) -> str:
    return json.dumps(metadata, ensure_ascii=True, sort_keys=True)


def _parse_cnmv_year_heading(value: str) -> str | None:
    match = re.search(r"\b(20\d{2}|19\d{2})\b", value)
    return match.group(1) if match else None


def _parse_cnmv_date(value: str) -> str | None:
    match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", value)
    if not match:
        return None
    day, month, year = match.groups()
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def _normalize_title(value: str) -> str:
    return _normalize_whitespace(_ascii_fold(value))


# ---------------------------------------------------------------------------
# Discovery (23.1) — scrape CNMV portal for new document URLs
# ---------------------------------------------------------------------------


def _discover_cnmv_circulares(
    max_year_ranges: int = 10,
    max_circulars_per_range: int = 0,
) -> list[str]:
    """Discover CNMV circular URLs from the CNMV circulars index pages.

    Iterates year-range index pages (e.g. Circulares-2021-2025.aspx) and
    extracts BOE PDF links for each circular.

    Args:
        max_year_ranges: Max number of year-range pages to scrape (0 = unlimited).
        max_circulars_per_range: Max circulars to extract per page (0 = unlimited).

    Returns:
        List of unique BOE document URLs.
    """
    urls: list[str] = []
    seen: set[str] = set()

    def _add(url: str) -> None:
        if url not in seen:
            seen.add(url)
            urls.append(url)

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        # Step 1: scrape the main circulars index to get year-range pages
        try:
            resp = client.get(CNMV_CIRCULARES_MAIN_URL)
            if resp.status_code != 200:
                return SEED_URLS or CNMV_SEED_URLS_FALLBACK

            soup = BeautifulSoup(resp.text, "html.parser")
            year_range_urls: list[str] = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                match = CNMV_CIRCULARES_PATTERN.search(href)
                if match:
                    full_url = httpx.URL(CNMV_CIRCULARES_MAIN_URL).join(href)
                    year_range_urls.append(str(full_url))

            if not year_range_urls:
                return SEED_URLS or CNMV_SEED_URLS_FALLBACK

        except Exception:
            return SEED_URLS or CNMV_SEED_URLS_FALLBACK

        # Step 2: iterate year-range pages and extract circular links
        for idx, range_url in enumerate(year_range_urls):
            if max_year_ranges and idx >= max_year_ranges:
                break

            try:
                resp = client.get(range_url)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    # Accept BOE PDFs and BOE TXT links
                    if "boe.es" in href and (".pdf" in href or "txt.php" in href):
                        # Resolve relative URLs, handling boe.es bare paths
                        if href.startswith("http"):
                            full_url = href
                        elif href.startswith("//"):
                            full_url = "https:" + href
                        elif href.startswith("/"):
                            # Absolute path — resolve against CNMV base
                            base_url = httpx.URL(range_url)
                            full_url = str(base_url.copy_with(path=href))
                        else:
                            full_url = str(httpx.URL(range_url).join(href))
                        _add(full_url)

                    if max_circulars_per_range and len(urls) >= max_circulars_per_range:
                        break

            except Exception:
                logger.warning("Failed to scrape year range page: %s", range_url)
                continue

    return urls or (SEED_URLS or CNMV_SEED_URLS_FALLBACK)


def _parse_cnmv_technical_guides(html: str, source_index_url: str) -> list[dict]:
    """Parse the official CNMV technical guides index into document candidates."""
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[dict] = []
    seen: set[str] = set()
    current_year: str | None = None

    for node in soup.find_all(["h2", "li"]):
        if node.name == "h2":
            current_year = _parse_cnmv_year_heading(node.get_text(" ", strip=True))
            continue

        raw_text = _normalize_whitespace(node.get_text(" ", strip=True))
        folded_text = _ascii_fold(raw_text)
        if not re.search(r"\bGuia Tecnica\s+\d+/\d{4}\b", folded_text, re.IGNORECASE):
            continue

        link = node.find("a", href=True)
        if not link:
            continue
        url = _absolute_cnmv_url(source_index_url, link["href"])
        if url in seen:
            continue
        seen.add(url)

        match = re.search(r"\bGuia Tecnica\s+(\d+/\d{4})\b", folded_text, re.IGNORECASE)
        if not match:
            continue
        guide_number = match.group(1)
        title = _normalize_title(raw_text)
        year = guide_number.split("/", 1)[1] if "/" in guide_number else current_year

        candidates.append(
            {
                "url": url,
                "referencia": f"CNMV-GUIA-TECNICA-{guide_number.replace('/', '-')}",
                "titulo": title,
                "fecha": f"{year}-01-01" if year else datetime.now(UTC).date().isoformat(),
                "fecha_publicacion": year,
                "tipo_documento": "guia_tecnica_cnmv",
                "estado_vigencia": _detect_vigencia(raw_text),
                "family_id": "guias_tecnicas",
                "source_index_url": source_index_url,
            }
        )

    return candidates


def _parse_cnmv_consultation_documents(html: str, source_index_url: str) -> list[dict]:
    """Parse official CNMV consultation-process rows as non-current documents."""
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[dict] = []
    seen_refs: set[str] = set()
    current_status = "consulta_abierta"

    for node in soup.find_all(["h2", "li"]):
        if node.name == "h2":
            heading = _ascii_fold(node.get_text(" ", strip=True)).lower()
            if "closed" in heading or "cerrado" in heading:
                current_status = "consulta_cerrada"
            elif "open" in heading or "abierto" in heading:
                current_status = "consulta_abierta"
            continue

        raw_text = _normalize_whitespace(node.get_text(" ", strip=True))
        date_value = _parse_cnmv_date(raw_text)
        links = [
            {
                "titulo": _normalize_title(a_tag.get_text(" ", strip=True)),
                "url": _absolute_cnmv_url(source_index_url, a_tag["href"]),
            }
            for a_tag in node.find_all("a", href=True)
        ]
        if not date_value or not links:
            continue

        title_text = raw_text
        for link in links:
            title_text = title_text.replace(link["titulo"], " ")
        title_text = re.sub(r"\b\d{1,2}/\d{1,2}/\d{4}\b", " ", title_text)
        title = _normalize_title(title_text)
        if not title:
            continue

        primary = next(
            (
                link
                for link in links
                if any(
                    token in link["titulo"].lower()
                    for token in ("consultation", "consulta", "prior")
                )
            ),
            links[0],
        )
        referencia = f"CNMV-CONSULTA-{date_value}-{_slug(title, 48)}"
        if referencia in seen_refs:
            continue
        seen_refs.add(referencia)

        candidates.append(
            {
                "url": primary["url"],
                "referencia": referencia,
                "titulo": title,
                "fecha": date_value,
                "fecha_publicacion": date_value,
                "tipo_documento": "documento_consulta_cnmv",
                "estado_vigencia": "consulta_cerrada"
                if current_status == "consulta_cerrada"
                else "historico",
                "estado_consulta": current_status,
                "family_id": "documentos_consulta_cnmv",
                "source_index_url": source_index_url,
                "documentos_asociados": links,
            }
        )

    return candidates


def _discover_source_family_documents() -> list[dict]:
    candidates: list[dict] = []
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for source_url, parser in (
            (CNMV_GUIAS_TECNICAS_URL, _parse_cnmv_technical_guides),
            (CNMV_CONSULTAS_CNMV_URL, _parse_cnmv_consultation_documents),
        ):
            try:
                response = client.get(source_url)
                if response.status_code == 200:
                    candidates.extend(parser(response.text, source_url))
            except Exception:
                logger.warning("Failed to scrape CNMV source family: %s", source_url)
                continue
    return candidates


def _discover_new_urls(seed_urls: list[str] | None = None) -> list[str]:
    """Discover CNMV document URLs from the CNMV portal.

    Returns a list of URLs to fetch. Falls back to seed URLs if scraping fails.
    """
    if seed_urls is not None:
        return seed_urls
    return _discover_cnmv_circulares()


def _normalize_family_filter(familia: str | None) -> str | None:
    if not familia:
        return None
    normalized = familia.strip().lower()
    if normalized in {"all", "todas", "todos"}:
        return None
    return CNMV_FAMILY_ALIASES.get(normalized, normalized)


def _candidate_family(candidate: dict | str) -> str:
    if isinstance(candidate, dict):
        return str(candidate.get("family_id") or "")
    return "circulares"


def _discover_new_documents(
    seed_urls: list[str] | None = None,
    familia: str | None = None,
    max_urls: int | None = None,
) -> list[dict | str]:
    family_filter = _normalize_family_filter(familia)
    candidates: list[dict | str] = []

    if family_filter in {None, "circulares"}:
        candidates.extend(_discover_new_urls(seed_urls))

    if seed_urls is None and family_filter != "circulares":
        candidates.extend(_discover_source_family_documents())

    if family_filter:
        candidates = [
            candidate
            for candidate in candidates
            if _candidate_family(candidate) == family_filter
        ]

    if max_urls is not None and max_urls > 0:
        candidates = candidates[:max_urls]
    return candidates


# ---------------------------------------------------------------------------
# Reference extraction
# ---------------------------------------------------------------------------


def _extract_reference(url: str, text_value: str) -> str:
    # Try BOE-A reference in URL
    match = re.search(r"(BOE-A-\d{4}-\d+)", url)
    if match:
        return match.group(1)

    # Try BOE-A reference in text
    match = re.search(r"(BOE-A-\d{4}-\d+)", text_value)
    if match:
        return match.group(1)

    # Try Circular N/NNNN pattern
    title_match = re.search(r"\bCircular\s+(\d+/\d{4})\b", text_value, flags=re.IGNORECASE)
    if title_match:
        return f"CNMV-CIRCULAR-{title_match.group(1).replace('/', '-')}"

    text_match = re.search(r"\bCircular\s+(\d+/\d{4})\b", text_value, flags=re.IGNORECASE)
    if text_match:
        return f"CNMV-CIRCULAR-{text_match.group(1).replace('/', '-')}"

    # Try Resolucion N/NNNN
    res_match = re.search(r"\bResolución?\s+(\d+/\d{4})\b", text_value, flags=re.IGNORECASE)
    if res_match:
        return f"CNMV-RESOLUCION-{res_match.group(1).replace('/', '-')}"

    # Try Manual N/NNNN
    manual_match = re.search(r"\bManual\s+(\d+/\d{4})\b", text_value, flags=re.IGNORECASE)
    if manual_match:
        return f"CNMV-MANUAL-{manual_match.group(1).replace('/', '-')}"

    # Try Guia N/NNNN
    guia_match = re.search(r"\bGu[ií]a\s+(\d+/\d{4})\b", text_value, flags=re.IGNORECASE)
    if guia_match:
        return f"CNMV-GUIA-{guia_match.group(1).replace('/', '-')}"

    # Fallback: URL path slug
    path = urlparse(url).path.rstrip("/").split("/")[-1]
    return f"CNMV-{path.removesuffix('.pdf') or 'seed'}"


# ---------------------------------------------------------------------------
# Metadata extraction from PDF text
# ---------------------------------------------------------------------------


def _extract_circular_number(text_value: str) -> str | None:
    """Extract circular number like '9/2008', '3/2015', etc."""
    match = re.search(r"\bCircular\s+(\d+/\d{4})\b", text_value, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _extract_publication_date(text_value: str) -> str | None:
    """Extract publication date from BOE reference or date patterns."""
    # Try BOE-A date: BOE-A-2009-133 -> 2009
    match = re.search(r"BOE-A-(\d{4})-", text_value)
    if match:
        return match.group(1)

    # Try date patterns: DD/MM/YYYY or DD de Month de YYYY
    match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text_value)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    match = re.search(
        r"\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})\b",
        text_value,
        flags=re.IGNORECASE,
    )
    if match:
        day, month_str, year = match.groups()
        months = {
            "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
            "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
            "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12",
        }
        month = months.get(month_str.lower(), "01")
        return f"{year}-{month}-{day.zfill(2)}"

    return None


def _extract_boe_reference(text_value: str, url: str = "") -> str | None:
    """Extract BOE reference like BOE-A-2009-133."""
    match = re.search(r"(BOE-A-\d{4}-\d+)", text_value)
    if match:
        return match.group(1)
    if url:
        match = re.search(r"(BOE-A-\d{4}-\d+)", url)
        if match:
            return match.group(1)
    return None


def _detect_vigencia(text_value: str) -> str:
    """Detect document vigency status."""
    lowered = text_value.lower()
    if any(p in lowered for p in ["derogado", "derogada", "derogada"]):
        return "derogado"
    if any(p in lowered for p in ["modificado", "modificada", "modificadas"]):
        return "vigente_modificado"
    if any(p in lowered for p in ["vigente", "vigente", "en vigor"]):
        return "vigente"
    return "vigente"  # default


# ---------------------------------------------------------------------------
# Document type detection (23.3)
# ---------------------------------------------------------------------------


def _detect_document_type(text_value: str) -> str:
    lowered = _normalize_whitespace(text_value).lower()
    # More specific patterns first
    if re.search(r"\bCircular\s+\d+/\d{4}\b", text_value, flags=re.IGNORECASE):
        return "circular_cnmv"
    if re.search(r"\bManual\s+\d+/\d{4}\b", text_value, flags=re.IGNORECASE):
        return "manual_cnmv"
    if re.search(r"\bGu[ií]a\s+\d+/\d{4}\b", text_value, flags=re.IGNORECASE):
        return "guia_cnmv"
    if re.search(r"\bResolución?\s+\d+/\d{4}\b", text_value, flags=re.IGNORECASE):
        return "resolucion_cnmv"
    if re.search(r"\bCódigo\b.*\bde\s+(Buen\s+)?Gobierno|codigo_autoregulacion|código.*conducta|conducta\s+profesional", lowered):
        return "codigo_conducta_cnmv"
    if re.search(r"\bCódigo\s+de\s+(Buen\s+)?Gobierno\b", text_value, flags=re.IGNORECASE):
        return "codigo_autoregulacion_cnmv"
    if re.search(r"\bInforme\s+(Anual|de\s+Supervisión|de\s+Actividad)\b", text_value, flags=re.IGNORECASE):
        return "informe_anual_cnmv"
    if re.search(r"\bInforme\b", text_value, flags=re.IGNORECASE):
        return "informe_cnmv"
    if re.search(r"\bInstrucción\s+Técnica\b|instruccion_tecnica|instruccion\s+ tecnica", text_value, flags=re.IGNORECASE):
        return "instruccion_tecnica_cnmv"
    if re.search(r"\bDictamen\b", text_value, flags=re.IGNORECASE):
        return "dictamen_cnmv"
    if re.search(r"\bModelo\s+de\s+Comunicación\b|modelo_comunicacion", text_value, flags=re.IGNORECASE):
        return "modelo_comunicacion_cnmv"
    if re.search(r"\bDecisión\s+de\s+Supervisión\b|decision_supervision", text_value, flags=re.IGNORECASE):
        return "decision_supervision_cnmv"
    if re.search(r"\bEstadística\b|estadistica_mercado|estadisticas?\s+(de\s+)?(mercados?|bolsa)", text_value, flags=re.IGNORECASE):
        return "estadistica_mercado_cnmv"
    if re.search(r"\bCirculo?\s+de\s+Acons[eé]jamiento\b|circ_asesoramiento|circulares\s+de\s+asesoramiento|asesoramiento\s+inversor", text_value, flags=re.IGNORECASE):
        return "circ_asesoramiento_cnmv"
    if re.search(r"\bReglamento\b.*\bCNMV|reglamento_cnmv|reglamento\s+(de|sobre|sobre\s+la|para\s+)", text_value, flags=re.IGNORECASE):
        return "reglamento_cnmv"
    if re.search(r"\bGu[ií]a\b|guia_cnmv", text_value, flags=re.IGNORECASE):
        return "guia_cnmv"
    if re.search(r"\bManual\b", text_value, flags=re.IGNORECASE):
        return "manual_cnmv"
    if re.search(r"\bCircular\b", text_value, flags=re.IGNORECASE):
        return "circular_cnmv"
    return "documento_cnmv"


# ---------------------------------------------------------------------------
# Ambito detection (23.4) — expanded
# ---------------------------------------------------------------------------


def _detect_ambito(text_value: str) -> str:
    lowered = text_value.lower()

    # Priority 1: Specific regulatory frameworks
    if any(p in lowered for p in ["mifid ii", "mifid2", "directiva mifid"]):
        return "mifid_ii"
    if any(p in lowered for p in ["directiva mifir", "reglamento mifir"]):
        return "mifir"
    if any(p in lowered for p in ["reglamento mar", "market abuse", "abuso de mercado"]):
        return "mar"
    if any(p in lowered for p in ["directiva dora", "resiliencia operacional digital", "dora"]):
        return "dora"
    if any(p in lowered for p in ["reglamento priips", "productos de inversión"]):
        return "priips"

    # Priority 2: CNMV-specific reporting
    if any(p in lowered for p in ["información reservada", "informacion reservada", "información confidencial", "informacion confidencial"]):
        return "reporting_regulatorio_cnmv"
    if any(p in lowered for p in ["estados de información", "estados de informacion", "cuentas anuales", "información reservada", "informacion reservada"]):
        return "reporting_financiero_cnmv"

    # Priority 3: Corporate governance / transparency
    if any(p in lowered for p in ["gobierno corporativo", "gobernanza corporativa", "codigo de buen gobierno"]):
        return "gobierno_corporativo"
    if any(p in lowered for p in ["transparencia de emisores", "hechos relevantes", "operaciones con instrumentos propios", "rdo de hechos relevantes"]):
        return "transparencia_emisores"

    # Priority 4: Market infrastructure
    if "infraestructuras de mercado" in lowered:
        return "infraestructuras_cnmv"

    # Priority 5: Investor protection
    if any(p in lowered for p in ["protección del inversor", "proteccion del inversor", "suitability", "apropiada", "apropiadez"]):
        return "proteccion_inversor_cnmv"

    # Priority 6: Sanctions / enforcement
    if any(p in lowered for p in ["régimen sancionador", "regimen sancionador", "sanciones cnmv", "infracciones", "sancion"]):
        return "sanciones_cnmv"

    # Priority 7: PGC / NIIF accounting
    if any(p in lowered for p in ["pgc", "plan general de contabilidad", "niif", "nias", "normas internacionales"]):
        return "pgc_cnmv"

    # Priority 8: Legacy fallbacks
    if any(p in lowered for p in ["información reservada", "informacion reservada"]):
        return "reporting_regulatorio"
    if any(p in lowered for p in ["estados", "cuentas anuales"]):
        return "reporting_financiero"
    if "infraestructuras de mercado" in lowered:
        return "infraestructuras_mercado"
    if "mifid" in lowered or "servicios de inversión" in lowered or "servicios de inversion" in lowered:
        return "mercados"

    return "mercados_cnmv"


# ---------------------------------------------------------------------------
# EU/ES regulation mapping (23.7)
# ---------------------------------------------------------------------------

REGULACION_MAP = {
    "mifid_ii": {
        "keywords": ["mifid ii", "mifid2", "directiva 2014/65/ue", "directive 2014/65", "mifir", "reglamento mifir", "2017/590"],
        "regulacion_id": "mifid_ii",
        "relacion_tipo": "implementa",
        "nota": "Implementa MiFID II/MiFIR (2014/65/UE) y su reglamento de ejecución",
    },
    "mar": {
        "keywords": ["reglamento mar", "market abuse regulation", "abuso de mercado", "reglamento (ue) 596/2014", "596/2014"],
        "regulacion_id": "mar",
        "relacion_tipo": "implementa",
        "nota": "Implementa MAR — Market Abuse Regulation (UE) 596/2014",
    },
    "dora": {
        "keywords": ["directiva dora", "resiliencia operacional digital", "digital operational resilience", "reglamento dora", "2022/2554", "dora"],
        "regulacion_id": "dora",
        "relacion_tipo": "implementa",
        "nota": "Implementa DORA — Digital Operational Resilience Act (UE) 2022/2554",
    },
    "priips": {
        "keywords": ["reglamento priips", "priips", "productos de inversión al por menor", "packaged retail", "878/2012"],
        "regulacion_id": "priips",
        "relacion_tipo": "implementa",
        "nota": "Implementa PRIIPs Regulation (UE) 1286/2014 (antes 878/2012)",
    },
    "livmc": {
        "keywords": ["directiva lvmc", "lvmc", "investigación con voz", "retail investor voice", "directiva (ue) 2024/...", "lvmc"],
        "regulacion_id": "livmc",
        "relacion_tipo": "implementa",
        "nota": "Implementa LIVMC — Retail Investment and Voice Directive",
    },
    "pgc": {
        "keywords": ["pgc", "plan general de contabilidad", "orden ecg/1840/2007", "orden ees/1814/2014", "normas contables españolas"],
        "regulacion_id": "pgc_es",
        "relacion_tipo": "deriva_de",
        "nota": "Deriva del PGC español (Orden ECG/1840/2007 y modificaciones)",
    },
    "niif": {
        "keywords": ["niif", "nias", "normas internacionales", "ifrs", "ias", "reglamento (ce) 1606/2002"],
        "regulacion_id": "niif_eu",
        "relacion_tipo": "implementa",
        "nota": "Implementa NIIF/IAS adoptadas por la UE (Reglamento 1606/2002)",
    },
    "transparencia": {
        "keywords": ["transparencia de emisores", "hechos relevantes", "operaciones con instrumentos propios", "rdo de hechos relevantes", "directiva transparencia", "2004/109/ce"],
        "regulacion_id": "transparencia_ue",
        "relacion_tipo": "implementa",
        "nota": "Deriva de Directiva de Transparencia (2004/109/CE)",
    },
    "gobernanza": {
        "keywords": ["gobierno corporativo", "gobernanza corporativa", "codigo de buen gobierno", "comisión de riesgos", "comité de auditoría"],
        "regulacion_id": "cgce",
        "relacion_tipo": "complementa",
        "nota": "Complementa el Código de Buen Gobierno de la CNMV (CGCE)",
    },
}


def _detect_regulaciones(text_value: str) -> list[dict]:
    """Detect EU/ES regulation links for a CNMV document.

    Returns list of dicts with keys: regulacion_id, relacion_tipo, nota.
    """
    lowered = text_value.lower()
    found = []
    seen_reg_ids = set()

    for info in REGULACION_MAP.values():
        if any(kw in lowered for kw in info["keywords"]):
            reg_id = info["regulacion_id"]
            if reg_id not in seen_reg_ids:
                seen_reg_ids.add(reg_id)
                found.append({
                    "regulacion_id": reg_id,
                    "relacion_tipo": info["relacion_tipo"],
                    "nota": info["nota"],
                })

    return found


def _upsert_regulation_links(
    conn,
    referencia: str,
    regulaciones: list[dict],
) -> int:
    """Upsert regulation links for a CNMV document.

    Deletes existing links and inserts new ones.
    Returns number of links inserted.
    """
    try:
        conn.execute(
            text(
                """
                DELETE FROM cnmv_regulation_link
                WHERE documento_referencia = :referencia
                """
            ),
            {"referencia": referencia},
        )

        dialect = conn.engine.dialect.name
        insert_sql = (
            """
            INSERT INTO cnmv_regulation_link
                (documento_referencia, regulacion_id, relacion_tipo, nota)
            VALUES (:referencia, :reg_id, :tipo, :nota)
            ON CONFLICT (documento_referencia, regulacion_id) DO UPDATE SET
                relacion_tipo = EXCLUDED.relacion_tipo,
                nota = EXCLUDED.nota
            """
            if dialect == "postgresql"
            else
            """
            INSERT OR REPLACE INTO cnmv_regulation_link
                (documento_referencia, regulacion_id, relacion_tipo, nota)
            VALUES (:referencia, :reg_id, :tipo, :nota)
            """
        )

        inserted = 0
        for reg in regulaciones:
            conn.execute(
                text(insert_sql),
                {
                    "referencia": referencia,
                    "reg_id": reg["regulacion_id"],
                    "tipo": reg["relacion_tipo"],
                    "nota": reg.get("nota"),
                },
            )
            inserted += 1
        return inserted
    except Exception:
        # Table may not exist yet (migration not applied)
        return 0


# ---------------------------------------------------------------------------
# Obligation derivation (23.8)
# ---------------------------------------------------------------------------

OBLIGATION_PATTERNS: list[dict] = [
    {
        "tipo_obligacion": "comunicacion_indicio",
        "keywords": [
            "comunicar indicios",
            "comunicar indicios de lavado",
            "comunicar indicios de lp",
            "comunicar indicios de delincuencia",
            "comunicación de operaciones sospechosas",
            "comunicacion de operaciones sospechosas",
            "comunicar operaciones inusuales",
            "comunicacion de operaciones inusuales",
            "suspender la operación",
            "suspender la operacion",
            "impedir la operación",
            "impedir la operacion",
            "informe de indicios",
            "indicios de delito",
            "operaciones sospechosas",
            "indicios de lp",
            "operación sospechosa",
            "operacion sospechosa",
            "prevención de blanqueo",
            "prevencion de blanqueo",
            "prevencion de lavado",
        ],
        "nota": "Obligación de comunicar indicios de lavado de dinero o delito",
    },
    {
        "tipo_obligacion": "presentacion_modelo",
        "keywords": [
            "deberá presentar el modelo",
            "debera presentar el modelo",
            "presentación del modelo",
            "presente el modelo",
            "modelo 620",
            "modelo 610",
            "modelo 200",
            "modelo 303",
            "modelo 347",
            "modelo 349",
            "modelo 390",
            "presentación de modelos",
            "presente modelos",
            "enviar modelo",
            "remitir modelo",
        ],
        "nota": "Obligación de presentación de modelo regulatorio",
    },
    {
        "tipo_obligacion": "remision_informacion",
        "keywords": [
            "obligación de comunicar",
            "obligacion de comunicar",
            "deberá comunicar",
            "debera comunicar",
            "remitir información",
            "remitir informacion",
            "enviar información",
            "enviar informacion",
            "remisión de información",
            "remision de informacion",
            "información periódica",
            "informacion periodica",
            "notificar a la cnmv",
            "comunicación de datos",
            "comunicacion de datos",
        ],
        "nota": "Obligación de remisión o comunicación de información",
    },
    {
        "tipo_obligacion": "control_interno",
        "keywords": [
            "deberá mantener controles",
            "debera mantener controles",
            "sistemas de control interno",
            "controles internos de la sociedad de valores",
            "políticas de control interno",
            "politicas de control interno",
            "registro de operaciones",
            "registro de ordenes",
            "archivado de comunicaciones",
            "conservación de registros",
            "conservacion de registros",
            "deberá documentar",
            "debera documentar",
            "deberá llevar un registro",
            "debera llevar un registro",
            "implementar procedimientos de control",
            "procedimientos de control interno",
        ],
        "nota": "Obligación de implementar controles internos y registros",
    },
    {
        "tipo_obligacion": "reporting_prudencial",
        "keywords": [
            "reporte prudencial",
            "reporting prudencial",
            "reporte prudencial de liquidez",
            "reporting prudencial de liquidez",
            "requisitos de capital",
            "requisitos de fondos propios",
            "ratio de capital",
            "ratio de fondos propios",
            "reporte de posiciones",
            "reporting de posiciones",
            "reporte de posiciones significativas",
            "reporting de posiciones significativas",
            "informe prudencial",
            "reporte de riesgos",
            "reporting de riesgos",
            "reporte de liquidez",
            "reporting de liquidez",
            "reporte de posiciones de cliente",
            "reporting de posiciones de cliente",
        ],
        "nota": "Obligación de reporting prudencial (capital, liquidez, riesgos)",
    },
]


def _detect_obligaciones(text_value: str) -> list[dict]:
    """Detect obligations by keyword patterns in CNMV document text.

    Returns list of dicts with keys: tipo_obligacion, nota.
    """
    lowered = text_value.lower()
    found = []
    seen_tipos = set()

    for pattern in OBLIGATION_PATTERNS:
        if any(kw in lowered for kw in pattern["keywords"]):
            tipo = pattern["tipo_obligacion"]
            if tipo not in seen_tipos:
                seen_tipos.add(tipo)
                found.append({
                    "tipo_obligacion": tipo,
                    "nota": pattern["nota"],
                })

    return found


def _upsert_obligation_links(
    conn,
    referencia: str,
    obligaciones: list[dict],
) -> int:
    """Upsert obligation links for a CNMV document.

    Deletes existing links and inserts new ones.
    Returns number of links inserted.
    """
    try:
        conn.execute(
            text(
                """
                DELETE FROM cnmv_obligation_link
                WHERE documento_referencia = :referencia
                """
            ),
            {"referencia": referencia},
        )

        dialect = conn.engine.dialect.name
        insert_sql = (
            """
            INSERT INTO cnmv_obligation_link
                (documento_referencia, tipo_obligacion, nota)
            VALUES (:referencia, :tipo, :nota)
            ON CONFLICT (documento_referencia, tipo_obligacion) DO UPDATE SET
                nota = EXCLUDED.nota
            """
            if dialect == "postgresql"
            else
            """
            INSERT OR REPLACE INTO cnmv_obligation_link
                (documento_referencia, tipo_obligacion, nota)
            VALUES (:referencia, :tipo, :nota)
            """
        )

        inserted = 0
        for obs in obligaciones:
            conn.execute(
                text(insert_sql),
                {
                    "referencia": referencia,
                    "tipo": obs["tipo_obligacion"],
                    "nota": obs.get("nota"),
                },
            )
            inserted += 1
        return inserted
    except Exception:
        # Table may not exist yet (migration not applied)
        return 0


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------


def extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    chunks = []
    for page in reader.pages:
        text_value = page.extract_text() or ""
        cleaned = _normalize_whitespace(text_value)
        if cleaned:
            chunks.append(cleaned)
    return "\n".join(chunks)


def extract_html_text(content: bytes) -> str:
    soup = BeautifulSoup(content.decode("utf-8", errors="ignore"), "html.parser")
    return _normalize_whitespace(soup.get_text(" ", strip=True))


def _resolve_boe_document_url(url: str, content: bytes, content_type: str) -> str:
    if "boe.es" not in url:
        return url
    if "pdf" in content_type.lower() or content.startswith(b"%PDF-"):
        return url

    soup = BeautifulSoup(content.decode("utf-8", errors="ignore"), "html.parser")
    txt_link = soup.find("a", href=re.compile(r"txt\.php\?id=BOE-A-"))
    if txt_link and txt_link.get("href"):
        return str(httpx.URL(url).join(txt_link["href"]))

    iframe = soup.find("iframe", src=re.compile(r"txt\.php\?id=BOE-A-"))
    if iframe and iframe.get("src"):
        return str(httpx.URL(url).join(iframe["src"]))

    return url


# ---------------------------------------------------------------------------
# Document payload builder (23.2 — enriched metadata)
# ---------------------------------------------------------------------------


def build_document_payload(
    url: str,
    content: bytes,
    content_type: str = "",
    metadata: dict | None = None,
) -> dict[str, str]:
    metadata = dict(metadata or {})
    text_value = ""
    try:
        if "pdf" in content_type.lower() or content.startswith(b"%PDF-"):
            text_value = extract_pdf_text(content)
        else:
            text_value = extract_html_text(content)
    except Exception:
        text_value = ""

    row_completeness = "complete"
    row_provenance = "official_exact"
    if not text_value:
        if not metadata:
            raise ValueError(f"Could not extract text from CNMV document: {url}")
        row_completeness = "partial"
        row_provenance = "official_best_effort"
        text_value = (
            f"[PARTIAL] Metadata oficial CNMV sin texto completo parseable. "
            f"Titulo: {metadata.get('titulo') or metadata.get('referencia') or url}. "
            f"URL oficial: {url}"
        )

    first_line = next((line.strip() for line in text_value.splitlines() if line.strip()), "")
    referencia = metadata.get("referencia") or _extract_reference(url, text_value)
    tipo_documento = metadata.get("tipo_documento") or _detect_document_type(text_value)
    estado_vigencia = metadata.get("estado_vigencia") or _detect_vigencia(
        f"{metadata.get('titulo', '')} {text_value}"
    )
    titulo = metadata.get("titulo") or first_line or referencia
    fecha = metadata.get("fecha") or datetime.now(UTC).date().isoformat()
    fecha_publicacion = metadata.get("fecha_publicacion") or _extract_publication_date(
        f"{metadata.get('titulo', '')} {text_value}"
    )
    verified = (
        row_completeness == "complete"
        and row_provenance == "official_exact"
        and "cnmv.es" in urlparse(url).netloc.lower()
    )
    metadata_payload = {
        "verified": verified,
        "family_id": metadata.get("family_id"),
        "source_index_url": metadata.get("source_index_url"),
        "estado_consulta": metadata.get("estado_consulta"),
        "documentos_asociados": metadata.get("documentos_asociados"),
    }
    metadata_payload = {key: value for key, value in metadata_payload.items() if value is not None}

    return {
        "referencia": referencia,
        "fecha": fecha,
        "titulo": titulo,
        "texto": text_value,
        "url_fuente": url,
        "tipo_documento": tipo_documento,
        "ambito": _detect_ambito(text_value),
        "numero_circular": _extract_circular_number(text_value),
        "fecha_publicacion": fecha_publicacion,
        "referencia_boe": _extract_boe_reference(text_value, url),
        "estado_vigencia": estado_vigencia,
        "regulacion_relacionada": _detect_regulacion_relacionada(text_value),
        "row_completeness": row_completeness,
        "row_provenance": row_provenance,
        "metadata": _metadata_json(metadata_payload) if metadata_payload else None,
    }


# ---------------------------------------------------------------------------
# Upsert (supports new columns)
# ---------------------------------------------------------------------------


def upsert_documento_interpretativo(conn, payload: dict[str, str]) -> None:
    payload = dict(payload)

    if conn.engine.dialect.name == "sqlite":
        table_columns = {
            row[1] for row in conn.execute(text("PRAGMA table_info(documento_interpretativo)"))
        }
    else:
        table_columns = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'documento_interpretativo'
                    """
                )
            )
        }

    # Add defaults for base columns if missing
    payload.setdefault("organismo_emisor", "CNMV")
    payload.setdefault("jurisdiccion", "es")
    payload.setdefault("tipo_fuente", "cnmv")
    payload.setdefault("row_completeness", "complete")
    payload.setdefault("row_provenance", "official_exact")

    existing = None
    referencia = payload.get("referencia")
    if referencia:
        existing = conn.execute(
            text("SELECT * FROM documento_interpretativo WHERE referencia = :ref"),
            {"ref": referencia},
        ).mappings().first()

    for col in ("tipo_documento", "ambito", "fecha", "titulo", "url_fuente", "estado_vigencia"):
        if payload.get(col) is None and existing and existing.get(col) is not None:
            payload[col] = existing[col]

    payload.setdefault("tipo_documento", "circular_cnmv")
    payload.setdefault("ambito", "general_cnmv")
    payload.setdefault("fecha", datetime.now(UTC).date().isoformat())
    payload.setdefault("titulo", payload.get("referencia", "Documento CNMV"))
    payload.setdefault("url_fuente", "")
    payload.setdefault("estado_vigencia", "vigente")

    payload = sanitize_documento_payload(payload)

    # Build column list dynamically based on payload keys
    columns = [
        "tipo_documento", "organismo_emisor", "jurisdiccion", "tipo_fuente",
        "ambito", "referencia", "fecha", "titulo", "texto", "url_fuente",
    ]
    # Add optional enriched columns
    optional_columns = (
        "numero_circular",
        "fecha_publicacion",
        "referencia_boe",
        "estado_vigencia",
        "metadata",
        "row_completeness",
        "row_provenance",
    )
    columns.extend(col for col in optional_columns if col in payload)

    columns = [col for col in columns if col in table_columns]

    placeholders = ", ".join(f":{c}" for c in columns)
    cols_str = ", ".join(columns)
    update_cols = ", ".join(f"{c} = excluded.{c}" for c in columns if c != "referencia")

    conn.execute(
        text(
            f"""
            INSERT INTO documento_interpretativo ({cols_str})
            VALUES ({placeholders})
            ON CONFLICT (referencia) DO UPDATE SET
                {update_cols}
            """
        ),
        payload,
    )


# ---------------------------------------------------------------------------
# Document versioning (23.6)
# ---------------------------------------------------------------------------


def _get_next_version(conn, referencia: str) -> int:
    """Get next version number for a document."""
    row = conn.execute(
        text(
            """
            SELECT COALESCE(MAX(version_num), 0) + 1 as next_ver
            FROM documento_version
            WHERE documento_referencia = :referencia
            """
        ),
        {"referencia": referencia},
    ).mappings().first()
    return row["next_ver"]


def _record_version(
    conn,
    referencia: str,
    texto: str,
    cambio_tipo: str,
    nota: str | None = None,
    url_version: str | None = None,
) -> None:
    """Record a new version of a document."""
    version_num = _get_next_version(conn, referencia)
    conn.execute(
        text(
            """
            INSERT INTO documento_version
                (documento_referencia, version_num, texto, cambio_tipo, fecha_version, nota, url_version)
            VALUES (:referencia, :ver_num, :texto, :cambio_tipo, :fecha, :nota, :url)
            """
        ),
        {
            "referencia": referencia,
            "ver_num": version_num,
            "texto": texto,
            "cambio_tipo": cambio_tipo,
            "fecha": datetime.now(UTC).isoformat(),
            "nota": nota,
            "url": url_version,
        },
    )


def upsert_with_versioning(conn, payload: dict[str, str]) -> dict[str, str]:
    """Upsert document and record version if it already exists.

    Returns dict with 'action' ('created' or 'updated') and 'version_num'.
    """
    referencia = payload["referencia"]
    texto = payload["texto"]

    def _sync_links() -> tuple[int, int]:
        regulaciones = _detect_regulaciones(texto)
        obligaciones = _detect_obligaciones(texto)
        _upsert_regulation_links(conn, referencia, regulaciones)
        _upsert_obligation_links(conn, referencia, obligaciones)
        reg_count = len(regulaciones)
        obl_count = len(obligaciones)
        return reg_count, obl_count

    # Check if document exists
    existing = conn.execute(
        text("SELECT id FROM documento_interpretativo WHERE referencia = :ref"),
        {"ref": referencia},
    ).mappings().first()

    if not existing:
        # New document
        upsert_documento_interpretativo(conn, payload)
        try:
            _record_version(conn, referencia, texto, "creado")
            version_num = 1
        except Exception:
            version_num = None
        reg_count, obl_count = _sync_links()
        return {
            "action": "created",
            "version_num": version_num,
            "regulaciones": reg_count,
            "obligaciones": obl_count,
        }

    # Existing document - upsert and record version
    old_row = conn.execute(
        text("SELECT texto FROM documento_interpretativo WHERE referencia = :ref"),
        {"ref": referencia},
    ).mappings().first()

    old_texto = old_row["texto"] if old_row else ""

    # Detect change type
    if old_texto == texto:
        reg_count, obl_count = _sync_links()
        return {
            "action": "unchanged",
            "version_num": None,
            "regulaciones": reg_count,
            "obligaciones": obl_count,
        }

    cambio_tipo = "modificado"
    vigencia = payload.get("estado_vigencia", "")
    if "derogado" in vigencia.lower() or "deroga" in texto.lower():
        cambio_tipo = "derogado"
    elif "sustituido" in vigencia.lower() or "sustituye" in texto.lower():
        cambio_tipo = "sustituido"

    upsert_documento_interpretativo(conn, payload)

    nota = "Cambio detectado en documento existente"
    if cambio_tipo == "derogado":
        nota = "Documento derogado"
    elif cambio_tipo == "sustituido":
        nota = "Documento sustituido por nueva versión"

    try:
        _record_version(conn, referencia, texto, cambio_tipo, nota)
        new_ver = _get_next_version(conn, referencia)
    except Exception:
        new_ver = None

    reg_count, obl_count = _sync_links()

    return {
        "action": "updated",
        "version_num": new_ver,
        "cambio_tipo": cambio_tipo,
        "regulaciones": reg_count,
        "obligaciones": obl_count,
    }


# ---------------------------------------------------------------------------
# Main sync loop
# ---------------------------------------------------------------------------


def run_sync(
    seed_urls: list[str] | None = None,
    worker_name: str = "worker-cnmv",
    familia: str | None = None,
    max_urls: int | None = None,
) -> dict[str, int]:
    # Validate before discovery to avoid unnecessary HTTP calls
    raw = SEED_URLS if seed_urls is None else seed_urls
    if not raw:
        logger.error(
            "SEED_URLS vacío en %s — worker abortado sin ingestión. "
            "Configura la variable de entorno correspondiente.",
            worker_name,
        )
        return {"processed": 0, "stored": 0, "discovered": 0}

    # Discover URLs (23.1)
    candidates = _discover_new_documents(seed_urls, familia=familia, max_urls=max_urls)
    if not candidates:
        logger.error(
            "SEED_URLS vacío en %s — worker abortado sin ingestión. "
            "Configura la variable de entorno correspondiente.",
            worker_name,
        )
        return {"processed": 0, "stored": 0, "discovered": 0}

    request_delay = float(os.environ.get("WORKER_REQUEST_DELAY", "1.0"))
    processed = 0
    stored = 0
    discovered = len(candidates)
    missing_document_failures = 0
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine, logger=logger)

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client, engine.begin() as conn:
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)
            for candidate in candidates:
                url = candidate["url"] if isinstance(candidate, dict) else str(candidate)
                metadata = (
                    candidate
                    if isinstance(candidate, dict) and candidate.keys() - {"url"}
                    else None
                )
                try:
                    try:
                        response = client.get(url)
                        response.raise_for_status()
                        resolved_url = _resolve_boe_document_url(
                            str(response.url),
                            response.content,
                            response.headers.get("content-type", ""),
                        )
                        if resolved_url != str(response.url):
                            response = client.get(resolved_url)
                            response.raise_for_status()
                            url = resolved_url
                    except httpx.HTTPError:
                        missing_document_failures += 1
                        continue

                    if metadata:
                        payload = build_document_payload(
                            url,
                            response.content,
                            response.headers.get("content-type", ""),
                            metadata=metadata,
                        )
                    else:
                        payload = build_document_payload(
                            url,
                            response.content,
                            response.headers.get("content-type", ""),
                        )
                    processed += 1

                    change = check_content_changed(
                        conn, worker_name, "documento", payload["referencia"], response.content
                    )

                    if not change.changed and destination_row_exists(
                        conn,
                        "documento_interpretativo",
                        "referencia",
                        payload["referencia"],
                    ):
                        print(f"  [SKIP] {payload['referencia']} unchanged")
                        continue

                    invalidated = invalidate_old_embeddings_by_entity(
                        conn,
                        entity_table="documento_interpretativo",
                        entity_id_column="referencia",
                        entity_id_value=payload["referencia"],
                    )
                    if invalidated:
                        print(
                            f"  [INVALIDATE] {invalidated} old embeddings for {payload['referencia']}"
                        )

                    upsert_result = upsert_with_versioning(conn, payload)
                    record_revision(
                        conn,
                        worker_name,
                        "documento",
                        payload["referencia"],
                        response.content,
                    )
                    if upsert_result["action"] != "unchanged":
                        stored += 1
                    time.sleep(request_delay)
                except Exception as exc:
                    logger.warning("Failed to process CNMV URL %s: %s", url, exc)
                    continue

            final_status, final_error_msg = finalize_partial_sync_status(
                base_status="ok",
                missing_count=missing_document_failures,
                source_label="CNMV documents",
            )

            log_sync(
                conn,
                worker_name,
                final_status,
                documentos_processed=processed,
                documentos_upserted=stored,
                error_msg=final_error_msg,
            )

        return {"processed": processed, "stored": stored, "discovered": discovered}
    except Exception as exc:
        entity_id = "cnmv"
        if not handle_worker_failure(engine, "cnmv", entity_id, "sync_entity", exc):
            logger.warning("Entity cnmv moved to dead-letter")
            return {"processed": 0, "stored": 0, "discovered": discovered}
        with engine.begin() as conn:
            log_sync(
                conn,
                worker_name,
                "error",
                documentos_processed=processed,
                documentos_upserted=stored,
                error_msg=str(exc),
            )
        raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CNMV worker: sync public circulars and related regulatory documents"
    )
    parser.add_argument(
        "--run-once", action="store_true", help="Run a single sync cycle and exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=f"Seconds between sync cycles in continuous mode (default: {SYNC_INTERVAL_SECONDS})",
    )
    parser.add_argument(
        "--discover-only", action="store_true", help="Only discover URLs, don't sync"
    )
    parser.add_argument(
        "--familia",
        choices=sorted(CNMV_FAMILY_ALIASES),
        default=None,
        help="Limit sync/discovery to one CNMV source family",
    )
    parser.add_argument(
        "--max-urls",
        type=int,
        default=None,
        help="Maximum URLs/documents to process in this run",
    )
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("cnmv")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(
            worker_name="cron-cnmv-weekly",
            familia=args.familia,
            max_urls=args.max_urls,
        )
        print(
            f"[run-once] URLs descubiertas: {result['discovered']}, "
            f"Documentos procesados: {result['processed']}, "
            f"almacenados: {result['stored']}"
        )
    elif args.discover_only:
        docs = _discover_new_documents(familia=args.familia, max_urls=args.max_urls)
        print(f"[discover-only] {len(docs)} documentos descubiertos:")
        for doc in docs:
            print(f"  - {doc['url'] if isinstance(doc, dict) else doc}")
    else:
        print(f"Starting CNMV worker in continuous mode (interval={interval}s)")
        while True:
            touch_heartbeat()
            result = run_sync(familia=args.familia, max_urls=args.max_urls)
            print(
                f"Synced descubiertas={result['discovered']}, documentos={result['processed']}, "
                f"almacenados={result['stored']} at {datetime.now(UTC).isoformat()}"
            )
            sleep_with_heartbeat(interval)
