import importlib
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

cendoj = importlib.import_module("cendoj")
build_document_payload = cendoj.build_document_payload
upsert_documento_interpretativo = cendoj.upsert_documento_interpretativo


CENDOJ_HTML = b"""
<html>
  <body>
    <h1>Sentencia del Tribunal Supremo 12345/2024</h1>
    <p>Recurso sobre IVA y obligacion tributaria.</p>
  </body>
</html>
"""


def test_build_document_payload_extracts_court_type_and_ambito():
    payload = build_document_payload(
        "https://www.poderjudicial.es/search/AN/openDocument/abc123",
        CENDOJ_HTML,
    )

    assert payload["tipo_fuente"] == "cendoj"
    assert payload["tipo_documento"] == "sentencia"
    assert payload["court"] == "tribunal_supremo"
    assert payload["ambito"] == "jurisprudencia_tributaria"
    assert payload["referencia"] == "CENDOJ-abc123"


def test_upsert_documento_interpretativo_normalizes_tsj_to_tribunal_supremo():
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
            "referencia": "CENDOJ-abc123",
            "fecha": "2026-05-04",
            "titulo": "Sentencia TSJ 1/2026",
            "texto": "Texto de ejemplo.",
            "url_fuente": "https://www.poderjudicial.es/search/TSJ/openDocument/abc123",
            "tipo_documento": "sentencia",
            "organismo_emisor": "TSJ",
            "jurisdiccion": "es",
            "tipo_fuente": "cendoj",
            "ambito": "jurisprudencia_tributaria",
        }

        upsert_documento_interpretativo(conn, payload)
        row = conn.execute(
            text(
                "SELECT tipo_documento, organismo_emisor, tipo_fuente, ambito "
                "FROM documento_interpretativo WHERE referencia = 'CENDOJ-abc123'"
            )
        ).fetchone()

    assert row == (
        "sentencia",
        "Tribunal Supremo",
        "cendoj",
        "jurisprudencia_tributaria",
    )


def test_run_sync_empty_seed_urls_returns_zero():
    """SEED_URLS vacío debe devolver processed=0, stored=0 sin hacer HTTP."""
    from cendoj import run_sync

    result = run_sync(seed_urls=[])
    assert result == {"processed": 0, "stored": 0}
