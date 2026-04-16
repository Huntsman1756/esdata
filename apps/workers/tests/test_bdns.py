from pathlib import Path
import sys

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bdns import build_document_payload, run_sync, upsert_documento_interpretativo


MINIMAL_PDF_WITH_TEXT = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 95 >>
stream
BT
/F1 12 Tf
36 100 Td
(Convocatoria de becas y subvenciones publicas) Tj
0 -18 Td
(Beneficiarios y cuantia de la ayuda) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000241 00000 n 
0000000387 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
457
%%EOF
"""


def test_build_document_payload_extracts_reference_title_and_text():
    payload = build_document_payload(
        "https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/749075/document/1034404",
        MINIMAL_PDF_WITH_TEXT,
    )

    assert payload["referencia"] == "BDNS-749075-1034404"
    assert "Convocatoria 749075" in payload["titulo"]
    assert "subvenciones publicas" in payload["texto"].lower()


def test_upsert_documento_interpretativo_stores_bdns_fields_once():
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
            "referencia": "BDNS-749075-1034404",
            "fecha": "2026-04-16",
            "titulo": "Convocatoria 749075 - Becas",
            "texto": "Texto de la convocatoria de subvenciones.",
            "url_fuente": "https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/749075/document/1034404",
        }

        upsert_documento_interpretativo(conn, payload)
        upsert_documento_interpretativo(conn, payload)

        row = conn.execute(
            text(
                "SELECT referencia, tipo_documento, organismo_emisor, tipo_fuente, ambito, COUNT(*) FROM documento_interpretativo GROUP BY referencia, tipo_documento, organismo_emisor, tipo_fuente, ambito"
            )
        ).fetchone()

    assert row == (
        "BDNS-749075-1034404",
        "convocatoria_subvencion",
        "BDNS",
        "bdns",
        "subvenciones",
        1,
    )


def test_run_sync_persists_bdns_document_and_metrics(monkeypatch):
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
        return httpx.Response(200, content=MINIMAL_PDF_WITH_TEXT)

    monkeypatch.setattr("bdns.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "bdns.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    result = run_sync(
        seed_urls=["https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/749075/document/1034404"]
    )

    assert result == {"processed": 1, "stored": 1}

    with engine.begin() as conn:
        doc = conn.execute(
            text(
                "SELECT referencia, organismo_emisor, tipo_fuente, ambito FROM documento_interpretativo WHERE referencia = 'BDNS-749075-1034404'"
            )
        ).fetchone()
        sync = conn.execute(
            text(
                "SELECT worker, status, documentos_processed, documentos_upserted FROM sync_log ORDER BY id DESC LIMIT 1"
            )
        ).fetchone()

    assert doc == ("BDNS-749075-1034404", "BDNS", "bdns", "subvenciones")
    assert sync == ("worker-bdns", "ok", 1, 1)
