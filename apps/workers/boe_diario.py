"""Worker BOE diario non-consolidated documents.

Fuente oficial primaria: https://www.boe.es/diario_boe/xml.php?id=<BOE-ID>.
Este worker es deliberadamente separado de `boe.py`: los anuncios,
suplementos y notificaciones no consolidables se almacenan en
`documento_interpretativo`, nunca en `norma/articulo/version_articulo`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from io import BytesIO
from urllib.parse import urljoin

import httpx
from boe import _ensure_sync_log_table, log_sync
from change_detection import ensure_source_revision_table, record_revision
from pypdf import PdfReader
from runtime import ensure_database_connection, get_database_url
from sqlalchemy import create_engine, text

BOE_BASE = "https://www.boe.es"
BOE_XML_URL = f"{BOE_BASE}/diario_boe/xml.php?id={{boe_id}}"
BOE_SUMMARY_URL = f"{BOE_BASE}/datosabiertos/api/boe/sumario/{{yyyymmdd}}"
WORKER_NAME = "cron-boe-diario-daily"
DATABASE_URL = get_database_url()


@dataclass(frozen=True)
class BOEDiarioDocumento:
    referencia: str
    fecha: str | None
    titulo: str
    texto: str
    url_fuente: str
    pdf_url: str | None
    tipo_documento: str
    row_completeness: str
    row_provenance: str
    metadata: dict


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _yyyymmdd_to_iso(value: str | None) -> str | None:
    if not value or len(value) != 8:
        return None
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def _node_text(root: ET.Element, path: str) -> str:
    node = root.find(path)
    if node is None:
        return ""
    return _normalize_whitespace("".join(node.itertext()))


def _tipo_documento(referencia: str) -> str:
    if referencia.startswith("BOE-B-"):
        return "anuncio_boe"
    if referencia.startswith("BOE-S-"):
        return "suplemento_boe"
    if referencia.startswith("BOE-N-"):
        return "notificacion_boe"
    return "boe_diario"


def parse_boe_diario_xml(xml_text: str, xml_url: str) -> BOEDiarioDocumento:
    root = ET.fromstring(xml_text)  # noqa: S314 - official BOE XML
    referencia = _node_text(root, "./metadatos/identificador")
    if not referencia:
        raise ValueError("BOE diario XML without metadatos/identificador")

    titulo = _node_text(root, "./metadatos/titulo") or referencia
    fecha = _yyyymmdd_to_iso(_node_text(root, "./metadatos/fecha_publicacion"))
    pdf_url_raw = _node_text(root, "./metadatos/url_pdf")
    pdf_url = urljoin(BOE_BASE, pdf_url_raw) if pdf_url_raw else None
    paragraphs = [
        _normalize_whitespace("".join(node.itertext()))
        for node in root.findall(".//texto//p")
    ]
    texto = "\n".join(part for part in paragraphs if part)
    metadata = {
        "source_format": "boe_daily_xml",
        "extraction_method": "xml_text",
        "xml_url": xml_url,
        "pdf_url": pdf_url,
        "text_length": len(texto),
        "content_hash": sha256(xml_text.encode("utf-8")).hexdigest(),
    }
    return BOEDiarioDocumento(
        referencia=referencia,
        fecha=fecha,
        titulo=titulo,
        texto=texto,
        url_fuente=xml_url,
        pdf_url=pdf_url,
        tipo_documento=_tipo_documento(referencia),
        row_completeness="complete" if texto else "partial",
        row_provenance="official_exact" if texto else "official_best_effort",
        metadata=metadata,
    )


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    parts = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(part.strip() for part in parts if part.strip())


def _with_pdf_fallback(doc: BOEDiarioDocumento, pdf_text: str, pdf_content: bytes) -> BOEDiarioDocumento:
    metadata = {
        **doc.metadata,
        "source_format": "boe_pdf",
        "extraction_method": "pypdf_extract_text",
        "text_length": len(pdf_text),
        "content_hash": sha256(pdf_content).hexdigest(),
    }
    return BOEDiarioDocumento(
        referencia=doc.referencia,
        fecha=doc.fecha,
        titulo=doc.titulo,
        texto=pdf_text,
        url_fuente=doc.pdf_url or doc.url_fuente,
        pdf_url=doc.pdf_url,
        tipo_documento=doc.tipo_documento,
        row_completeness="partial",
        row_provenance="official_best_effort",
        metadata=metadata,
    )


def fetch_boe_diario_document(
    client: httpx.Client,
    boe_id: str,
    *,
    fetch_pdf_fallback: bool = True,
) -> BOEDiarioDocumento:
    xml_url = BOE_XML_URL.format(boe_id=boe_id)
    response = client.get(xml_url, headers={"Accept": "application/xml"}, timeout=30.0)
    response.raise_for_status()
    doc = parse_boe_diario_xml(response.text, xml_url)
    if doc.texto or not fetch_pdf_fallback or not doc.pdf_url:
        return doc

    pdf_response = client.get(doc.pdf_url, headers={"Accept": "application/pdf"}, timeout=60.0)
    pdf_response.raise_for_status()
    content_type = pdf_response.headers.get("content-type", "")
    if "pdf" not in content_type.lower() and not pdf_response.content.startswith(b"%PDF-"):
        return doc
    pdf_text = _extract_pdf_text(pdf_response.content)
    if not pdf_text:
        return doc
    return _with_pdf_fallback(doc, pdf_text, pdf_response.content)


def upsert_documento_interpretativo(conn, doc: BOEDiarioDocumento) -> None:
    conn.execute(
        text(
            """
            INSERT INTO documento_interpretativo (
                tipo_documento,
                organismo_emisor,
                jurisdiccion,
                tipo_fuente,
                ambito,
                referencia,
                fecha,
                titulo,
                texto,
                url_fuente,
                metadata,
                row_completeness,
                row_provenance
            )
            VALUES (
                :tipo_documento,
                'BOE',
                'es',
                'boe_diario',
                'boe_diario',
                :referencia,
                :fecha,
                :titulo,
                :texto,
                :url_fuente,
                CAST(:metadata AS JSON),
                :row_completeness,
                :row_provenance
            )
            ON CONFLICT (referencia) DO UPDATE SET
                tipo_documento = excluded.tipo_documento,
                fecha = excluded.fecha,
                titulo = excluded.titulo,
                texto = excluded.texto,
                url_fuente = excluded.url_fuente,
                metadata = excluded.metadata,
                row_completeness = excluded.row_completeness,
                row_provenance = excluded.row_provenance
            """
        ),
        {
            "tipo_documento": doc.tipo_documento,
            "referencia": doc.referencia,
            "fecha": doc.fecha,
            "titulo": doc.titulo,
            "texto": doc.texto,
            "url_fuente": doc.url_fuente,
            "metadata": json.dumps(doc.metadata, ensure_ascii=False),
            "row_completeness": doc.row_completeness,
            "row_provenance": doc.row_provenance,
        },
    )


def _csv_ids(value: str | None) -> list[str]:
    if not value:
        return []
    ids = [_normalize_whitespace(item).upper() for item in value.split(",") if item.strip()]
    return [item for item in ids if re.fullmatch(r"BOE-[ABSN]-\d{4}-\d+", item)]


def _walk_ids(value) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            found.update(_walk_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_walk_ids(item))
    elif isinstance(value, str):
        found.update(re.findall(r"BOE-[BSN]-\d{4}-\d+", value))
    return found


def discover_boe_diario_ids(client: httpx.Client, *, days_back: int, max_ids: int) -> list[str]:
    found: list[str] = []
    today = datetime.now(UTC).date()
    for offset in range(max(days_back, 0) + 1):
        day = today - timedelta(days=offset)
        url = BOE_SUMMARY_URL.format(yyyymmdd=day.strftime("%Y%m%d"))
        response = client.get(url, headers={"Accept": "application/json"}, timeout=30.0)
        if response.status_code != 200:
            continue
        for boe_id in sorted(_walk_ids(response.json())):
            if boe_id not in found:
                found.append(boe_id)
            if len(found) >= max_ids:
                return found
    return found


def run_sync(worker_name: str = WORKER_NAME) -> dict[str, int]:
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)
    fetch_pdf = os.getenv("BOE_DIARIO_FETCH_PDF_FALLBACK", "true").lower() != "false"
    max_ids = int(os.getenv("BOE_DIARIO_MAX_IDS_PER_RUN", "10"))
    days_back = int(os.getenv("BOE_DIARIO_DAYS_BACK", "1"))
    explicit_ids = _csv_ids(os.getenv("BOE_DIARIO_IDS"))
    sync_start = datetime.now(UTC).isoformat()
    processed = 0
    upserted = 0
    errors = 0

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client, engine.begin() as conn:
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)
            boe_ids = explicit_ids or discover_boe_diario_ids(
                client,
                days_back=days_back,
                max_ids=max_ids,
            )
            for boe_id in boe_ids[:max_ids]:
                processed += 1
                try:
                    doc = fetch_boe_diario_document(
                        client,
                        boe_id,
                        fetch_pdf_fallback=fetch_pdf,
                    )
                    upsert_documento_interpretativo(conn, doc)
                    record_revision(
                        conn,
                        worker_name,
                        "documento_interpretativo",
                        doc.referencia,
                        doc.texto or doc.referencia,
                    )
                    upserted += 1
                    time.sleep(0.2)
                except Exception as exc:
                    errors += 1
                    print(f"[WARN] BOE diario {boe_id} skipped: {exc}")
            log_sync(
                conn,
                worker_name,
                "partial" if errors else "ok",
                documentos_processed=processed,
                documentos_upserted=upserted,
                error_msg=(
                    f"summary: ids={len(boe_ids)}; upserted={upserted}; errors={errors}; "
                    f"discovery={'off' if explicit_ids else 'on'}"
                ),
                started_at=sync_start,
            )
        return {"processed": processed, "upserted": upserted, "errors": errors}
    except Exception:
        with engine.begin() as conn:
            log_sync(
                conn,
                worker_name,
                "error",
                documentos_processed=processed,
                documentos_upserted=upserted,
                error_msg="boe_diario sync failed",
                started_at=sync_start,
            )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BOE diario worker")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    args = parser.parse_args()
    result = run_sync()
    print(
        f"[run-once] BOE diario processed={result['processed']} "
        f"upserted={result['upserted']} errors={result['errors']}"
    )
