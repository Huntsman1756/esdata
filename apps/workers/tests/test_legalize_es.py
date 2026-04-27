"""Tests para worker legalize-es: parser, upsert e idempotencia."""

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from legalize_es import parse_markdown_norma, run_sync


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "legalize_es"
FIXTURE_CC = FIXTURE_DIR / "cc.md"
FIXTURE_LEC = FIXTURE_DIR / "lec.md"
FIXTURE_ET = FIXTURE_DIR / "et.md"
FIXTURE_LSC = FIXTURE_DIR / "lsc.md"
FIXTURE_LC = FIXTURE_DIR / "lc.md"
FIXTURE_IRPF = FIXTURE_DIR / "irpf.md"


def _create_schema(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE norma (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                titulo TEXT NOT NULL,
                boe_id TEXT,
                eli_uri TEXT,
                jurisdiccion TEXT NOT NULL,
                tipo_fuente TEXT NOT NULL,
                tipo_documento TEXT NOT NULL,
                ambito TEXT NOT NULL,
                estado_cobertura TEXT NOT NULL,
                vigente_desde TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE articulo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                norma_id INTEGER NOT NULL,
                numero TEXT NOT NULL,
                titulo TEXT,
                tipo TEXT NOT NULL,
                UNIQUE (norma_id, numero)
            )
        """))
        conn.execute(text("""
            CREATE TABLE version_articulo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                articulo_id INTEGER NOT NULL,
                texto TEXT NOT NULL,
                vigente_desde TEXT NOT NULL,
                vigente_hasta TEXT,
                boe_bloque_id TEXT
            )
        """))


def test_parse_markdown_norma_extracts_cc_articles():
    parsed = parse_markdown_norma(FIXTURE_CC)

    assert parsed["codigo"] == "CC"
    assert parsed["titulo"] == "Codigo Civil"
    assert parsed["vigente_desde"] == "2025-01-01"
    assert len(parsed["articulos"]) == 2
    assert parsed["articulos"][0]["numero"] == "1"
    assert "fuentes del ordenamiento juridico" in parsed["articulos"][0]["texto"].lower()


def test_parse_markdown_norma_extracts_lec_articles():
    parsed = parse_markdown_norma(FIXTURE_LEC)

    assert parsed["codigo"] == "LEC"
    assert parsed["titulo"] == "Ley de Enjuiciamiento Civil"
    assert parsed["vigente_desde"] == "2025-01-01"
    assert len(parsed["articulos"]) == 2
    assert parsed["articulos"][0]["numero"] == "1"


def test_parse_markdown_norma_extracts_et_articles():
    parsed = parse_markdown_norma(FIXTURE_ET)

    assert parsed["codigo"] == "ET"
    assert parsed["titulo"] == "Estatuto de los Trabajadores"
    assert parsed["vigente_desde"] == "2025-01-01"
    assert len(parsed["articulos"]) == 2
    assert parsed["articulos"][0]["numero"] == "1"


def test_run_sync_upserts_norma_articulo_and_version_once():
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_schema(engine)

    result_first = run_sync(engine, fixture_paths=[FIXTURE_CC])
    result_second = run_sync(engine, fixture_paths=[FIXTURE_CC])

    with engine.begin() as conn:
        norma_count = conn.execute(text("SELECT COUNT(*) FROM norma WHERE codigo = 'CC'" )).scalar_one()
        articulo_count = conn.execute(text("SELECT COUNT(*) FROM articulo" )).scalar_one()
        version_count = conn.execute(text("SELECT COUNT(*) FROM version_articulo" )).scalar_one()

    assert result_first["normas_upserted"] == 1
    assert result_first["articulos_upserted"] == 2
    assert result_first["versiones_upserted"] == 2
    assert result_second["normas_upserted"] == 0
    assert result_second["articulos_upserted"] == 0
    assert result_second["versiones_upserted"] == 0
    assert norma_count == 1
    assert articulo_count == 2
    assert version_count == 2


def test_run_sync_multi_norma_cc_lec_et():
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_schema(engine)

    result = run_sync(engine, fixture_paths=[FIXTURE_CC, FIXTURE_LEC, FIXTURE_ET])

    with engine.begin() as conn:
        norma_count = conn.execute(text("SELECT COUNT(*) FROM norma")).scalar_one()
        articulo_count = conn.execute(text("SELECT COUNT(*) FROM articulo")).scalar_one()
        version_count = conn.execute(text("SELECT COUNT(*) FROM version_articulo")).scalar_one()
        codigos = conn.execute(text("SELECT codigo FROM norma ORDER BY codigo")).scalars().all()

    assert result["normas_upserted"] == 3
    assert result["articulos_upserted"] == 6
    assert result["versiones_upserted"] == 6
    assert norma_count == 3
    assert articulo_count == 6
    assert version_count == 6
    assert codigos == ["CC", "ET", "LEC"]


def test_parse_markdown_norma_extracts_lsc_articles():
    parsed = parse_markdown_norma(FIXTURE_LSC)

    assert parsed["codigo"] == "LSC"
    assert parsed["titulo"] == "Ley de Sociedades de Capital"
    assert parsed["vigente_desde"] == "2025-01-01"
    assert len(parsed["articulos"]) == 3
    assert parsed["articulos"][0]["numero"] == "1"


def test_parse_markdown_norma_extracts_lc_articles():
    parsed = parse_markdown_norma(FIXTURE_LC)

    assert parsed["codigo"] == "LC"
    assert parsed["titulo"] == "Ley Concursal"
    assert parsed["vigente_desde"] == "2025-01-01"
    assert len(parsed["articulos"]) == 3
    assert parsed["articulos"][0]["numero"] == "1"


def test_parse_markdown_norma_extracts_irpf_articles():
    parsed = parse_markdown_norma(FIXTURE_IRPF)

    assert parsed["codigo"] == "LIRPF"
    assert parsed["titulo"] == "Ley del Impuesto sobre la Renta de las Personas Físicas"
    assert parsed["vigente_desde"] == "2025-01-01"
    assert len(parsed["articulos"]) == 3
    assert parsed["articulos"][0]["numero"] == "1"


def test_run_sync_all_six_normas():
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_schema(engine)

    result = run_sync(engine, fixture_paths=[FIXTURE_CC, FIXTURE_LEC, FIXTURE_ET, FIXTURE_LSC, FIXTURE_LC, FIXTURE_IRPF])

    with engine.begin() as conn:
        norma_count = conn.execute(text("SELECT COUNT(*) FROM norma")).scalar_one()
        articulo_count = conn.execute(text("SELECT COUNT(*) FROM articulo")).scalar_one()
        version_count = conn.execute(text("SELECT COUNT(*) FROM version_articulo")).scalar_one()
        codigos = conn.execute(text("SELECT codigo FROM norma ORDER BY codigo")).scalars().all()

    assert result["normas_upserted"] == 6
    assert result["articulos_upserted"] == 15
    assert result["versiones_upserted"] == 15
    assert norma_count == 6
    assert articulo_count == 15
    assert version_count == 15
    assert codigos == ["CC", "ET", "LC", "LEC", "LIRPF", "LSC"]
