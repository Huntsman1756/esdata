import argparse
import os
import re
import time
from datetime import UTC, datetime
from html import unescape
from io import BytesIO

import httpx
from boe import _ensure_sync_log_table, log_sync
from change_detection import (
    check_content_changed,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    record_revision,
)
from pypdf import PdfReader
from runtime import get_database_url, get_interval_seconds
from sqlalchemy import create_engine, text


def _parse_seed_urls(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


SEED_URLS = _parse_seed_urls(os.getenv("BDE_SEED_URLS"))
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_reference(url: str, text_value: str) -> str:
    path_match = re.search(r"(/publi/|/doc/|/informes/)([^/]+)", url)
    if path_match:
        return f"BDE-{path_match.group(2)}"
    text_match = re.search(r"(\d{4}/\d{2})", text_value)
    if text_match:
        return f"BDE-{text_match.group(1).replace('/', '-')}"
    return f"BDE-{datetime.now(UTC).date().isoformat().replace('-', '')}"


def _detect_document_type(text_value: str) -> str:
    lowered = text_value.lower()
    if "informe" in lowered:
        return "informe_bde"
    if "comunicación" in lowered or "comunicacion" in lowered:
        return "comunicacion_bde"
    if "publicación" in lowered or "publicacion" in lowered:
        return "publicacion_bde"
    if "guía" in lowered or "guia" in lowered:
        return "guia_bde"
    return "documento_bde"


def _detect_ambito(text_value: str) -> str:
    lowered = text_value.lower()
    if "estabilidad financiera" in lowered:
        return "estabilidad_financiera"
    if "política monetaria" in lowered or "politica monetaria" in lowered:
        return "politica_monetaria"
    if "supervisión bancaria" in lowered or "supervision bancaria" in lowered:
        return "supervision_bancaria"
    if "pago" in lowered or "sistemas de pago" in lowered:
        return "sistemas_pago"
    return "economia_espanola"


def extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    chunks = []
    for page in reader.pages:
        text_value = page.extract_text() or ""
        cleaned = _normalize_whitespace(text_value)
        if cleaned:
            chunks.append(cleaned)
    return "\n".join(chunks)


def extract_text(content: bytes) -> str:
    html = content.decode("utf-8", errors="ignore")
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", "\n", html)
    text_value = re.sub(r"\n\s*\n", "\n", html)
    return _normalize_whitespace(unescape(text_value))


def _is_pdf(content: bytes) -> bool:
    return content[:5] == b"%PDF-"


def build_document_payload(url: str, content: bytes) -> dict[str, str]:
    if _is_pdf(content):
        text_value = extract_pdf_text(content)
        if not text_value:
            raise ValueError(f"Could not extract text from Banco de España PDF: {url}")
    else:
        text_value = extract_text(content)
        if not text_value:
            raise ValueError(f"Could not extract text from Banco de España document: {url}")

    referencia = _extract_reference(url, text_value)
    first_line = next((line.strip() for line in text_value.splitlines() if line.strip()), "")

    return {
        "referencia": referencia,
        "fecha": datetime.now(UTC).date().isoformat(),
        "titulo": first_line or referencia,
        "texto": text_value,
        "url_fuente": url,
        "tipo_documento": _detect_document_type(text_value),
        "tipo_fuente": "bde",
        "organismo_emisor": "Banco de España",
        "ambito": _detect_ambito(text_value),
        "jurisdiccion": "es",
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
                'Banco de España',
                'es',
                'bde',
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
    worker_name: str = "worker-bde",
) -> dict[str, int]:
    urls = seed_urls or SEED_URLS
    processed = 0
    stored = 0
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(UTC).isoformat()

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client, engine.begin() as conn:
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)
            for url in urls:
                response = client.get(url)
                response.raise_for_status()
                payload = build_document_payload(url, response.content)
                processed += 1

                change = check_content_changed(
                    conn, worker_name, "documento", payload["referencia"], response.content
                )

                if not change.changed:
                    print(f"  [SKIP] {payload['referencia']} unchanged")
                    continue

                invalidated = invalidate_old_embeddings(conn, payload["referencia"])
                if invalidated:
                    print(
                        f"  [INVALIDATE] {invalidated} old embeddings for {payload['referencia']}"
                    )

                upsert_documento_interpretativo(conn, payload)
                record_revision(
                    conn,
                    worker_name,
                    "documento",
                    payload["referencia"],
                    response.content,
                )
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
        description="Banco de España worker: sync public economic and banking documents"
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
    init_sentry("bde")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-bde-weekly")
        print(
            f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}"
        )
    else:
        print(f"Starting Banco de España worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced documentos={result['processed']}, almacenados={result['stored']} at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
