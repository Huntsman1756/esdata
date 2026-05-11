"""
Tests for the IRNR models discovery worker.
"""

import sys
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aeat_irnr import (
    _discover_irnr_models,
    _extract_model_name,
    _extract_instruction_sections,
    _extract_irnr_rate_rows,
    _get_existing_codes,
    _mark_deprecated_irnr_models,
    _upsert_irnr_model,
    _upsert_irnr_instructions,
    _upsert_irnr_rates,
)

# ---------------------------------------------------------------------------
# Model name extraction
# ---------------------------------------------------------------------------


class TestExtractModelName:
    def test_simple_code_only(self):
        assert _extract_model_name("", "116") == "Modelo 116"

    def test_text_with_dash_separator(self):
        name = _extract_model_name("123 - Rendimientos IRNR", "123")
        assert "Rendimientos" in name
        assert "IRNR" in name

    def test_text_with_emoji_separator(self):
        name = _extract_model_name("124 – Dividendos", "124")
        assert "Dividendos" in name

    def test_long_text_truncated(self):
        long_text = "116: " + "x" * 300
        name = _extract_model_name(long_text, "116")
        assert len(name) <= 200

    def test_html_entities_replaced(self):
        name = _extract_model_name("296 &amp; Retenciones", "296")
        assert "&amp;" not in name
        assert "Retenciones" in name


class TestExtractInstructionSections:
    def test_extracts_official_page_text_with_source(self):
        html = """
        <html>
        <body>
          <header>Menu</header>
          <main>
            <h1>Modelo 210</h1>
            <h2>Información</h2>
            <p>Instrucciones oficiales para presentar el modelo 210.</p>
            <h2>Normativa</h2>
            <p>Orden EHA/3316/2010.</p>
          </main>
        </body>
        </html>
        """

        result = _extract_instruction_sections(
            html,
            "Modelo 210. IRNR",
            "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GF00.shtml",
        )

        assert len(result) == 1
        assert result[0]["seccion"] == "portal_aeat_modelo"
        assert result[0]["source_family"] == "AEAT official portal"
        assert "Fuente oficial AEAT" in result[0]["contenido"]
        assert "Orden EHA/3316/2010" in result[0]["contenido"]


class TestExtractIrnrRateRows:
    def test_extracts_current_aeat_rate_rows(self):
        html = """
        <html><body>
        <h1>Tipos de gravamen en el IRNR sin establecimiento permanente</h1>
        <p>Dividendos y otros rendimientos derivados de la participación en fondos propios.</p>
        <p>Intereses y otros rendimientos obtenidos por la cesión a terceros de capitales propios.</p>
        <p>Pensiones y demás prestaciones similares.</p>
        <p>Página actualizada: 18/junio/2025</p>
        </body></html>
        """

        result = _extract_irnr_rate_rows(html)

        tipos = {row["tipo_renta"]: row["tipo_retencion"] for row in result}
        assert tipos["general_ue_islandia_noruega"] == 19.0
        assert tipos["general_resto_contribuyentes"] == 24.0
        assert tipos["trabajo_temporada"] == 2.0
        assert tipos["reaseguro"] == 1.5
        assert all("AEAT official portal" in row["source_family"] for row in result)


# ---------------------------------------------------------------------------
# Model discovery
# ---------------------------------------------------------------------------


class TestDiscoverIrrnModels:
    def test_discovers_irnr_models_from_links(self):
        html = """
        <html>
        <body>
            <a href="/Sede/procedimientoini/GF00.shtml">
                Modelo 210. IRNR sin establecimiento permanente
            </a>
            <a href="/Sede/procedimientoini/GF01.shtml">
                Modelo 211. Retencion adquisicion inmuebles
            </a>
            <a href="/Sede/procedimientoini/GF05.shtml">
                Modelo 216. Retenciones IRNR
            </a>
        </body>
        </html>
        """
        with patch("aeat_irnr._fetch", return_value=html):
            result = _discover_irnr_models()

        codigos = {m["codigo"] for m in result}
        assert "210" in codigos
        assert "211" in codigos
        assert "216" in codigos
        assert len(result) == 3

    def test_discovers_all_irnr_modelos(self):
        html = """
        <html>
        <body>
            <a href="/modelo-210-test.html">Modelo 210. Sin establecimiento permanente</a>
            <a href="/modelo-211-test.html">Modelo 211. Retencion inmuebles</a>
            <a href="/modelo-213-test.html">Modelo 213. Gravamen especial</a>
            <a href="/modelo-216-test.html">Modelo 216. Retenciones</a>
            <a href="/modelo-226-test.html">Modelo 226. Regimen opcional</a>
            <a href="/modelo-228-test.html">Modelo 228. Devolucion reinversion</a>
            <a href="/modelo-247-test.html">Modelo 247. Desplazamiento</a>
            <a href="/modelo-296-test.html">Modelo 296. Resumen anual</a>
        </body>
        </html>
        """
        with patch("aeat_irnr._fetch", return_value=html):
            result = _discover_irnr_models()

        codigos = {m["codigo"] for m in result}
        assert codigos == {"210", "211", "213", "216", "226", "228", "247", "296"}
        assert len(result) == 8

    def test_deduplicates_by_code(self):
        html = """
        <html>
        <body>
            <a href="/modelo_210_first.html">Modelo 210. First link</a>
            <a href="/modelo_210_second.html">Modelo 210. Second link</a>
            <a href="/modelo_216.html">Modelo 216. Retenciones</a>
        </body>
        </html>
        """
        with patch("aeat_irnr._fetch", return_value=html):
            result = _discover_irnr_models()

        assert len(result) == 2
        codigos = [m["codigo"] for m in result]
        assert codigos.count("210") == 1

    def test_returns_empty_on_no_html(self):
        with patch("aeat_irnr._fetch", return_value=None):
            result = _discover_irnr_models()
        assert result == []

    def test_skips_non_irnr_models(self):
        html = """
        <html>
        <body>
            <a href="/modelo_303_test.html">303 - IVA trimestral</a>
            <a href="/modelo_200_test.html">200 - Impuesto sociedades</a>
            <a href="/modelo_100_test.html">100 - IRPF</a>
        </body>
        </html>
        """
        with patch("aeat_irnr._fetch", return_value=html):
            result = _discover_irnr_models()
        assert result == []

    def test_text_only_pattern(self):
        html = """
        <html>
        <body>
            <a href="/generic.html">Modelo 210. IRNR</a>
            <a href="/generic2.html">216 - Retenciones no residentes</a>
        </body>
        </html>
        """
        with patch("aeat_irnr._fetch", return_value=html):
            result = _discover_irnr_models()

        codigos = {m["codigo"] for m in result}
        assert "210" in codigos
        assert "216" in codigos


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------


class TestUpsertIrrnModel:
    def test_upsert_new_model(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE aeat_modelo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo TEXT UNIQUE NOT NULL,
                        nombre TEXT,
                        periodo TEXT,
                        impuesto TEXT,
                        url_info TEXT,
                        activo INTEGER DEFAULT 1,
                        actualizado_at TEXT
                    )
                    """
                )
            )

            result = _upsert_irnr_model(
                conn, "123", "Rendimientos IRNR", "https://example.com/123",
                "anual", "IRNR"
            )

        assert result is True

        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT codigo, nombre, periodo, impuesto, url_info FROM aeat_modelo WHERE codigo = '123'")
            ).fetchone()

        assert row == ("123", "Rendimientos IRNR", "anual", "IRNR", "https://example.com/123")

    def test_upsert_irnr_instructions(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE irnr_instruccion (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        modelo_id INTEGER NOT NULL,
                        seccion TEXT NOT NULL,
                        titulo TEXT NOT NULL,
                        contenido TEXT,
                        source_url TEXT,
                        source_family TEXT,
                        actualizado_en TEXT,
                        UNIQUE (modelo_id, seccion)
                    )
                    """
                )
            )

            result = _upsert_irnr_instructions(
                conn,
                1,
                [
                    {
                        "seccion": "portal_aeat_modelo",
                        "titulo": "Modelo 210",
                        "contenido": "Fuente oficial AEAT",
                        "source_url": "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GF00.shtml",
                        "source_family": "AEAT official portal",
                    }
                ],
            )

        assert result == 1

        with engine.begin() as conn:
            row = conn.execute(
                text(
                    "SELECT seccion, source_family FROM irnr_instruccion WHERE modelo_id = 1"
                )
            ).fetchone()

        assert row == ("portal_aeat_modelo", "AEAT official portal")

    def test_upsert_irnr_rates(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE irnr_withholding_rate (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        modelo_id INTEGER NOT NULL,
                        tipo_renta TEXT NOT NULL,
                        tipo_retencion FLOAT NOT NULL,
                        articulo_referencia TEXT,
                        fuente_texto TEXT,
                        source_url TEXT,
                        source_family TEXT,
                        effective_date TEXT,
                        legal_basis TEXT,
                        uncertainty_notes TEXT,
                        activo BOOLEAN DEFAULT 1,
                        actualizado_en TEXT,
                        UNIQUE (modelo_id, tipo_renta)
                    )
                    """
                )
            )

            result = _upsert_irnr_rates(
                conn,
                1,
                [
                    {
                        "tipo_renta": "general_resto_contribuyentes",
                        "tipo_retencion": 24.0,
                        "articulo_referencia": "art. 25 TRLIRNR",
                        "fuente_texto": "Resto contribuyentes: 24%",
                        "source_url": "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/tipos-gravamen-irnr-sin-establecimiento-permanente.html",
                        "source_family": "AEAT official portal; BOE official text",
                        "effective_date": None,
                        "legal_basis": "Artículo 25 TRLIRNR",
                        "uncertainty_notes": "Test",
                    }
                ],
            )

        assert result == 1

        with engine.begin() as conn:
            row = conn.execute(
                text(
                    "SELECT tipo_renta, tipo_retencion, source_family FROM irnr_withholding_rate WHERE modelo_id = 1"
                )
            ).fetchone()

        assert row == (
            "general_resto_contribuyentes",
            24.0,
            "AEAT official portal; BOE official text",
        )

    def test_upsert_updates_existing_model(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE aeat_modelo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo TEXT UNIQUE NOT NULL,
                        nombre TEXT,
                        periodo TEXT,
                        impuesto TEXT,
                        url_info TEXT,
                        activo INTEGER DEFAULT 1,
                        actualizado_at TEXT
                    )
                    """
                )
            )
            # Insert initial record
            conn.execute(
                text(
                    """
                    INSERT INTO aeat_modelo (codigo, nombre, periodo, url_info)
                    VALUES ('123', 'Old name', 'anual', 'https://old.url')
                    """
                )
            )

            # Upsert with new data
            _upsert_irnr_model(
                conn, "123", "New name", "https://new.url", "trimestral", "IRNR"
            )

        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT nombre, url_info, periodo, impuesto FROM aeat_modelo WHERE codigo = '123'")
            ).fetchone()

        assert row == ("New name", "https://new.url", "trimestral", "IRNR")

    def test_upsert_reactivates_deprecated_model(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE aeat_modelo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo TEXT UNIQUE NOT NULL,
                        nombre TEXT,
                        periodo TEXT,
                        impuesto TEXT,
                        url_info TEXT,
                        activo INTEGER DEFAULT 1,
                        actualizado_at TEXT
                    )
                    """
                )
            )
            # Insert as inactive (deprecated)
            conn.execute(
                text(
                    """
                    INSERT INTO aeat_modelo (codigo, nombre, url_info, activo)
                    VALUES ('123', 'IRNR', 'https://example.com/123', 0)
                    """
                )
            )

            # Upsert should reactivate
            result = _upsert_irnr_model(
                conn, "123", "Rendimientos IRNR", "https://example.com/123"
            )

        assert result is True

        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT activo FROM aeat_modelo WHERE codigo = '123'")
            ).fetchone()

        assert row[0] == 1


class TestMarkDeprecatedIrrnModels:
    def test_marks_missing_irnr_models_as_deprecated(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE aeat_modelo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo TEXT UNIQUE NOT NULL,
                        nombre TEXT,
                        impuesto TEXT,
                        activo INTEGER DEFAULT 1,
                        actualizado_at TEXT
                    )
                    """
                )
            )
            # Insert IRNR models: 123, 124, 216 (all IRNR) + 303 (IVA)
            for codigo, impuesto in [("123", "IRNR"), ("124", "IRNR"), ("216", "IRNR"), ("303", "IVA")]:
                conn.execute(
                    text(
                        """
                        INSERT INTO aeat_modelo (codigo, nombre, impuesto, activo)
                        VALUES (:codigo, :nombre, :impuesto, 1)
                        """
                    ),
                    {"codigo": codigo, "nombre": f"Modelo {codigo}", "impuesto": impuesto},
                )

            # Only 123 and 124 are discovered; 216 should be marked deprecated
            deprecated = _mark_deprecated_irnr_models(conn, {"123", "124"})

        assert deprecated == 1

        with engine.begin() as conn:
            rows = conn.execute(
                text("SELECT codigo, activo, impuesto FROM aeat_modelo ORDER BY codigo")
            ).fetchall()

        # 303 (IVA) should NOT be marked deprecated because it's not IRNR
        assert rows[0] == ("123", 1, "IRNR")
        assert rows[1] == ("124", 1, "IRNR")
        assert rows[2] == ("216", 0, "IRNR")
        assert rows[3] == ("303", 1, "IVA")

    def test_no_deprecation_when_all_found(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE aeat_modelo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo TEXT UNIQUE NOT NULL,
                        impuesto TEXT,
                        activo INTEGER DEFAULT 1
                    )
                    """
                )
            )
            conn.execute(
                text("INSERT INTO aeat_modelo (codigo, impuesto) VALUES ('123', 'IRNR'), ('124', 'IRNR')")
            )

            deprecated = _mark_deprecated_irnr_models(conn, {"123", "124"})

        assert deprecated == 0

    def test_no_deprecation_when_no_discovered(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE aeat_modelo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo TEXT UNIQUE NOT NULL,
                        impuesto TEXT,
                        activo INTEGER DEFAULT 1
                    )
                    """
                )
            )
            conn.execute(
                text("INSERT INTO aeat_modelo (codigo, impuesto) VALUES ('123', 'IRNR')")
            )

            # Empty discovered set should not crash
            deprecated = _mark_deprecated_irnr_models(conn, set())

        assert deprecated == 0


class TestGetExistingCodes:
    def test_returns_irnr_codes(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE aeat_modelo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo TEXT UNIQUE NOT NULL,
                        impuesto TEXT
                    )
                    """
                )
            )
            for codigo, impuesto in [("123", "IRNR"), ("124", "IRNR"), ("303", "IVA"), ("216", "IRNR")]:
                conn.execute(
                    text("INSERT INTO aeat_modelo (codigo, impuesto) VALUES (:codigo, :impuesto)"),
                    {"codigo": codigo, "impuesto": impuesto},
                )

            codes = _get_existing_codes(conn)

        assert codes == {"123", "124", "216"}

    def test_returns_empty_when_table_empty(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE aeat_modelo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo TEXT UNIQUE NOT NULL,
                        impuesto TEXT
                    )
                    """
                )
            )

            codes = _get_existing_codes(conn)

        assert codes == set()
