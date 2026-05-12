#!/usr/bin/env python
"""Ingest current AEAT 1XX/2XX designs and 2026 fiscal calendar.

This worker only uses official AEAT pages:
- current record designs for models 100-199 and 200-299;
- current taxpayer calendar 2026.

It stores official design resources and extracts deterministic spreadsheet,
properties, and PDF design-register fields as `modelo_casilla` records with
`tipo_casilla='diseno_registro_campo'`.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
from datetime import UTC, date, datetime
from urllib.parse import urljoin, urlparse

import httpx
import openpyxl
import xlrd
from bs4 import BeautifulSoup
from runtime import configure_logging, get_database_url, ensure_database_connection
from sqlalchemy import create_engine, text


logger = configure_logging("worker-aeat-current-designs")

AEAT_SEDE = "https://sede.agenciatributaria.gob.es"
DESIGN_INDEX_URLS = [
    "https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro/modelos-100-199.html",
    "https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro/modelos-200-299.html",
]
CALENDAR_ANNUAL_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/ayuda/calendario-contribuyente/"
    "calendario-contribuyente-2026/calendario-anual.html"
)
USER_AGENT = "Mozilla/5.0 (compatible; esdata-bot/1.0; official AEAT worker)"
MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def _http_client() -> httpx.Client:
    return httpx.Client(
        follow_redirects=True,
        timeout=45,
        verify=False,
        headers={"User-Agent": USER_AGENT},
    )


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fetch_text(client: httpx.Client, url: str) -> str:
    resp = client.get(url)
    resp.raise_for_status()
    return resp.text


def _fetch_bytes(client: httpx.Client, url: str) -> bytes:
    resp = client.get(url)
    resp.raise_for_status()
    return resp.content


def _normalize_url(base_url: str, href: str) -> str:
    return urljoin(base_url, href.strip())


def _is_official_aeat_url(url: str) -> bool:
    return urlparse(url).netloc.lower() == "sede.agenciatributaria.gob.es"


def _extract_model_code(text_value: str) -> str | None:
    match = re.match(r"\s*(?:Anexo\s+modelo\s+|Anexo\s+)?([12]\d{2})\b", text_value, flags=re.IGNORECASE)
    return match.group(1) if match else None


def _resource_type(label: str, url: str) -> str:
    hint = f"{label} {url}".lower()
    if "diccionario" in hint and "toma" in hint:
        return "diseno_registro_diccionario_toma_datos"
    if "diccionario" in hint:
        return "diseno_registro_diccionario"
    if ".xsd" in hint or "esquema xsd" in hint:
        return "diseno_registro_xsd"
    if "anexo" in hint:
        return "diseno_registro_anexo"
    return "diseno_registro"


def discover_current_design_links(client: httpx.Client) -> list[dict]:
    links: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for index_url in DESIGN_INDEX_URLS:
        soup = BeautifulSoup(_fetch_text(client, index_url), "html.parser")
        for anchor in soup.find_all("a", href=True):
            label = " ".join(anchor.get_text(" ", strip=True).split())
            code = _extract_model_code(label)
            if not code:
                continue
            url = _normalize_url(index_url, anchor["href"])
            if not _is_official_aeat_url(url):
                continue
            if url.split("#", 1)[0] == index_url:
                continue
            key = (code, url)
            if key in seen:
                continue
            seen.add(key)
            links.append(
                {
                    "codigo": code,
                    "label": label,
                    "url": url,
                    "tipo_recurso": _resource_type(label, url),
                    "formato": url.rsplit(".", 1)[-1].lower() if "." in url.rsplit("/", 1)[-1] else "html",
                    "source_index": index_url,
                }
            )
    return links


def _get_active_campaign(conn, codigo: str) -> tuple[int, str] | None:
    row = conn.execute(
        text(
            """
            SELECT mc.id, mc.campana
            FROM modelo_campana mc
            JOIN aeat_modelo m ON m.id = mc.modelo_id
            WHERE m.codigo = :codigo
              AND COALESCE(m.activo, true) = true
              AND mc.activo = true
            ORDER BY mc.campana DESC
            LIMIT 1
            """
        ),
        {"codigo": codigo},
    ).fetchone()
    return (int(row.id), str(row.campana)) if row else None


def _store_design_resource(conn, campana_id: int, link: dict, payload: bytes) -> str:
    sha = _sha256(payload)
    metadata = {
        "label": link["label"],
        "source_index": link["source_index"],
        "ingested_by": "aeat_current_designs",
    }
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
        {"campana_id": campana_id, "tipo_recurso": link["tipo_recurso"]},
    ).fetchone()
    if existing and existing.sha256_contenido == sha:
        conn.execute(
            text(
                """
                UPDATE modelo_recurso
                SET last_seen_at = CURRENT_TIMESTAMP,
                    url_recurso = :url_recurso,
                    formato = :formato,
                    metadata = CAST(:metadata AS JSON)
                WHERE id = :id
                """
            ),
            {
                "id": existing.id,
                "url_recurso": link["url"],
                "formato": link["formato"],
                "metadata": json.dumps(metadata),
            },
        )
        return "unchanged"

    if existing:
        conn.execute(text("UPDATE modelo_recurso SET activa = false WHERE id = :id"), {"id": existing.id})

    conn.execute(
        text(
            """
            INSERT INTO modelo_recurso (
                campana_id, tipo_recurso, formato, url_recurso, sha256_contenido,
                metadata, row_completeness, row_provenance
            )
            VALUES (
                :campana_id, :tipo_recurso, :formato, :url_recurso, :sha256,
                CAST(:metadata AS JSON), 'complete', 'official_exact'
            )
            ON CONFLICT (campana_id, tipo_recurso, sha256_contenido) DO UPDATE SET
                activa = true,
                url_recurso = EXCLUDED.url_recurso,
                formato = EXCLUDED.formato,
                metadata = EXCLUDED.metadata,
                last_seen_at = CURRENT_TIMESTAMP
            """
        ),
        {
            "campana_id": campana_id,
            "tipo_recurso": link["tipo_recurso"],
            "formato": link["formato"],
            "url_recurso": link["url"],
            "sha256": sha,
            "metadata": json.dumps(metadata),
        },
    )
    return "stored"


def _is_spreadsheet_format(url: str) -> bool:
    return url.lower().split("?", 1)[0].endswith((".xls", ".xlsx"))


def _is_properties_format(url: str) -> bool:
    return url.lower().split("?", 1)[0].endswith(".properties")


def _is_pdf_format(url: str) -> bool:
    return url.lower().split("?", 1)[0].endswith(".pdf")


def _cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def extract_spreadsheet_fields(payload: bytes) -> list[dict]:
    rows_by_sheet = _read_spreadsheet_rows(payload)
    fields: list[dict] = []
    for sheet_index, rows in enumerate(rows_by_sheet, start=1):
        header_row = None
        for idx, row in enumerate(rows):
            joined = " ".join(_cell_text(v).lower() for v in row)
            if "posic" in joined and "descrip" in joined:
                header_row = idx
                break
        if header_row is None:
            continue

        headers = [_cell_text(v).lower() for v in rows[header_row]]
        desc_col = next((i for i, h in enumerate(headers) if "descrip" in h), None)
        pos_col = next((i for i, h in enumerate(headers) if "posic" in h), None)
        len_col = next((i for i, h in enumerate(headers) if h in {"lon", "longitud"} or "long" in h), None)
        type_col = next((i for i, h in enumerate(headers) if h == "tipo" or "tipo" in h), None)
        content_col = next((i for i, h in enumerate(headers) if "contenido" in h), None)
        number_col = 0
        if desc_col is None:
            continue

        for row in rows[header_row + 1 :]:
            number = _cell_text(row[number_col] if number_col < len(row) else "")
            description = _cell_text(row[desc_col] if desc_col < len(row) else "")
            if not number or not description or not re.match(r"^\d+$", number):
                continue
            codigo = f"DR:{sheet_index}:{number}"
            parts = []
            if pos_col is not None:
                parts.append(f"Posic.: {_cell_text(row[pos_col] if pos_col < len(row) else '')}")
            if len_col is not None:
                parts.append(f"Lon.: {_cell_text(row[len_col] if len_col < len(row) else '')}")
            if type_col is not None:
                parts.append(f"Tipo: {_cell_text(row[type_col] if type_col < len(row) else '')}")
            if content_col is not None:
                content = _cell_text(row[content_col] if content_col < len(row) else "")
                if content:
                    parts.append(f"Contenido: {content}")
            fields.append(
                {
                    "codigo": codigo,
                    "etiqueta": description[:500],
                    "descripcion": "; ".join(parts)[:2000] or None,
                    "tipo_casilla": "diseno_registro_campo",
                    "pagina": sheet_index,
                    "orden": len(fields) + 1,
                }
            )
    return fields


def extract_properties_fields(payload: bytes) -> list[dict]:
    for encoding in ("utf-8", "iso-8859-1", "cp1252"):
        try:
            text_value = payload.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text_value = payload.decode("utf-8", errors="replace")

    fields: list[dict] = []
    pattern = re.compile(r"^([^=#\s]+)=\[(.*?)\]\[(.*?)\]\[(.*?)\]\[(.*?)\]\s*$")
    for line in text_value.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        key, xpath, datatype, official_box, label = match.groups()
        if not label:
            continue
        descriptor = [
            f"XPath: {xpath}",
            f"Tipo: {datatype}",
        ]
        if official_box and official_box != "###":
            descriptor.append(f"Casilla oficial: {official_box}")
        fields.append(
            {
                "codigo": f"DRP:{key}"[:120],
                "etiqueta": label[:500],
                "descripcion": "; ".join(descriptor)[:2000],
                "tipo_casilla": "diseno_registro_campo",
                "pagina": None,
                "orden": len(fields) + 1,
            }
        )
    return fields


_PDF_NATURE_WORDS = {
    "A",
    "AN",
    "ALFABETICO",
    "ALFABÉTICO",
    "ALFANUMERICO",
    "ALFANUMÉRICO",
    "NUM",
    "NUMERICO",
    "NUMÉRICO",
}


def _normalize_pdf_word(value: str) -> str:
    return (
        value.upper()
        .replace("Á", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ú", "U")
    )


def _clean_pdf_label(value: str) -> str:
    label = " ".join(value.split())
    marker = re.search(
        r"\s+(?:obligatorio|opcional|optativo|obligatoria|opcionalmente)\b",
        label,
        flags=re.IGNORECASE,
    )
    if marker:
        label = label[: marker.start()]
    return label.strip(" .")[:500]


def _append_pdf_field(
    fields: list[dict],
    seen_codes: set[str],
    codigo: str,
    etiqueta: str,
    descripcion: str,
) -> None:
    if not etiqueta:
        return
    unique_code = codigo[:120]
    if unique_code in seen_codes:
        unique_code = f"{unique_code}:{len(fields) + 1}"[:120]
    seen_codes.add(unique_code)
    fields.append(
        {
            "codigo": unique_code,
            "etiqueta": etiqueta[:500],
            "descripcion": descripcion[:2000],
            "tipo_casilla": "diseno_registro_campo",
            "pagina": None,
            "orden": len(fields) + 1,
        }
    )


def extract_pdf_text_fields(text_value: str) -> list[dict]:
    """Extract only clear AEAT design-register rows from PDF text."""

    fields: list[dict] = []
    seen_codes: set[str] = set()
    numbered_row = re.compile(
        r"^\s*(\d{1,4})\s+(\d{1,5})\s+(\d{1,5})\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)\s+(.+?)\s*$"
    )
    positions_row = re.compile(
        r"^\s*(\d{1,5}(?:\s*-\s*\d{1,5})?)\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)\s+(.+?)\s*$"
    )

    for raw_line in text_value.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue

        numbered_match = numbered_row.match(line)
        if numbered_match:
            number, position, length, field_type, label = numbered_match.groups()
            if _normalize_pdf_word(field_type) in _PDF_NATURE_WORDS:
                _append_pdf_field(
                    fields,
                    seen_codes,
                    f"DRPDF:N:{number}",
                    _clean_pdf_label(label),
                    f"Posic.: {position}; Lon.: {length}; Tipo: {field_type}",
                )
                continue

        positions_match = positions_row.match(line)
        if not positions_match:
            continue
        positions, nature, label = positions_match.groups()
        if _normalize_pdf_word(nature) not in _PDF_NATURE_WORDS:
            continue
        cleaned_positions = re.sub(r"\s+", "", positions)
        _append_pdf_field(
            fields,
            seen_codes,
            f"DRPDF:POS:{cleaned_positions}",
            _clean_pdf_label(label),
            f"Posiciones: {cleaned_positions}; Naturaleza: {nature}",
        )
    return fields


def extract_pdf_fields(payload: bytes) -> list[dict]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(payload))
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return extract_pdf_text_fields("\n".join(text_parts))


def _read_spreadsheet_rows(payload: bytes) -> list[list[list[object]]]:
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
        rows_by_sheet = []
        for sheet in workbook.worksheets:
            rows_by_sheet.append([list(row) for row in sheet.iter_rows(values_only=True)])
        workbook.close()
        return rows_by_sheet
    except Exception:
        book = xlrd.open_workbook(file_contents=payload)
        return [
            [sheet.row_values(row_idx) for row_idx in range(sheet.nrows)]
            for sheet in book.sheets()
        ]


def _campaign_has_fields(conn, campana_id: int) -> bool:
    return bool(
        conn.execute(
            text(
                """
                SELECT 1
                FROM modelo_casilla
                WHERE campana_id = :campana_id
                  AND tipo_casilla = 'diseno_registro_campo'
                LIMIT 1
                """
            ),
            {"campana_id": campana_id},
        ).fetchone()
    )


def _upsert_design_fields(conn, campana_id: int, fields: list[dict]) -> int:
    count = 0
    for field in fields:
        conn.execute(
            text(
                """
                INSERT INTO modelo_casilla (
                    campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden, activa
                )
                VALUES (
                    :campana_id, :codigo, :etiqueta, :descripcion, :tipo_casilla, :pagina, :orden, true
                )
                ON CONFLICT (campana_id, codigo) DO UPDATE SET
                    etiqueta = EXCLUDED.etiqueta,
                    descripcion = EXCLUDED.descripcion,
                    tipo_casilla = EXCLUDED.tipo_casilla,
                    pagina = EXCLUDED.pagina,
                    orden = EXCLUDED.orden,
                    activa = true
                """
            ),
            {"campana_id": campana_id, **field},
        )
        count += 1
    return count


def _extract_deadline_date(title: str) -> date | None:
    normalized = title.lower()
    match = re.search(r"(?:hasta\s+el\s+)?(\d{1,2})\s+de\s+([a-záéíóúñ]+)", normalized)
    if not match:
        return None
    month = MONTHS.get(match.group(2).replace("á", "a").replace("é", "e"))
    if not month:
        month = MONTHS.get(match.group(2))
    return date(2026, month, int(match.group(1))) if month else None


def _calendar_day_links(client: httpx.Client) -> list[str]:
    soup = BeautifulSoup(_fetch_text(client, CALENDAR_ANNUAL_URL), "html.parser")
    links = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        url = _normalize_url(CALENDAR_ANNUAL_URL, anchor["href"])
        if "/calendario-anual/" not in url or not re.search(r"/hasta-|/\d+-", url):
            continue
        if url in seen:
            continue
        seen.add(url)
        links.append(url)
    return links


def _extract_calendar_entries(client: httpx.Client) -> list[dict]:
    entries: list[dict] = []
    for url in _calendar_day_links(client):
        soup = BeautifulSoup(_fetch_text(client, url), "html.parser")
        title = soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else ""
        deadline = _extract_deadline_date(title)
        if not deadline:
            continue
        main = soup.find("main") or soup
        lines = [line.strip() for line in main.get_text("\n", strip=True).splitlines()]
        for line in lines:
            codes = sorted(set(re.findall(r"\b[12]\d{2}\b", line)))
            for code in codes:
                entries.append(
                    {
                        "codigo": code,
                        "deadline": deadline,
                        "observaciones": line[:1000],
                        "fuente": url,
                    }
                )
    return entries


def _upsert_calendar_entry(conn, entry: dict) -> bool:
    campaign = _get_active_campaign(conn, entry["codigo"])
    if campaign is None:
        return False
    campana_id, _campana = campaign
    exists = conn.execute(
        text(
            """
            SELECT 1
            FROM modelo_fiscal_calendar
            WHERE campana_id = :campana_id
              AND fecha_fin_presentacion = :deadline
              AND fuente = :fuente
            LIMIT 1
            """
        ),
        {"campana_id": campana_id, "deadline": entry["deadline"], "fuente": entry["fuente"]},
    ).fetchone()
    if exists:
        return False
    conn.execute(
        text(
            """
            INSERT INTO modelo_fiscal_calendar (
                campana_id, fecha_inicio_presentacion, fecha_fin_presentacion,
                fecha_fin_prorroga, observaciones, fuente, activo
            )
            VALUES (
                :campana_id, :deadline, :deadline,
                NULL, :observaciones, :fuente, true
            )
            """
        ),
        {
            "campana_id": campana_id,
            "deadline": entry["deadline"],
            "observaciones": "Fecha limite oficial AEAT 2026. " + entry["observaciones"],
            "fuente": entry["fuente"],
        },
    )
    return True


def run_sync(engine) -> dict:
    stats = {
        "design_links": 0,
        "resources_stored": 0,
        "resources_unchanged": 0,
        "spreadsheet_fields": 0,
        "pdf_fields": 0,
        "parse_errors": 0,
        "calendar_entries": 0,
        "calendar_inserted": 0,
        "skipped": 0,
    }
    started_at = datetime.now(UTC)
    with _http_client() as client, engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE modelo_recurso
                SET activa = false
                WHERE tipo_recurso LIKE 'diseno_registro%'
                  AND activa = true
                  AND url_recurso = metadata ->> 'source_index'
                  AND metadata ->> 'ingested_by' = 'aeat_current_designs'
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE modelo_fiscal_calendar c
                SET activo = false
                FROM modelo_campana mc
                JOIN aeat_modelo m ON m.id = mc.modelo_id
                WHERE c.campana_id = mc.id
                  AND c.fuente LIKE :calendar_source
                  AND COALESCE(m.activo, true) = false
                """
            ),
            {"calendar_source": "%/calendario-contribuyente-2026/calendario-anual/%"},
        )
        links = discover_current_design_links(client)
        stats["design_links"] = len(links)
        for link in links:
            campaign = _get_active_campaign(conn, link["codigo"])
            if campaign is None:
                stats["skipped"] += 1
                continue
            campana_id, _campana = campaign
            payload = _fetch_bytes(client, link["url"])
            outcome = _store_design_resource(conn, campana_id, link, payload)
            if outcome == "unchanged":
                stats["resources_unchanged"] += 1
            else:
                stats["resources_stored"] += 1

            if not _campaign_has_fields(conn, campana_id):
                try:
                    if _is_spreadsheet_format(link["url"]):
                        fields = extract_spreadsheet_fields(payload)
                        stats["spreadsheet_fields"] += _upsert_design_fields(conn, campana_id, fields)
                    elif _is_properties_format(link["url"]):
                        fields = extract_properties_fields(payload)
                        stats["spreadsheet_fields"] += _upsert_design_fields(conn, campana_id, fields)
                    elif _is_pdf_format(link["url"]):
                        fields = extract_pdf_fields(payload)
                        stats["pdf_fields"] += _upsert_design_fields(conn, campana_id, fields)
                except Exception as exc:
                    stats["parse_errors"] += 1
                    logger.warning(
                        "Could not extract design fields from official AEAT resource",
                        extra={"codigo": link["codigo"], "url": link["url"], "error": str(exc)},
                    )

        calendar_entries = _extract_calendar_entries(client)
        stats["calendar_entries"] = len(calendar_entries)
        for entry in calendar_entries:
            if _upsert_calendar_entry(conn, entry):
                stats["calendar_inserted"] += 1

        finished_at = datetime.now(UTC)
        conn.execute(
            text(
                """
                INSERT INTO sync_log (
                    worker, started_at, finished_at, status, rows_processed,
                    errors, error_msg, duration_ms
                )
                VALUES (
                    'worker-aeat-current-designs', :started_at, :finished_at, 'ok',
                    :rows_processed, 0, :error_msg, :duration_ms
                )
                """
            ),
            {
                "started_at": started_at,
                "finished_at": finished_at,
                "rows_processed": stats["resources_stored"] + stats["resources_unchanged"] + stats["calendar_inserted"],
                "error_msg": "summary: " + json.dumps(stats, sort_keys=True),
                "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
            },
        )
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-once", action="store_true", help="Run once and exit.")
    parser.parse_args()

    engine = create_engine(get_database_url(), future=True, pool_pre_ping=True)
    ensure_database_connection(engine)
    stats = run_sync(engine)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
