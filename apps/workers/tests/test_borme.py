# ruff: noqa: I001

import sys
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from borme import (
    build_document_payload,
    link_documento_empresas,
    run_sync,
    upsert_documento_interpretativo,
    upsert_empresa,
    upsert_empresas,
)


MINIMAL_BORME_PDF = b"""%PDF-1.4
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
<< /Length 143 >>
stream
BT
/F1 12 Tf
20 110 Td
(ALDITRAEX SOCIEDAD LIMITADA (Sociedad absorbente)) Tj
0 -18 Td
(MURILLO BARRERO SOCIEDAD LIMITADA (Sociedad absorbida)) Tj
0 -18 Td
(Domicilio: C SANTA LUCIA 19) Tj
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
0000000435 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
505
%%EOF
"""


def test_build_document_payload_extracts_reference_event_and_text():
    payload = build_document_payload(
        "https://www.boe.es/borme/dias/2025/03/20/pdfs/BORME-A-2025-55-37.pdf",
        MINIMAL_BORME_PDF,
    )

    assert payload["referencia"] == "BORME-A-2025-55-37"
    assert payload["tipo_documento"] == "cambio_domicilio"
    assert payload["empresa_nombre"] == "ALDITRAEX SOCIEDAD LIMITADA"
    assert payload["empresa_domicilio"] == "C SANTA LUCIA 19"
    assert len(payload["empresas"]) >= 2
    assert any(item["rol"] == "absorbente" for item in payload["empresas"])
    assert any(item["rol"] == "absorbida" for item in payload["empresas"])


def test_upsert_documento_interpretativo_stores_borme_fields_once():
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
            "referencia": "BORME-A-2025-55-37",
            "fecha": "2025-03-20",
            "titulo": "Actos de SALAMANCA del BORME núm. 55 de 2025",
            "tipo_documento": "nombramiento",
            "texto": "Nombramientos. Adm. Unico: ALVAREZ GARCIA JOSE MARIA.",
            "url_fuente": "https://www.boe.es/borme/dias/2025/03/20/pdfs/BORME-A-2025-55-37.pdf",
        }

        upsert_documento_interpretativo(conn, payload)
        upsert_documento_interpretativo(conn, payload)

        row = conn.execute(
            text(
                "SELECT referencia, tipo_documento, organismo_emisor, tipo_fuente, ambito, COUNT(*) FROM documento_interpretativo GROUP BY referencia, tipo_documento, organismo_emisor, tipo_fuente, ambito"
            )
        ).fetchone()

    assert row == (
        "BORME-A-2025-55-37",
        "nombramiento",
        "BORME",
        "borme",
        "mercantil",
        1,
    )


def test_upsert_empresas_and_link_documento_empresas_keeps_heuristic_contract():
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
        conn.execute(
            text(
                """
                CREATE TABLE empresa (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    nif TEXT,
                    domicilio TEXT,
                    fuente_inicial TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (nombre)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE documento_empresa (
                    documento_id INTEGER NOT NULL,
                    empresa_id INTEGER NOT NULL,
                    rol TEXT NOT NULL,
                    confianza_extraccion REAL NOT NULL,
                    nota TEXT,
                    PRIMARY KEY (documento_id, empresa_id)
                )
                """
            )
        )

        payload = {
            "referencia": "BORME-A-2025-55-37",
            "fecha": "2025-03-20",
            "titulo": "Actos de SALAMANCA del BORME núm. 55 de 2025",
            "tipo_documento": "cambio_domicilio",
            "texto": "ALDITRAEX SOCIEDAD LIMITADA (Sociedad absorbente). MURILLO BARRERO SOCIEDAD LIMITADA (Sociedad absorbida).",
            "url_fuente": "https://www.boe.es/borme/dias/2025/03/20/pdfs/BORME-A-2025-55-37.pdf",
            "empresa_nombre": "ALDITRAEX SOCIEDAD LIMITADA",
            "empresa_domicilio": "C SANTA LUCIA 19",
            "empresas": [
                {"nombre": "ALDITRAEX SOCIEDAD LIMITADA", "domicilio": "C SANTA LUCIA 19", "rol": "absorbente", "confianza_extraccion": 0.7, "nota": "absorcion"},
                {"nombre": "MURILLO BARRERO SOCIEDAD LIMITADA", "domicilio": None, "rol": "absorbida", "confianza_extraccion": 0.7, "nota": "absorcion"},
            ],
        }

        upsert_documento_interpretativo(conn, payload)
        empresas = upsert_empresas(conn, payload)
        link_documento_empresas(conn, payload["referencia"], empresas)

        rows = conn.execute(
            text(
                "SELECT e.nombre, e.domicilio, de.rol, de.confianza_extraccion, de.nota FROM empresa e JOIN documento_empresa de ON de.empresa_id = e.id ORDER BY e.nombre"
            )
        ).fetchall()

    assert rows == [
        ("ALDITRAEX SOCIEDAD LIMITADA", "C SANTA LUCIA 19", "absorbente", 0.7, "absorcion"),
        ("MURILLO BARRERO SOCIEDAD LIMITADA", None, "absorbida", 0.7, "absorcion"),
    ]


def test_run_sync_persists_borme_document_and_metrics(monkeypatch):
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
                CREATE TABLE empresa (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    nif TEXT,
                    domicilio TEXT,
                    fuente_inicial TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (nombre)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE documento_empresa (
                    documento_id INTEGER NOT NULL,
                    empresa_id INTEGER NOT NULL,
                    rol TEXT NOT NULL,
                    confianza_extraccion REAL NOT NULL,
                    nota TEXT,
                    PRIMARY KEY (documento_id, empresa_id)
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
        return httpx.Response(200, content=MINIMAL_BORME_PDF)

    monkeypatch.setattr("borme.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "borme.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    result = run_sync(
        seed_urls=["https://www.boe.es/borme/dias/2025/03/20/pdfs/BORME-A-2025-55-37.pdf"]
    )

    assert result == {"processed": 1, "stored": 1}

    with engine.begin() as conn:
        doc = conn.execute(
            text(
                "SELECT referencia, organismo_emisor, tipo_fuente, ambito, tipo_documento FROM documento_interpretativo WHERE referencia = 'BORME-A-2025-55-37'"
            )
        ).fetchone()
        empresas = conn.execute(
            text("SELECT nombre, domicilio, fuente_inicial FROM empresa ORDER BY nombre")
        ).fetchall()
        enlaces = conn.execute(
            text("SELECT rol, confianza_extraccion FROM documento_empresa ORDER BY rol")
        ).fetchall()
        sync = conn.execute(
            text(
                "SELECT worker, status, documentos_processed, documentos_upserted FROM sync_log ORDER BY id DESC LIMIT 1"
            )
        ).fetchone()

    assert doc == ("BORME-A-2025-55-37", "BORME", "borme", "mercantil", "cambio_domicilio")
    assert empresas == [
        ("ALDITRAEX SOCIEDAD LIMITADA", "C SANTA LUCIA 19", "BORME"),
        ("MURILLO BARRERO SOCIEDAD LIMITADA", None, "BORME"),
    ]
    assert enlaces == [("absorbente", 0.7), ("absorbida", 0.7)]
    assert sync == ("worker-borme", "ok", 1, 1)


def test_upsert_empresa_accepts_positional_conn_payload():
    """Verifica que upsert_empresa(conn, payload) funciona con args posicionales.

    Este test detecta el bug de argumentos swappeados en borme.py:365 donde se
    llamaba upsert_empresa(payload=payload, conn=conn) pero la firma es
    upsert_empresa(conn, payload). La llamada con kwargs swappeadas provocaba
    TypeError: got an unexpected keyword argument 'conn'.
    """
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE empresa (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    nif TEXT,
                    domicilio TEXT,
                    fuente_inicial TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (nombre)
                )
                """
            )
        )

        payload = {
            "empresa_nombre": "TEST EMPRESA SL",
            "empresa_domicilio": "CALLE TEST 1",
        }

        empresa_id = upsert_empresa(conn, payload)

    assert empresa_id is not None
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT nombre, domicilio, fuente_inicial FROM empresa WHERE id = :id"),
            {"id": empresa_id},
        ).fetchone()
    assert row == ("TEST EMPRESA SL", "CALLE TEST 1", "BORME")


def test_run_sync_empty_seed_urls_returns_error_without_http_calls(monkeypatch):
    """Verifica que SEED_URLS vacío produce resultado de error sin hacer HTTP.

    Este test detecta el bug de workers silentemente vacíos: si SEED_URLS
    está vacío, el worker debe abortar inmediatamente con processed=0, stored=0
    y NO debe intentar ninguna llamada HTTP.
    """
    mock_client = type("MockClient", (), {"__enter__": lambda self: self, "__exit__": lambda self, *a: None})()
    monkeypatch.setattr("borme.httpx.Client", lambda *args, **kwargs: mock_client)

    calls_made = []
    result = run_sync(seed_urls=[], worker_name="test-worker")

    assert result == {"processed": 0, "stored": 0}
    assert calls_made == [], "No se debe hacer ninguna llamada HTTP con SEED_URLS vacío"


def test_run_sync_calls_time_sleep_between_requests(monkeypatch):
    """Verifica que se llama a time.sleep entre requests de documentos.

    El rate limiting entre requests al mismo dominio es obligatorio para
    evitar bans por scraping agresivo en BOE, AEAT, TEAC, etc.
    """
    engine = create_engine("sqlite:///:memory:", future=True)
    sleep_calls = []

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
                CREATE TABLE empresa (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    nif TEXT,
                    domicilio TEXT,
                    fuente_inicial TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (nombre)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE documento_empresa (
                    documento_id INTEGER NOT NULL,
                    empresa_id INTEGER NOT NULL,
                    rol TEXT NOT NULL,
                    confianza_extraccion REAL NOT NULL,
                    nota TEXT,
                    PRIMARY KEY (documento_id, empresa_id)
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
        return httpx.Response(200, content=MINIMAL_BORME_PDF)

    # Guardar el original ANTES de monkeypatchear
    _orig_client = httpx.Client
    monkeypatch.setattr("borme.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "borme.httpx",
        type("MockHpxx", (), {"Client": lambda *a, **kw: _orig_client(transport=httpx.MockTransport(handler))}),
    )
    monkeypatch.setattr("borme.time", type("T", (), {"sleep": lambda *a: sleep_calls.append(a[0])})())

    result = run_sync(
        seed_urls=["https://www.boe.es/borme/dias/2025/03/20/pdfs/BORME-A-2025-55-37.pdf"],
    )

    assert result == {"processed": 1, "stored": 1}
    assert len(sleep_calls) >= 1, "Se debe llamar a time.sleep al menos una vez entre requests"
