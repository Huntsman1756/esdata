"""
Tests for the AEAT models discovery worker.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aeat_models import (
    _discover_aeat_models,
    _extract_model_name,
    _mark_deprecated_models,
    _upsert_aeat_model,
    _get_existing_codes,
)


# ---------------------------------------------------------------------------
# Model name extraction
# ---------------------------------------------------------------------------


class TestExtractModelName:
    def test_simple_code_only(self):
        assert _extract_model_name("", "303") == "Modelo 303"

    def test_text_with_dash_separator(self):
        name = _extract_model_name("303 - IVA trimestral", "303")
        assert "IVA" in name
        assert "trimestral" in name

    def test_text_with_emoji_separator(self):
        name = _extract_model_name("303 – IVA trimestral", "303")
        assert "IVA" in name

    def test_long_text_truncated(self):
        long_text = "303: " + "x" * 300
        name = _extract_model_name(long_text, "303")
        assert len(name) <= 200

    def test_html_entities_replaced(self):
        name = _extract_model_name("100 &amp; IRPF", "100")
        assert "&amp;" not in name
        assert "IRPF" in name


# ---------------------------------------------------------------------------
# Model discovery
# ---------------------------------------------------------------------------


class TestDiscoverAeatModels:
    def test_discovers_models_from_links(self):
        html = """
        <html>
        <body>
            <a href="/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_303_autoliquidacion_ivaversion_abreviada.html">
                303 - IVA trimestral
            </a>
            <a href="/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/is/modelo_200_autoliquidacion_impuesto_sociedades.html">
                200 - Impuesto sobre Sociedades
            </a>
            <a href="/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/irpf/modelo_100_autoliquidacion_irpf.html">
                100 - Declaracion de la Renta
            </a>
        </body>
        </html>
        """
        with patch("aeat_models._fetch", return_value=html):
            result = _discover_aeat_models()

        codigos = {m["codigo"] for m in result}
        assert "303" in codigos
        assert "200" in codigos
        assert "100" in codigos
        assert len(result) == 3

    def test_deduplicates_by_code(self):
        html = """
        <html>
        <body>
            <a href="/modelo_303_first.html">303 - First link</a>
            <a href="/modelo_303_second.html">303 - Second link</a>
            <a href="/modelo_100.html">100 - Renta</a>
        </body>
        </html>
        """
        with patch("aeat_models._fetch", return_value=html):
            result = _discover_aeat_models()

        assert len(result) == 2
        codigos = [m["codigo"] for m in result]
        assert codigos.count("303") == 1

    def test_returns_empty_on_no_html(self):
        with patch("aeat_models._fetch", return_value=None):
            result = _discover_aeat_models()
        assert result == []

    def test_skips_links_without_model_code(self):
        html = """
        <html>
        <body>
            <a href="/general/information.html">Informacion general</a>
            <a href="/other/page.html">Otra pagina</a>
        </body>
        </html>
        """
        with patch("aeat_models._fetch", return_value=html):
            result = _discover_aeat_models()
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
        with patch("aeat_models._fetch", return_value=html):
            result = _discover_aeat_models()

        codigos = {m["codigo"] for m in result}
        assert "123" in codigos
        assert "216" in codigos


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------


class TestUpsertAeatModel:
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

            result = _upsert_aeat_model(
                conn, "303", "IVA trimestral", "https://example.com/303", "trimestral", "IVA"
            )

        assert result is True

        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT codigo, nombre, periodo, impuesto, url_info FROM aeat_modelo WHERE codigo = '303'")
            ).fetchone()

        assert row == ("303", "IVA trimestral", "trimestral", "IVA", "https://example.com/303")

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
                    VALUES ('100', 'Old name', 'anual', 'https://old.url')
                    """
                )
            )

            # Upsert with new data
            _upsert_aeat_model(
                conn, "100", "New name", "https://new.url", "anual", "IRPF"
            )

        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT nombre, url_info, periodo, impuesto FROM aeat_modelo WHERE codigo = '100'")
            ).fetchone()

        assert row == ("New name", "https://new.url", "anual", "IRPF")

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
                    VALUES ('303', 'IVA', 'https://example.com/303', 0)
                    """
                )
            )

            # Upsert should reactivate
            result = _upsert_aeat_model(
                conn, "303", "IVA trimestral", "https://example.com/303"
            )

        assert result is True

        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT activo FROM aeat_modelo WHERE codigo = '303'")
            ).fetchone()

        assert row[0] == 1


class TestMarkDeprecatedModels:
    def test_marks_missing_models_as_deprecated(self):
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
            # Insert 3 models
            for codigo in ["100", "303", "200"]:
                conn.execute(
                    text(
                        """
                        INSERT INTO aeat_modelo (codigo, nombre, activo)
                        VALUES (:codigo, :nombre, 1)
                        """
                    ),
                    {"codigo": codigo, "nombre": f"Modelo {codigo}"},
                )

            # Only 100 and 303 are discovered
            deprecated = _mark_deprecated_models(conn, {"100", "303"})

        assert deprecated == 1

        with engine.begin() as conn:
            rows = conn.execute(
                text("SELECT codigo, activo FROM aeat_modelo ORDER BY codigo")
            ).fetchall()

        assert rows == [("100", 1), ("200", 0), ("303", 1)]

    def test_no_deprecation_when_all_found(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE aeat_modelo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo TEXT UNIQUE NOT NULL,
                        activo INTEGER DEFAULT 1
                    )
                    """
                )
            )
            conn.execute(
                text("INSERT INTO aeat_modelo (codigo) VALUES ('100'), ('303')")
            )

            deprecated = _mark_deprecated_models(conn, {"100", "303"})

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
                        activo INTEGER DEFAULT 1
                    )
                    """
                )
            )
            conn.execute(
                text("INSERT INTO aeat_modelo (codigo) VALUES ('100')")
            )

            # Empty discovered set should not crash
            deprecated = _mark_deprecated_models(conn, set())

        assert deprecated == 0


class TestGetExistingCodes:
    def test_returns_all_codes(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE aeat_modelo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo TEXT UNIQUE NOT NULL
                    )
                    """
                )
            )
            for codigo in ["100", "303", "200", "111"]:
                conn.execute(
                    text("INSERT INTO aeat_modelo (codigo) VALUES (:codigo)"),
                    {"codigo": codigo},
                )

            codes = _get_existing_codes(conn)

        assert codes == {"100", "303", "200", "111"}

    def test_returns_empty_when_table_empty(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE aeat_modelo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo TEXT UNIQUE NOT NULL
                    )
                    """
                )
            )

            codes = _get_existing_codes(conn)

        assert codes == set()
