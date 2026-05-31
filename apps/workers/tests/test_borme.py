# ruff: noqa: I001

import sys
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from borme import (
    build_document_payload,
    discover_borme_pdf_urls,
    _extract_person_appointments,
    _extract_borme_pdf_urls_from_summary,
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


def test_extract_borme_pdf_urls_from_summary_skips_daily_summary_pdf():
    payload = {
        "status": {"code": "200", "text": "ok"},
        "data": {
            "sumario": {
                "diario": [
                    {
                        "sumario_diario": {
                            "identificador": "BORME-S-2026-88",
                            "url_pdf": {
                                "texto": "https://www.boe.es/borme/dias/2026/05/11/pdfs/BORME-S-2026-88.pdf"
                            },
                        },
                        "seccion": [
                            {
                                "item": [
                                    {
                                        "identificador": "BORME-A-2026-88-02",
                                        "url_pdf": {
                                            "texto": "https://www.boe.es/borme/dias/2026/05/11/pdfs/BORME-A-2026-88-02.pdf"
                                        },
                                    },
                                    {
                                        "identificador": "BORME-B-2026-88-02",
                                        "url_pdf": {
                                            "texto": "https://www.boe.es/borme/dias/2026/05/11/pdfs/BORME-B-2026-88-02.pdf"
                                        },
                                    },
                                ]
                            }
                        ],
                    }
                ]
            }
        },
    }

    assert _extract_borme_pdf_urls_from_summary(payload) == [
        "https://www.boe.es/borme/dias/2026/05/11/pdfs/BORME-A-2026-88-02.pdf",
        "https://www.boe.es/borme/dias/2026/05/11/pdfs/BORME-B-2026-88-02.pdf",
    ]


def test_discover_borme_pdf_urls_uses_official_summary_api():
    original_client = httpx.Client
    seen_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(
            200,
            json={
                "status": {"code": "200", "text": "ok"},
                "data": {
                    "sumario": {
                        "diario": [
                            {
                                "seccion": [
                                    {
                                        "item": [
                                            {
                                                "identificador": "BORME-A-2026-88-02",
                                                "url_pdf": {
                                                    "texto": "https://www.boe.es/borme/dias/2026/05/11/pdfs/BORME-A-2026-88-02.pdf"
                                                },
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                },
            },
        )

    with original_client(transport=httpx.MockTransport(handler)) as client:
        urls = discover_borme_pdf_urls(
            client,
            days_back=1,
            max_urls=10,
            today=date(2026, 5, 11),
        )

    assert seen_urls == ["https://www.boe.es/datosabiertos/api/borme/sumario/20260511"]
    assert urls == [
        "https://www.boe.es/borme/dias/2026/05/11/pdfs/BORME-A-2026-88-02.pdf"
    ]


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


def test_extract_person_appointments_detects_cargo_and_person_from_official_text():
    appointments = _extract_person_appointments(
        "Nombramientos. Adm. Unico: ALVAREZ GARCIA JOSE MARIA. "
        "Datos registrales. T 100, F 20."
    )

    assert appointments == [
        {
            "nombre": "ALVAREZ GARCIA JOSE MARIA",
            "cargo": "administrador_unico",
            "confianza_extraccion": 0.72,
            "nota": "Extraccion heuristica desde BORME",
        }
    ]


def test_build_document_payload_includes_borme_structured_metadata():
    payload = build_document_payload(
        "https://www.boe.es/borme/dias/2025/03/20/pdfs/BORME-A-2025-55-37.pdf",
        MINIMAL_BORME_PDF,
    )

    assert payload["row_completeness"] == "partial"
    assert payload["row_provenance"] == "official_best_effort"
    assert payload["metadata"]["source_kind"] == "official_borme_pdf"
    assert payload["metadata"]["companies_extracted"] >= 2


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
                    url_fuente TEXT,
                    metadata TEXT,
                    row_completeness TEXT,
                    row_provenance TEXT
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
            "metadata": {
                "source_kind": "official_borme_pdf",
                "appointments": [
                    {
                        "nombre": "ALVAREZ GARCIA JOSE MARIA",
                        "cargo": "administrador_unico",
                    }
                ],
            },
            "row_completeness": "partial",
            "row_provenance": "official_best_effort",
        }

        upsert_documento_interpretativo(conn, payload)
        upsert_documento_interpretativo(conn, payload)

        row = conn.execute(
            text(
                "SELECT referencia, tipo_documento, organismo_emisor, tipo_fuente, ambito, metadata, row_completeness, row_provenance, COUNT(*) FROM documento_interpretativo GROUP BY referencia, tipo_documento, organismo_emisor, tipo_fuente, ambito, metadata, row_completeness, row_provenance"
            )
        ).fetchone()

    assert row == (
        "BORME-A-2025-55-37",
        "nombramiento",
        "BORME",
        "borme",
        "mercantil",
        '{"appointments": [{"cargo": "administrador_unico", "nombre": "ALVAREZ GARCIA JOSE MARIA"}], "source_kind": "official_borme_pdf"}',
        "partial",
        "official_best_effort",
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
    """Explicit empty URL input must write sync telemetry and avoid HTTP."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
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

    class MockClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, *args, **kwargs):
            raise AssertionError("No HTTP calls expected with explicit empty seed_urls")

    monkeypatch.setattr("borme.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("borme.httpx.Client", lambda *args, **kwargs: MockClient())

    result = run_sync(seed_urls=[], worker_name="test-worker")

    assert result == {"processed": 0, "stored": 0}
    with engine.begin() as conn:
        sync = conn.execute(
            text(
                "SELECT worker, status, documentos_processed, documentos_upserted, error_msg FROM sync_log ORDER BY id DESC LIMIT 1"
            )
        ).fetchone()

    assert sync[0:4] == ("test-worker", "partial", 0, 0)
    assert "No BORME PDF URLs discovered" in sync[4]


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
