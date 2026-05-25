"""
Tests for the AEAT models discovery worker.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aeat_models
from aeat_models import (
    FallbackRequired,
    HttpxClient,
    PlaywrightClient,
    _classify_resource,
    _discover_aeat_models,
    _extract_model_name,
    _get_existing_codes,
    _infer_campaign,
    _infer_impuesto,
    _is_official_model_resource,
    _mark_deprecated_models,
    _normalize_aeat_url,
    _record_sync_log,
    _store_modelo_recurso_version,
    _upsert_aeat_model,
    get_portal_client,
)


class TestInferCampaign:
    def test_modelo_290_gi38_uses_previous_year_not_fatca_agreement_year(self):
        text = (
            "Modelo 290. Declaracion informativa anual FATCA. "
            "Acuerdo hecho en Madrid el 14 de mayo de 2013."
        )

        campaign = _infer_campaign(
            text,
            "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI38.shtml",
            today=aeat_models.datetime(2026, 5, 25, tzinfo=aeat_models.UTC),
        )

        assert campaign == "2025"

    def test_annual_information_web_service_models_use_previous_year(self):
        for url, text in (
            (
                "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI42.shtml",
                "Modelo 289. Declaracion informativa anual de cuentas financieras.",
            ),
            (
                "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI53.shtml",
                "Modelo 172. Declaracion informativa anual sobre saldos en monedas virtuales.",
            ),
            (
                "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI54.shtml",
                "Modelo 173. Declaracion informativa anual sobre operaciones con monedas virtuales.",
            ),
        ):
            assert (
                _infer_campaign(
                    text,
                    url,
                    today=aeat_models.datetime(2026, 5, 25, tzinfo=aeat_models.UTC),
                )
                == "2025"
            )

    def test_non_290_pages_keep_explicit_url_year(self):
        assert _infer_campaign("", "https://example.test/modelo-303-2026.html") == "2026"

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
        portal_client = MagicMock()
        portal_client.fetch_listing.return_value = html
        result = _discover_aeat_models(portal_client=portal_client)

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
        portal_client = MagicMock()
        portal_client.fetch_listing.return_value = html
        result = _discover_aeat_models(portal_client=portal_client)

        assert len(result) == 2
        codigos = [m["codigo"] for m in result]
        assert codigos.count("303") == 1

    def test_returns_empty_on_no_html(self):
        portal_client = MagicMock()
        portal_client.fetch_listing.side_effect = FallbackRequired("blocked")
        result = _discover_aeat_models(portal_client=portal_client)
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
        portal_client = MagicMock()
        portal_client.fetch_listing.return_value = html
        result = _discover_aeat_models(portal_client=portal_client)
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
        portal_client = MagicMock()
        portal_client.fetch_listing.return_value = html
        result = _discover_aeat_models(portal_client=portal_client)

        codigos = {m["codigo"] for m in result}
        assert "123" in codigos
        assert "216" in codigos

    def test_discovers_models_from_live_catalog_pattern(self):
        html = """
        <html>
        <body>
            <h1>Presentar y consultar declaraciones por modelo</h1>
            <a href="/Sede/procedimientoini/G321.shtml">Modelo 030</a>
            <p>Censo de obligados tributarios.</p>
            <a href="/Sede/procedimientoini/G344.shtml">Modelo 036</a>
            <p>Declaracion censal.</p>
            <a href="/Sede/procedimientoini/G401.shtml">Modelo 303</a>
            <p>IVA. Autoliquidacion.</p>
        </body>
        </html>
        """
        portal_client = MagicMock()
        portal_client.fetch_listing.return_value = html

        result = _discover_aeat_models(portal_client=portal_client)

        assert {m["codigo"] for m in result} == {"030", "036", "303"}
        assert all(
            m["url_info"].startswith("https://sede.agenciatributaria.gob.es/Sede/procedimientoini/")
            for m in result
        )


class TestPortalClientSelection:
    def test_aeat_listing_uses_resolvable_host(self):
        assert aeat_models.AEAT_MODELOS_PORTAL.startswith("https://sede.agenciatributaria.gob.es/")

    def test_httpx_client_requires_fallback_when_listing_has_no_model_anchors(self):
        client = HttpxClient()
        with patch.object(client, "_fetch_text", return_value="<html><body>sin anchors</body></html>"):
            try:
                client.fetch_listing()
                assert False, "Expected FallbackRequired"
            except FallbackRequired as exc:
                assert "No anchors in listing" in str(exc)

    def test_httpx_client_follows_live_catalog_navigation(self):
        client = HttpxClient()
        with patch.object(
            client,
            "_fetch_text",
            side_effect=[
                '<a href="/Sede/todas-declaraciones-modelo.html">Todas las declaraciones por modelo</a>',
                '<a href="/Sede/presentar-consultar-declaraciones-modelo.html">Presentar y consultar declaraciones</a>',
                '<a href="/Sede/procedimientoini/G401.shtml">Modelo 303</a>',
            ],
        ) as fetch_text:
            html = client.fetch_listing()

        assert "Modelo 303" in html
        assert fetch_text.call_count == 3

    def test_get_portal_client_uses_httpx_when_listing_is_usable(self):
        with patch("aeat_models.HttpxClient.fetch_listing", return_value="<a href='/modelo_100.html'>100</a>"):
            client = get_portal_client()
        assert isinstance(client, HttpxClient)

    def test_get_portal_client_falls_back_to_playwright(self):
        with patch("aeat_models.HttpxClient.fetch_listing", side_effect=FallbackRequired("js")):
            with patch("aeat_models.PlaywrightClient", return_value="playwright-client") as factory:
                client = get_portal_client()
        factory.assert_called_once_with()
        assert client == "playwright-client"

    def test_get_portal_client_can_force_playwright(self):
        with patch("aeat_models.PlaywrightClient", return_value="forced-client") as factory:
            client = get_portal_client(force_playwright=True)
        factory.assert_called_once_with()
        assert client == "forced-client"


class TestPlaywrightClient:
    def test_class_is_constructible_when_sync_playwright_is_mocked(self):
        fake_sync_playwright = MagicMock()
        with patch.dict(sys.modules, {"playwright.sync_api": MagicMock(sync_playwright=fake_sync_playwright)}):
            with patch("aeat_models._ensure_playwright_browser_installation"):
                client = PlaywrightClient()
        assert client._sync_playwright is fake_sync_playwright

    def test_defaults_browser_path_when_env_missing(self):
        fake_sync_playwright = MagicMock()
        with patch.dict(sys.modules, {"playwright.sync_api": MagicMock(sync_playwright=fake_sync_playwright)}):
            with patch.dict(aeat_models.os.environ, {}, clear=True):
                with patch("aeat_models._ensure_playwright_browser_installation"):
                    PlaywrightClient()

        assert aeat_models.os.environ["PLAYWRIGHT_BROWSERS_PATH"] == "/tmp/ms-playwright"

    def test_installs_browser_when_missing(self, monkeypatch):
        browser_root = Path("/tmp/ms-playwright")
        run = MagicMock()

        monkeypatch.setattr(aeat_models, "subprocess", MagicMock(run=run))
        monkeypatch.setattr(aeat_models.Path, "exists", lambda self: False if self == browser_root else Path.exists(self))
        monkeypatch.setattr(aeat_models.Path, "mkdir", MagicMock())

        aeat_models._ensure_playwright_browser_installation()

        run.assert_called_once_with(["playwright", "install", "chromium"], check=True)

    def test_fetch_resource_falls_back_to_http_when_playwright_aborts(self):
        response = MagicMock()
        response.body.side_effect = RuntimeError("Page.goto: net::ERR_ABORTED")
        page = MagicMock()
        page.goto.return_value = response
        browser = MagicMock()
        browser.new_page.return_value = page
        playwright = MagicMock()
        playwright.chromium.launch.return_value = browser
        manager = MagicMock()
        manager.__enter__.return_value = playwright
        manager.__exit__.return_value = None

        client = PlaywrightClient.__new__(PlaywrightClient)
        client._sync_playwright = MagicMock(return_value=manager)

        with patch.object(HttpxClient, "fetch_resource", return_value=b"pdf-bytes") as http_fetch:
            payload = client.fetch_resource("https://example.com/model.pdf")

        http_fetch.assert_called_once_with("https://example.com/model.pdf")
        assert payload == b"pdf-bytes"


class TestHttpxClient:
    def test_fetch_resource_retries_timeout_then_returns_none(self, monkeypatch):
        client = HttpxClient()
        attempts = []

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return None

            def get(self, url):
                attempts.append(url)
                raise httpx.ConnectTimeout("timed out")

        monkeypatch.setattr(client, "_build_client", lambda: FakeClient())

        payload = client.fetch_resource("https://www1.agenciatributaria.gob.es/recurso.pdf")

        assert payload is None
        assert len(attempts) == 3


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------


class TestFetchModelMetadata:
    def test_infers_modelo_200_as_is_irnr_even_when_page_has_iva_navigation(self):
        portal_client = MagicMock()
        portal_client.fetch_detail.return_value = """
        <html><body>
            <nav>IVA IRPF Censos</nav>
            <h1>Modelo 200. IS. Impuesto sobre Sociedades e Impuesto sobre la Renta de no Residentes.</h1>
        </body></html>
        """

        result = aeat_models._fetch_model_metadata(
            "200",
            url_info="https://sede.agenciatributaria.gob.es/Sede/impuesto-sociedades/modelo-200.html",
            portal_client=portal_client,
        )

        assert result is not None
        assert result["impuesto"] == "IS/IRNR"

    def test_infers_iva_after_more_specific_tax_families(self):
        assert _infer_impuesto(
            "303",
            "Modelo 303. IVA. Impuesto sobre el Valor Añadido. Autoliquidación.",
            "https://sede.agenciatributaria.gob.es/Sede/iva/modelo-303.html",
            "Modelo 303",
        ) == "IVA"

    def test_inference_uses_code_override_before_noisy_page_text(self):
        noisy_nav = "IVA IRNR Impuesto sobre la Renta de no Residentes Impuesto sobre Sociedades"

        assert _infer_impuesto(
            "100",
            noisy_nav,
            "https://sede.agenciatributaria.gob.es/Sede/ayuda/modelo-100/index.shtml",
            "Modelo 100. Impuesto sobre la Renta de las Personas Físicas.",
        ) == "IRPF"
        assert _infer_impuesto(
            "289",
            noisy_nav,
            "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI42.shtml",
            "Modelo 289. Declaración informativa anual de cuentas financieras.",
        ) == "INFORMATIVO"
        assert _infer_impuesto(
            "290",
            noisy_nav,
            "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI38.shtml",
            "Modelo 290. Declaración informativa anual de cuentas financieras FATCA.",
        ) == "INFORMATIVO"

        assert _infer_impuesto(
            "124",
            noisy_nav,
            "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GH05.shtml",
            "Modelo 124. Retenciones e ingresos a cuenta sobre activos financieros.",
        ) == "IRPF/IS/IRNR"

    def test_informative_models_are_not_classified_as_iva_from_nav_noise(self):
        assert _infer_impuesto(
            "231",
            "IVA IRNR Impuesto sobre la Renta de no Residentes Impuesto sobre Sociedades",
            "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI99.shtml",
            "Modelo 231. Declaración Informativa. Declaración de información país por país.",
        ) == "INFORMATIVO"

    def test_applies_known_metadata_override_when_detail_page_describes_parent_model(self):
        portal_client = MagicMock()
        portal_client.fetch_detail.return_value = """
        <html><body>
            <h1>Modelo 200. IS. Impuesto sobre Sociedades e Impuesto sobre la Renta de no Residentes.</h1>
        </body></html>
        """

        result = aeat_models._fetch_model_metadata(
            "206",
            url_info="https://sede.agenciatributaria.gob.es/Sede/procedimientos/GE04.shtml",
            portal_client=portal_client,
        )

        assert result is not None
        assert result["nombre"].startswith("Modelo 206.")
        assert result["impuesto"] == "IS/IRNR"
        assert result["metadata_override"] is True

    def test_known_metadata_overrides_keep_102_and_206_official_names(self):
        portal_client = MagicMock()
        portal_client.fetch_detail.return_value = """
        <html><body>
            <h1>Modelo 100. Impuesto sobre la Renta de las Personas Fisicas.</h1>
            <h2>Modelo 200. Documentos de ingreso o devolucion.</h2>
        </body></html>
        """

        model_102 = aeat_models._fetch_model_metadata(
            "102",
            url_info=aeat_models.MODEL_METADATA_OVERRIDES["102"]["url_info"],
            portal_client=portal_client,
        )
        model_206 = aeat_models._fetch_model_metadata(
            "206",
            url_info=aeat_models.MODEL_METADATA_OVERRIDES["206"]["url_info"],
            portal_client=portal_client,
        )

        assert model_102 is not None
        assert model_102["nombre"] == "Modelo 102. IRPF. Segundo plazo del fraccionamiento de la declaracion anual."
        assert model_102["url_info"].endswith("descarga-modelo-102.html")
        assert model_206 is not None
        assert model_206["nombre"] == (
            "Modelo 206. IS/IRNR. Documento de ingreso o devolucion. "
            "(Modelo 200 y 206)."
        )
        assert model_206["url_info"].endswith("procedimientoini/GE04.shtml")

    def test_rejects_unexpected_model_code_mismatch_without_override(self):
        portal_client = MagicMock()
        portal_client.fetch_detail.return_value = "<html><body><h1>Modelo 100. IRPF.</h1></body></html>"

        result = aeat_models._fetch_model_metadata(
            "103",
            url_info="https://sede.agenciatributaria.gob.es/Sede/procedimientoini/example.shtml",
            portal_client=portal_client,
        )

        assert result is None

    def test_normalizes_provided_url_before_fetching_detail(self):
        portal_client = MagicMock()
        portal_client.fetch_detail.return_value = "<html><body><h1>230 - Modelo 230</h1></body></html>"

        result = aeat_models._fetch_model_metadata(
            "230",
            url_info="ttps://www1.agenciatributaria.gob.es/wlpl/PAMW-M230/index.zul",
            portal_client=portal_client,
        )

        portal_client.fetch_detail.assert_called_once_with(
            "https://www1.agenciatributaria.gob.es/wlpl/PAMW-M230/index.zul"
        )
        assert result is not None
        assert result["url_info"] == "https://www1.agenciatributaria.gob.es/wlpl/PAMW-M230/index.zul"

    def test_uses_provided_url_without_listing_lookup(self):
        portal_client = MagicMock()
        portal_client.fetch_detail.return_value = """
        <html><body>
            <h1>100 - Declaracion de la Renta</h1>
            <a href="/docs/modelo100.pdf">Modelo PDF</a>
        </body></html>
        """

        result = aeat_models._fetch_model_metadata(
            "100",
            url_info="https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/index.shtml",
            portal_client=portal_client,
        )

        portal_client.fetch_listing.assert_not_called()
        portal_client.fetch_detail.assert_called_once()
        assert result is not None
        assert result["url_info"].endswith("modelo-100/index.shtml")
        assert any(r["tipo_recurso"] == "formulario_pdf" for r in result["recursos"])

    def test_skips_aeat_blocked_4033_pages(self):
        portal_client = MagicMock()
        portal_client.fetch_detail.return_value = "<html><body>erro4033.html Acceso denegado</body></html>"

        result = aeat_models._fetch_model_metadata(
            "230",
            url_info="https://www1.agenciatributaria.gob.es/wlpl/PAMW-M230/index.zul",
            portal_client=portal_client,
        )

        assert result is None


class TestClassifyResource:
    def test_prefers_pdf_instruction_and_design_signals_from_url(self):
        assert _classify_resource("Descargar", "https://example.com/instrucciones-modelo-303.pdf") == (
            "instrucciones",
            "pdf",
        )
        assert _classify_resource("Descargar", "https://example.com/disenos-registro/modelo-190.pdf") == (
            "diseno_registro",
            "pdf",
        )

    def test_detects_normativa_and_formulario_from_url_when_text_is_generic(self):
        assert _classify_resource("Descargar", "https://example.com/boe/orden-hfp-123.pdf") == (
            "normativa",
            "pdf",
        )
        assert _classify_resource("Descargar", "https://example.com/modelos/modelo-303.pdf") == (
            "formulario_pdf",
            "pdf",
        )

class TestExtractModelResources:
    def test_skips_external_resources_from_detail_page(self):
        html = """
        <html><body>
            <a href="/docs/modelo303.pdf">Modelo PDF</a>
            <a href="https://www.oecd.org/example.html">Guia OECD</a>
            <a href="https://www.boe.es/diario_boe/txt.php?id=BOE-A-2024-1">Orden BOE</a>
        </body></html>
        """

        resources = aeat_models._extract_model_resources(
            html,
            "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G401.shtml",
        )

        resource_urls = {resource["url_recurso"] for resource in resources}
        assert "https://www.oecd.org/example.html" not in resource_urls
        assert "https://sede.agenciatributaria.gob.es/docs/modelo303.pdf" in resource_urls
        assert "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2024-1" in resource_urls


class TestNormalizeAeatUrl:
    def test_repairs_missing_h_in_https_scheme(self):
        assert _normalize_aeat_url("ttps://www1.agenciatributaria.gob.es/wlpl/PAMW-M230/index.zul") == (
            "https://www1.agenciatributaria.gob.es/wlpl/PAMW-M230/index.zul"
        )

    def test_prefixes_https_for_scheme_less_host(self):
        assert _normalize_aeat_url("www1.agenciatributaria.gob.es/wlpl/PAMW-M230/index.zul") == (
            "https://www1.agenciatributaria.gob.es/wlpl/PAMW-M230/index.zul"
        )

    def test_upgrades_http_scheme_for_www1_aeat_host(self):
        assert _normalize_aeat_url("http://www1.agenciatributaria.gob.es/wlpl/REGD-JDIT/FG?fTramite=GC592") == (
            "https://www1.agenciatributaria.gob.es/wlpl/REGD-JDIT/FG?fTramite=GC592"
        )


class TestOfficialModelResource:
    def test_accepts_official_aeat_resource(self):
        assert _is_official_model_resource("https://www1.agenciatributaria.gob.es/wlpl/REGD-JDIT/FG?fTramite=GC592") is True

    def test_rejects_non_official_resource(self):
        assert _is_official_model_resource("https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/") is False


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
                        updated_at TEXT
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
                        updated_at TEXT
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
                        updated_at TEXT
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
                        updated_at TEXT
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


class TestModeloRecursoVersioning:
    def _setup_db(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE modelo_recurso (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        campana_id INTEGER NOT NULL,
                        tipo_recurso TEXT NOT NULL,
                        formato TEXT NOT NULL,
                        url_recurso TEXT NOT NULL,
                        sha256_contenido TEXT NOT NULL,
                        row_completeness TEXT NOT NULL,
                        row_provenance TEXT NOT NULL,
                        etag TEXT,
                        last_modified TEXT,
                        content_length INTEGER,
                        metadata TEXT NOT NULL DEFAULT '{}',
                        activa INTEGER NOT NULL DEFAULT 1,
                        first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(campana_id, tipo_recurso, sha256_contenido)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX idx_modelo_recurso_activa_unica ON modelo_recurso (campana_id, tipo_recurso) WHERE activa = 1"
                )
            )
        return engine

    def test_mismo_hash_no_duplica(self):
        engine = self._setup_db()
        with engine.begin() as conn:
            assert _store_modelo_recurso_version(conn, 1, "instrucciones", "pdf", "https://example.com/a.pdf", b"same") == "inserted"
            assert _store_modelo_recurso_version(conn, 1, "instrucciones", "pdf", "https://example.com/a.pdf", b"same") == "unchanged"

        with engine.begin() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM modelo_recurso WHERE campana_id = 1 AND tipo_recurso = 'instrucciones'")) .scalar()
            active = conn.execute(text("SELECT COUNT(*) FROM modelo_recurso WHERE campana_id = 1 AND tipo_recurso = 'instrucciones' AND activa = 1")).scalar()

        assert total == 1
        assert active == 1

    def test_inserted_resource_sets_row_quality_contract(self):
        engine = self._setup_db()
        with engine.begin() as conn:
            assert _store_modelo_recurso_version(
                conn,
                1,
                "instrucciones",
                "pdf",
                "https://example.com/a.pdf",
                b"same",
            ) == "inserted"
            row = conn.execute(
                text(
                    "SELECT row_completeness, row_provenance FROM modelo_recurso WHERE campana_id = 1 AND tipo_recurso = 'instrucciones'"
                )
            ).fetchone()

        assert row == ("complete", "official_exact")

    def test_hash_cambia_rota_version(self):
        engine = self._setup_db()
        with engine.begin() as conn:
            assert _store_modelo_recurso_version(conn, 1, "instrucciones", "pdf", "https://example.com/a.pdf", b"v1") == "inserted"
            assert _store_modelo_recurso_version(conn, 1, "instrucciones", "pdf", "https://example.com/a.pdf", b"v2") == "rotated"

        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT activa FROM modelo_recurso WHERE campana_id = 1 AND tipo_recurso = 'instrucciones' ORDER BY id"
                )
            ).fetchall()

        assert rows == [(0,), (1,)]

    def test_reuses_existing_inactive_version_with_same_hash(self):
        engine = self._setup_db()
        with engine.begin() as conn:
            assert _store_modelo_recurso_version(conn, 1, "instrucciones", "pdf", "https://example.com/a.pdf", b"v1") == "inserted"
            assert _store_modelo_recurso_version(conn, 1, "instrucciones", "pdf", "https://example.com/a.pdf", b"v2") == "rotated"
            assert _store_modelo_recurso_version(conn, 1, "instrucciones", "pdf", "https://example.com/a.pdf", b"v1") == "unchanged"

        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT sha256_contenido, activa FROM modelo_recurso WHERE campana_id = 1 AND tipo_recurso = 'instrucciones' ORDER BY id"
                )
            ).fetchall()

        assert rows == [
            (aeat_models._sha256_bytes(b"v1"), 1),
            (aeat_models._sha256_bytes(b"v2"), 0),
        ]

    def test_fallo_entre_update_e_insert_no_deja_sin_activa(self):
        engine = self._setup_db()
        with engine.begin() as conn:
            _store_modelo_recurso_version(conn, 1, "instrucciones", "pdf", "https://example.com/a.pdf", b"v1")

        try:
            with engine.begin() as conn:
                _store_modelo_recurso_version(conn, 1, "instrucciones", "pdf", "https://example.com/a.pdf", b"v2")
                raise RuntimeError("force rollback after update+insert")
        except RuntimeError:
            pass

        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT COUNT(*) FROM modelo_recurso WHERE campana_id = 1 AND tipo_recurso = 'instrucciones' AND activa = 1"
                )
            ).scalar()

        assert rows == 1


class TestSyncLog:
    def test_record_sync_log_writes_expected_mapping(self):
        engine = create_engine("sqlite:///:memory:")
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
                        errors INTEGER,
                        rows_processed INTEGER,
                        error_msg TEXT
                    )
                    """
                )
            )
            _record_sync_log(
                conn,
                started_at="2026-05-01T00:00:00Z",
                finished_at="2026-05-01T00:01:00Z",
                status="ok",
                stats={
                    "modelos_descubiertos": 3,
                    "campanas_upserted": 2,
                    "recursos_descargados": 7,
                    "versiones_nuevas": 4,
                    "sin_cambios": 3,
                    "errores": 1,
                },
            )

        with engine.begin() as conn:
            row = conn.execute(
                text(
                    "SELECT worker, status, bloques_processed, articulos_upserted, documentos_processed, documentos_upserted, errors, rows_processed FROM sync_log"
                )
            ).fetchone()

        assert row == ("worker-aeat-modelos", "ok", 7, 4, 3, 2, 1, 3)

    def test_record_sync_log_uses_worker_name_env(self, monkeypatch):
        engine = create_engine("sqlite:///:memory:")
        monkeypatch.setenv("WORKER_NAME", "worker-modelos")

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
                        errors INTEGER,
                        rows_processed INTEGER,
                        error_msg TEXT
                    )
                    """
                )
            )
            _record_sync_log(
                conn,
                started_at="2026-05-01T00:00:00Z",
                finished_at="2026-05-01T00:01:00Z",
                status="ok",
                stats={
                    "modelos_descubiertos": 1,
                    "campanas_upserted": 1,
                    "recursos_descargados": 0,
                    "versiones_nuevas": 0,
                    "sin_cambios": 0,
                    "errores": 0,
                },
            )

        with engine.begin() as conn:
            worker = conn.execute(text("SELECT worker FROM sync_log")).scalar()

        assert worker == "worker-modelos"


def test_run_sync_uses_heartbeat_sleep(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    heartbeat_calls = []
    sleep_calls = []

    class LoopStopped(BaseException):
        pass

    monkeypatch.setattr("aeat_models.get_portal_client", lambda force_playwright=False: object())
    monkeypatch.setattr("aeat_models._discover_aeat_models", lambda portal_client=None: [])
    monkeypatch.setattr("aeat_models._record_sync_log", lambda *args, **kwargs: None)
    monkeypatch.setattr("aeat_models.touch_heartbeat", lambda: heartbeat_calls.append("touch"), raising=False)

    def fake_sleep_with_heartbeat(seconds):
        sleep_calls.append(seconds)
        raise LoopStopped

    monkeypatch.setattr("aeat_models.sleep_with_heartbeat", fake_sleep_with_heartbeat, raising=False)

    def fail_plain_sleep(_seconds):
        raise AssertionError("time.sleep should not be used directly")

    monkeypatch.setattr(aeat_models.time, "sleep", fail_plain_sleep)

    try:
        aeat_models.run_sync(engine, run_once=False)
        assert False, "Expected StopIteration"
    except LoopStopped:
        pass

    assert heartbeat_calls == ["touch"]
    assert sleep_calls == [aeat_models.SYNC_INTERVAL_SECONDS]


def test_run_sync_refreshes_heartbeat_while_processing_models(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    heartbeat_calls = []
    sleep_calls = []

    class LoopStopped(BaseException):
        pass

    discovered = [{"codigo": "303", "nombre": "Modelo 303", "url_info": "https://example.com/303"}]

    monkeypatch.setattr("aeat_models.get_portal_client", lambda force_playwright=False: object())
    monkeypatch.setattr("aeat_models._try_acquire_sync_lock", lambda conn: True)
    monkeypatch.setattr("aeat_models._discover_aeat_models", lambda portal_client=None: discovered)
    monkeypatch.setattr("aeat_models._upsert_aeat_model", lambda *args, **kwargs: True)
    monkeypatch.setattr("aeat_models._get_modelo_id", lambda *args, **kwargs: 1)
    monkeypatch.setattr("aeat_models._upsert_modelo_campana", lambda *args, **kwargs: (1, True))
    monkeypatch.setattr("aeat_models._store_modelo_recurso_version", lambda *args, **kwargs: "unchanged")
    monkeypatch.setattr("aeat_models._mark_deprecated_models", lambda *args, **kwargs: 0)
    monkeypatch.setattr("aeat_models._record_sync_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "aeat_models._fetch_model_metadata",
        lambda codigo, url_info=None, portal_client=None: {
            "codigo": codigo,
            "nombre": "Modelo 303",
            "url_info": url_info,
            "campana": "2025",
            "periodo": "trimestral",
            "impuesto": "IVA",
            "recursos": [],
        },
    )
    monkeypatch.setattr("aeat_models.touch_heartbeat", lambda: heartbeat_calls.append("touch"), raising=False)

    def fake_sleep_with_heartbeat(seconds):
        sleep_calls.append(seconds)
        raise LoopStopped

    monkeypatch.setattr("aeat_models.sleep_with_heartbeat", fake_sleep_with_heartbeat, raising=False)

    try:
        aeat_models.run_sync(engine, run_once=False)
        assert False, "Expected LoopStopped"
    except LoopStopped:
        pass

    assert heartbeat_calls == ["touch", "touch"]
    assert sleep_calls == [aeat_models.SYNC_INTERVAL_SECONDS]


def test_run_sync_falls_back_to_seeded_models_when_discovery_is_empty(monkeypatch):
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE aeat_modelo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE NOT NULL,
                    nombre TEXT,
                    url_info TEXT,
                    activo INTEGER DEFAULT 1
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
                    errors INTEGER,
                    rows_processed INTEGER,
                    error_msg TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO aeat_modelo (codigo, nombre, url_info, activo) VALUES ('100', 'Modelo 100', 'https://example.com/modelo-100', 1)"
            )
        )

    metadata_fetch = MagicMock(
        return_value={
            "codigo": "100",
            "nombre": "Modelo 100",
            "url_info": "https://example.com/modelo-100",
            "campana": "2025",
            "recursos": [],
        }
    )

    monkeypatch.setattr("aeat_models.get_portal_client", lambda force_playwright=False: object())
    monkeypatch.setattr("aeat_models._discover_aeat_models", lambda portal_client=None: [])
    monkeypatch.setattr("aeat_models._fetch_model_metadata", metadata_fetch)
    monkeypatch.setattr("aeat_models._upsert_aeat_model", lambda *args, **kwargs: True)
    monkeypatch.setattr("aeat_models._get_modelo_id", lambda *args, **kwargs: 1)
    monkeypatch.setattr("aeat_models._upsert_modelo_campana", lambda *args, **kwargs: (10, True))
    monkeypatch.setattr("aeat_models._mark_deprecated_models", lambda *args, **kwargs: 0)

    aeat_models.run_sync(engine, run_once=True)

    metadata_fetch.assert_called_once()

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT status, documentos_processed, documentos_upserted, error_msg FROM sync_log ORDER BY id DESC LIMIT 1")
        ).fetchone()

    assert row == ("ok", 1, 1, None)


def test_run_sync_skips_when_advisory_lock_is_unavailable(monkeypatch):
    engine = create_engine("sqlite:///:memory:")

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
                    errors INTEGER,
                    rows_processed INTEGER,
                    error_msg TEXT
                )
                """
            )
        )

    monkeypatch.setattr("aeat_models.get_portal_client", lambda force_playwright=False: object())
    monkeypatch.setattr("aeat_models._try_acquire_sync_lock", lambda conn: False)
    monkeypatch.setattr(
        "aeat_models._discover_aeat_models",
        lambda portal_client=None: (_ for _ in ()).throw(AssertionError("discovery should not run without lock")),
    )

    aeat_models.run_sync(engine, run_once=True)

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT status, documentos_processed, documentos_upserted, error_msg FROM sync_log ORDER BY id DESC LIMIT 1")
        ).fetchone()

    assert row == ("partial", 0, 0, "AEAT sync already in progress")


def test_run_sync_skips_failed_official_resource_and_finishes_partial(monkeypatch):
    engine = create_engine("sqlite:///:memory:")

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
                    errors INTEGER,
                    rows_processed INTEGER,
                    error_msg TEXT
                )
                """
            )
        )

    portal_client = MagicMock()
    portal_client.fetch_resource.return_value = None
    stored_payloads = []

    monkeypatch.setattr("aeat_models.get_portal_client", lambda force_playwright=False: portal_client)
    monkeypatch.setattr("aeat_models._try_acquire_sync_lock", lambda conn: True)
    monkeypatch.setattr(
        "aeat_models._discover_aeat_models",
        lambda portal_client=None: [{"codigo": "303", "nombre": "Modelo 303", "url_info": "https://example.com/303"}],
    )
    monkeypatch.setattr(
        "aeat_models._fetch_model_metadata",
        lambda *args, **kwargs: {
            "codigo": "303",
            "nombre": "Modelo 303",
            "url_info": "https://example.com/303",
            "campana": "2026",
            "recursos": [
                {
                    "tipo_recurso": "normativa",
                    "formato": "html",
                    "url_recurso": "https://www.boe.es/buscar/act.php?id=BOE-A-2024-1771",
                }
            ],
        },
    )
    monkeypatch.setattr("aeat_models._upsert_aeat_model", lambda *args, **kwargs: True)
    monkeypatch.setattr("aeat_models._get_modelo_id", lambda *args, **kwargs: 1)
    monkeypatch.setattr("aeat_models._upsert_modelo_campana", lambda *args, **kwargs: (10, True))
    monkeypatch.setattr("aeat_models._mark_deprecated_models", lambda *args, **kwargs: 0)
    monkeypatch.setattr(
        "aeat_models._store_modelo_recurso_version",
        lambda *args, **kwargs: stored_payloads.append(args[5]) or "inserted",
    )

    aeat_models.run_sync(engine, run_once=True)

    assert stored_payloads == []

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT status, errors, error_msg FROM sync_log ORDER BY id DESC LIMIT 1")
        ).fetchone()

    assert row == ("partial", 0, "Skipped 1 AEAT official resources after fetch failures")


def test_run_sync_ignores_failed_protected_official_resource_and_finishes_ok(monkeypatch):
    engine = create_engine("sqlite:///:memory:")

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
                    errors INTEGER,
                    rows_processed INTEGER,
                    error_msg TEXT
                )
                """
            )
        )

    portal_client = MagicMock()
    portal_client.fetch_resource.return_value = None
    stored_payloads = []

    monkeypatch.setattr("aeat_models.get_portal_client", lambda force_playwright=False: portal_client)
    monkeypatch.setattr("aeat_models._try_acquire_sync_lock", lambda conn: True)
    monkeypatch.setattr(
        "aeat_models._discover_aeat_models",
        lambda portal_client=None: [{"codigo": "792", "nombre": "Modelo 792", "url_info": "https://example.com/792"}],
    )
    monkeypatch.setattr(
        "aeat_models._fetch_model_metadata",
        lambda *args, **kwargs: {
            "codigo": "792",
            "nombre": "Modelo 792",
            "url_info": "https://example.com/792",
            "campana": "2025",
            "recursos": [
                {
                    "tipo_recurso": "recurso_oficial",
                    "formato": "other",
                    "url_recurso": "http://www1.agenciatributaria.gob.es/wlpl/REGD-JDIT/FG?fTramite=GC592",
                }
            ],
        },
    )
    monkeypatch.setattr("aeat_models._upsert_aeat_model", lambda *args, **kwargs: True)
    monkeypatch.setattr("aeat_models._get_modelo_id", lambda *args, **kwargs: 1)
    monkeypatch.setattr("aeat_models._upsert_modelo_campana", lambda *args, **kwargs: (10, True))
    monkeypatch.setattr(
        "aeat_models._store_modelo_recurso_version",
        lambda *args, **kwargs: stored_payloads.append(args[5]) or "inserted",
    )
    monkeypatch.setattr("aeat_models._mark_deprecated_models", lambda *args, **kwargs: 0)

    aeat_models.run_sync(engine, run_once=True)

    assert stored_payloads == []

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT status, errors, error_msg FROM sync_log ORDER BY id DESC LIMIT 1")
        ).fetchone()

    assert row == ("ok", 0, None)


def test_run_sync_stores_pagina_modelo_without_resource_url_regression(monkeypatch):
    engine = create_engine("sqlite:///:memory:")

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
                    errors INTEGER,
                    rows_processed INTEGER,
                    error_msg TEXT
                )
                """
            )
        )

    portal_client = MagicMock()
    stored_urls = []

    monkeypatch.setattr("aeat_models.get_portal_client", lambda force_playwright=False: portal_client)
    monkeypatch.setattr("aeat_models._try_acquire_sync_lock", lambda conn: True)
    monkeypatch.setattr(
        "aeat_models._discover_aeat_models",
        lambda portal_client=None: [{"codigo": "001", "nombre": "Modelo 001", "url_info": "https://example.com/001"}],
    )
    monkeypatch.setattr(
        "aeat_models._fetch_model_metadata",
        lambda *args, **kwargs: {
            "codigo": "001",
            "nombre": "Modelo 001",
            "url_info": "https://example.com/001",
            "campana": "2025",
            "recursos": [
                {
                    "tipo_recurso": "pagina_modelo",
                    "formato": "html",
                    "url_recurso": "https://example.com/001",
                    "payload": b"<html>pagina modelo</html>",
                }
            ],
        },
    )
    monkeypatch.setattr("aeat_models._upsert_aeat_model", lambda *args, **kwargs: True)
    monkeypatch.setattr("aeat_models._get_modelo_id", lambda *args, **kwargs: 1)
    monkeypatch.setattr("aeat_models._upsert_modelo_campana", lambda *args, **kwargs: (10, True))
    monkeypatch.setattr(
        "aeat_models._store_modelo_recurso_version",
        lambda *args, **kwargs: stored_urls.append(args[4]) or "inserted",
    )
    monkeypatch.setattr("aeat_models._mark_deprecated_models", lambda *args, **kwargs: 0)

    aeat_models.run_sync(engine, run_once=True)

    assert stored_urls == ["https://example.com/001"]

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT status, errors, error_msg FROM sync_log ORDER BY id DESC LIMIT 1")
        ).fetchone()

    assert row == ("ok", 0, None)
