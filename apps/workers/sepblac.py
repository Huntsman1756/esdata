import argparse
import hashlib
import json
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
from sqlalchemy import create_engine, text
from vocabulary_validation import sanitize_documento_payload


def _parse_seed_urls(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


SEED_URLS = _parse_seed_urls(os.getenv("SEPBLAC_SEED_URLS"))
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)
SEPBLAC_NORMATIVA_URL = "https://www.sepblac.es/es/normativa/?lang=es"
SEPBLAC_NORMATIVA_NACIONAL_URL = "https://www.sepblac.es/es/normativa/normativa-nacional/"
SEPBLAC_NORMATIVA_COMUNITARIA_URL = "https://www.sepblac.es/es/normativa/normativa-comunitaria/"
SEPBLAC_OBLIGACIONES_URL = "https://www.sepblac.es/es/sujetos-obligados/obligaciones/"
SEPBLAC_GUIAS_URL = "https://www.sepblac.es/es/publicaciones/"
SEPBLAC_RECOMENDACIONES_CONTROL_INTERNO_URL = (
    "https://www.sepblac.es/es/publicaciones/recomendaciones-de-control-interno/"
)
SEPBLAC_MAS_PUBLICACIONES_URL = "https://www.sepblac.es/es/publicaciones/mas-publicaciones/"
SEPBLAC_TIPOLOGIAS_URL = "https://www.sepblac.es/es/documentacion/"
DEFAULT_SOURCE_URLS = [
    SEPBLAC_NORMATIVA_URL,
    SEPBLAC_NORMATIVA_NACIONAL_URL,
    SEPBLAC_NORMATIVA_COMUNITARIA_URL,
    SEPBLAC_OBLIGACIONES_URL,
]
SEPBLAC_FAMILY_MAP = {
    "normativa": {
        "tipo_documento": "normativa_sepblac",
        "source_urls": [
            SEPBLAC_NORMATIVA_URL,
            SEPBLAC_NORMATIVA_NACIONAL_URL,
            SEPBLAC_NORMATIVA_COMUNITARIA_URL,
        ],
        "tokens": ("normativa", "ley", "real-decreto", "reglamento", ".pdf"),
    },
    "obligaciones": {
        "tipo_documento": "obligacion_sepblac",
        "source_urls": [SEPBLAC_OBLIGACIONES_URL],
        "tokens": ("obligacion", "obligaciones", "sujetos-obligados"),
    },
    "guias": {
        "tipo_documento": "guia_operativa_sepblac",
        "source_urls": [
            SEPBLAC_GUIAS_URL,
            SEPBLAC_RECOMENDACIONES_CONTROL_INTERNO_URL,
            SEPBLAC_MAS_PUBLICACIONES_URL,
        ],
        "tokens": (
            "guia",
            "guía",
            "orientacion",
            "orientación",
            "manual",
            "recomendacion",
            "recomendación",
            "control interno",
            "publicaciones",
            ".pdf",
        ),
    },
    "tipologias": {
        "tipo_documento": "tipologia_sepblac",
        "source_urls": [SEPBLAC_TIPOLOGIAS_URL],
        "tokens": ("tipologia", "tipología", "operaciones-sospechosas", ".pdf"),
    },
}
SEPBLAC_FAMILY_ALIASES = {
    "normativa_sepblac": "normativa",
    "obligacion_sepblac": "obligaciones",
    "obligacion": "obligaciones",
    "guia_operativa_sepblac": "guias",
    "guia": "guias",
    "tipologia_sepblac": "tipologias",
    "tipologia": "tipologias",
}


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _resolve_family(familia: str | None) -> str | None:
    if not familia:
        return None
    normalized = familia.strip().lower()
    normalized = SEPBLAC_FAMILY_ALIASES.get(normalized, normalized)
    if normalized not in SEPBLAC_FAMILY_MAP:
        raise ValueError(f"Unsupported SEPBLAC family: {familia}")
    return normalized


def _stable_reference(url: str, tipo_documento: str) -> str:
    digest = hashlib.sha256(f"sepblac|{tipo_documento}|{url}".encode("utf-8")).hexdigest()[:16]
    return f"SEPBLAC-{tipo_documento.upper()}-{digest}"


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
    if "sujetos obligados" in lowered or "obligaciones" in lowered:
        return "obligacion_sepblac"
    if "modelo 19" in lowered:
        return "formulario_sepblac"
    if "manual" in lowered:
        return "manual_sepblac"
    if "comunicación por indicio" in lowered or "comunicacion por indicio" in lowered:
        return "guia_operativa_sepblac"
    if "ley 10/2010" in lowered or "real decreto 304/2014" in lowered:
        return "normativa_sepblac"
    return "documento_sepblac"


def _detect_sujeto_obligado(url: str, text_value: str) -> str:
    normalized = f"{url} {text_value}".lower()
    mappings = [
        ("sociedad_valores", ("sociedad de valores", "sociedades-valores", "empresas de servicios de inversion")),
        ("agencia_valores", ("agencia de valores", "agencias-valores")),
        ("entidad_credito", ("entidad de credito", "entidades de credito", "entidades-credito", "bancos")),
        ("sgiic", ("sgiic", "sociedades gestoras de instituciones de inversion colectiva")),
        ("eaf", ("eaf", "empresa de asesoramiento financiero")),
        ("aseguradora", ("aseguradora", "seguros")),
        ("notario", ("notario", "notarial")),
        ("abogado", ("abogado", "abogacia")),
        ("empresa_servicios_pago", ("servicios de pago", "medios-de-pago", "dinero electronico")),
    ]
    for value, tokens in mappings:
        if any(token in normalized for token in tokens):
            return value
    return "all"


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


def _absolute_sepblac_url(base_url: str, href: str) -> str:
    if href.startswith("//"):
        return "https:" + href
    return urljoin(base_url, href)


def _is_official_sepblac_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return host.endswith("sepblac.es")


def _source_urls_for_family(familia: str | None) -> list[str]:
    resolved = _resolve_family(familia)
    if not resolved:
        return DEFAULT_SOURCE_URLS
    return list(SEPBLAC_FAMILY_MAP[resolved]["source_urls"])


def discover_default_urls(max_urls: int = 200, familia: str | None = None) -> list[str]:
    """Discover official SEPBLAC documents from normative and obligation pages."""
    discovered: list[str] = []
    seen: set[str] = set()
    resolved_family = _resolve_family(familia)
    family_tokens = (
        SEPBLAC_FAMILY_MAP[resolved_family]["tokens"]
        if resolved_family
        else ("normativa", "ley", "real-decreto", "reglamento", "obligacion", "guia", ".pdf")
    )

    def add(url: str) -> None:
        if url not in seen and _is_official_sepblac_url(url):
            seen.add(url)
            discovered.append(url)

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for source_url in _source_urls_for_family(resolved_family):
            add(source_url)
            try:
                response = client.get(source_url)
                if response.status_code != 200:
                    continue
            except Exception:
                continue

            html = response.text
            for match in re.finditer(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", html, flags=re.IGNORECASE | re.DOTALL):
                href, raw_label = match.groups()
                label = extract_html_text(raw_label.encode("utf-8", errors="ignore")).lower()
                if not any(token in f"{href} {label}".lower() for token in family_tokens):
                    continue
                add(_absolute_sepblac_url(source_url, href.strip()))
                if len(discovered) >= max_urls:
                    return discovered

    return discovered


def extract_text(content: bytes, content_type: str, url: str) -> str:
    if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
        try:
            return extract_pdf_text(content)
        except Exception:
            if "pdf" in content_type.lower():
                raise
    return extract_html_text(content)


def build_document_payload(
    url: str,
    content: bytes,
    content_type: str,
    *,
    familia: str | None = None,
) -> dict[str, str | bool]:
    text_value = extract_text(content, content_type, url)
    if not text_value:
        raise ValueError(f"Could not extract text from SEPBLAC document: {url}")

    first_line = next((line.strip() for line in text_value.splitlines() if line.strip()), "")
    resolved_family = _resolve_family(familia)
    tipo_documento = (
        SEPBLAC_FAMILY_MAP[resolved_family]["tipo_documento"]
        if resolved_family
        else _detect_document_type(text_value)
    )
    referencia = _stable_reference(url, tipo_documento) if resolved_family else _extract_reference(url, text_value)
    sujeto_obligado = (
        _detect_sujeto_obligado(url, text_value)
        if tipo_documento == "obligacion_sepblac"
        else None
    )

    payload: dict[str, str | bool] = {
        "referencia": referencia,
        "fecha": datetime.now(UTC).date().isoformat(),
        "titulo": first_line or referencia,
        "texto": text_value,
        "url_fuente": url,
        "tipo_documento": tipo_documento,
        "ambito": "aml_cft" if resolved_family else _detect_ambito(text_value),
        "source_url": url,
        "capture_date": datetime.now(UTC).date().isoformat(),
        "verified": _is_official_sepblac_url(url),
        "row_completeness": "complete",
        "row_provenance": "official_exact" if _is_official_sepblac_url(url) else "unverified",
    }
    if sujeto_obligado:
        payload["sujeto_obligado"] = sujeto_obligado
    return payload


def _documento_columns(conn) -> set[str]:
    dialect_name = conn.dialect.name
    if dialect_name == "sqlite":
        rows = conn.execute(text("PRAGMA table_info(documento_interpretativo)")).fetchall()
        return {row[1] for row in rows}
    rows = conn.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'documento_interpretativo'
            """
        )
    ).fetchall()
    return {row[0] for row in rows}


def upsert_documento_interpretativo(conn, payload: dict[str, str | bool]) -> None:
    metadata = {
        "source_url": payload.get("source_url") or payload["url_fuente"],
        "capture_date": payload.get("capture_date"),
        "verified": payload.get("verified", False),
        "sujeto_obligado": payload.get("sujeto_obligado"),
    }
    record = sanitize_documento_payload(
        {
            "tipo_documento": payload["tipo_documento"],
            "organismo_emisor": payload.get("organismo_emisor", "SEPBLAC"),
            "jurisdiccion": payload.get("jurisdiccion", "es"),
            "tipo_fuente": payload.get("tipo_fuente", "sepblac"),
            "ambito": payload["ambito"],
            "referencia": payload["referencia"],
            "fecha": payload["fecha"],
            "titulo": payload["titulo"],
            "texto": payload["texto"],
            "url_fuente": payload["url_fuente"],
        }
    )
    columns = _documento_columns(conn)
    optional_values = {}
    if "metadata" in columns:
        optional_values["metadata"] = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
    if "row_completeness" in columns:
        optional_values["row_completeness"] = payload.get("row_completeness", "complete")
    if "row_provenance" in columns:
        optional_values["row_provenance"] = payload.get("row_provenance", "official_exact")
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


def run_sync(
    seed_urls: list[str] | None = None,
    worker_name: str = "worker-sepblac",
    *,
    familia: str | None = None,
    max_urls: int = 200,
) -> dict[str, int]:
    import logging
    import os

    logger = logging.getLogger(__name__)
    if seed_urls is not None:
        urls = seed_urls
    else:
        urls = SEED_URLS if not familia and SEED_URLS else discover_default_urls(max_urls=max_urls, familia=familia)
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
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client, engine.begin() as conn:
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)
            for url in urls:
                response = client.get(url)
                response.raise_for_status()
                payload = build_document_payload(
                    url,
                    response.content,
                    response.headers.get("content-type", ""),
                    familia=familia,
                )
                processed += 1

                change = check_content_changed(
                    conn, worker_name, "documento", payload["referencia"], payload["texto"]
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
                    payload["texto"],
                )
                stored += 1
                time.sleep(request_delay)

            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=processed,
                documentos_upserted=stored,
            )

        return {"processed": processed, "stored": stored}
    except Exception as exc:
        entity_id = "sepblac"
        if not handle_worker_failure(engine, "sepblac", entity_id, "sync_entity", exc):
            logger.warning("Entity sepblac moved to dead-letter")
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
    parser.add_argument(
        "--familia",
        choices=["normativa", "obligaciones", "guias", "tipologias"],
        default=None,
        help="SEPBLAC source family to sync separately",
    )
    parser.add_argument(
        "--max-urls",
        type=int,
        default=200,
        help="Maximum discovered URLs to process when using family discovery",
    )
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("sepblac")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(
            worker_name="cron-sepblac-weekly",
            familia=args.familia,
            max_urls=args.max_urls,
        )
        print(
            f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}"
        )
    else:
        print(f"Starting SEPBLAC worker in continuous mode (interval={interval}s)")
        while True:
            touch_heartbeat()
            result = run_sync(familia=args.familia, max_urls=args.max_urls)
            print(
                f"Synced documentos={result['processed']}, almacenados={result['stored']} at {datetime.now(UTC).isoformat()}"
            )
            sleep_with_heartbeat(interval)
