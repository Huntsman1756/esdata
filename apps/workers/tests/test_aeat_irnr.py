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
    _get_existing_codes,
    _mark_deprecated_irnr_models,
    _upsert_irnr_model,
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


# ---------------------------------------------------------------------------
# Model discovery
# ---------------------------------------------------------------------------


class TestDiscoverIrrnModels:
    def test_discovers_irnr_models_from_links(self):
        html = """
        <html>
        <body>
            <a href="/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_123_irnr.html">
                123 - Rendimientos IRNR
            </a>
            <a href="/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_124_dividendos.html">
                124 - Dividendos
            </a>
            <a href="/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_216_facta.html">
                216 - FactA no residentes
            </a>
        </body>
        </html>
        """
        with patch("aeat_irnr._fetch", return_value=html):
            result = _discover_irnr_models()

        codigos = {m["codigo"] for m in result}
        assert "123" in codigos
        assert "124" in codigos
        assert "216" in codigos
        assert len(result) == 3

    def test_discovers_all_irnr_modelos(self):
        html = """
        <html>
        <body>
            <a href="/modelo_116_test.html">116 - Actividades</a>
            <a href="/modelo_123_test.html">123 - Rendimientos</a>
            <a href="/modelo_124_test.html">124 - Dividendos</a>
            <a href="/modelo_212_test.html">212 - Dividendos empresas</a>
            <a href="/modelo_216_test.html">216 - FactA</a>
            <a href="/modelo_296_test.html">296 - Resumen</a>
            <a href="/modelo_878_test.html">878 - Proveedores</a>
        </body>
        </html>
        """
        with patch("aeat_irnr._fetch", return_value=html):
            result = _discover_irnr_models()

        codigos = {m["codigo"] for m in result}
        assert codigos == {"116", "123", "124", "212", "216", "296", "878"}
        assert len(result) == 7

    def test_deduplicates_by_code(self):
        html = """
        <html>
        <body>
            <a href="/modelo_123_first.html">123 - First link</a>
            <a href="/modelo_123_second.html">123 - Second link</a>
            <a href="/modelo_216.html">216 - FactA</a>
        </body>
        </html>
        """
        with patch("aeat_irnr._fetch", return_value=html):
            result = _discover_irnr_models()

        assert len(result) == 2
        codigos = [m["codigo"] for m in result]
        assert codigos.count("123") == 1

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
            <a href="/generic.html">123 - Rendimientos IRNR</a>
            <a href="/generic2.html">216 - FactA no residentes</a>
        </body>
        </html>
        """
        with patch("aeat_irnr._fetch", return_value=html):
            result = _discover_irnr_models()

        codigos = {m["codigo"] for m in result}
        assert "123" in codigos
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
