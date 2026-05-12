"""Tests unitarios para el worker de Ley 13/2023 (regulacion IA).

Cubre: constantes, parse helpers, upsert norma, parsing XML de bloques,
run_sync con API mock, idempotencia y manejo de errores.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ley13_2023 import (
    LEY13_2023_NORMA,
    BloqueIndex,
    BloqueTexto,
    _infer_tipo_y_numero,
    _is_supported_block,
    _yyyymmdd_to_iso,
    parse_block_xml,
    run_sync,
    upsert_ley13_norma,
)


# ====================================================================
# Fixtures
# ====================================================================

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
                error_msg TEXT
            )
        """))
    yield eng


# ====================================================================
# Test: Constantes
# ====================================================================

def test_ley13_norma_constante():
    """Verifica que la norma Ley 13/2023 tiene las propiedades correctas."""
    assert LEY13_2023_NORMA["codigo"] == "LEY13_2023"
    assert LEY13_2023_NORMA["boe_id"] == "BOE-A-2023-23080"
    assert LEY13_2023_NORMA["tipo_fuente"] == "boe"
    assert LEY13_2023_NORMA["jurisdiccion"] == "es"
    assert LEY13_2023_NORMA["tipo_documento"] == "ley"
    assert LEY13_2023_NORMA["ambito"] == "ia_regulacion"


# ====================================================================
# Test: Parse helpers
# ====================================================================

def test_infer_tipo_y_numero_articulo_con_acento():
    tipo, numero = _infer_tipo_y_numero("Artículo 1. Objeto")
    assert tipo == "articulo"
    assert numero == "1"


def test_infer_tipo_y_numero_articulo_sin_acento():
    tipo, numero = _infer_tipo_y_numero("Articulo 2. Definiciones")
    assert tipo == "articulo"
    assert numero == "2"


def test_infer_tipo_y_numero_disposicion_adicional():
    tipo, numero = _infer_tipo_y_numero("Disposición adicional primera.")
    assert tipo == "disposicion_adicional"
    assert numero == "primera"


def test_infer_tipo_y_numero_disposicion_transitoria():
    tipo, numero = _infer_tipo_y_numero("Disposición transitoria segunda.")
    assert tipo == "disposicion_transitoria"
    assert numero == "segunda"


def test_infer_tipo_y_numero_disposicion_final():
    tipo, numero = _infer_tipo_y_numero("Disposición final tercera.")
    assert tipo == "disposicion_final"
    assert numero == "tercera"


def test_infer_tipo_y_numero_disposicion_derogatoria():
    tipo, numero = _infer_tipo_y_numero("Disposición derogatoria única.")
    assert tipo == "disposicion_derogatoria"
    assert numero == "única"


def test_infer_tipo_y_numero_otro():
    tipo, numero = _infer_tipo_y_numero("Preámbulo")
    assert tipo == "otro"
    assert numero == "Preámbulo"


def test_is_supported_block_articulo():
    assert _is_supported_block("Artículo 1. Objeto") is True


def test_is_supported_block_disposicion_final():
    assert _is_supported_block("Disposición final primera.") is True


def test_is_supported_block_disposicion_transitoria():
    assert _is_supported_block("Disposición transitoria segunda.") is True


def test_is_supported_block_preambulo():
    assert _is_supported_block("Preámbulo") is False


def test_is_supported_block_exploracion():
    assert _is_supported_block("Exposición de motivos") is False


def test_yyyymmdd_to_iso():
    assert _yyyymmdd_to_iso("20231122") == "2023-11-22"


# ====================================================================
# Test: parse_block_xml
# ====================================================================

def test_parse_block_xml_articulo():
    """Parsea un bloque XML de articulo del BOE."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<resultado>
  <bloque tipo="articulo" titulo="Artículo 1. Objeto y ámbito de aplicación">
    <articulo>
      <p>La presente ley tiene por objeto establecer el régimen jurídico de regulación de la inteligencia artificial.</p>
      <p>Se aplicará a los sistemas de IA desarrollados o utilizados en España.</p>
    </articulo>
  </bloque>
  <version fecha_vigencia="20231122" fecha_actualizacion="20231122"/>
</resultado>
"""
    bloque = parse_block_xml("BOE-2023-1", xml)

    assert bloque.bloque_id == "BOE-2023-1"
    assert bloque.numero == "1"
    assert bloque.tipo_articulo == "articulo"
    assert "Artículo 1" in bloque.titulo
    assert "2023-11-22" in bloque.vigente_desde
    assert "régimen jurídico" in bloque.texto


def test_parse_block_xml_disposicion_final():
    """Parsea un bloque XML de disposicion final."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<resultado>
  <bloque tipo="disposicion_final" titulo="Disposición final primera. Modificaciones">
    <disposicion>
      <p>Se modifica el Reglamento (UE) en el sentido indicado en el anexo.</p>
    </disposicion>
  </bloque>
  <version fecha_vigencia="20231122" fecha_actualizacion="20231122"/>
</resultado>
"""
    bloque = parse_block_xml("BOE-DF-1", xml)

    assert bloque.tipo_articulo == "disposicion_final"
    assert bloque.numero == "primera"


# ====================================================================
# Test: upsert_ley13_norma
# ====================================================================

def test_upsert_ley13_norma_inserts_norma(engine):
    """upsert_ley13_norma inserta la norma en la DB."""
    with engine.begin() as conn:
        upsert_ley13_norma(conn)

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT codigo, titulo, boe_id, jurisdiccion FROM norma WHERE codigo = 'LEY13_2023'")
        ).fetchone()
        assert row is not None
        assert row[0] == "LEY13_2023"
        assert "Ley 13/2023" in row[1]
        assert row[2] == "BOE-A-2023-23080"
        assert row[3] == "es"


def test_upsert_ley13_norma_is_idempotent(engine):
    """upsert_ley13_norma es idempotente (no duplica)."""
    with engine.begin() as conn:
        upsert_ley13_norma(conn)
        upsert_ley13_norma(conn)

    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM norma WHERE codigo = 'LEY13_2023'")
        ).scalar()
        assert count == 1


# ====================================================================
# Test: run_sync (mocking BOE API)
# ====================================================================

def test_run_sync_persists_ley13_norma_and_articles(engine):
    """run_sync persiste la norma Ley 13/2023 y sus articulos."""
    mock_index = [
        BloqueIndex(
            id="BOE-ART-1",
            titulo="Artículo 1. Objeto y ámbito de aplicación",
            fecha_actualizacion="20231122",
        ),
        BloqueIndex(
            id="BOE-ART-3",
            titulo="Artículo 3. Requisitos de transparencia",
            fecha_actualizacion="20231122",
        ),
        BloqueIndex(
            id="BOE-ART-12",
            titulo="Artículo 12. Régimen sancionador",
            fecha_actualizacion="20231122",
        ),
    ]

    mock_block_1 = BloqueTexto(
        bloque_id="BOE-ART-1",
        tipo_bloque="articulo",
        numero="1",
        titulo="Artículo 1. Objeto y ámbito de aplicación",
        tipo_articulo="articulo",
        texto="La presente ley establece el régimen de regulación de la IA.",
        vigente_desde="2023-11-23",
    )

    mock_block_3 = BloqueTexto(
        bloque_id="BOE-ART-3",
        tipo_bloque="articulo",
        numero="3",
        titulo="Artículo 3. Requisitos de transparencia",
        tipo_articulo="articulo",
        texto="Los sistemas de IA deberan proporcionar información transparente.",
        vigente_desde="2023-11-23",
    )

    mock_block_12 = BloqueTexto(
        bloque_id="BOE-ART-12",
        tipo_bloque="articulo",
        numero="12",
        titulo="Artículo 12. Régimen sancionador",
        tipo_articulo="articulo",
        texto="Las infracciones se sancionaran conforme a esta ley.",
        vigente_desde="2023-11-23",
    )

    with patch("ley13_2023.httpx.Client"), \
         patch("ley13_2023.fetch_index", return_value=mock_index), \
         patch("ley13_2023.fetch_block", side_effect=[mock_block_1, mock_block_3, mock_block_12]), \
         patch("ley13_2023.create_engine", return_value=engine):

        result = run_sync(worker_name="test-ley13-2023")

    assert result["bloques"] == 3
    assert result["articulos"] == 3

    # Verificar que se persistió la norma
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT codigo, titulo FROM norma WHERE codigo = 'LEY13_2023'")
        ).fetchone()
        assert row is not None
        assert row[0] == "LEY13_2023"

    # Verificar que se persistieron los articulos
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT numero FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'LEY13_2023')")
        ).fetchall()
        numeros = [r[0] for r in rows]
        assert "1" in numeros
        assert "3" in numeros
        assert "12" in numeros


def test_run_sync_creates_sync_log(engine):
    """run_sync crea un registro en sync_log."""
    mock_index = [
        BloqueIndex(id="BOE-ART-1", titulo="Artículo 1", fecha_actualizacion="20231122"),
    ]
    mock_block = BloqueTexto(
        bloque_id="BOE-ART-1",
        tipo_bloque="articulo",
        numero="1",
        titulo="Artículo 1",
        tipo_articulo="articulo",
        texto="Texto del artículo 1",
        vigente_desde="2023-11-23",
    )

    with patch("ley13_2023.httpx.Client"), \
         patch("ley13_2023.fetch_index", return_value=mock_index), \
         patch("ley13_2023.fetch_block", return_value=mock_block), \
         patch("ley13_2023.create_engine", return_value=engine):

        run_sync(worker_name="test-ley13-2023-log")

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT status, bloques_processed FROM sync_log WHERE worker = 'test-ley13-2023-log'")
        ).fetchall()
        assert len(rows) >= 1
        assert rows[0][0] == "ok"
        assert rows[0][1] == 1


def test_run_sync_handles_api_error(engine):
    """run_sync maneja errores de API gracefully y registra error en sync_log."""
    with patch("ley13_2023.httpx.Client") as mock_client_class, \
         patch("ley13_2023.create_engine", return_value=engine), \
         patch("ley13_2023.handle_worker_failure", return_value=True):

        mock_client_class.side_effect = Exception("Connection refused to BOE API")

        with pytest.raises(Exception):
            run_sync(worker_name="test-ley13-2023-error")

    # Verificar que se creó un registro de error en sync_log
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT status, error_msg FROM sync_log WHERE worker = 'test-ley13-2023-error'")
        ).fetchall()
        assert len(rows) >= 1
        assert rows[0][0] == "error"
        assert "Connection refused" in rows[0][1]


def test_run_sync_skips_unsupported_blocks(engine):
    """run_sync ignora bloques que no son articulos (preambulo, exposicion, etc.)."""
    mock_index = [
        BloqueIndex(id="BOE-PRE", titulo="Exposición de motivos", fecha_actualizacion="20231122"),
        BloqueIndex(id="BOE-ART-1", titulo="Artículo 1. Objeto", fecha_actualizacion="20231122"),
        BloqueIndex(id="BOE-CON", titulo="Considerando 5", fecha_actualizacion="20231122"),
        BloqueIndex(id="BOE-ART-3", titulo="Artículo 3. Contenido", fecha_actualizacion="20231122"),
    ]

    mock_block_1 = BloqueTexto(
        bloque_id="BOE-ART-1",
        tipo_bloque="articulo",
        numero="1",
        titulo="Artículo 1. Objeto",
        tipo_articulo="articulo",
        texto="Artículo 1",
        vigente_desde="2023-11-23",
    )

    mock_block_3 = BloqueTexto(
        bloque_id="BOE-ART-3",
        tipo_bloque="articulo",
        numero="3",
        titulo="Artículo 3. Contenido",
        tipo_articulo="articulo",
        texto="Artículo 3",
        vigente_desde="2023-11-23",
    )

    with patch("ley13_2023.httpx.Client"), \
         patch("ley13_2023.fetch_index", return_value=mock_index), \
         patch("ley13_2023.fetch_block", side_effect=[mock_block_1, mock_block_3]), \
         patch("ley13_2023.create_engine", return_value=engine):

        result = run_sync(worker_name="test-ley13-2023-skips")

    assert result["bloques"] == 2
    assert result["articulos"] == 2

    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'LEY13_2023')")
        ).scalar()
        assert count == 2


def test_run_sync_empty_index_uses_synthetic_fallback(engine):
    """run_sync con index vacio usa fallback sintetico (19 bloques)."""
    with patch("ley13_2023.httpx.Client"), \
         patch("ley13_2023.fetch_index", return_value=[]), \
         patch("ley13_2023.create_engine", return_value=engine):

        result = run_sync(worker_name="test-ley13-2023-empty")

    # El worker usa dataset sintetico de 19 bloques como fallback
    assert result["bloques"] == 19
    assert result["articulos"] == 19

    # La norma se persiste aunque no haya datos del BOE
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT codigo FROM norma WHERE codigo = 'LEY13_2023'")
        ).fetchone()
        assert row is not None
