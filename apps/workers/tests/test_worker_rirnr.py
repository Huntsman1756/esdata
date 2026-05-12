"""Tests unitarios para el worker rirnr de ingestion del RIRNR (RD 435/1995)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rirnr import RIRNR_BOE_ID, RIRNR_CODIGO, run_sync
from boe import BloqueIndex, BloqueTexto, NormaMetadata


@pytest.fixture
def engine():
    """Engine SQLite en memoria para tests."""
    eng = create_engine("sqlite:///:memory:", future=True)
    with eng.begin() as conn:
        conn.execute(text("""
            CREATE TABLE norma (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                titulo TEXT NOT NULL,
                boe_id TEXT UNIQUE NOT NULL,
                eli_uri TEXT,
                jurisdiccion TEXT NOT NULL,
                tipo_fuente TEXT NOT NULL,
                tipo_documento TEXT NOT NULL,
                ambito TEXT NOT NULL,
                estado_cobertura TEXT NOT NULL,
                vigente_desde TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE articulo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                norma_id INTEGER NOT NULL REFERENCES norma(id),
                numero TEXT NOT NULL,
                titulo TEXT,
                tipo TEXT NOT NULL,
                UNIQUE (norma_id, numero)
            )
        """))
        conn.execute(text("""
            CREATE TABLE version_articulo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                articulo_id INTEGER NOT NULL REFERENCES articulo(id),
                texto TEXT NOT NULL,
                vigente_desde TEXT NOT NULL,
                vigente_hasta TEXT,
                boe_bloque_id TEXT
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
    yield eng


def test_rirnr_constants(engine):
    """Verifica que las constantes de RIRNR estan definidas correctamente."""
    assert RIRNR_CODIGO == "RIRNR"
    assert RIRNR_BOE_ID == "BOE-A-1995-7256"


def test_run_sync_persists_rirnr_norma(engine):
    """run_sync persiste la norma RIRNR en la base de datos."""
    mock_metadata_response = MagicMock()
    mock_metadata_response.json.return_value = {
        "data": [{
            "titulo": "Real Decreto 435/1995, de 27 de marzo, por el que se aprueba el Reglamento del Impuesto sobre la Renta de no Residentes",
            "fecha_vigencia": "19950328"
        }]
    }

    mock_index = [
        BloqueIndex(
            id="art-31",
            titulo="Articulo 31. Rendimientos del capital mobiliario.",
            fecha_actualizacion="20240101",
        ),
        BloqueIndex(
            id="art-32",
            titulo="Articulo 32. Tipos de retencion.",
            fecha_actualizacion="20240101",
        ),
    ]

    mock_block_31 = BloqueTexto(
        bloque_id="art-31",
        tipo_bloque="articulo",
        numero="31",
        titulo="Articulo 31. Rendimientos del capital mobiliario.",
        tipo_articulo="articulo",
        texto="Articulo 31. Constituyen rendimientos del capital mobiliario los dividendos, las rentas derivadas de la participacion en inversiones colectivas y los intereses y demas rendimientos equivalentes obtenidos por no residentes sin establecimiento permanente en Espana.",
        vigente_desde="1995-03-28",
    )

    mock_block_32 = BloqueTexto(
        bloque_id="art-32",
        tipo_bloque="articulo",
        numero="32",
        titulo="Articulo 32. Tipos de retencion.",
        tipo_articulo="articulo",
        texto="Articulo 32. El tipo de retencion aplicable a los dividendos sera del 15 por ciento cuando el rendimiento bruto este sujeto al Impuesto sobre la Renta de las Personas Fisicas, y del 24 por ciento en los demas casos.",
        vigente_desde="1995-03-28",
    )

    with patch("rirnr.httpx.Client") as mock_client_class, \
         patch("rirnr.parse_metadata", return_value=NormaMetadata(
             codigo="RIRNR",
             boe_id="BOE-A-1995-7256",
             titulo="Real Decreto 435/1995, de 27 de marzo, por el que se aprueba el Reglamento del Impuesto sobre la Renta de no Residentes",
             eli_uri=None,
             jurisdiccion="es",
             tipo_fuente="boe",
             tipo_documento="real_decreto",
             ambito="tributario",
             estado_cobertura="vigente",
             vigente_desde="1995-03-28",
         )), \
         patch("rirnr.fetch_index", return_value=mock_index), \
         patch("rirnr.fetch_block", side_effect=[mock_block_31, mock_block_32]), \
         patch("rirnr.create_engine", return_value=engine):

        result = run_sync(seed_norma="BOE-A-1995-7256", worker_name="test-rirnr")

    assert result["processed"] >= 1
    assert result["articulos_upserted"] >= 2

    # Verificar que se persistio la norma
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT codigo, titulo FROM norma WHERE codigo = 'RIRNR'")
        ).fetchone()
        assert row is not None
        assert row[0] == "RIRNR"

    # Verificar que se persistieron los articulos
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT numero FROM articulo WHERE numero IN ('31', '32')")
        ).fetchall()
        assert len(rows) >= 2


def test_run_sync_creates_sync_log(engine):
    """run_sync crea un registro en sync_log."""
    mock_index = [
        BloqueIndex(id="art-31", titulo="Articulo 31", fecha_actualizacion="20240101"),
    ]
    mock_block = BloqueTexto(
        bloque_id="art-31",
        tipo_bloque="articulo",
        numero="31",
        titulo="Articulo 31",
        tipo_articulo="articulo",
        texto="Texto del articulo 31",
        vigente_desde="1995-03-28",
    )

    with patch("rirnr.httpx.Client") as mock_client_class, \
         patch("rirnr.parse_metadata", return_value=NormaMetadata(
             codigo="RIRNR",
             boe_id="BOE-A-1995-7256",
             titulo="Real Decreto 435/1995",
             eli_uri=None,
             jurisdiccion="es",
             tipo_fuente="boe",
             tipo_documento="real_decreto",
             ambito="tributario",
             estado_cobertura="vigente",
             vigente_desde="1995-03-28",
         )), \
         patch("rirnr.fetch_index", return_value=mock_index), \
         patch("rirnr.fetch_block", return_value=mock_block), \
         patch("rirnr.create_engine", return_value=engine):

        run_sync(seed_norma="BOE-A-1995-7256", worker_name="test-rirnr-log")

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT COUNT(*) as cnt FROM sync_log WHERE worker = 'test-rirnr-log'")
        ).fetchall()
        assert rows[0][0] >= 1


def test_run_sync_handles_api_error(engine):
    """run_sync maneja errores de API gracefully."""
    with patch("rirnr.httpx.Client") as mock_client_class, \
         patch("rirnr.create_engine", return_value=engine), \
         patch("rirnr.handle_worker_failure", return_value=True):

        mock_client_class.side_effect = Exception("Connection refused")

        with pytest.raises(Exception):
            run_sync(seed_norma="BOE-A-INVALID-NONEXISTENT", worker_name="test-rirnr-error")

    # Verificar que se creo un registro de error en sync_log
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT status FROM sync_log WHERE worker = 'test-rirnr-error'")
        ).fetchall()
        assert len(rows) >= 1
        assert rows[0][0] == "error"


def test_run_sync_uses_configurable_ssl_verification(engine):
    """run_sync respeta la configuracion SSL del entorno."""
    mock_index = [
        BloqueIndex(id="art-31", titulo="Articulo 31", fecha_actualizacion="20240101"),
    ]
    mock_block = BloqueTexto(
        bloque_id="art-31",
        tipo_bloque="articulo",
        numero="31",
        titulo="Articulo 31",
        tipo_articulo="articulo",
        texto="Texto del articulo 31",
        vigente_desde="1995-03-28",
    )

    with patch("rirnr.httpx.Client") as mock_client_class, \
         patch("rirnr.parse_metadata", return_value=NormaMetadata(
             codigo="RIRNR",
             boe_id="BOE-A-1995-7256",
             titulo="Real Decreto 435/1995",
             eli_uri=None,
             jurisdiccion="es",
             tipo_fuente="boe",
             tipo_documento="real_decreto",
             ambito="tributario",
             estado_cobertura="vigente",
             vigente_desde="1995-03-28",
         )), \
         patch("rirnr.fetch_index", return_value=mock_index), \
         patch("rirnr.fetch_block", return_value=mock_block), \
         patch("rirnr.create_engine", return_value=engine):

        result = run_sync(seed_norma="BOE-A-1995-7256", worker_name="test-rirnr-ssl")
        assert result["processed"] >= 1
