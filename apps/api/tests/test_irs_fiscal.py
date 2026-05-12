"""Tests for IRS & international fiscal compliance router (Fase 24).

Cubre: listado con filtros, detalle por codigo, endpoint /check,
fallos 404 y comportamiento de filtros booleanos.
"""

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from main import app


# ---------------------------------------------------------------------------
# Client fixture (uses conftest db tables + seed)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# IRS Fiscal Norma
# ---------------------------------------------------------------------------


class TestListarNormasIRS:
    @pytest.mark.asyncio
    async def test_listado_sin_filtros(self, client):
        resp = await client.get("/v1/irs-fiscal/normas")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 3
        assert len(body["normas"]) >= 3

    @pytest.mark.asyncio
    async def test_listado_filtro_tipo(self, client):
        resp = await client.get("/v1/irs-fiscal/normas?tipo=forma")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2
        for n in body["normas"]:
            assert n["tipo"] == "forma"

    @pytest.mark.asyncio
    async def test_listado_filtro_estado(self, client):
        resp = await client.get("/v1/irs-fiscal/normas?estado=activo")
        assert resp.status_code == 200
        body = resp.json()
        for n in body["normas"]:
            assert n["estado"] == "activo"

    @pytest.mark.asyncio
    async def test_detalle_norma(self, client):
        resp = await client.get("/v1/irs-fiscal/normas/FORM_1040")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "FORM_1040"
        assert body["tipo"] == "forma"

    @pytest.mark.asyncio
    async def test_detalle_norma_404(self, client):
        resp = await client.get("/v1/irs-fiscal/normas/NO_EXISTE")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# IRS DTA Convention
# ---------------------------------------------------------------------------


class TestListarConveniosDTA:
    @pytest.mark.asyncio
    async def test_listado_sin_filtros(self, client):
        resp = await client.get("/v1/irs-fiscal/convenios")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2
        assert len(body["convenios"]) >= 2

    @pytest.mark.asyncio
    async def test_listado_filtro_pais(self, client):
        resp = await client.get("/v1/irs-fiscal/convenios?pais=US")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2
        for c in body["convenios"]:
            assert c["pais_origen"] == "US" or c["pais_destino"] == "US"

    @pytest.mark.asyncio
    async def test_listado_filtro_estado(self, client):
        resp = await client.get("/v1/irs-fiscal/convenios?estado=vigente")
        assert resp.status_code == 200
        body = resp.json()
        for c in body["convenios"]:
            assert c["estado"] == "vigente"

    @pytest.mark.asyncio
    async def test_detalle_convenio(self, client):
        resp = await client.get("/v1/irs-fiscal/convenios/DTA_US_ES")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "DTA_US_ES"
        assert body["pais_origen"] == "US"
        assert body["pais_destino"] == "ES"

    @pytest.mark.asyncio
    async def test_detalle_convenio_404(self, client):
        resp = await client.get("/v1/irs-fiscal/convenios/NO_EXISTE")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# IRS Withholding Rule
# ---------------------------------------------------------------------------


class TestListarReglasRetencion:
    @pytest.mark.asyncio
    async def test_listado_sin_filtros(self, client):
        resp = await client.get("/v1/irs-fiscal/retenciones")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 3
        assert len(body["reglas"]) >= 3

    @pytest.mark.asyncio
    async def test_listado_filtro_tipo_renta(self, client):
        resp = await client.get("/v1/irs-fiscal/retenciones?tipo_renta=dividends")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for r in body["reglas"]:
            assert r["tipo_renta"] == "dividends"

    @pytest.mark.asyncio
    async def test_listado_filtro_estado(self, client):
        resp = await client.get("/v1/irs-fiscal/retenciones?estado=activo")
        assert resp.status_code == 200
        body = resp.json()
        for r in body["reglas"]:
            assert r["estado"] == "activo"

    @pytest.mark.asyncio
    async def test_detalle_regla(self, client):
        resp = await client.get("/v1/irs-fiscal/retenciones/WHT_DIVIDENDS")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "WHT_DIVIDENDS"
        assert body["tipo_renta"] == "dividends"
        assert body["tipo_retencion_default"] == 30.0

    @pytest.mark.asyncio
    async def test_detalle_regla_404(self, client):
        resp = await client.get("/v1/irs-fiscal/retenciones/NO_EXISTE")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# IRS W-8 Form
# ---------------------------------------------------------------------------


class TestListarFormulariosW8:
    @pytest.mark.asyncio
    async def test_listado_sin_filtros(self, client):
        resp = await client.get("/v1/irs-fiscal/w8-formularios")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2
        assert len(body["formularios"]) >= 2

    @pytest.mark.asyncio
    async def test_listado_filtro_tipo_sujeto(self, client):
        resp = await client.get("/v1/irs-fiscal/w8-formularios?tipo_sujeto=persona_fisica")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for f in body["formularios"]:
            assert f["tipo_sujeto"] == "persona_fisica"

    @pytest.mark.asyncio
    async def test_listado_filtro_estado(self, client):
        resp = await client.get("/v1/irs-fiscal/w8-formularios?estado=activo")
        assert resp.status_code == 200
        body = resp.json()
        for f in body["formularios"]:
            assert f["estado"] == "activo"

    @pytest.mark.asyncio
    async def test_detalle_formulario(self, client):
        resp = await client.get("/v1/irs-fiscal/w8-formularios/W8BEN")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "W8BEN"
        assert body["tipo_sujeto"] == "persona_fisica"

    @pytest.mark.asyncio
    async def test_detalle_formulario_404(self, client):
        resp = await client.get("/v1/irs-fiscal/w8-formularios/NO_EXISTE")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# IRS TIN Reference
# ---------------------------------------------------------------------------


class TestListarReferenciasTIN:
    @pytest.mark.asyncio
    async def test_listado_sin_filtros(self, client):
        resp = await client.get("/v1/irs-fiscal/tin-referencias")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2
        assert len(body["referencias"]) >= 2

    @pytest.mark.asyncio
    async def test_listado_filtro_pais(self, client):
        resp = await client.get("/v1/irs-fiscal/tin-referencias?pais=US")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for r in body["referencias"]:
            assert r["codigo_pais"] == "US"

    @pytest.mark.asyncio
    async def test_listado_filtro_ocde(self, client):
        resp = await client.get("/v1/irs-fiscal/tin-referencias?ocde=true")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2
        for r in body["referencias"]:
            assert r["es_ocde"] is True

    @pytest.mark.asyncio
    async def test_listado_filtro_eu_vat(self, client):
        resp = await client.get("/v1/irs-fiscal/tin-referencias?eu_vat=true")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for r in body["referencias"]:
            assert r["es_eu_vat"] is True

    @pytest.mark.asyncio
    async def test_detalle_referencia(self, client):
        resp = await client.get("/v1/irs-fiscal/tin-referencias/US")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo_pais"] == "US"
        assert body["es_ocde"] is True

    @pytest.mark.asyncio
    async def test_detalle_referencia_404(self, client):
        resp = await client.get("/v1/irs-fiscal/tin-referencias/ZZ")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GIIN Registry
# ---------------------------------------------------------------------------


class TestListarGIIN:
    @pytest.mark.asyncio
    async def test_listado_sin_filtros(self, client):
        resp = await client.get("/v1/irs-fiscal/giin")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2
        assert len(body["registros"]) >= 2
        assert body["limit"] == 50
        assert body["offset"] == 0

    @pytest.mark.asyncio
    async def test_listado_paginado(self, client):
        resp = await client.get("/v1/irs-fiscal/giin?limit=1&offset=1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2
        assert len(body["registros"]) == 1
        assert body["limit"] == 1
        assert body["offset"] == 1
        assert body["has_more"] is False
        assert body["next_offset"] is None

    @pytest.mark.asyncio
    async def test_listado_filtro_estado(self, client):
        resp = await client.get("/v1/irs-fiscal/giin?estado=activo")
        assert resp.status_code == 200
        body = resp.json()
        for r in body["registros"]:
            assert r["estado_fatca"] == "activo"

    @pytest.mark.asyncio
    async def test_listado_filtro_pais(self, client):
        resp = await client.get("/v1/irs-fiscal/giin?pais=ES")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for r in body["registros"]:
            assert r["entidad_pais"] == "ES"

    @pytest.mark.asyncio
    async def test_listado_filtro_tipo(self, client):
        resp = await client.get("/v1/irs-fiscal/giin?tipo=FFI")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for r in body["registros"]:
            assert r["tipo_entidad"] == "FFI"

    @pytest.mark.asyncio
    async def test_detalle_registro(self, client):
        resp = await client.get("/v1/irs-fiscal/giin/GIIN123.456.789.001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["giin"] == "GIIN123.456.789.001"
        assert body["tipo_entidad"] == "FFI"

    @pytest.mark.asyncio
    async def test_detalle_registro_404(self, client):
        resp = await client.get("/v1/irs-fiscal/giin/NO_EXISTE")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# IRS Fiscal Check — calculo de retencion
# ---------------------------------------------------------------------------


class TestIRSFiscalCheck:
    @pytest.mark.asyncio
    async def test_check_dividendos_espana(self, client):
        resp = await client.post("/v1/irs-fiscal/check", json={
            "pais_residencia": "ES",
            "tipo_renta": "dividends",
            "tiene_formulario_w8": False,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["tipo_renta"] == "dividends"
        assert body["tiene_convenio_dta"] is True
        assert body["codigo_convenio"] == "DTA_US_ES"
        assert body["requiere_w8"] is True
        assert body["formulario_recomendado"] == "W-8BEN-E"

    @pytest.mark.asyncio
    async def test_check_dividendos_sin_pais(self, client):
        resp = await client.post("/v1/irs-fiscal/check", json={
            "pais_residencia": None,
            "tipo_renta": "dividends",
            "tiene_formulario_w8": True,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["tipo_renta"] == "dividends"
        assert body["tiene_convenio_dta"] is False
        assert body["requiere_w8"] is False

    @pytest.mark.asyncio
    async def test_check_tipo_renta_no_encontrado(self, client):
        resp = await client.post("/v1/irs-fiscal/check", json={
            "pais_residencia": "FR",
            "tipo_renta": "capital_gains",
            "tiene_formulario_w8": False,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["tipo_renta"] == "capital_gains"
        assert body["tipo_retencion_aplicable"] == 30.0
        assert body["tiene_convenio_dta"] is False
        assert body["requiere_w8"] is True

    @pytest.mark.asyncio
    async def test_check_intereses_con_dta(self, client):
        resp = await client.post("/v1/irs-fiscal/check", json={
            "pais_residencia": "ES",
            "tipo_renta": "interest",
            "tiene_formulario_w8": False,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["tiene_convenio_dta"] is True
        assert body["tipo_retencion_aplicable"] == 10.0

    @pytest.mark.asyncio
    async def test_check_regalias_sin_dta(self, client):
        resp = await client.post("/v1/irs-fiscal/check", json={
            "pais_residencia": "JP",
            "tipo_renta": "royalties",
            "tiene_formulario_w8": False,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["tiene_convenio_dta"] is False
        assert body["tipo_retencion_aplicable"] == 30.0
