from pathlib import Path
import sys

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aepd import build_document_payload, run_sync, upsert_documento_interpretativo


MINIMAL_AEPD_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 133 >>\nstream\nBT\n/F1 12 Tf\n20 110 Td\n"
    b"(Guia sobre proteccion de datos y onboarding PBC) Tj\n0 -18 Td\n"
    b"(Agencia Espanola de Proteccion de Datos) Tj\nET\nendstream\nendobj\n"
    b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
    b"0000000115 00000 n \n0000000241 00000 n \n0000000465 00000 n \n"
    b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n505\n%%EOF\n"
)

AEPD_HTML = (
    b"<html>\n"
    b"  <body>\n"
    b"    <h1>Resolucion sobre cookies</h1>\n"
    b"    <p>Guia de consentimiento y proteccion de datos en navegadores.</p>\n"
    b"  </body>\n"
    b"</html>\n"
)


def test_build_document_payload_from_pdf():
    payload = build_document_payload(
        "https://www.aepd.es/guias/proteccion-datos-onboarding-pbc.pdf",
        MINIMAL_AEPD_PDF,
    )

    assert payload["tipo_fuente"] == "aepd"
    assert payload["tipo_documento"] == "guia_aepd"
    assert payload["organismo_emisor"] == "AEPD"
    assert payload["ambito"] == "proteccion_datos"
    assert "proteccion de datos y onboarding pbc" in payload["texto"].lower()
    assert "agencia espanola de proteccion de datos" in payload["texto"].lower()


def test_build_document_payload_from_html():
    payload = build_document_payload(
        "https://www.aepd.es/guias/cookies/",
        AEPD_HTML,
    )

    assert payload["tipo_fuente"] == "aepd"
    assert payload["tipo_documento"] == "guia_aepd"
    assert payload["organismo_emisor"] == "AEPD"
    assert payload["ambito"] == "proteccion_datos"


def test_upsert_documento_interpretativo_stores_aepd_fields_once():
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
            "referencia": "AEPD-guias-onboarding-pbc",
            "fecha": "2024-03-10",
            "titulo": "Guía sobre protección de datos y onboarding PBC",
            "tipo_documento": "guia_aepd",
            "ambito": "proteccion_datos",
            "texto": "Guía de la Agencia Española de Protección de Datos sobre onboarding.",
            "url_fuente": "https://www.aepd.es/guias/proteccion-datos-onboarding-pbc.pdf",
        }

        upsert_documento_interpretativo(conn, payload)
        upsert_documento_interpretativo(conn, payload)

        row = conn.execute(
            text(
                "SELECT referencia, tipo_documento, organismo_emisor, tipo_fuente, ambito, COUNT(*) FROM documento_interpretativo GROUP BY referencia, tipo_documento, organismo_emisor, tipo_fuente, ambito"
            )
        ).fetchone()

    assert row == (
        "AEPD-guias-onboarding-pbc",
        "guia_aepd",
        "AEPD",
        "aepd",
        "proteccion_datos",
        1,
    )


def test_run_sync_persists_aepd_document_and_metrics(monkeypatch):
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
                    error_msg TEXT
                )
                """
            )
        )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MINIMAL_AEPD_PDF)

    monkeypatch.setattr("aepd.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "aepd.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    result = run_sync(seed_urls=["https://www.aepd.es/guias/proteccion-datos-onboarding-pbc.pdf"])

    assert result == {"processed": 1, "stored": 1}

    with engine.begin() as conn:
        doc = conn.execute(
            text(
                "SELECT referencia, organismo_emisor, tipo_fuente, ambito, tipo_documento FROM documento_interpretativo"
            )
        ).fetchone()
        sync = conn.execute(
            text(
                "SELECT worker, status, documentos_processed, documentos_upserted FROM sync_log ORDER BY id DESC LIMIT 1"
            )
        ).fetchone()

    assert doc[1] == "AEPD"
    assert doc[2] == "aepd"
    assert doc[3] == "proteccion_datos"
    assert doc[4] == "guia_aepd"
    assert sync == ("worker-aepd", "ok", 1, 1)


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
                error_msg TEXT
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
        return httpx.Response(200, content=MINIMAL_AEPD_PDF)

    monkeypatch.setattr("aepd.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "aepd.check_content_changed",
        lambda *args, **kwargs: type("Change", (), {"changed": False})(),
    )
    monkeypatch.setattr(
        "aepd.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    result = run_sync(seed_urls=["https://www.aepd.es/guias/proteccion-datos-onboarding-pbc.pdf"])

    assert result == {"processed": 1, "stored": 1}

    with engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM documento_interpretativo")).scalar_one()

    assert count == 1


def test_run_sync_empty_seed_urls_returns_zero():
    """SEED_URLS vacío debe devolver processed=0, stored=0 sin hacer HTTP."""
    result = run_sync(seed_urls=[])
    assert result == {"processed": 0, "stored": 0}
