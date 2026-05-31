"""Worker BORME — Boletin Oficial del Registro Mercantil.

Fuente: anuncios de actos inscribibles publicados en BORME via
https://www.boe.es/diario_borme/. Persistencia: `documento_interpretativo`
con `tipo_fuente='borme'`. Conflict key: `referencia` UNIQUE.

Sync intervalo: diario. Auditoria via `sync_log`.

Limitaciones conocidas:
- Estructura por seccion/provincia; parser tolerante a discrepancias de
  formato. Anuncios sin denominacion social estable se marcan `[PARTIAL]`.
"""

import argparse
import json
import logging
import os
import re
import time
from datetime import UTC, date, datetime, timedelta
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

logger = logging.getLogger(__name__)

EVENT_PATTERNS = [
    ("nombramiento", r"\bNombramientos?\b"),
    ("cese", r"\bCeses?\b"),
    ("constitucion", r"\bConstituci[oó]n\b"),
    ("cambio_domicilio", r"\bDomicilio\b"),
    ("ampliacion_capital", r"\bAmpliaci[oó]n de capital\b"),
    ("reduccion_capital", r"\bReducci[oó]n de capital\b"),
    ("disolucion", r"\bDisoluci[oó]n\b"),
    ("concurso", r"\bConcurso\b"),
]

COMPANY_SUFFIXES = r"(?:S\.L\.|SL|S\.A\.|SA|S\.L|S\.A|SOCIEDAD LIMITADA|SOCIEDAD ANONIMA)"
ROLE_PATTERNS = [
    ("absorbente", r"\(([Ss]ociedad absorbente)\)"),
    ("absorbida", r"\(([Ss]ociedad absorbida)\)"),
    ("beneficiaria", r"\(([Ss]ociedades? beneficiarias?)\)"),
    ("escindida", r"\(([Ss]ociedad totalmente escindida)\)"),
]
APPOINTMENT_ROLE_PATTERNS = [
    ("administrador_unico", r"\bAdm\.\s*Unico:\s*([^\.]+)"),
    ("administrador_solidario", r"\bAdm\.\s*Solid\.\s*:\s*([^\.]+)"),
    ("administrador_mancomunado", r"\bAdm\.\s*Mancom\.\s*:\s*([^\.]+)"),
    ("consejero", r"\bConsejero:\s*([^\.]+)"),
    ("presidente", r"\bPresidente:\s*([^\.]+)"),
    ("secretario", r"\bSecretario:\s*([^\.]+)"),
    ("apoderado", r"\bApoderad[oa]:\s*([^\.]+)"),
]


def _parse_seed_urls(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


SEED_URLS = _parse_seed_urls(os.getenv("BORME_SEED_URLS"))
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)
BORME_SUMMARY_API_BASE = "https://www.boe.es/datosabiertos/api/borme/sumario"
DEFAULT_BORME_DAYS_BACK = 7
DEFAULT_BORME_MAX_URLS_PER_RUN = 50


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


def _extract_pdf_code(url: str) -> str:
    match = re.search(r"/(BORME-[A-Z]-\d{4}-\d+-\d+)\.pdf$", url)
    if match:
        return match.group(1)

    path = urlparse(url).path.rstrip("/").split("/")[-1]
    return path.removesuffix(".pdf") or "BORME-SEED"


def _is_official_borme_pdf_url(value: str) -> bool:
    parsed = urlparse(value)
    return (
        parsed.scheme in {"http", "https"}
        and parsed.netloc in {"www.boe.es", "boe.es"}
        and parsed.path.startswith("/borme/")
        and parsed.path.endswith(".pdf")
    )


def _extract_borme_pdf_urls_from_summary(payload: object) -> list[str]:
    """Extract individual BORME document PDFs from BOE's official summary JSON."""
    urls: list[str] = []
    seen: set[str] = set()

    def visit(node: object, current_identifier: str | None = None) -> None:
        if isinstance(node, dict):
            identifier = node.get("identificador")
            if not isinstance(identifier, str):
                identifier = current_identifier

            url_pdf = node.get("url_pdf")
            candidate = None
            if isinstance(url_pdf, dict):
                texto = url_pdf.get("texto")
                if isinstance(texto, str):
                    candidate = texto
            elif isinstance(url_pdf, str):
                candidate = url_pdf

            if (
                candidate
                and _is_official_borme_pdf_url(candidate)
                and not str(identifier or "").startswith("BORME-S-")
                and candidate not in seen
            ):
                seen.add(candidate)
                urls.append(candidate)

            for value in node.values():
                visit(value, identifier)
            return

        if isinstance(node, list):
            for item in node:
                visit(item, current_identifier)

    visit(payload)
    return urls


def discover_borme_pdf_urls(
    client: httpx.Client,
    *,
    days_back: int,
    max_urls: int,
    today: date | None = None,
) -> list[str]:
    """Discover recent BORME PDFs through BOE's official open-data summary API."""
    if days_back <= 0 or max_urls <= 0:
        return []

    discovered: list[str] = []
    seen: set[str] = set()
    reference_date = today or datetime.now(UTC).date()

    for offset in range(days_back):
        day = reference_date - timedelta(days=offset)
        url = f"{BORME_SUMMARY_API_BASE}/{day:%Y%m%d}"
        try:
            response = client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.warning("BORME summary discovery skipped %s: %s", day.isoformat(), exc)
            continue

        status = payload.get("status", {}) if isinstance(payload, dict) else {}
        if isinstance(status, dict) and str(status.get("code")) != "200":
            logger.warning("BORME summary returned non-ok status for %s: %s", day.isoformat(), status)
            continue

        for pdf_url in _extract_borme_pdf_urls_from_summary(payload):
            if pdf_url in seen:
                continue
            seen.add(pdf_url)
            discovered.append(pdf_url)
            if len(discovered) >= max_urls:
                return discovered

    return discovered


def _detect_event_type(text_value: str) -> str:
    for event_type, pattern in EVENT_PATTERNS:
        if re.search(pattern, text_value, flags=re.IGNORECASE):
            return event_type
    return "acto_societario"


def _extract_company_name(text_value: str) -> str | None:
    patterns = [
        rf"\bConstituci[oó]n\.\s*([A-Z0-9ÁÉÍÓÚÑ .,\-]+?\s+{COMPANY_SUFFIXES})\b",
        rf"\b([A-Z0-9ÁÉÍÓÚÑ .,\-]+?\s+{COMPANY_SUFFIXES})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text_value, flags=re.IGNORECASE)
        if match:
            return _normalize_whitespace(match.group(1)).strip(" .,")
    return None


def _dedupe_company_entries(entries: list[dict[str, str | float | None]]) -> list[dict[str, str | float | None]]:
    deduped: list[dict[str, str | float | None]] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        nombre = str(entry["nombre"])
        rol = str(entry["rol"])
        key = (nombre, rol)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def _extract_related_companies(text_value: str) -> list[dict[str, str | float | None]]:
    entries: list[dict[str, str | float | None]] = []

    primary_name = _extract_company_name(text_value)
    if primary_name:
        entries.append(
            {
                "nombre": primary_name,
                "domicilio": _extract_domicilio(text_value),
                "rol": "principal",
                "confianza_extraccion": 0.85,
                "nota": "Extraccion heuristica desde BORME",
            }
        )

    company_pattern = rf"([A-Z0-9ÁÉÍÓÚÑ .,\-]+?\s+{COMPANY_SUFFIXES})\s*\(([^\)]+)\)"
    for match in re.finditer(company_pattern, text_value, flags=re.IGNORECASE):
        nombre = _normalize_whitespace(match.group(1)).strip(" .,")
        role_context = match.group(2)
        role = "relacionada"
        for candidate_role, role_pattern in ROLE_PATTERNS:
            if re.search(role_pattern, f"({role_context})", flags=re.IGNORECASE):
                role = candidate_role
                break
        entries.append(
            {
                "nombre": nombre,
                "domicilio": None,
                "rol": role,
                "confianza_extraccion": 0.7,
                "nota": f"Extraccion heuristica desde BORME: {role_context}",
            }
        )

    return _dedupe_company_entries(entries)


def _extract_person_appointments(text_value: str) -> list[dict[str, str | float | None]]:
    appointments: list[dict[str, str | float | None]] = []
    seen: set[tuple[str, str]] = set()
    for cargo, pattern in APPOINTMENT_ROLE_PATTERNS:
        for match in re.finditer(pattern, text_value, flags=re.IGNORECASE):
            raw_names = match.group(1)
            for raw_name in re.split(r"\s*;\s*|\s*,\s*(?=[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ ]{3,})", raw_names):
                nombre = _normalize_whitespace(raw_name).strip(" .,:;")
                if not nombre:
                    continue
                key = (nombre.upper(), cargo)
                if key in seen:
                    continue
                seen.add(key)
                appointments.append(
                    {
                        "nombre": nombre,
                        "cargo": cargo,
                        "confianza_extraccion": 0.72,
                        "nota": "Extraccion heuristica desde BORME",
                    }
                )
    return appointments


def _extract_domicilio(text_value: str) -> str | None:
    match = re.search(r"\bDomicilio:\s*([^\.]+)", text_value, flags=re.IGNORECASE)
    if not match:
        return None
    return _normalize_whitespace(match.group(1)).strip(" .,")


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
        raise ValueError(f"Could not extract text from BORME document: {url}")

    referencia = _extract_pdf_code(url)
    first_line = next((line.strip() for line in text_value.splitlines() if line.strip()), "")
    event_type = _detect_event_type(text_value)
    empresas = _extract_related_companies(text_value)
    appointments = _extract_person_appointments(text_value)
    title_bits = [bit for bit in [referencia, first_line] if bit]

    return {
        "referencia": referencia,
        "fecha": datetime.now(UTC).date().isoformat(),
        "titulo": " - ".join(title_bits) or referencia,
        "texto": text_value,
        "url_fuente": url,
        "tipo_documento": event_type,
        "empresa_nombre": _extract_company_name(text_value),
        "empresa_domicilio": _extract_domicilio(text_value),
        "empresas": empresas,
        "metadata": {
            "source_kind": "official_borme_pdf",
            "parser": "esdata_borme_pdf_heuristic",
            "companies_extracted": len(empresas),
            "appointments": appointments,
        },
        "row_completeness": "partial",
        "row_provenance": "official_best_effort",
    }


def _table_columns(conn, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def upsert_documento_interpretativo(conn, payload: dict[str, object]) -> None:
    record = {
        "tipo_documento": payload["tipo_documento"],
        "referencia": payload["referencia"],
        "fecha": payload["fecha"],
        "titulo": payload["titulo"],
        "texto": payload["texto"],
        "url_fuente": payload["url_fuente"],
        "metadata": json.dumps(payload.get("metadata", {}), ensure_ascii=False, sort_keys=True),
        "row_completeness": payload.get("row_completeness", "partial"),
        "row_provenance": payload.get("row_provenance", "official_best_effort"),
    }
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
    values = {
        **record,
        "organismo_emisor": "BORME",
        "jurisdiccion": "es",
        "tipo_fuente": "borme",
        "ambito": "mercantil",
    }
    update_columns = [
        column
        for column in (
            "tipo_documento",
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
        {column: values[column] for column in columns},
    )


def upsert_empresa(conn, payload: dict[str, str]) -> int | None:
    nombre = payload.get("empresa_nombre")
    if not nombre:
        return None

    conn.execute(
        text(
            """
            INSERT INTO empresa (nombre, nif, domicilio, fuente_inicial)
            VALUES (:nombre, NULL, :domicilio, 'BORME')
            ON CONFLICT (nombre) DO UPDATE SET
                domicilio = COALESCE(excluded.domicilio, empresa.domicilio)
            """
        ),
        {"nombre": nombre, "domicilio": payload.get("empresa_domicilio")},
    )

    row = conn.execute(
        text("SELECT id FROM empresa WHERE nombre = :nombre LIMIT 1"),
        {"nombre": nombre},
    ).fetchone()
    return row[0] if row else None


def upsert_empresas(conn, payload: dict[str, object]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for company in payload.get("empresas", []):
        nombre = company.get("nombre")
        if not nombre:
            continue
        conn.execute(
            text(
                """
                INSERT INTO empresa (nombre, nif, domicilio, fuente_inicial)
                VALUES (:nombre, NULL, :domicilio, 'BORME')
                ON CONFLICT (nombre) DO UPDATE SET
                    domicilio = COALESCE(excluded.domicilio, empresa.domicilio)
                """
            ),
            {"nombre": nombre, "domicilio": company.get("domicilio")},
        )
        row = conn.execute(
            text("SELECT id FROM empresa WHERE nombre = :nombre LIMIT 1"),
            {"nombre": nombre},
        ).fetchone()
        if not row:
            continue
        results.append(
            {
                "empresa_id": row[0],
                "rol": company.get("rol", "relacionada"),
                "confianza_extraccion": company.get("confianza_extraccion", 0.7),
                "nota": company.get("nota"),
            }
        )
    return results


def link_documento_empresa(conn, referencia: str, empresa_id: int | None) -> None:
    if empresa_id is None:
        return

    conn.execute(
        text(
            """
            INSERT INTO documento_empresa (documento_id, empresa_id, rol, confianza_extraccion, nota)
            SELECT d.id, :empresa_id, 'principal', 0.85, 'Extraccion heuristica desde BORME'
            FROM documento_interpretativo d
            WHERE d.referencia = :referencia
            ON CONFLICT (documento_id, empresa_id) DO UPDATE SET
                rol = excluded.rol,
                confianza_extraccion = excluded.confianza_extraccion,
                nota = excluded.nota
            """
        ),
        {"empresa_id": empresa_id, "referencia": referencia},
    )


def link_documento_empresas(conn, referencia: str, empresas: list[dict[str, object]]) -> None:
    for empresa in empresas:
        conn.execute(
            text(
                """
                INSERT INTO documento_empresa (documento_id, empresa_id, rol, confianza_extraccion, nota)
                SELECT d.id, :empresa_id, :rol, :confianza_extraccion, :nota
                FROM documento_interpretativo d
                WHERE d.referencia = :referencia
                ON CONFLICT (documento_id, empresa_id) DO UPDATE SET
                    rol = excluded.rol,
                    confianza_extraccion = excluded.confianza_extraccion,
                    nota = excluded.nota
                """
            ),
            {
                "empresa_id": empresa["empresa_id"],
                "rol": empresa["rol"],
                "confianza_extraccion": empresa["confianza_extraccion"],
                "nota": empresa["nota"],
                "referencia": referencia,
            },
        )


def run_sync(
    seed_urls: list[str] | None = None,
    worker_name: str = "worker-borme",
) -> dict[str, int]:
    urls = list(seed_urls) if seed_urls is not None else []
    if seed_urls is None and SEED_URLS:
        urls.extend(SEED_URLS)
    request_delay = float(os.environ.get("WORKER_REQUEST_DELAY", "1.0"))
    processed = 0
    stored = 0
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)
    sync_start = datetime.now(UTC).isoformat()

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client, engine.begin() as conn:
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)
            if seed_urls is None and _env_bool("BORME_DISCOVER_FROM_SUMMARY", True):
                urls = discover_borme_pdf_urls(
                    client,
                    days_back=_env_int("BORME_DAYS_BACK", DEFAULT_BORME_DAYS_BACK),
                    max_urls=_env_int(
                        "BORME_MAX_URLS_PER_RUN",
                        DEFAULT_BORME_MAX_URLS_PER_RUN,
                    ),
                ) + urls

            deduped_urls = []
            seen_urls = set()
            for candidate_url in urls:
                if candidate_url in seen_urls:
                    continue
                seen_urls.add(candidate_url)
                deduped_urls.append(candidate_url)
            urls = deduped_urls

            if not urls:
                error_msg = (
                    "No BORME PDF URLs discovered from official summary API "
                    "or configured seeds"
                )
                logger.warning("%s - worker=%s", error_msg, worker_name)
                log_sync(
                    conn,
                    worker_name,
                    "partial",
                    documentos_processed=0,
                    documentos_upserted=0,
                    error_msg=error_msg,
                    started_at=sync_start,
                )
                return {"processed": 0, "stored": 0}

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
                empresas = upsert_empresas(conn, payload)
                if empresas:
                    link_documento_empresas(conn, payload["referencia"], empresas)
                else:
                    empresa_id = upsert_empresa(conn, payload)
                    link_documento_empresa(conn, payload["referencia"], empresa_id)
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
        entity_id = "borme"
        if not handle_worker_failure(engine, "borme", entity_id, "sync_entity", exc):
            logger.warning("Entity borme moved to dead-letter")
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
        description="BORME worker: sync public corporate events from BORME PDFs"
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
    init_sentry("borme")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-borme-weekly")
        print(
            f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}"
        )
    else:
        print(f"Starting BORME worker in continuous mode (interval={interval}s)")
        while True:
            touch_heartbeat()
            result = run_sync()
            print(
                f"Synced actos={result['processed']}, almacenados={result['stored']} at {datetime.now(UTC).isoformat()}"
            )
            sleep_with_heartbeat(interval)
