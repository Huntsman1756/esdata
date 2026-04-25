import argparse
from datetime import UTC, datetime, timezone
from html import unescape
from io import BytesIO
import os
import re
import time
from urllib.parse import urlparse

import httpx
from pypdf import PdfReader
from sqlalchemy import create_engine, text

from boe import _ensure_sync_log_table, log_sync
from runtime import get_database_url, get_interval_seconds


def _parse_seed_urls(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


SEED_URLS = _parse_seed_urls(os.getenv("SEPBLAC_SEED_URLS"))
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_reference(url: str, text_value: str) -> str:
    lowered = text_value.lower()
    if "modelo 19" in lowered:
        return "SEPBLAC-MODELO-19"
    if "manual" in lowered and "blanqueo de capitales" in lowered:
        return "SEPBLAC-MANUAL-PBCFT"
    if "comunicación por indicio" in lowered or "comunicacion por indicio" in lowered:
        return "SEPBLAC-COMUNICACION-INDICIO"

    path = urlparse(url).path.rstrip("/").split("/")[-1]
    return f"SEPBLAC-{path.removesuffix('.pdf').removesuffix('.html') or 'seed'}"


def _detect_document_type(text_value: str) -> str:
    lowered = text_value.lower()
    if "modelo 19" in lowered:
        return "formulario_sepblac"
    if "manual" in lowered:
        return "manual_sepblac"
    if "comunicación por indicio" in lowered or "comunicacion por indicio" in lowered:
        return "guia_operativa_sepblac"
    if "ley 10/2010" in lowered or "real decreto 304/2014" in lowered:
        return "normativa_sepblac"
    return "documento_sepblac"


def _detect_ambito(text_value: str) -> str:
    lowered = text_value.lower()
    if "comunicación por indicio" in lowered or "comunicacion por indicio" in lowered:
        return "aml_cft_reporting"
    if "blanqueo de capitales" in lowered or "financiación del terrorismo" in lowered or "financiacion del terrorismo" in lowered:
        return "aml_cft"
    return "supervision_sepblac"


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
    html = content.decode("utf-8", errors="ignore")
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    text_value = re.sub(r"<[^>]+>", " ", html)
    return _normalize_whitespace(unescape(text_value))


def extract_text(content: bytes, content_type: str, url: str) -> str:
    if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
        return extract_pdf_text(content)
    return extract_html_text(content)


def build_document_payload(url: str, content: bytes, content_type: str) -> dict[str, str]:
    text_value = extract_text(content, content_type, url)
    if not text_value:
        raise ValueError(f"Could not extract text from SEPBLAC document: {url}")

    first_line = next((line.strip() for line in text_value.splitlines() if line.strip()), "")
    referencia = _extract_reference(url, text_value)

    return {
        "referencia": referencia,
        "fecha": datetime.now(UTC).date().isoformat(),
        "titulo": first_line or referencia,
        "texto": text_value,
        "url_fuente": url,
        "tipo_documento": _detect_document_type(text_value),
        "ambito": _detect_ambito(text_value),
    }


def upsert_documento_interpretativo(conn, payload: dict[str, str]) -> None:
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
                url_fuente
            )
            VALUES (
                :tipo_documento,
                'SEPBLAC',
                'es',
                'sepblac',
                :ambito,
                :referencia,
                :fecha,
                :titulo,
                :texto,
                :url_fuente
            )
            ON CONFLICT (referencia) DO UPDATE SET
                tipo_documento = excluded.tipo_documento,
                ambito = excluded.ambito,
                fecha = excluded.fecha,
                titulo = excluded.titulo,
                texto = excluded.texto,
                url_fuente = excluded.url_fuente
            """
        ),
        payload,
    )


def run_sync(
    seed_urls: list[str] | None = None,
    worker_name: str = "worker-sepblac",
) -> dict[str, int]:
    urls = seed_urls or SEED_URLS
    processed = 0
    stored = 0
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(timezone.utc).isoformat()

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            with engine.begin() as conn:
                _ensure_sync_log_table(conn)
                for url in urls:
                    response = client.get(url)
                    response.raise_for_status()
                    payload = build_document_payload(
                        url, response.content, response.headers.get("content-type", "")
                    )
                    processed += 1
                    upsert_documento_interpretativo(conn, payload)
                    stored += 1

                log_sync(
                    conn,
                    worker_name,
                    "ok",
                    documentos_processed=processed,
                    documentos_upserted=stored,
                )

        return {"processed": processed, "stored": stored}
    except Exception as exc:
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SEPBLAC worker: sync public operational and AML/CFT documents"
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
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("sepblac")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-sepblac-weekly")
        print(
            f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}"
        )
    else:
        print(f"Starting SEPBLAC worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced documentos={result['processed']}, almacenados={result['stored']} at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
