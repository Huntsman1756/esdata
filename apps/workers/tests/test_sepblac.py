import sys
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sepblac import build_document_payload, discover_default_urls, run_sync, upsert_documento_interpretativo

SEPBLAC_HTML = b"""
<html>
  <body>
    <h1>Comunicaci\xc3\xb3n por indicio - Modelo 19 SEPBLAC</h1>
    <p>Procedimiento para la comunicaci\xc3\xb3n por indicio de hechos u operaciones respecto de los que existan indicios o certeza de blanqueo de capitales o financiaci\xc3\xb3n del terrorismo.</p>
  </body>
</html>
"""

SEPBLAC_DISCOVERY_HTML = """
<html><body>
  <a href="/es/normativa/normativa-nacional/">Normativa nacional</a>
  <a href="/media/2026/guia-obligaciones.pdf">Guia de obligaciones para sujetos obligados</a>
  <a href="https://example.com/not-official.pdf">No oficial</a>
</body></html>
"""


def test_build_document_payload_extracts_reference_type_and_ambito():
    payload = build_document_payload(
        "https://www.sepblac.es/es/",
        SEPBLAC_HTML,
        "text/html; charset=utf-8",
    )

    assert payload["referencia"] == "SEPBLAC-MODELO-19"
    assert payload["tipo_documento"] == "formulario_sepblac"
    assert payload["ambito"] == "aml_cft_reporting"
    assert "modelo 19" in payload["texto"].lower()


def test_build_document_payload_classifies_obligations_separately():
    payload = build_document_payload(
        "https://www.sepblac.es/es/sujetos-obligados/obligaciones/",
        b"<html><body><h1>Obligaciones de los sujetos obligados</h1><p>Ley 10/2010 sobre blanqueo de capitales y Real Decreto 304/2014.</p></body></html>",
        "text/html; charset=utf-8",
    )

    assert payload["tipo_documento"] == "obligacion_sepblac"
    assert payload["ambito"] == "aml_cft"


def test_discover_default_urls_uses_official_sepblac_sources(monkeypatch):
    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SEPBLAC_DISCOVERY_HTML)

    monkeypatch.setattr(
        "sepblac.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    urls = discover_default_urls(max_urls=10)

    assert "https://www.sepblac.es/es/normativa/?lang=es" in urls
    assert "https://www.sepblac.es/media/2026/guia-obligaciones.pdf" in urls
    assert all("sepblac.es" in url for url in urls)


def test_upsert_documento_interpretativo_stores_sepblac_fields_once():
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento TEXT NOT NULL,
                    organismo_emisor TEXT NOT NULL,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    referencia TEXT UNIQUE NOT NULL,
                    fecha TEXT NOT NULL,
                    titulo TEXT,
                    texto TEXT NOT NULL,
                    url_fuente TEXT
                )
                """
            )
        )

        payload = {
            "referencia": "SEPBLAC-MODELO-19",
            "fecha": "2026-04-16",
            "titulo": "Comunicación por indicio - Modelo 19 SEPBLAC",
            "tipo_documento": "formulario_sepblac",
            "ambito": "aml_cft_reporting",
            "texto": "Procedimiento para la comunicación por indicio y formulario oficial Modelo 19 SEPBLAC.",
            "url_fuente": "https://www.sepblac.es/es/",
        }

        upsert_documento_interpretativo(conn, payload)
        upsert_documento_interpretativo(conn, payload)

        row = conn.execute(
            text(
                "SELECT referencia, tipo_documento, organismo_emisor, tipo_fuente, ambito, COUNT(*) FROM documento_interpretativo GROUP BY referencia, tipo_documento, organismo_emisor, tipo_fuente, ambito"
            )
        ).fetchone()

    assert row == (
        "SEPBLAC-MODELO-19",
        "formulario_sepblac",
        "SEPBLAC",
        "sepblac",
        "aml_cft_reporting",
        1,
    )


def test_run_sync_persists_sepblac_document_and_metrics(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)
    original_client = httpx.Client

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento TEXT NOT NULL,
                    organismo_emisor TEXT NOT NULL,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    referencia TEXT UNIQUE NOT NULL,
                    fecha TEXT NOT NULL,
                    titulo TEXT,
                    texto TEXT NOT NULL,
                    url_fuente TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    bloques_processed INTEGER,
                    articulos_upserted INTEGER,
                    documentos_processed INTEGER,
                    documentos_upserted INTEGER,
                    doctrina_links_created INTEGER,
                    error_msg TEXT,
                    rows_processed INTEGER,
                    errors INTEGER,
                    duration_ms INTEGER
                )
                """
            )
        )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=SEPBLAC_HTML, headers={"content-type": "text/html; charset=utf-8"})

    monkeypatch.setattr("sepblac.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "sepblac.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    result = run_sync(seed_urls=["https://www.sepblac.es/es/"])

    assert result == {"processed": 1, "stored": 1}

    with engine.begin() as conn:
        doc = conn.execute(
            text(
                "SELECT referencia, organismo_emisor, tipo_fuente, ambito, tipo_documento FROM documento_interpretativo WHERE referencia = 'SEPBLAC-MODELO-19'"
            )
        ).fetchone()
        sync = conn.execute(
            text(
                "SELECT worker, status, documentos_processed, documentos_upserted FROM sync_log ORDER BY id DESC LIMIT 1"
            )
        ).fetchone()

    assert doc == (
        "SEPBLAC-MODELO-19",
        "SEPBLAC",
        "sepblac",
        "aml_cft_reporting",
        "formulario_sepblac",
    )
    assert sync == ("worker-sepblac", "ok", 1, 1)


def test_run_sync_rehydrates_missing_document_when_revision_exists(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)
    original_client = httpx.Client

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE documento_interpretativo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_documento TEXT NOT NULL,
                organismo_emisor TEXT NOT NULL,
                jurisdiccion TEXT NOT NULL,
                tipo_fuente TEXT NOT NULL,
                ambito TEXT NOT NULL,
                referencia TEXT UNIQUE NOT NULL,
                fecha TEXT NOT NULL,
                titulo TEXT,
                texto TEXT NOT NULL,
                url_fuente TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                bloques_processed INTEGER,
                articulos_upserted INTEGER,
                documentos_processed INTEGER,
                documentos_upserted INTEGER,
                doctrina_links_created INTEGER,
                error_msg TEXT,
                rows_processed INTEGER,
                errors INTEGER,
                duration_ms INTEGER
            )
        """))
        conn.execute(text("""
            CREATE TABLE source_revision (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_name TEXT NOT NULL,
                source_entity_tipo TEXT NOT NULL,
                source_entity_id TEXT NOT NULL,
                content_hash_sha256 TEXT NOT NULL,
                etag TEXT,
                last_modified TEXT,
                content_length INTEGER,
                fetched_at TEXT,
                UNIQUE(worker_name, source_entity_tipo, source_entity_id)
            )
        """))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=SEPBLAC_HTML, headers={"content-type": "text/html; charset=utf-8"})

    monkeypatch.setattr("sepblac.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "sepblac.check_content_changed",
        lambda *args, **kwargs: type("Change", (), {"changed": False})(),
    )
    monkeypatch.setattr(
        "sepblac.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    result = run_sync(seed_urls=["https://www.sepblac.es/es/"])

    assert result == {"processed": 1, "stored": 1}

    with engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM documento_interpretativo")).scalar_one()

    assert count == 1


def test_run_sync_empty_seed_urls_returns_zero():
    """SEED_URLS vacío debe devolver processed=0, stored=0 sin hacer HTTP."""
    result = run_sync(seed_urls=[])
    assert result == {"processed": 0, "stored": 0}
