"""Tests unitarios para el worker prospectos de ingestion del Reglamento UE 2017/1129."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prospectos import (
    PROSPECTOS_NORMA,
    BloqueIndex,
    BloqueTexto,
    _infer_tipo_y_numero,
    _is_supported_block,
    _yyyymmdd_to_iso,
    parse_block_xml,
    run_sync,
    upsert_prospectos_norma,

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

def test_prospectos_norma_constante(engine):
    """Verifica que la norma Prospectos tiene las propiedades correctas."""
    assert PROSPECTOS_NORMA["codigo"] == "PROSPECTOS_2017_1129"
    assert PROSPECTOS_NORMA["tipo_fuente"] == "eurlex"
    assert PROSPECTOS_NORMA["jurisdiccion"] == "ue"
    assert PROSPECTOS_NORMA["tipo_documento"] == "reglamento"
    assert PROSPECTOS_NORMA["ambito"] == "mercados_financieros_ue"


# ====================================================================
# Test: Parse helpers
# ====================================================================

def test_infer_tipo_y_numero_articulo_con_acento():
    """Infer tipo y numero para articulo con accent."""
    tipo, numero = _infer_tipo_y_numero("Artículo 1. Objeto")
    assert tipo == "articulo"
    assert numero == "1"


def test_infer_tipo_y_numero_articulo_sin_acento():
    """Infer tipo y numero para articulo sin accent."""
    tipo, numero = _infer_tipo_y_numero("Articulo 2. Definiciones")
    assert tipo == "articulo"
    assert numero == "2"


def test_infer_tipo_y_numero_disposicion_adicional():
    """Infer tipo y numero para disposicion adicional."""
    tipo, numero = _infer_tipo_y_numero("Disposición adicional primera.")
    assert tipo == "disposicion_adicional"
    assert numero == "primera"


def test_infer_tipo_y_numero_capitulo():
    """Infer tipo y numero para capitulo."""
    tipo, numero = _infer_tipo_y_numero("Capítulo I. Disposiciones generales")
    assert tipo == "capitulo"
    assert numero == "Capítulo I. Disposiciones generales"


def test_infer_tipo_y_numero_seccion():
    """Infer tipo y numero para seccion."""
    tipo, numero = _infer_tipo_y_numero("Sección 2. Emisores de valores")
    assert tipo == "seccion"
    assert numero == "Sección 2. Emisores de valores"


def test_infer_tipo_y_numero_otro():
    """Infer tipo y numero para texto sin prefijo conocido."""
    tipo, numero = _infer_tipo_y_numero("Preámbulo")
    assert tipo == "otro"
    assert numero == "Preámbulo"


def test_is_supported_block_articulo():
    """Verifica que un articulo es un bloque soportado."""
    assert _is_supported_block("Artículo 1. Objeto") is True


def test_is_supported_block_disposicion_final():
    """Verifica que una disposicion final es un bloque soportado."""
    assert _is_supported_block("Disposición final tercera.") is True


def test_is_supported_block_preambulo():
    """Verifica que un preambulo NO es un bloque soportado."""
    assert _is_supported_block("Preámbulo") is False


def test_is_supported_block_exploracion():
    """Verifica que una exploracion NO es un bloque soportado."""
    assert _is_supported_block("Exposición de motivos") is False


def test_yyyymmdd_to_iso():
    """Convierte YYYYMMDD a ISO."""
    assert _yyyymmdd_to_iso("20170607") == "2017-06-07"


# ====================================================================
# Test: parse_block_xml
# ====================================================================

def test_parse_block_xml_articulo():
    """Parsea un bloque XML de articulo de EUR-Lex."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<resultado>
  <bloque tipo="articulo" titulo="Artículo 1. Objeto y ámbito de aplicación">
    <articulo>
      <p>El presente Reglamento establece un procedimiento armonizado para la elaboración, verificación y distribución del prospecto.</p>
      <p>Se adoptarán normas de desarrollo por la Comisión para detallar el contenido del prospecto.</p>
    </articulo>
  </bloque>
  <version fecha_vigencia="20170607" fecha_actualizacion="20240101"/>
</resultado>
"""
    bloque = parse_block_xml("art-1", xml)

    assert bloque.bloque_id == "art-1"
    assert bloque.numero == "1"
    assert bloque.tipo_articulo == "articulo"
    assert "Artículo 1" in bloque.titulo
    assert "2017-06-07" in bloque.vigente_desde
    assert "procedimiento armonizado" in bloque.texto


def test_parse_block_xml_disposicion_final():
    """Parsea un bloque XML de disposicion final."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<resultado>
  <bloque tipo="disposicion_final" titulo="Disposición final primera. Modificaciones del Reglamento (UE) n.º 216/2024">
    <disposicion>
      <p>Se modifica el Reglamento (UE) n.º 216/2024 en el sentido indicado en el anexo.</p>
    </disposicion>
  </bloque>
  <version fecha_vigencia="20240301" fecha_actualizacion="20240301"/>
</resultado>
"""
    bloque = parse_block_xml("df-1", xml)

    assert bloque.tipo_articulo == "disposicion_final"
    assert bloque.numero == "primera"


# ====================================================================
# Test: upsert_prospectos_norma
# ====================================================================

def test_upsert_prospectos_norma_inserts_norma(engine):
    """upsert_prospectos_norma inserta la norma prospectos en la DB."""
    with engine.begin() as conn:
        upsert_prospectos_norma(conn)

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT codigo, titulo, boe_id, jurisdiccion FROM norma WHERE codigo = 'PROSPECTOS_2017_1129'")
        ).fetchone()
        assert row is not None
        assert row[0] == "PROSPECTOS_2017_1129"
        assert "Reglamento" in row[1]
        assert row[2] == "EUR-CELEX-32017R1129"
        assert row[3] == "ue"


def test_upsert_prospectos_norma_is_idempotent(engine):
    """upsert_prospectos_norma es idempotente (no duplica)."""
    with engine.begin() as conn:
        upsert_prospectos_norma(conn)
        upsert_prospectos_norma(conn)

    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM norma WHERE codigo = 'PROSPECTOS_2017_1129'")
        ).scalar()
        assert count == 1


# ====================================================================
# Test: run_sync (mocking EUR-Lex API)
# ====================================================================

def test_run_sync_persists_prospectos_norma_and_articles(engine):
    """run_sync persiste la norma Prospectos y sus articulos."""
    mock_index = [
        BloqueIndex(
            id="art-1",
            titulo="Artículo 1. Objeto y ámbito de aplicación",
            fecha_actualizacion="20240101",
        ),
        BloqueIndex(
            id="art-3",
            titulo="Artículo 3. Contenido del prospecto",
            fecha_actualizacion="20240101",
        ),
        BloqueIndex(
            id="art-10",
            titulo="Artículo 10. Resumen",
            fecha_actualizacion="20240101",
        ),
    ]

    mock_block_1 = BloqueTexto(
        bloque_id="art-1",
        tipo_bloque="articulo",
        numero="1",
        titulo="Artículo 1. Objeto y ámbito de aplicación",
        tipo_articulo="articulo",
        texto="El presente Reglamento establece un procedimiento armonizado para la elaboración del prospecto.",
        vigente_desde="2017-06-07",
    )

    mock_block_3 = BloqueTexto(
        bloque_id="art-3",
        tipo_bloque="articulo",
        numero="3",
        titulo="Artículo 3. Contenido del prospecto",
        tipo_articulo="articulo",
        texto="El prospecto contiene la información necesaria para que los inversores puedan tomar una decisión informada.",
        vigente_desde="2017-06-07",
    )

    mock_block_10 = BloqueTexto(
        bloque_id="art-10",
        tipo_bloque="articulo",
        numero="10",
        titulo="Artículo 10. Resumen",
        tipo_articulo="articulo",
        texto="El resumen debe contener la información clave sobre el emisor y los valores que se ofrecen.",
        vigente_desde="2017-06-07",
    )

    with patch("prospectos.httpx.Client") as mock_client_class, \
         patch("prospectos.fetch_index", return_value=mock_index), \
         patch("prospectos.fetch_block", side_effect=[mock_block_1, mock_block_3, mock_block_10]), \
         patch("prospectos.create_engine", return_value=engine):

        result = run_sync(worker_name="test-prospectos")

    assert result["bloques"] == 3
    assert result["articulos"] == 3

    # Verificar que se persistió la norma
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT codigo, titulo FROM norma WHERE codigo = 'PROSPECTOS_2017_1129'")
        ).fetchone()
        assert row is not None
        assert row[0] == "PROSPECTOS_2017_1129"

    # Verificar que se persistieron los articulos
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT numero FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'PROSPECTOS_2017_1129')")
        ).fetchall()
        numeros = [r[0] for r in rows]
        assert "1" in numeros
        assert "3" in numeros
        assert "10" in numeros


def test_run_sync_creates_sync_log(engine):
    """run_sync crea un registro en sync_log."""
    mock_index = [
        BloqueIndex(id="art-1", titulo="Artículo 1", fecha_actualizacion="20240101"),
    ]
    mock_block = BloqueTexto(
        bloque_id="art-1",
        tipo_bloque="articulo",
        numero="1",
        titulo="Artículo 1",
        tipo_articulo="articulo",
        texto="Texto del artículo 1",
        vigente_desde="2017-06-07",
    )

    with patch("prospectos.httpx.Client"), \
         patch("prospectos.fetch_index", return_value=mock_index), \
         patch("prospectos.fetch_block", return_value=mock_block), \
         patch("prospectos.create_engine", return_value=engine):

        run_sync(worker_name="test-prospectos-log")

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT status, bloques_processed FROM sync_log WHERE worker = 'test-prospectos-log'")
        ).fetchall()
        assert len(rows) >= 1
        assert rows[0][0] == "ok"
        assert rows[0][1] == 1


def test_run_sync_handles_api_error(engine):
    """run_sync maneja errores de API gracefully y registra error en sync_log."""
    with patch("prospectos.httpx.Client") as mock_client_class, \
         patch("prospectos.create_engine", return_value=engine):

        mock_client_class.side_effect = Exception("Connection refused to EUR-Lex")

        with pytest.raises(Exception):
            run_sync(worker_name="test-prospectos-error")

    # Verificar que se creó un registro de error en sync_log
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT status, error_msg FROM sync_log WHERE worker = 'test-prospectos-error'")
        ).fetchall()
        assert len(rows) >= 1
        assert rows[0][0] == "error"
        assert "Connection refused" in rows[0][1]


def test_run_sync_skips_unsupported_blocks(engine):
    """run_sync ignora bloques que no son articulos (preambulo, exposicion, etc.)."""
    mock_index = [
        BloqueIndex(id="pre", titulo="Exposición de motivos", fecha_actualizacion="20240101"),
        BloqueIndex(id="art-1", titulo="Artículo 1. Objeto", fecha_actualizacion="20240101"),
        BloqueIndex(id="exp", titulo="Considerando 5", fecha_actualizacion="20240101"),
        BloqueIndex(id="art-3", titulo="Artículo 3. Contenido", fecha_actualizacion="20240101"),
    ]

    mock_block_1 = BloqueTexto(
        bloque_id="art-1",
        tipo_bloque="articulo",
        numero="1",
        titulo="Artículo 1. Objeto",
        tipo_articulo="articulo",
        texto="Artículo 1",
        vigente_desde="2017-06-07",
    )

    mock_block_3 = BloqueTexto(
        bloque_id="art-3",
        tipo_bloque="articulo",
        numero="3",
        titulo="Artículo 3. Contenido",
        tipo_articulo="articulo",
        texto="Artículo 3",
        vigente_desde="2017-06-07",
    )

    with patch("prospectos.httpx.Client"), \
         patch("prospectos.fetch_index", return_value=mock_index), \
         patch("prospectos.fetch_block", side_effect=[mock_block_1, mock_block_3]), \
         patch("prospectos.create_engine", return_value=engine):

        result = run_sync(worker_name="test-prospectos-skips")

    assert result["bloques"] == 2
    assert result["articulos"] == 2

    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'PROSPECTOS_2017_1129')")
        ).scalar()
        assert count == 2


def test_run_sync_empty_index_returns_zero(engine):
    """run_sync con index vacio retorna cero articulos."""
    with patch("prospectos.httpx.Client"), \
         patch("prospectos.fetch_index", return_value=[]), \
         patch("prospectos.create_engine", return_value=engine):

        result = run_sync(worker_name="test-prospectos-empty")

    assert result["bloques"] == 0
    assert result["articulos"] == 0

    # La norma se persiste aunque no haya articulos
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT codigo FROM norma WHERE codigo = 'PROSPECTOS_2017_1129'")
        ).fetchone()
        assert row is not None
