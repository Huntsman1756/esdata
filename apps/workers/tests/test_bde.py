from pathlib import Path
import sys

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bde import build_document_payload, run_sync, upsert_documento_interpretativo


MINIMAL_BDE_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 137 >>\nstream\nBT\n/F1 12 Tf\n20 110 Td\n"
    b"(Informe sobre la estabilidad financiera 2024) Tj\n0 -18 Td\n"
    b"(Banco de Espa\xc3\xb1a) Tj\nET\nendstream\nendobj\n"
    b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
    b"0000000115 00000 n \n0000000241 00000 n \n0000000469 00000 n \n"
    b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n509\n%%EOF\n"
)

BDE_HTML = (
    b"<html>\n"
    b"  <body>\n"
    b"    <h1>Comunicaci\xc3\xb3n sobre sistemas de pago</h1>\n"
    b"    <p>Gu\xc3\xada operativa para la supervisi\xc3\xb3n bancaria de sistemas de pago.</p>\n"
    b"  </body>\n"
    b"</html>\n"
)


def test_build_document_payload_from_pdf():
    payload = build_document_payload(
        "https://www.bde.es/f/webbde/INF/Secciones/Publicaciones/Informes/informes24/estabilidad24.pdf",
        MINIMAL_BDE_PDF,
    )

    assert payload["tipo_fuente"] == "bde"
    assert payload["tipo_documento"] == "informe_bde"
    assert payload["organismo_emisor"] == "Banco de España"
    assert payload["ambito"] == "estabilidad_financiera"
    assert "estabilidad financiera 2024" in payload["texto"].lower()


def test_build_document_payload_from_html():
    payload = build_document_payload(
        "https://www.bde.es/bdees/guias/sistemasdepago/",
        BDE_HTML,
    )

    assert payload["tipo_fuente"] == "bde"
    assert payload["tipo_documento"] == "comunicacion_bde"
    assert payload["organismo_emisor"] == "Banco de España"
    assert payload["ambito"] == "supervision_bancaria"


def test_upsert_documento_interpretativo_stores_bde_fields_once():
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
            "referencia": "BDE-informes-2024-estabilidad",
            "fecha": "2024-01-15",
            "titulo": "Informe sobre la estabilidad financiera 2024",
            "tipo_documento": "informe_bde",
            "ambito": "estabilidad_financiera",
            "texto": "Informe de estabilidad financiera del Banco de España.",
            "url_fuente": "https://www.bde.es/f/webbde/INF/Secciones/Publicaciones/Informes/informes24/estabilidad24.pdf",
        }

        upsert_documento_interpretativo(conn, payload)
        upsert_documento_interpretativo(conn, payload)

        row = conn.execute(
            text(
                "SELECT referencia, tipo_documento, organismo_emisor, tipo_fuente, ambito, COUNT(*) FROM documento_interpretativo GROUP BY referencia, tipo_documento, organismo_emisor, tipo_fuente, ambito"
            )
        ).fetchone()

    assert row == (
        "BDE-informes-2024-estabilidad",
        "informe_bde",
        "Banco de España",
        "bde",
        "estabilidad_financiera",
        1,
    )


def test_run_sync_persists_bde_document_and_metrics(monkeypatch):
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
        return httpx.Response(200, content=MINIMAL_BDE_PDF)

    monkeypatch.setattr("bde.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "bde.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    result = run_sync(seed_urls=["https://www.bde.es/f/webbde/INF/Secciones/Publicaciones/Informes/informes24/estabilidad24.pdf"])

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

    assert doc[1] == "Banco de España"
    assert doc[2] == "bde"
    assert doc[3] == "estabilidad_financiera"
    assert doc[4] == "informe_bde"
    assert sync == ("worker-bde", "ok", 1, 1)


def test_run_sync_rehydrates_missing_document_when_revision_exists(monkeypatch):
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
        conn.execute(
            text(
                """
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
                """
            )
        )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MINIMAL_BDE_PDF)

    monkeypatch.setattr("bde.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "bde.check_content_changed",
        lambda *args, **kwargs: type("Change", (), {"changed": False})(),
    )
    monkeypatch.setattr(
        "bde.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    result = run_sync(seed_urls=["https://www.bde.es/f/webbde/INF/Secciones/Publicaciones/Informes/informes24/estabilidad24.pdf"])

    assert result == {"processed": 1, "stored": 1}

    with engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM documento_interpretativo")).scalar_one()

    assert count == 1
