import argparse
from datetime import UTC, datetime, timezone
from html import unescape
import os
import re
import time

import httpx
from sqlalchemy import create_engine, text

from boe import _ensure_sync_log_table, log_sync
from runtime import get_database_url, get_interval_seconds


def _parse_seed_urls(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


SEED_URLS = _parse_seed_urls(os.getenv("EURLEX_SEED_URLS"))
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_reference(url: str, text_value: str) -> str:
    celex_match = re.search(r"/legal-content/[^/]+/TXT/\?uri=CELEX:([^&#]+)", url, flags=re.IGNORECASE)
    if celex_match:
        return f"EURLEX-CELEX-{celex_match.group(1)}"

    match = re.search(r"(\d{4})/(\d{2})/(\d{4})", text_value)
    if match:
        return f"EURLEX-{match.group(1)}-{match.group(2)}-{match.group(3)}"
    match = re.search(r"([A-Z]{2,}-\d+/\d+)", text_value)
    if match:
        return f"EURLEX-{match.group(1)}"
    return f"EURLEX-{datetime.now(UTC).date().isoformat().replace('-', '')}"


def _detect_document_type(text_value: str) -> str:
    lowered = text_value.lower()
    if "directiva" in lowered:
        return "directiva"
    if "reglamento" in lowered:
        return "reglamento"
    if "decisión" in lowered or "decision" in lowered:
        return "decision"
    if "directive" in lowered:
        return "directive"
    if "regulation" in lowered:
        return "regulation"
    if "recommendation" in lowered or "recomendación" in lowered or "recomendacion" in lowered:
        return "recommendation"
    return "documento_ue"


def _detect_ambito(text_value: str) -> str:
    lowered = text_value.lower()
    if "fiscal" in lowered or "taxation" in lowered or "fiscaux" in lowered:
        return "fiscal_ue"
    if "mifid" in lowered or "markets in financial instruments" in lowered:
        return "mercados_financieros_ue"
    if "market abuse" in lowered or "mar" in lowered:
        return "abuso_mercado_ue"
    if "priips" in lowered:
        return "disclosure_ue"
    if "dora" in lowered or "digital operational resilience" in lowered:
        return "resiliencia_digital_ue"
    if "mercado interior" in lowered or "internal market" in lowered:
        return "mercado_interior"
    if "competencia" in lowered or "competition" in lowered:
        return "competencia_ue"
    return "ue_general"


def extract_text(content: bytes) -> str:
    html = content.decode("utf-8", errors="ignore")
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", "\n", html)
    text_value = re.sub(r"\n\s*\n", "\n", html)
    return _normalize_whitespace(unescape(text_value))


def build_document_payload(url: str, content: bytes) -> dict[str, str]:
    text_value = extract_text(content)
    if not text_value:
        raise ValueError(f"Could not extract text from EUR-Lex document: {url}")

    referencia = _extract_reference(url, text_value)

    return {
        "referencia": referencia,
        "fecha": datetime.now(UTC).date().isoformat(),
        "titulo": f"{_detect_document_type(text_value)} - {referencia}",
        "texto": text_value,
        "url_fuente": url,
        "tipo_documento": _detect_document_type(text_value),
        "tipo_fuente": "eurlex",
        "organismo_emisor": "UE",
        "ambito": _detect_ambito(text_value),
        "jurisdiccion": "ue",
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
                organismo_emisor = excluded.organismo_emisor,
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
    worker_name: str = "worker-eurlex",
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
        description="EUR-Lex worker: sync EU legislation from EUR-Lex"
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
    init_sentry("eurlex")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-eurlex-weekly")
        print(
            f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}"
        )
    else:
        print(f"Starting EUR-Lex worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced documentos={result['processed']}, almacenados={result['stored']} at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
