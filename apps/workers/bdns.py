import argparse
import json
import logging
import os
import re
import time
from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse

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
from sqlalchemy import create_engine, inspect, text
from vocabulary_validation import sanitize_documento_payload

logger = logging.getLogger(__name__)


def _parse_seed_urls(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


SEED_URLS = _parse_seed_urls(os.getenv("BDNS_SEED_URLS"))
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)
BDNS_API_BASE_URL = "https://www.infosubvenciones.es/bdnstrans/api"
BDNS_PUBLIC_BASE_URL = "https://www.infosubvenciones.es/bdnstrans/GE/es"
BDNS_STRUCTURED_ENDPOINTS = _parse_seed_urls(os.getenv("BDNS_STRUCTURED_ENDPOINTS"))
BDNS_ENDPOINT_CONFIG = {
    "convocatoria": {
        "path": "/convocatorias/busqueda",
        "kind": "convocatoria",
        "params": {"vpd": "GE", "order": "fechaRecepcion", "direccion": "desc"},
    },
    "concesion": {
        "path": "/concesiones/busqueda",
        "kind": "concesion",
        "params": {"vpd": "GE"},
    },
    "minimis": {
        "path": "/minimis/busqueda",
        "kind": "concesion",
        "params": {"vpd": "GE"},
    },
    "ayudas_estado": {
        "path": "/ayudasestado/busqueda",
        "kind": "concesion",
        "params": {"vpd": "GE"},
    },
    "grandes_beneficiarios": {
        "path": "/grandesbeneficiarios/busqueda",
        "kind": "concesion",
        "params": {"vpd": "GE"},
    },
    "partidos_politicos": {
        "path": "/partidospoliticos/busqueda",
        "kind": "concesion",
        "params": {"vpd": "GE"},
    },
    "sanciones": {
        "path": "/sanciones/busqueda",
        "kind": "concesion",
        "params": {"vpd": "GE"},
    },
}


def _extract_convocatoria_id(url: str) -> str | None:
    match = re.search(r"/convocatoria/(\d+)", url)
    if not match:
        return None
    return match.group(1)


def _extract_document_id(url: str) -> str | None:
    match = re.search(r"/document/(\d+)", url)
    if not match:
        return None
    return match.group(1)


def _build_referencia(url: str) -> str:
    convocatoria_id = _extract_convocatoria_id(url)
    document_id = _extract_document_id(url)
    if convocatoria_id and document_id:
        return f"BDNS-{convocatoria_id}-{document_id}"
    if convocatoria_id:
        return f"BDNS-{convocatoria_id}"

    path = urlparse(url).path.rstrip("/").split("/")[-1]
    return f"BDNS-{path or 'seed'}"


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    chunks = []
    for page in reader.pages:
        text_value = page.extract_text() or ""
        cleaned = _normalize_whitespace(text_value)
        if cleaned:
            chunks.append(cleaned)
    return "\n".join(chunks)


def build_document_payload(url: str, content: bytes) -> dict[str, str]:
    text_value = extract_pdf_text(content)
    if not text_value:
        raise ValueError(f"Could not extract text from BDNS document: {url}")

    first_line = next((line.strip() for line in text_value.splitlines() if line.strip()), "")
    referencia = _build_referencia(url)
    convocatoria_id = _extract_convocatoria_id(url)
    title_bits = [bit for bit in [f"Convocatoria {convocatoria_id}" if convocatoria_id else None, first_line] if bit]

    return {
        "referencia": referencia,
        "fecha": datetime.utcnow().date().isoformat(),
        "titulo": " - ".join(title_bits) or referencia,
        "texto": text_value,
        "url_fuente": url,
    }


def _first_text(*values: object) -> str | None:
    for value in values:
        if value is None:
            continue
        text_value = str(value).strip()
        if text_value:
            return text_value
    return None


def _compact_metadata(raw: dict, endpoint: str) -> dict[str, object]:
    metadata: dict[str, object] = {
        "bdns_endpoint": endpoint,
        "source_api_base": BDNS_API_BASE_URL,
    }
    mapping = {
        "id": "id_interno",
        "numeroConvocatoria": "numero_convocatoria",
        "codConcesion": "codigo_concesion",
        "beneficiario": "beneficiario",
        "instrumento": "instrumento",
        "importe": "importe",
        "ayudaEquivalente": "ayuda_equivalente",
        "nivel1": "nivel_administracion",
        "nivel2": "administracion",
        "nivel3": "organo",
        "mrr": "mrr",
        "codigoInvente": "codigo_invente",
        "idConvocatoria": "id_convocatoria",
        "idPersona": "id_persona",
        "fechaAlta": "fecha_alta",
        "urlBR": "url_bases_reguladoras",
    }
    for source_key, target_key in mapping.items():
        if source_key in raw and raw[source_key] not in (None, ""):
            metadata[target_key] = raw[source_key]
    return metadata


def normalize_bdns_api_item(raw: dict, endpoint: str) -> dict[str, object]:
    """Normalize one official BDNS API item to ESData's document payload shape."""
    endpoint = endpoint.strip().lower()
    numero_convocatoria = _first_text(raw.get("numeroConvocatoria"), raw.get("codigoBDNS"))

    if endpoint == "convocatoria":
        natural_id = numero_convocatoria or _first_text(raw.get("id")) or "unknown"
        referencia = f"BDNS-CONVOCATORIA-{natural_id}"
        tipo_documento = "convocatoria_bdns"
        titulo = _first_text(raw.get("descripcion"), raw.get("descripcionLeng"), referencia)
        fecha = _first_text(raw.get("fechaRecepcion"), raw.get("fechaAlta"))
        url_fuente = (
            f"{BDNS_PUBLIC_BASE_URL}/convocatoria/{natural_id}"
            if numero_convocatoria
            else f"{BDNS_API_BASE_URL}/convocatorias?id={natural_id}"
        )
    elif endpoint == "concesion":
        codigo_concesion = _first_text(raw.get("codConcesion"), raw.get("id")) or "unknown"
        referencia = f"BDNS-CONCESION-{codigo_concesion}"
        tipo_documento = "concesion_bdns"
        titulo = _first_text(raw.get("convocatoria"), raw.get("descripcionCooficial"), referencia)
        fecha = _first_text(raw.get("fechaConcesion"), raw.get("fechaAlta"))
        url_fuente = (
            f"{BDNS_PUBLIC_BASE_URL}/convocatoria/{numero_convocatoria}"
            if numero_convocatoria
            else f"{BDNS_API_BASE_URL}/concesiones/busqueda"
        )
    else:
        raise ValueError(f"Unsupported BDNS endpoint type: {endpoint}")

    organismo = " - ".join(
        value
        for value in (
            _first_text(raw.get("nivel1")),
            _first_text(raw.get("nivel2")),
            _first_text(raw.get("nivel3")),
        )
        if value
    )

    metadata = _compact_metadata(raw, endpoint)
    if numero_convocatoria:
        metadata["numero_convocatoria"] = numero_convocatoria

    return {
        "referencia": referencia,
        "tipo_documento": tipo_documento,
        "fecha": fecha or datetime.utcnow().date().isoformat(),
        "titulo": titulo,
        "url_fuente": url_fuente,
        "organismo": organismo,
        "metadata": metadata,
    }


def build_bdns_text_payload(item: dict[str, object]) -> str:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    lines = [
        f"Referencia: {item.get('referencia', '')}",
        f"Tipo: {item.get('tipo_documento', '')}",
        f"Titulo: {item.get('titulo', '')}",
        f"Fecha: {item.get('fecha', '')}",
    ]
    if item.get("organismo"):
        lines.append(f"Organismo: {item['organismo']}")
    if metadata.get("beneficiario"):
        lines.append(f"Beneficiario: {metadata['beneficiario']}")
    if "importe" in metadata:
        lines.append(f"Importe: {metadata['importe']}")
    if metadata.get("instrumento"):
        lines.append(f"Instrumento: {metadata['instrumento']}")
    if metadata.get("numero_convocatoria"):
        lines.append(f"Numero convocatoria: {metadata['numero_convocatoria']}")
    if metadata.get("url_bases_reguladoras"):
        lines.append(f"Bases reguladoras: {metadata['url_bases_reguladoras']}")
    lines.append(f"URL oficial: {item.get('url_fuente', '')}")
    return "\n".join(line for line in lines if line.strip())


def build_structured_payload(item: dict[str, object]) -> dict[str, object]:
    return {
        "tipo_documento": str(item["tipo_documento"]),
        "organismo_emisor": "BDNS",
        "jurisdiccion": "es",
        "tipo_fuente": "bdns",
        "ambito": "subvenciones",
        "referencia": str(item["referencia"]),
        "fecha": str(item["fecha"]),
        "titulo": str(item["titulo"]),
        "texto": build_bdns_text_payload(item),
        "url_fuente": str(item["url_fuente"]),
        "metadata": item.get("metadata", {}),
        "row_completeness": "partial",
        "row_provenance": "official_exact",
    }


def fetch_structured_bdns_items(
    client: httpx.Client,
    endpoint: str,
    *,
    max_pages: int,
    page_size: int,
) -> list[dict[str, object]]:
    config = BDNS_ENDPOINT_CONFIG.get(endpoint)
    if not config:
        raise ValueError(f"Unsupported structured BDNS endpoint: {endpoint}")

    items: list[dict[str, object]] = []
    for page in range(max_pages):
        params = {
            **config["params"],
            "page": page,
            "pageSize": page_size,
        }
        response = client.get(f"{BDNS_API_BASE_URL}{config['path']}", params=params)
        response.raise_for_status()
        page_payload = response.json()
        content = page_payload.get("content", []) if isinstance(page_payload, dict) else []
        if not content:
            break
        for raw_item in content:
            if isinstance(raw_item, dict):
                items.append(normalize_bdns_api_item(raw_item, str(config["kind"])))
        if bool(page_payload.get("last")):
            break
    return items


def _table_columns(conn, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def upsert_documento_interpretativo(conn, payload: dict[str, object]) -> None:
    record = sanitize_documento_payload(
        {
            "tipo_documento": payload.get("tipo_documento", "convocatoria_subvencion"),
            "organismo_emisor": payload.get("organismo_emisor", "BDNS"),
            "jurisdiccion": payload.get("jurisdiccion", "es"),
            "tipo_fuente": payload.get("tipo_fuente", "bdns"),
            "ambito": payload.get("ambito", "subvenciones"),
            "referencia": payload["referencia"],
            "fecha": payload["fecha"],
            "titulo": payload["titulo"],
            "texto": payload["texto"],
            "url_fuente": payload["url_fuente"],
            "metadata": json.dumps(payload.get("metadata", {}), ensure_ascii=False, sort_keys=True),
            "row_completeness": payload.get("row_completeness", "partial"),
            "row_provenance": payload.get("row_provenance", "official_best_effort"),
        }
    )
    existing_columns = _table_columns(conn, "documento_interpretativo")
    columns = [
        column
        for column in (
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
            "metadata",
            "row_completeness",
            "row_provenance",
        )
        if column in existing_columns
    ]
    update_columns = [
        column
        for column in (
            "fecha",
            "titulo",
            "texto",
            "url_fuente",
            "metadata",
            "row_completeness",
            "row_provenance",
        )
        if column in existing_columns
    ]
    column_sql = ",\n                ".join(columns)
    values_sql = ",\n                ".join(f":{column}" for column in columns)
    update_sql = ",\n                ".join(
        f"{column} = excluded.{column}" for column in update_columns
    )
    conn.execute(
        text(
            f"""
            INSERT INTO documento_interpretativo (
                {column_sql}
            )
            VALUES (
                {values_sql}
            )
            ON CONFLICT (referencia) DO UPDATE SET
                {update_sql}
            """
        ),
        {column: record[column] for column in columns},
    )


def run_sync(
    seed_urls: list[str] | None = None,
    worker_name: str = "worker-bdns",
    structured_endpoints: list[str] | None = None,
    max_pages: int | None = None,
    page_size: int | None = None,
) -> dict[str, int]:
    import logging
    import os

    logger = logging.getLogger(__name__)
    urls = seed_urls if seed_urls is not None else SEED_URLS
    endpoints = (
        structured_endpoints
        if structured_endpoints is not None
        else BDNS_STRUCTURED_ENDPOINTS
    )
    if not urls and not endpoints:
        logger.error(
            "SEED_URLS vacío en %s — worker abortado sin ingestión. "
            "Configura la variable de entorno correspondiente.",
            worker_name,
        )
        return {"processed": 0, "stored": 0}

    request_delay = float(os.environ.get("WORKER_REQUEST_DELAY", "1.0"))
    structured_max_pages = max_pages or int(os.environ.get("BDNS_MAX_PAGES", "1"))
    structured_page_size = page_size or int(os.environ.get("BDNS_PAGE_SIZE", "100"))
    processed = 0
    stored = 0
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client, engine.begin() as conn:
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)
            for endpoint in endpoints:
                for item in fetch_structured_bdns_items(
                    client,
                    endpoint,
                    max_pages=structured_max_pages,
                    page_size=structured_page_size,
                ):
                    payload = build_structured_payload(item)
                    processed += 1
                    content = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()

                    change = check_content_changed(
                        conn, worker_name, "documento", payload["referencia"], content
                    )

                    if not change.changed and destination_row_exists(
                        conn,
                        "documento_interpretativo",
                        "referencia",
                        payload["referencia"],
                    ):
                        print(f"  [SKIP] {payload['referencia']} unchanged")
                        continue

                    invalidated = invalidate_old_embeddings(conn, str(payload["referencia"]))
                    if invalidated:
                        print(
                            f"  [INVALIDATE] {invalidated} old embeddings for {payload['referencia']}"
                        )

                    upsert_documento_interpretativo(conn, payload)
                    record_revision(
                        conn,
                        worker_name,
                        "documento",
                        str(payload["referencia"]),
                        content,
                    )
                    stored += 1
                    time.sleep(request_delay)

            for url in urls:
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

            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=processed,
                documentos_upserted=stored,
            )

        return {"processed": processed, "stored": stored}
    except Exception as exc:
        entity_id = "bdns"
        if not handle_worker_failure(engine, "bdns", entity_id, "sync_entity", exc):
            logger.warning("Entity bdns moved to dead-letter")
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
        description="BDNS worker: sync public subsidy calls from BDNS documents"
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
    init_sentry("bdns")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-bdns-weekly")
        print(
            f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}"
        )
    else:
        print(f"Starting BDNS worker in continuous mode (interval={interval}s)")
        while True:
            touch_heartbeat()
            result = run_sync()
            print(
                f"Synced convocatorias={result['processed']}, almacenadas={result['stored']} at {datetime.utcnow().isoformat()}"
            )
            sleep_with_heartbeat(interval)
