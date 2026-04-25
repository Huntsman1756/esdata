import argparse
from datetime import UTC, datetime
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


def _parse_seed_urls(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


SEED_URLS = _parse_seed_urls(os.getenv("BORME_SEED_URLS"))
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_pdf_code(url: str) -> str:
    match = re.search(r"/(BORME-[A-Z]-\d{4}-\d+-\d+)\.pdf$", url)
    if match:
        return match.group(1)

    path = urlparse(url).path.rstrip("/").split("/")[-1]
    return path.removesuffix(".pdf") or "BORME-SEED"


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
        "empresas": _extract_related_companies(text_value),
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
                'BORME',
                'es',
                'borme',
                'mercantil',
                :referencia,
                :fecha,
                :titulo,
                :texto,
                :url_fuente
            )
            ON CONFLICT (referencia) DO UPDATE SET
                tipo_documento = excluded.tipo_documento,
                fecha = excluded.fecha,
                titulo = excluded.titulo,
                texto = excluded.texto,
                url_fuente = excluded.url_fuente
            """
        ),
        payload,
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
                    payload = build_document_payload(url, response.content)
                    processed += 1
                    upsert_documento_interpretativo(conn, payload)
                    empresas = upsert_empresas(conn, payload)
                    if empresas:
                        link_documento_empresas(conn, payload["referencia"], empresas)
                    else:
                        empresa_id = upsert_empresa(payload=payload, conn=conn)
                        link_documento_empresa(conn, payload["referencia"], empresa_id)
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
            result = run_sync()
            print(
                f"Synced actos={result['processed']}, almacenados={result['stored']} at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
