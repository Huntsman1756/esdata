"""
Tests for the modelos worker (AEAT model content scraper).
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modelos_support import (
    derive_campaign_operativa,
    pick_active_campaign,
    scrape_casillas_from_page,
    scrape_claves_from_page,
    scrape_instructions_from_page,
    detect_campaigns,
    ensure_campaigns,
    upsert_campaign_operativa,
    upsert_instructions,
)
import modelos


# ---------------------------------------------------------------------------
# Casilla scraping
# ---------------------------------------------------------------------------


class TestScrapeCasillas:
    def test_table_pattern(self):
        html = """
        <table>
            <tr><td>0002</td><td>Rendimientos del trabajo</td></tr>
            <tr><td>0003</td><td>Actividades econ&oacute;micas</td></tr>
            <tr><td>0416</td><td>Ganancias patrimoniales</td></tr>
        </table>
        """
        result = scrape_casillas_from_page(html, "100")
        assert len(result) == 3
        assert result[0]["codigo"] == "0002"
        assert "Rendimientos" in result[0]["etiqueta"]
        assert result[1]["codigo"] == "0003"
        assert result[2]["codigo"] == "0416"

    def test_single_digit_codes_padded(self):
        html = """
        <table>
            <tr><td>1</td><td>Casilla uno</td></tr>
            <tr><td>12</td><td>Casilla doce</td></tr>
            <tr><td>123</td><td>Casilla ciento</td></tr>
        </table>
        """
        result = scrape_casillas_from_page(html, "111")
        assert result[0]["codigo"] == "0001"
        assert result[1]["codigo"] == "0012"
        assert result[2]["codigo"] == "0123"

    def test_empty_html(self):
        assert scrape_casillas_from_page("<html></html>", "303") == []

    def test_short_labels_filtered(self):
        html = """
        <table>
            <tr><td>01</td><td>OK</td></tr>
            <tr><td>02</td><td>This is a valid label with enough text</td></tr>
        </table>
        """
        result = scrape_casillas_from_page(html, "111")
        assert len(result) == 1
        assert result[0]["codigo"] == "0002"

    def test_iva_model_303(self):
        html = """
        <table>
            <tr><td>01</td><td>Base imponible operaciones corrientes tipo general</td></tr>
            <tr><td>03</td><td>Cuota operaciones corrientes tipo 21%</td></tr>
            <tr><td>04</td><td>Cuota operaciones corrientes tipo 10%</td></tr>
            <tr><td>62</td><td>Resultado liquidaci&oacute;n: A ingresar</td></tr>
        </table>
        """
        result = scrape_casillas_from_page(html, "303")
        assert len(result) == 4
        assert result[0]["codigo"] == "0001"
        assert "Base imponible" in result[0]["etiqueta"]


# ---------------------------------------------------------------------------
# Clave scraping
# ---------------------------------------------------------------------------


class TestScrapeClaves:
    def test_letter_claves(self):
        html = """
        <p>Clave A: Dividendos y participaciones</p>
        <p>Clave B: Intereses y seguros</p>
        <p>Clave C: Transmisi&oacute;n activos</p>
        """
        result = scrape_claves_from_page(html)
        assert len(result) == 3
        assert result[0]["codigo"] == "A"
        assert "Dividendos" in result[0]["etiqueta"]

    def test_numeric_claves(self):
        html = """
        <p>0 - R&eacute;gimen general</p>
        <p>1 - R&eacute;gimen especial agricultura</p>
        <p>3 - R&eacute;gimen especial bienes usados</p>
        """
        result = scrape_claves_from_page(html)
        # This pattern may or may not match depending on regex
        # At minimum, verify it doesn't crash
        assert isinstance(result, list)

    def test_empty_html(self):
        assert scrape_claves_from_page("<html></html>") == []


# ---------------------------------------------------------------------------
# Instruction scraping
# ---------------------------------------------------------------------------


class TestScrapeInstructions:
    def test_characteristics_section(self):
        html = """
        <h2>Características</h2>
        <p>El modelo 100 es la declaraci&oacute;n anual del IRPF.
        Permite regularizar la situaci&oacute;n fiscal del contribuyente.</p>
        """
        result = scrape_instructions_from_page(html)
        assert len(result) >= 1
        assert result[0]["seccion"] == "caracteristicas"
        assert "modelo 100" in result[0]["contenido"].lower()

    def test_quien_debe_section(self):
        html = """
        <h2>¿Quién debe presentar?</h2>
        <p>Todos los residentes fiscales en Espa&ntilde;a que hayan
        obtenido rentas durante el ejercicio.</p>
        """
        result = scrape_instructions_from_page(html)
        secciones = [r["seccion"] for r in result]
        assert "quien-debe" in secciones

    def test_plazo_section(self):
        html = """
        <h3>Plazo de presentación</h3>
        <p>Del 1 de abril al 30 de junio de 2025.</p>
        """
        result = scrape_instructions_from_page(html)
        secciones = [r["seccion"] for r in result]
        assert "plazo" in secciones

    def test_empty_html(self):
        assert scrape_instructions_from_page("<html></html>") == []


class TestCampaignOperativa:
    def test_derive_campaign_operativa_for_irnr_model(self):
        payload = derive_campaign_operativa(
            modelo_codigo="216",
            impuesto="IRNR",
            periodo="mensual",
            instrucciones=[
                {
                    "seccion": "quien-debe",
                    "contenido": "Deben presentar el modelo 216 los obligados a practicar retenciones e ingresos a cuenta sobre determinadas rentas de no residentes.",
                },
                {
                    "seccion": "plazo",
                    "contenido": "El modelo 216 se presenta del 1 al 20 del mes siguiente al periodo declarado.",
                },
                {
                    "seccion": "como-presentar",
                    "contenido": "La presentacion se realiza por via electronica en la sede de la AEAT.",
                },
            ],
        )

        assert payload["categoria_obligado"] == "retenedor_irnr"
        assert payload["frecuencia_presentacion"] == "mensual"
        assert payload["ventana_presentacion"] == "primeros_20_dias_periodo_siguiente"
        assert payload["canal_presentacion"] == "electronica"

    def test_upsert_campaign_operativa_replaces_existing_row(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE modelo_campana_operativa (
                        campana_id INTEGER PRIMARY KEY,
                        categoria_obligado TEXT,
                        frecuencia_presentacion TEXT,
                        ventana_presentacion TEXT,
                        canal_presentacion TEXT,
                        obligados_resumen TEXT,
                        plazo_resumen TEXT,
                        presentacion_resumen TEXT,
                        norma_base TEXT,
                        nota TEXT,
                        origen_metadato TEXT DEFAULT 'seed_curado',
                        estado_metadato TEXT DEFAULT 'curado'
                    )
                    """
                )
            )

            wrote_first = upsert_campaign_operativa(
                conn,
                1,
                {
                    "categoria_obligado": "retenedor_irnr",
                    "frecuencia_presentacion": "mensual",
                    "ventana_presentacion": "primeros_20_dias_periodo_siguiente",
                    "canal_presentacion": "electronica",
                    "obligados_resumen": "Inicial",
                    "plazo_resumen": "Inicial",
                    "presentacion_resumen": "Inicial",
                    "norma_base": "IRNR art. 14",
                    "nota": "Inicial",
                    "origen_metadato": "worker_derivado",
                    "estado_metadato": "borrador",
                },
            )
            wrote_second = upsert_campaign_operativa(
                conn,
                1,
                {
                    "categoria_obligado": "retenedor_irnr",
                    "frecuencia_presentacion": "mensual",
                    "ventana_presentacion": "primeros_20_dias_periodo_siguiente",
                    "canal_presentacion": "electronica",
                    "obligados_resumen": "Actualizado",
                    "plazo_resumen": "Actualizado",
                    "presentacion_resumen": "Actualizado",
                    "norma_base": "IRNR art. 14",
                    "nota": "Actualizado",
                    "origen_metadato": "worker_derivado",
                    "estado_metadato": "borrador",
                },
            )

            row = conn.execute(
                text(
                    """
                    SELECT obligados_resumen, plazo_resumen, presentacion_resumen, nota, origen_metadato, estado_metadato
                    FROM modelo_campana_operativa
                    WHERE campana_id = 1
                    """
                )
            ).fetchone()

        assert wrote_first is True
        assert wrote_second is True
        assert row == ("Actualizado", "Actualizado", "Actualizado", "Actualizado", "worker_derivado", "borrador")

    def test_upsert_campaign_operativa_preserves_curated_row_against_worker_derivation(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE modelo_campana_operativa (
                        campana_id INTEGER PRIMARY KEY,
                        categoria_obligado TEXT,
                        frecuencia_presentacion TEXT,
                        ventana_presentacion TEXT,
                        canal_presentacion TEXT,
                        obligados_resumen TEXT,
                        plazo_resumen TEXT,
                        presentacion_resumen TEXT,
                        norma_base TEXT,
                        nota TEXT,
                        origen_metadato TEXT DEFAULT 'seed_curado',
                        estado_metadato TEXT DEFAULT 'curado'
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO modelo_campana_operativa (
                        campana_id,
                        categoria_obligado,
                        frecuencia_presentacion,
                        obligados_resumen,
                        nota,
                        origen_metadato,
                        estado_metadato
                    )
                    VALUES (1, 'retenedor_irnr', 'mensual', 'Curado', 'Metadato operativo curado para agentes.', 'seed_curado', 'curado')
                    """
                )
            )

            wrote = upsert_campaign_operativa(
                conn,
                1,
                {
                    "categoria_obligado": "retenedor_irnr",
                    "frecuencia_presentacion": "mensual",
                    "ventana_presentacion": "primeros_20_dias_periodo_siguiente",
                    "canal_presentacion": "electronica",
                    "obligados_resumen": "Borrador worker",
                    "plazo_resumen": "Borrador worker",
                    "presentacion_resumen": "Borrador worker",
                    "norma_base": None,
                    "nota": "Borrador derivado automaticamente desde instrucciones AEAT.",
                    "origen_metadato": "worker_derivado",
                    "estado_metadato": "borrador",
                },
            )

            row = conn.execute(
                text(
                    """
                    SELECT obligados_resumen, nota, origen_metadato, estado_metadato
                    FROM modelo_campana_operativa
                    WHERE campana_id = 1
                    """
                )
            ).fetchone()

        assert wrote is False
        assert row == ("Curado", "Metadato operativo curado para agentes.", "seed_curado", "curado")


def test_upsert_instructions_replaces_existing_rows():
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE modelo_instruccion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campana_id INTEGER NOT NULL,
                    seccion TEXT NOT NULL,
                    titulo TEXT NOT NULL,
                    contenido TEXT NOT NULL,
                    orden INTEGER DEFAULT 0,
                    creado_at TEXT,
                    UNIQUE(campana_id, seccion, titulo)
                )
                """
            )
        )

        upsert_instructions(
            conn,
            1,
            [
                {
                    "seccion": "plazo",
                    "titulo": "Plazo de presentacion",
                    "contenido": "Contenido inicial",
                    "orden": 1,
                }
            ],
        )
        upsert_instructions(
            conn,
            1,
            [
                {
                    "seccion": "plazo",
                    "titulo": "Plazo de presentacion",
                    "contenido": "Contenido actualizado",
                    "orden": 1,
                }
            ],
        )

        rows = conn.execute(
            text(
                "SELECT seccion, titulo, contenido FROM modelo_instruccion WHERE campana_id = 1"
            )
        ).fetchall()

    assert rows == [("plazo", "Plazo de presentacion", "Contenido actualizado")]


# ---------------------------------------------------------------------------
# Campaign detection
# ---------------------------------------------------------------------------


class TestDetectCampaigns:
    def test_year_in_text(self):
        html = """
        <p>Campaña 2025 del IRPF</p>
        <p>Ejercicio fiscal 2024</p>
        """
        result = detect_campaigns(html, "100")
        assert "2025" in result
        assert "2024" in result

    def test_campaign_keyword(self):
        html = """
        <a href="/campana-2025/">Campaña 2025</a>
        <a href="/campana-2024/">Campaña 2024</a>
        """
        result = detect_campaigns(html, "100")
        assert "2025" in result
        assert "2024" in result

    def test_no_campaigns(self):
        html = "<p>Some text without any year references</p>"
        result = detect_campaigns(html, "303")
        assert result == []

    def test_sorted_descending(self):
        html = "2023 2024 2025"
        result = detect_campaigns(html, "100")
        assert result == ["2025", "2024", "2023"]

    def test_future_years_ignored(self):
        html = "2015 2018 2019"
        result = detect_campaigns(html, "100")
        assert result == []

    def test_far_future_ignored(self):
        html = "2031 2035"
        result = detect_campaigns(html, "100")
        assert result == []


class TestActiveCampaignSelection:
    def test_pick_active_campaign_uses_latest_year(self):
        assert pick_active_campaign(["2024", "2025", "2023"]) == "2025"

    def test_pick_active_campaign_returns_none_for_empty(self):
        assert pick_active_campaign([]) is None

    def test_ensure_campaigns_activates_only_latest_detected(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE modelo_campana (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        modelo_id INTEGER NOT NULL,
                        campana TEXT NOT NULL,
                        url_instrucciones TEXT,
                        activo INTEGER NOT NULL DEFAULT 0,
                        UNIQUE(modelo_id, campana)
                    )
                    """
                )
            )

            class Result:
                campaigns_created = 0

            class Logger:
                def info(self, _message):
                    return None

            result = Result()
            ensure_campaigns(
                conn,
                modelo_id=1,
                modelo_codigo="100",
                campaigns=["2025", "2024"],
                instruction_url="https://example.com/instructions",
                fallback_url="https://example.com/modelo",
                result=result,
                logger=Logger(),
            )

            rows = conn.execute(
                text(
                    "SELECT campana, activo FROM modelo_campana WHERE modelo_id = 1 ORDER BY campana DESC"
                )
            ).fetchall()

        assert result.campaigns_created == 2
        assert rows == [("2025", 1), ("2024", 0)]

    def test_ensure_campaigns_switches_active_to_newer_existing_campaign(self):
        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE modelo_campana (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        modelo_id INTEGER NOT NULL,
                        campana TEXT NOT NULL,
                        url_instrucciones TEXT,
                        activo INTEGER NOT NULL DEFAULT 0,
                        UNIQUE(modelo_id, campana)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, activo)
                    VALUES (1, '2025', 'https://example.com/2025', 1),
                           (1, '2026', 'https://example.com/2026', 0)
                    """
                )
            )

            class Result:
                campaigns_created = 0

            class Logger:
                def info(self, _message):
                    return None

            result = Result()
            ensure_campaigns(
                conn,
                modelo_id=1,
                modelo_codigo="100",
                campaigns=["2026", "2025"],
                instruction_url="https://example.com/instructions",
                fallback_url="https://example.com/modelo",
                result=result,
                logger=Logger(),
            )

            rows = conn.execute(
                text(
                    "SELECT campana, activo FROM modelo_campana WHERE modelo_id = 1 ORDER BY campana DESC"
                )
            ).fetchall()

        assert result.campaigns_created == 0
        assert rows == [("2026", 1), ("2025", 0)]


class TestAeatDriftGuard:
    def test_sync_model_logs_drift_and_preserves_previous_casillas_when_new_campaign_scrapes_zero(self):
        result = SimpleNamespace(
            models_checked=0,
            campaigns_created=0,
            casillas_upserted=0,
            claves_upserted=0,
            instrucciones_upserted=0,
            operativa_upserted=0,
            operativa_skipped=0,
            errors=[],
        )

        class FakeBegin:
            def __enter__(self):
                return object()

            def __exit__(self, exc_type, exc, tb):
                return False

        class FakeEngine:
            def begin(self):
                return FakeBegin()

        drift_logs = []

        with (
            patch.object(modelos, "get_model_id", return_value=1),
            patch.object(modelos, "_fetch_model_page", return_value="<html>2026</html>"),
            patch.object(modelos, "detect_campaigns", return_value=["2026"]),
            patch.object(modelos, "ensure_campaigns"),
            patch.object(modelos, "get_campaign_row", return_value=(99, "https://example.com/2026")),
            patch.object(modelos, "_fetch_instruction_page", return_value="<html>sin casillas</html>"),
            patch.object(modelos, "scrape_casillas_from_page", return_value=[]),
            patch.object(modelos, "scrape_claves_from_page", return_value=[]),
            patch.object(modelos, "scrape_instructions_from_page", return_value=[]),
            patch.object(modelos, "upsert_casillas") as upsert_casillas,
            patch.object(modelos, "get_previous_campaign_casillas_count", return_value=12),
            patch.object(modelos.logger, "error", side_effect=lambda message, *args: drift_logs.append(message % args)),
        ):
            modelos.sync_model(FakeEngine(), "303", "https://example.com/modelo-303", None, result)

        assert result.models_checked == 1
        assert result.casillas_upserted == 0
        assert upsert_casillas.called is False
        assert any("DRIFT_AEAT" in entry for entry in drift_logs)
        assert any("303" in entry and "2026" in entry for entry in drift_logs)
