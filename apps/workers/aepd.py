"""Worker AEPD — Agencia Espanola de Proteccion de Datos.

Fuente: resoluciones publicadas en https://www.aepd.es/ (procedimientos
sancionadores y otras resoluciones). Persistencia: `documento_interpretativo`
con `tipo_fuente='aepd'`. Conflict key: `referencia` UNIQUE.

Sync intervalo: semanal. Auditoria via `sync_log`.

Limitaciones conocidas:
- Listados HTML pueden cambiar estructura; parser tolerante pero limitado.
- PDFs adjuntos no se parsean por defecto (solo metadata + cuerpo HTML).
"""

import argparse
import logging
import os
import re
import time
from datetime import UTC, datetime
from html import unescape
from io import BytesIO
from urllib.parse import urljoin, urlparse

import httpx
from boe import _ensure_sync_log_table, log_sync
from change_detection import (
    check_content_changed,
    destination_row_exists,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    record_revision,
)
from pypdf import PdfReader
from runtime import (
    ensure_database_connection,
    get_database_url,
    get_interval_seconds,
    handle_worker_failure,
    sleep_with_heartbeat,
    touch_heartbeat,
)
from sqlalchemy import create_engine, text
from vocabulary_validation import sanitize_documento_payload

logger = logging.getLogger(__name__)


def _parse_seed_urls(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


SEED_URLS = _parse_seed_urls(os.getenv("AEPD_SEED_URLS"))
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)
AEPD_GUIDES_INDEX_URL = os.getenv(
    "AEPD_GUIDES_INDEX_URL", "https://www.aepd.es/guias-y-herramientas/guias"
)
DEFAULT_AEPD_MAX_URLS_PER_RUN = 25
DEFAULT_AEPD_DISCOVERY_PAGES = 3


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        logger.warning("Invalid integer for %s=%r; using %s", name, value, default)
        return default
    return max(parsed, 0)


def _extract_reference(url: str, text_value: str) -> str:
    path = urlparse(url).path.rstrip("/")
    filename = path.split("/")[-1]
    if filename:
        slug = filename.removesuffix(".pdf")
        if slug:
            return f"AEPD-{slug}"
    text_match = re.search(r"(\d{4}/\d{2})", text_value)
    if text_match:
        return f"AEPD-{text_match.group(1).replace('/', '-')}"
    return f"AEPD-{datetime.now(UTC).date().isoformat().replace('-', '')}"


def _detect_document_type(text_value: str) -> str:
    lowered = text_value.lower()
    if "guía" in lowered or "guia" in lowered:
        return "guia_aepd"
    if "resolución" in lowered or "resolucion" in lowered:
        return "resolucion_aepd"
    if "instrucción" in lowered or "instruccion" in lowered:
        return "instruccion_aepd"
    if "acuerdo" in lowered:
        return "acuerdo_aepd"
    return "documento_aepd"


def _detect_ambito(text_value: str) -> str:
    lowered = text_value.lower()
    if "protección de datos" in lowered or "proteccion de datos" in lowered:
        return "proteccion_datos"
    if "derecho de acceso" in lowered or "derecho acceso" in lowered:
        return "derechos_ar"
    if "ficheros" in lowered or "ficheros de datos" in lowered:
        return "ficheros_datos"
    if "cookies" in lowered:
        return "cookies"
    return "proteccion_datos_general"


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


def _is_official_aepd_document_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc not in {"www.aepd.es", "aepd.es"}:
        return False

    path = parsed.path
    if path.endswith(".pdf") and path.startswith(("/documento/", "/guias/")):
        return True

    return (
        path.startswith("/guias-y-herramientas/guias/")
        and "guias-y-documentos-obsoletos" not in path
        and not parsed.query
        and "." not in path.rsplit("/", 1)[-1]
    )


def _extract_aepd_document_urls_from_index(html: str, *, base_url: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE):
        absolute_url = urljoin(base_url, unescape(match.group(1)))
        if not _is_official_aepd_document_url(absolute_url):
            continue
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        urls.append(absolute_url)
    return urls


def discover_aepd_document_urls(
    client: httpx.Client,
    *,
    index_url: str = AEPD_GUIDES_INDEX_URL,
    max_urls: int,
    max_pages: int,
) -> list[str]:
    """Discover current AEPD guide/document URLs from the official index."""
    if max_urls <= 0 or max_pages <= 0:
        return []

    discovered: list[str] = []
    seen: set[str] = set()
    page_urls = [index_url]
    for page in range(1, max_pages):
        page_urls.append(urljoin(index_url, f"?page={page}"))

    for page_url in page_urls:
        try:
            response = client.get(page_url)
            response.raise_for_status()
        except Exception as exc:
            logger.warning("AEPD discovery skipped %s: %s", page_url, exc)
            continue

        for document_url in _extract_aepd_document_urls_from_index(
            response.text, base_url=page_url
        ):
            if document_url in seen:
                continue
            seen.add(document_url)
            discovered.append(document_url)
            if len(discovered) >= max_urls:
                return discovered

    return discovered


def build_document_payload(url: str, content: bytes) -> dict[str, str]:
    if _is_pdf(content):
        text_value = extract_pdf_text(content)
        if not text_value:
            raise ValueError(f"Could not extract text from AEPD PDF: {url}")
    else:
        text_value = extract_text(content)
        if not text_value:
            raise ValueError(f"Could not extract text from AEPD document: {url}")

    referencia = _extract_reference(url, text_value)
    first_line = next((line.strip() for line in text_value.splitlines() if line.strip()), "")

    return {
        "referencia": referencia,
        "fecha": datetime.now(UTC).date().isoformat(),
        "titulo": first_line or referencia,
        "texto": text_value,
        "url_fuente": url,
        "tipo_documento": _detect_document_type(text_value),
        "tipo_fuente": "aepd",
        "organismo_emisor": "AEPD",
        "ambito": _detect_ambito(text_value),
        "jurisdiccion": "es",
    }


def upsert_documento_interpretativo(conn, payload: dict[str, str]) -> None:
    record = sanitize_documento_payload(
        {
            "tipo_documento": payload["tipo_documento"],
            "organismo_emisor": payload.get("organismo_emisor", "AEPD"),
            "jurisdiccion": payload.get("jurisdiccion", "es"),
            "tipo_fuente": payload.get("tipo_fuente", "aepd"),
            "ambito": payload["ambito"],
            "referencia": payload["referencia"],
            "fecha": payload["fecha"],
            "titulo": payload["titulo"],
            "texto": payload["texto"],
            "url_fuente": payload["url_fuente"],
        }
    )
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
                :organismo_emisor,
                :jurisdiccion,
                :tipo_fuente,
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
        record,
    )


def run_sync(
    seed_urls: list[str] | None = None,
    worker_name: str = "worker-aepd",
) -> dict[str, int]:
    request_delay = float(os.environ.get("WORKER_REQUEST_DELAY", "1.0"))
    processed = 0
    stored = 0
    errors = 0
    sync_start = datetime.now(UTC).isoformat()
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client, engine.begin() as conn:
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)
            urls = list(seed_urls) if seed_urls is not None else list(SEED_URLS)
            if seed_urls is None and _env_bool("AEPD_DISCOVER_FROM_INDEX", True):
                discovered = discover_aepd_document_urls(
                    client,
                    index_url=os.getenv("AEPD_GUIDES_INDEX_URL", AEPD_GUIDES_INDEX_URL),
                    max_urls=_env_int("AEPD_MAX_URLS_PER_RUN", DEFAULT_AEPD_MAX_URLS_PER_RUN),
                    max_pages=_env_int("AEPD_DISCOVERY_PAGES", DEFAULT_AEPD_DISCOVERY_PAGES),
                )
                if discovered:
                    urls = discovered

            urls = list(dict.fromkeys(urls))
            if not urls:
                message = (
                    "No AEPD URLs discovered and AEPD_SEED_URLS is empty; "
                    "worker wrote explicit partial telemetry."
                )
                logger.warning(message)
                log_sync(
                    conn,
                    worker_name,
                    "partial",
                    documentos_processed=0,
                    documentos_upserted=0,
                    error_msg=message,
                    started_at=sync_start,
                )
                return {"processed": 0, "stored": 0, "errors": 0}

            for url in urls:
                try:
                    response = client.get(url)
                    response.raise_for_status()
                    payload = build_document_payload(url, response.content)
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
                    time.sleep(request_delay)
                except Exception as item_exc:
                    errors += 1
                    logger.warning("AEPD URL skipped %s: %s", url, item_exc)

            log_sync(
                conn,
                worker_name,
                "partial" if errors else "ok",
                documentos_processed=processed,
                documentos_upserted=stored,
                error_msg=f"{errors} AEPD URLs skipped" if errors else None,
                started_at=sync_start,
            )

        return {"processed": processed, "stored": stored, "errors": errors}
    except Exception as exc:
        entity_id = "aepd"
        if not handle_worker_failure(engine, "aepd", entity_id, "sync_entity", exc):
            logger.warning("Entity aepd moved to dead-letter")
            return {"processed": 0, "stored": 0, "errors": errors}
        with engine.begin() as conn:
            log_sync(
                conn,
                worker_name,
                "error",
                documentos_processed=processed,
                documentos_upserted=stored,
                error_msg=str(exc),
                started_at=sync_start,
            )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AEPD worker: sync public data protection documents"
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
    init_sentry("aepd")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-aepd-weekly")
        print(
            f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}"
        )
    else:
        print(f"Starting AEPD worker in continuous mode (interval={interval}s)")
        while True:
            touch_heartbeat()
            result = run_sync()
            print(
                f"Synced documentos={result['processed']}, almacenados={result['stored']} at {datetime.now(UTC).isoformat()}"
            )
            sleep_with_heartbeat(interval)
