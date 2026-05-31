import sys
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bdns import (
    build_bdns_text_payload,
    build_document_payload,
    build_structured_payload,
    normalize_bdns_api_item,
    run_sync,
    upsert_documento_interpretativo,
)

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


def test_normalize_bdns_api_item_maps_convocatoria_summary_to_official_payload():
    raw = {
        "id": 1110924,
        "mrr": False,
        "numeroConvocatoria": "909363",
        "descripcion": "Bono Social Termico 2024",
        "fechaRecepcion": "2026-05-31",
        "nivel1": "AUTONOMICA",
        "nivel2": "ILLES BALEARS",
        "nivel3": "DIRECCION GENERAL DE PLANIFICACION Y SERVICIOS SOCIALES",
    }

    item = normalize_bdns_api_item(raw, "convocatoria")

    assert item["referencia"] == "BDNS-CONVOCATORIA-909363"
    assert item["tipo_documento"] == "convocatoria_bdns"
    assert item["fecha"] == "2026-05-31"
    assert item["titulo"] == "Bono Social Termico 2024"
    assert item["url_fuente"] == "https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/909363"
    assert item["metadata"]["numero_convocatoria"] == "909363"
    assert item["metadata"]["bdns_endpoint"] == "convocatoria"


def test_normalize_bdns_api_item_maps_concesion_summary_with_amount_and_beneficiary():
    raw = {
        "id": 152503817,
        "codConcesion": "SB152503817",
        "fechaConcesion": "2026-05-29",
        "beneficiario": "B57250185 IDEAL SERVICES PROPERTY MANAGEMENT SL",
        "instrumento": "SUBVENCION",
        "importe": 3317.18,
        "numeroConvocatoria": "877699",
        "convocatoria": "Ayudas para empresas con actividad en Islas Baleares",
        "nivel1": "AUTONOMICA",
        "nivel2": "ILLES BALEARS",
        "nivel3": "DIRECCION GENERAL DEL TESORO",
    }

    item = normalize_bdns_api_item(raw, "concesion")
    text_payload = build_bdns_text_payload(item)

    assert item["referencia"] == "BDNS-CONCESION-SB152503817"
    assert item["tipo_documento"] == "concesion_bdns"
    assert item["titulo"] == "Ayudas para empresas con actividad en Islas Baleares"
    assert item["metadata"]["importe"] == 3317.18
    assert item["metadata"]["beneficiario"] == "B57250185 IDEAL SERVICES PROPERTY MANAGEMENT SL"
    assert "Importe: 3317.18" in text_payload
    assert "Beneficiario: B57250185 IDEAL SERVICES PROPERTY MANAGEMENT SL" in text_payload


def test_build_structured_payload_preserves_metadata_and_exact_provenance():
    item = normalize_bdns_api_item(
        {
            "numeroConvocatoria": "909363",
            "descripcion": "Bono Social Termico 2024",
            "fechaRecepcion": "2026-05-31",
        },
        "convocatoria",
    )

    payload = build_structured_payload(item)

    assert payload["referencia"] == "BDNS-CONVOCATORIA-909363"
    assert payload["row_completeness"] == "partial"
    assert payload["row_provenance"] == "official_exact"
    assert payload["metadata"]["source_api_base"] == "https://www.infosubvenciones.es/bdnstrans/api"
    assert "Bono Social Termico 2024" in payload["texto"]


def test_upsert_documento_interpretativo_stores_structured_metadata_when_columns_exist():
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
                    url_fuente TEXT,
                    metadata TEXT,
                    row_completeness TEXT,
                    row_provenance TEXT
                )
                """
            )
        )

        payload = build_structured_payload(
            normalize_bdns_api_item(
                {
                    "numeroConvocatoria": "909363",
                    "descripcion": "Bono Social Termico 2024",
                    "fechaRecepcion": "2026-05-31",
                },
                "convocatoria",
            )
        )
        upsert_documento_interpretativo(conn, payload)

        row = conn.execute(
            text(
                """
                SELECT referencia, tipo_documento, metadata, row_completeness, row_provenance
                FROM documento_interpretativo
                WHERE referencia = 'BDNS-CONVOCATORIA-909363'
                """
            )
        ).fetchone()

    assert row[0] == "BDNS-CONVOCATORIA-909363"
    assert row[1] == "convocatoria_bdns"
    assert '"numero_convocatoria": "909363"' in row[2]
    assert row[3:] == ("partial", "official_exact")


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


def test_run_sync_persists_structured_bdns_api_items(monkeypatch):
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
                    url_fuente TEXT,
                    metadata TEXT,
                    row_completeness TEXT,
                    row_provenance TEXT
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
        assert request.url.path.endswith("/convocatorias/busqueda")
        return httpx.Response(
            200,
            json={
                "content": [
                    {
                        "numeroConvocatoria": "909363",
                        "descripcion": "Bono Social Termico 2024",
                        "fechaRecepcion": "2026-05-31",
                    },
                    {
                        "numeroConvocatoria": "909364",
                        "descripcion": "Ayudas eficiencia energetica",
                        "fechaRecepcion": "2026-05-30",
                    },
                ],
                "last": True,
                "totalPages": 1,
            },
        )

    monkeypatch.setattr("bdns.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "bdns.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    result = run_sync(seed_urls=[], structured_endpoints=["convocatoria"], max_pages=1)

    assert result == {"processed": 2, "stored": 2}

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT referencia, tipo_documento, row_provenance
                FROM documento_interpretativo
                ORDER BY referencia
                """
            )
        ).fetchall()

    assert rows == [
        ("BDNS-CONVOCATORIA-909363", "convocatoria_bdns", "official_exact"),
        ("BDNS-CONVOCATORIA-909364", "convocatoria_bdns", "official_exact"),
    ]


def test_run_sync_empty_seed_urls_returns_zero():
    """SEED_URLS vacío debe devolver processed=0, stored=0 sin hacer HTTP."""
    result = run_sync(seed_urls=[])
    assert result == {"processed": 0, "stored": 0}
