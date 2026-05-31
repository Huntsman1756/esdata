"""Worker BdE — Banco de Espana.

Fuente: circulares, guias supervisoras y comunicaciones del BdE en
https://www.bde.es/. Persistencia: `documento_interpretativo` con
`tipo_fuente='bde'`. Conflict key: `referencia` UNIQUE.

Sync intervalo: semanal. Auditoria via `sync_log`.

Limitaciones conocidas:
- Algunos documentos solo en PDF; texto extraido sin layout preservado.
- Vigencia/derogacion no siempre explicita en upstream.
"""

import argparse
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import unquote, urljoin, urlparse

import httpx
from boe import _ensure_sync_log_table, log_sync
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
    get_database_url,
    get_interval_seconds,
    handle_worker_failure,
    sleep_with_heartbeat,
    touch_heartbeat,
)
from sqlalchemy import create_engine, inspect, text
from vocabulary_validation import sanitize_documento_payload

logger = logging.getLogger(__name__)

BDE_CIRCULARES_URL = (
    "https://www.bde.es/wbe/es/areas-actuacion/normativa/circulares-banco-de-espana/"
    "circulares-banco-espana-indice-cronologico/"
)
BDE_DISCOVERY_ENABLED = os.getenv("BDE_DISCOVERY_ENABLED", "true").lower() == "true"
BDE_DISCOVERY_MAX_URLS = 10
CIRCULAR_REFERENCE_RE = re.compile(r"\bCircular\s+(\d{1,3})\s*/\s*(\d{4})\b", re.IGNORECASE)


@dataclass(frozen=True)
class BDECircularLink:
    url: str
    title: str
    reference: str
    source_url: str


class _AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []
        self._current: dict[str, object] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        values = {key.lower(): value or "" for key, value in attrs}
        self._current = {
            "href": values.get("href", ""),
            "title": values.get("title", ""),
            "text_parts": [],
        }

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current["text_parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._current is None:
            return
        self.links.append(
            {
                "href": str(self._current["href"]),
                "title": str(self._current["title"]),
                "text": "".join(self._current["text_parts"]),
            }
        )
        self._current = None


def _parse_seed_urls(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


SEED_URLS = _parse_seed_urls(os.getenv("BDE_SEED_URLS"))
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning("Invalid integer for %s=%r; using %s", name, value, default)
        return default


def _is_official_bde_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return parsed.scheme == "https" and (host == "bde.es" or host.endswith(".bde.es"))


def _circular_reference(value: str) -> str | None:
    match = CIRCULAR_REFERENCE_RE.search(value)
    if not match:
        return None
    return f"Circular {int(match.group(1))}/{match.group(2)}"


def extract_bde_circular_links(
    html: str,
    base_url: str = BDE_CIRCULARES_URL,
) -> list[BDECircularLink]:
    parser = _AnchorCollector()
    parser.feed(html)
    discovered: list[BDECircularLink] = []
    seen_urls: set[str] = set()

    for link in parser.links:
        href = link["href"].strip()
        if not href:
            continue
        url = urljoin(base_url, href)
        if url in seen_urls or not _is_official_bde_url(url):
            continue
        title = _normalize_whitespace(link["text"] or link["title"])
        reference = _circular_reference(
            " ".join(
                part
                for part in (link["text"], link["title"], unquote(url))
                if part
            )
        )
        if reference is None:
            continue
        discovered.append(
            BDECircularLink(
                url=url,
                title=title or reference,
                reference=reference,
                source_url=base_url,
            )
        )
        seen_urls.add(url)

    return discovered


def discover_bde_circulars(
    client: httpx.Client,
    *,
    max_urls: int = BDE_DISCOVERY_MAX_URLS,
    discovery_url: str = BDE_CIRCULARES_URL,
) -> list[BDECircularLink]:
    if max_urls <= 0:
        return []
    response = client.get(discovery_url)
    response.raise_for_status()
    return extract_bde_circular_links(response.text, discovery_url)[:max_urls]


def _extract_reference(url: str, text_value: str) -> str:
    path_match = re.search(r"(/publi/|/doc/|/informes/)([^/]+)", url)
    if path_match:
        return f"BDE-{path_match.group(2)}"
    circular_match = _circular_reference(text_value)
    if circular_match:
        return f"BDE-{circular_match.replace('Circular ', '').replace('/', '-')}"
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


def build_document_payload(
    url: str,
    content: bytes,
    discovery_metadata: dict[str, str] | None = None,
) -> dict[str, object]:
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
        "metadata": {
            "source_url": url,
            "discovery": discovery_metadata or {},
        },
    }


def _table_columns(conn, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def upsert_documento_interpretativo(conn, payload: dict[str, object]) -> None:
    record = sanitize_documento_payload(
        {
            "tipo_documento": payload["tipo_documento"],
            "organismo_emisor": payload.get("organismo_emisor", "Banco de España"),
            "jurisdiccion": payload.get("jurisdiccion", "es"),
            "tipo_fuente": payload.get("tipo_fuente", "bde"),
            "ambito": payload["ambito"],
            "referencia": payload["referencia"],
            "fecha": payload["fecha"],
            "titulo": payload["titulo"],
            "texto": payload["texto"],
            "url_fuente": payload["url_fuente"],
        }
    )
    existing_columns = _table_columns(conn, "documento_interpretativo")
    optional_values = {}
    if "metadata" in existing_columns:
        optional_values["metadata"] = json.dumps(
            payload.get("metadata", {}),
            ensure_ascii=False,
            sort_keys=True,
        )
    record.update(optional_values)

    insert_columns = [
        "tipo_documento",
        "organismo_emisor",
        "jurisdiccion",
        "tipo_fuente",
        "ambito",
        "referencia",
        "fecha",
        "titulo",
        "texto",
        "url_fuente",
        *optional_values.keys(),
    ]
    update_columns = [
        "tipo_documento",
        "organismo_emisor",
        "ambito",
        "fecha",
        "titulo",
        "texto",
        "url_fuente",
        *optional_values.keys(),
    ]
    conn.execute(
        text(
            f"""
            INSERT INTO documento_interpretativo (
                {", ".join(insert_columns)}
            )
            VALUES (
                {", ".join(f":{column}" for column in insert_columns)}
            )
            ON CONFLICT (referencia) DO UPDATE SET
                {", ".join(f"{column} = excluded.{column}" for column in update_columns)}
            """
        ),
        record,
    )


def run_sync(  # noqa: C901 - ingestion loop keeps change detection and telemetry together.
    seed_urls: list[str] | None = None,
    worker_name: str = "worker-bde",
) -> dict[str, int]:
    import logging
    import os

    logger = logging.getLogger(__name__)
    urls = list(seed_urls) if seed_urls is not None else list(SEED_URLS)
    discovery_metadata_by_url: dict[str, dict[str, str]] = {}
    if seed_urls is None and _env_flag("BDE_DISCOVERY_ENABLED", BDE_DISCOVERY_ENABLED):
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as discovery_client:
                discovered = discover_bde_circulars(
                    discovery_client,
                    max_urls=_env_int("BDE_DISCOVERY_MAX_URLS", BDE_DISCOVERY_MAX_URLS),
                    discovery_url=os.getenv("BDE_CIRCULARES_URL", BDE_CIRCULARES_URL),
                )
            for link in discovered:
                discovery_metadata_by_url[link.url] = {
                    "source": "bde_circulars_index",
                    "source_url": link.source_url,
                    "reference": link.reference,
                    "title": link.title,
                }
                if link.url not in urls:
                    urls.append(link.url)
        except Exception as exc:
            logger.warning("BDE circular discovery skipped: %s", exc)
    if seed_urls is None and not urls:
        engine = create_engine(DATABASE_URL, future=True)
        ensure_database_connection(engine)
        message = "No BDE URLs configured or discovered; worker wrote explicit partial telemetry."
        logger.warning(message)
        with engine.begin() as conn:
            _ensure_sync_log_table(conn)
            log_sync(
                conn,
                worker_name,
                "partial",
                documentos_processed=0,
                documentos_upserted=0,
                error_msg=message,
            )
        return {"processed": 0, "stored": 0}

    if not urls:
        logger.error(
            "SEED_URLS vacío en %s — worker abortado sin ingestión. "
            "Configura la variable de entorno correspondiente.",
            worker_name,
        )
        return {"processed": 0, "stored": 0}

    request_delay = float(os.environ.get("WORKER_REQUEST_DELAY", "1.0"))
    processed = 0
    stored = 0
    errors = 0
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client, engine.begin() as conn:
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)
            for url in urls:
                try:
                    response = client.get(url)
                    response.raise_for_status()
                    payload = build_document_payload(
                        url,
                        response.content,
                        discovery_metadata_by_url.get(url),
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
                    logger.warning("BDE URL skipped %s: %s", url, item_exc)

            log_sync(
                conn,
                worker_name,
                "partial" if errors else "ok",
                documentos_processed=processed,
                documentos_upserted=stored,
                error_msg=f"{errors} BDE URLs skipped" if errors else None,
            )

        return {"processed": processed, "stored": stored}
    except Exception as exc:
        entity_id = "bde"
        if not handle_worker_failure(engine, "bde", entity_id, "sync_entity", exc):
            logger.warning("Entity bde moved to dead-letter")
            return {"processed": 0, "stored": 0}
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
            touch_heartbeat()
            result = run_sync()
            print(
                f"Synced documentos={result['processed']}, almacenados={result['stored']} at {datetime.now(UTC).isoformat()}"
            )
            sleep_with_heartbeat(interval)
