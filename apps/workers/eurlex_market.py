"""Load official EUR-Lex market acts into dedicated market tables.

This worker owns data loading only. Schema is owned by Alembic migration
20260513_0074_eurlex_esma_market_tables.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent))

from boe import _ensure_sync_log_table, log_sync
from eurlex import (
    EURLEX_BASE,
    OFFICIAL_NOTICE_ACCEPT,
    OFFICIAL_RDF_ACCEPT,
    _extract_consolidation_item_url,
    _extract_consolidation_manifestation_urls,
    _extract_consolidation_manifestation_urls_from_celex_rdf,
    _parse_official_consolidation_html,
)
from runtime import (
    assert_table_exists,
    configure_logging,
    ensure_database_connection,
    get_database_url,
    get_interval_seconds,
    handle_worker_failure,
    init_sentry,
)


logger = configure_logging("workers.eurlex_market")
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("EURLEX_MARKET_SYNC_INTERVAL_SECONDS", 2592000)


@dataclass(frozen=True)
class MarketAct:
    celex: str
    titulo: str
    tipo: str
    fecha_publicacion: str | None = None
    fecha_vigor: str | None = None


@dataclass(frozen=True)
class DownloadedAct:
    act: MarketAct
    source_url: str
    source_hash: str
    vigente_desde: str
    html: str


MARKET_ACTS: dict[str, MarketAct] = {
    "32014R0600": MarketAct(
        celex="32014R0600",
        titulo="Reglamento (UE) n.o 600/2014 sobre los mercados de instrumentos financieros (MiFIR)",
        tipo="REGULATION",
        fecha_publicacion="2014-06-12",
    ),
    "32023R1114": MarketAct(
        celex="32023R1114",
        titulo="Reglamento (UE) 2023/1114 relativo a los mercados de criptoactivos (MiCA)",
        tipo="REGULATION",
        fecha_publicacion="2023-06-09",
    ),
    "32022R0858": MarketAct(
        celex="32022R0858",
        titulo="Reglamento (UE) 2022/858 sobre un regimen piloto de infraestructuras de mercado basadas en DLT",
        tipo="REGULATION",
        fecha_publicacion="2022-06-02",
    ),
}


def _date_or_none(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _discover_manifestation_urls(client: httpx.Client, celex: str) -> list[str]:
    notice_response = client.get(
        f"{EURLEX_BASE}/legal-content/ES/TXT/XML/?uri=CELEX:{celex}",
        headers={"Accept": OFFICIAL_NOTICE_ACCEPT},
        follow_redirects=True,
        timeout=30.0,
    )
    notice_response.raise_for_status()
    notice_text = notice_response.text or ""
    manifestation_urls = (
        _extract_consolidation_manifestation_urls(notice_text)
        if notice_text.strip()
        else []
    )
    if manifestation_urls:
        return manifestation_urls

    celex_response = client.get(
        f"http://publications.europa.eu/resource/celex/{celex}",
        headers={"Accept": OFFICIAL_RDF_ACCEPT},
        follow_redirects=True,
        timeout=30.0,
    )
    celex_response.raise_for_status()
    return _extract_consolidation_manifestation_urls_from_celex_rdf(celex_response.text)


def download_market_act(act: MarketAct) -> DownloadedAct:
    """Download the current official consolidated HTML for a CELEX act."""

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        last_error: Exception | None = None
        for manifestation_url in _discover_manifestation_urls(client, act.celex):
            try:
                manifestation = client.get(
                    manifestation_url,
                    headers={"Accept": OFFICIAL_RDF_ACCEPT},
                    follow_redirects=True,
                    timeout=30.0,
                )
                manifestation.raise_for_status()
                item_url = _extract_consolidation_item_url(manifestation.text)
                if not item_url:
                    continue

                html_response = client.get(
                    item_url,
                    headers={"Accept": "text/html, application/xhtml+xml"},
                    follow_redirects=True,
                    timeout=60.0,
                )
                html_response.raise_for_status()
                source_hash = hashlib.md5(html_response.content).hexdigest()
                vigente_desde = manifestation_url.rstrip("/").split("/")[-2]
                if len(vigente_desde) == 8 and vigente_desde.isdigit():
                    vigente_desde = f"{vigente_desde[:4]}-{vigente_desde[4:6]}-{vigente_desde[6:8]}"
                else:
                    vigente_desde = ""
                return DownloadedAct(
                    act=act,
                    source_url=item_url,
                    source_hash=source_hash,
                    vigente_desde=vigente_desde,
                    html=html_response.text,
                )
            except Exception as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
    raise RuntimeError(f"No official consolidated manifestation found for CELEX {act.celex}")


def parse_articles(download: DownloadedAct) -> list[dict]:
    """Extract article records from the official consolidated HTML."""

    blocks = _parse_official_consolidation_html(
        download.act.celex,
        download.html,
        vigente_desde=download.vigente_desde,
    )
    articles = [
        {
            "numero": block.numero,
            "titulo": block.titulo,
            "texto": block.texto.strip(),
            "url_eurlex": download.source_url,
            "source_hash": download.source_hash,
            "capture_date": date.today().isoformat(),
        }
        for block in blocks
        if block.tipo_articulo == "articulo" and block.numero and block.texto.strip()
    ]
    if not articles:
        raise RuntimeError(f"Official EUR-Lex parse returned zero articles for {download.act.celex}")
    return articles


def assert_market_tables(conn) -> None:
    assert_table_exists(
        conn,
        "eurlex_act",
        required_columns=("celex", "titulo", "url_eurlex", "source_hash", "capture_date", "verified", "completeness"),
    )
    assert_table_exists(
        conn,
        "eurlex_article",
        required_columns=("act_id", "numero", "texto", "url_eurlex", "source_hash", "capture_date"),
    )


def upsert_market_act(conn, download: DownloadedAct, articles: list[dict]) -> int:
    capture_date = date.today().isoformat()
    act_id = conn.execute(
        text(
            """
            INSERT INTO eurlex_act (
                celex, titulo, tipo, fecha_publicacion, fecha_vigor,
                url_eurlex, source_hash, capture_date, verified, completeness, updated_at
            )
            VALUES (
                :celex, :titulo, :tipo, :fecha_publicacion, :fecha_vigor,
                :url_eurlex, :source_hash, :capture_date, true, 'completa', now()
            )
            ON CONFLICT (celex) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                tipo = EXCLUDED.tipo,
                fecha_publicacion = EXCLUDED.fecha_publicacion,
                fecha_vigor = EXCLUDED.fecha_vigor,
                url_eurlex = EXCLUDED.url_eurlex,
                source_hash = EXCLUDED.source_hash,
                capture_date = EXCLUDED.capture_date,
                verified = EXCLUDED.verified,
                completeness = EXCLUDED.completeness,
                updated_at = now()
            RETURNING id
            """
        ),
        {
            "celex": download.act.celex,
            "titulo": download.act.titulo,
            "tipo": download.act.tipo,
            "fecha_publicacion": _date_or_none(download.act.fecha_publicacion),
            "fecha_vigor": _date_or_none(download.act.fecha_vigor),
            "url_eurlex": download.source_url,
            "source_hash": download.source_hash,
            "capture_date": capture_date,
        },
    ).scalar_one()

    conn.execute(text("DELETE FROM eurlex_article WHERE act_id = :act_id"), {"act_id": act_id})
    for article in articles:
        conn.execute(
            text(
                """
                INSERT INTO eurlex_article (
                    act_id, numero, titulo, texto, url_eurlex,
                    source_hash, capture_date, updated_at
                )
                VALUES (
                    :act_id, :numero, :titulo, :texto, :url_eurlex,
                    :source_hash, :capture_date, now()
                )
                """
            ),
            {**article, "act_id": act_id},
        )
    return len(articles)


def run_once(celexs: list[str] | None = None, worker_name: str = "worker-eurlex-market") -> dict:
    selected = celexs or list(MARKET_ACTS)
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine, logger=logger)
    sync_start = datetime.now(UTC).isoformat()
    total_articles = 0

    try:
        with engine.begin() as conn:
            assert_market_tables(conn)
            for celex in selected:
                act = MARKET_ACTS.get(celex)
                if act is None:
                    raise ValueError(f"Unsupported market CELEX: {celex}")
                download = download_market_act(act)
                articles = parse_articles(download)
                count = upsert_market_act(conn, download, articles)
                total_articles += count
                logger.info("Loaded %s with %d articles from %s", celex, count, download.source_url)
            _ensure_sync_log_table(conn)
            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=len(selected),
                articulos=total_articles,
                started_at=sync_start,
            )
    except Exception as exc:
        if not handle_worker_failure(engine, "eurlex_market", ",".join(selected), "sync_market_act", exc):
            logger.warning("EUR-Lex market sync moved to dead-letter")
        try:
            with engine.begin() as conn:
                _ensure_sync_log_table(conn)
                log_sync(conn, worker_name, "error", error_msg=str(exc)[:500], started_at=sync_start)
        except Exception as log_exc:
            logger.warning("Failed to write EUR-Lex market sync error log: %s", log_exc)
        raise

    return {"worker": worker_name, "acts": len(selected), "articles": total_articles}


def main() -> None:
    parser = argparse.ArgumentParser(description="Load dedicated EUR-Lex market acts")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    parser.add_argument("--celex", action="append", help="CELEX to load; may be repeated")
    parser.add_argument("--interval", type=int, default=None, help="Sync interval in seconds")
    args = parser.parse_args()

    init_sentry("eurlex_market")
    selected = [_celex.upper() for _celex in args.celex] if args.celex else None
    interval = args.interval or SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_once(selected)
        print(f"[run-once] EUR-Lex market: acts={result['acts']} articles={result['articles']}")
        return

    while True:
        try:
            result = run_once(selected)
            logger.info("EUR-Lex market sync complete: %s", result)
        except Exception:
            logger.exception("Error in EUR-Lex market sync cycle")
        time.sleep(interval)


if __name__ == "__main__":
    main()
