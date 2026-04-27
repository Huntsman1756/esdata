"""Tests for micro-obligaciones router (Fase 20).

Cubre: listado con filtros, detalle por codigo, mapeo por obligacion,
fallos 404 y comportamiento de activo=false.
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
# GET /v1/micro-obligaciones — listado
# ---------------------------------------------------------------------------


class TestListarMicroObligaciones:
    """Pruebas del endpoint de listado."""

    @pytest.mark.asyncio
    async def test_listado_sin_filtros(self, client):
        resp = await client.get("/v1/micro-obligaciones")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 52
        assert len(body["micro_obligaciones"]) >= 52

    @pytest.mark.asyncio
    async def test_listado_filtro_regulacion(self, client):
        resp = await client.get("/v1/micro-obligaciones?regulacion=mifid_ii")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] > 0
        for mo in body["micro_obligaciones"]:
            assert mo["regulacion_relacionada"] == "mifid_ii"

    @pytest.mark.asyncio
    async def test_listado_filtro_regulacion_cnmv(self, client):
        resp = await client.get("/v1/micro-obligaciones?regulacion=cnmv_lmcv")
        assert resp.status_code == 200
        body = resp.json()
        for mo in body["micro_obligaciones"]:
            assert mo["regulacion_relacionada"] == "cnmv_lmcv"

    @pytest.mark.asyncio
    async def test_listado_filtro_regulacion_sepblac(self, client):
        resp = await client.get("/v1/micro-obligaciones?regulacion=pblcft")
        assert resp.status_code == 200
        body = resp.json()
        for mo in body["micro_obligaciones"]:
            assert mo["regulacion_relacionada"] == "pblcft"

    @pytest.mark.asyncio
    async def test_listado_filtro_regulacion_mifir(self, client):
        resp = await client.get("/v1/micro-obligaciones?regulacion=mifir")
        assert resp.status_code == 200
        body = resp.json()
        for mo in body["micro_obligaciones"]:
            assert mo["regulacion_relacionada"] == "mifir"

    @pytest.mark.asyncio
    async def test_listado_filtro_regulacion_mar(self, client):
        resp = await client.get("/v1/micro-obligaciones?regulacion=mar")
        assert resp.status_code == 200
        body = resp.json()
        for mo in body["micro_obligaciones"]:
            assert mo["regulacion_relacionada"] == "mar"

    @pytest.mark.asyncio
    async def test_listado_filtro_ambito(self, client):
        resp = await client.get("/v1/micro-obligaciones?ambito=aml_cft")
        assert resp.status_code == 200
        body = resp.json()
        for mo in body["micro_obligaciones"]:
            assert mo["ambito"] == "aml_cft"

    @pytest.mark.asyncio
    async def test_listado_filtro_severidad(self, client):
        resp = await client.get("/v1/micro-obligaciones?severidad=alta")
        assert resp.status_code == 200
        body = resp.json()
        for mo in body["micro_obligaciones"]:
            assert mo["severidad"] == "alta"

    @pytest.mark.asyncio
    async def test_listado_filtro_owner_rol(self, client):
        resp = await client.get("/v1/micro-obligaciones?owner_rol=compliance")
        assert resp.status_code == 200
        body = resp.json()
        for mo in body["micro_obligaciones"]:
            assert mo["owner_rol"] == "compliance"

    @pytest.mark.asyncio
    async def test_listado_filtro_activo(self, client):
        resp = await client.get("/v1/micro-obligaciones?activo=true")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 30

    @pytest.mark.asyncio
    async def test_listado_filtro_combinado(self, client):
        resp = await client.get(
            "/v1/micro-obligaciones?regulacion=pblcft&severidad=alta"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] > 0
        for mo in body["micro_obligaciones"]:
            assert mo["regulacion_relacionada"] == "pblcft"
            assert mo["severidad"] == "alta"

    @pytest.mark.asyncio
    async def test_listado_respuesta_con_total(self, client):
        resp = await client.get("/v1/micro-obligaciones")
        body = resp.json()
        assert "total" in body
        assert "micro_obligaciones" in body
        assert body["total"] == len(body["micro_obligaciones"])

    @pytest.mark.asyncio
    async def test_listado_campos_respuesta(self, client):
        resp = await client.get("/v1/micro-obligaciones?regulacion=mifid_ii")
        body = resp.json()
        first = body["micro_obligaciones"][0]
        assert "codigo" in first
        assert "nombre" in first
        assert "descripcion" in first
        assert "regulacion_relacionada" in first
        assert "ambito" in first
        assert "trigger_evento" in first
        assert "frecuencia" in first
        assert "owner_rol" in first
        assert "severidad" in first
        assert "activo" in first

    @pytest.mark.asyncio
    async def test_listado_ordenacion(self, client):
        resp = await client.get("/v1/micro-obligaciones")
        body = resp.json()
        # ORDER BY regulacion_relacionada ASC, codigo ASC
        items = body["micro_obligaciones"]
        keys = [(mo["regulacion_relacionada"], mo["codigo"]) for mo in items]
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# GET /v1/micro-obligaciones/{codigo} — detalle
# ---------------------------------------------------------------------------


class TestGetMicroObligacion:
    """Pruebas del endpoint de detalle."""

    @pytest.mark.asyncio
    async def test_detalle_mifid_suitability(self, client):
        resp = await client.get("/v1/micro-obligaciones/MIFID_SUITABILITY")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "MIFID_SUITABILITY"
        assert body["regulacion_relacionada"] == "mifid_ii"
        assert body["ambito"] == "mercados"
        assert body["severidad"] == "alta"
        assert body["owner_rol"] == "compliance"
        assert body["activo"] is True

    @pytest.mark.asyncio
    async def test_detalle_cnmv_transparencia(self, client):
        resp = await client.get("/v1/micro-obligaciones/CNMV_TRANSPARENCIA")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "CNMV_TRANSPARENCIA"
        assert body["regulacion_relacionada"] == "cnmv_lmcv"
        assert body["ambito"] == "reporting_regulatorio"

    @pytest.mark.asyncio
    async def test_detalle_sepblac_kyc(self, client):
        resp = await client.get("/v1/micro-obligaciones/SEPBLAC_KYC")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "SEPBLAC_KYC"
        assert body["regulacion_relacionada"] == "pblcft"
        assert body["ambito"] == "aml_cft"

    @pytest.mark.asyncio
    async def test_detalle_no_encontrado(self, client):
        resp = await client.get("/v1/micro-obligaciones/NO_EXISTE")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_detalle_mifir_reporting(self, client):
        resp = await client.get("/v1/micro-obligaciones/MIFIR_REPORTING")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "MIFIR_REPORTING"
        assert body["regulacion_relacionada"] == "mifir"
        assert body["trigger_evento"] == "ejecucion_orden"

    @pytest.mark.asyncio
    async def test_detalle_mifid_best_execution(self, client):
        resp = await client.get("/v1/micro-obligaciones/MIFID_BEST_EXECUTION")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "MIFID_BEST_EXECUTION"
        assert body["owner_rol"] == "trading"
        assert body["frecuencia"] == "continua"

    @pytest.mark.asyncio
    async def test_detalle_sepblac_str(self, client):
        resp = await client.get("/v1/micro-obligaciones/SEPBLAC_STR")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "SEPBLAC_STR"
        assert body["trigger_evento"] == "indicio_lp"
        assert body["severidad"] == "alta"

    @pytest.mark.asyncio
    async def test_detalle_obligaciones_relacionadas(self, client):
        resp = await client.get("/v1/micro-obligaciones/MIFID_BEST_EXECUTION")
        assert resp.status_code == 200
        body = resp.json()
        assert "obligaciones_relacionadas" in body
        assert isinstance(body["obligaciones_relacionadas"], list)

    @pytest.mark.asyncio
    async def test_detalle_lecr_ecr_registration(self, client):
        resp = await client.get("/v1/micro-obligaciones/LECR_ECR_REGISTRATION")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "LECR_ECR_REGISTRATION"
        assert body["regulacion_relacionada"] == "lecr"
        assert body["ambito"] == "ecr_regulatorio"
        assert body["severidad"] == "alta"

    @pytest.mark.asyncio
    async def test_detalle_socimi_asset_composition(self, client):
        resp = await client.get("/v1/micro-obligaciones/SOCIMI_ASSET_COMPOSITION")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "SOCIMI_ASSET_COMPOSITION"
        assert body["regulacion_relacionada"] == "socimi"
        assert body["ambito"] == "societario_fiscal"
        assert body["severidad"] == "alta"

    @pytest.mark.asyncio
    async def test_detalle_csdr_settlement(self, client):
        resp = await client.get("/v1/micro-obligaciones/CSDR_SETTLEMENT")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "CSDR_SETTLEMENT"
        assert body["regulacion_relacionada"] == "csdr"
        assert body["ambito"] == "infraestructuras_csd"
        assert body["frecuencia"] == "continua"

    @pytest.mark.asyncio
    async def test_detalle_cnmv_ecr_reporting(self, client):
        resp = await client.get("/v1/micro-obligaciones/CNMV_ECR_REPORTING")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "CNMV_ECR_REPORTING"
        assert body["regulacion_relacionada"] == "cnmv_ecr"
        assert body["ambito"] == "reporting_cnmv_ecr"

    @pytest.mark.asyncio
    async def test_detalle_dgt_socimi_gravamenes(self, client):
        resp = await client.get("/v1/micro-obligaciones/DGT_SOCIMI_GRAVAMENES")
        assert resp.status_code == 200
        body = resp.json()
        assert body["codigo"] == "DGT_SOCIMI_GRAVAMENES"
        assert body["regulacion_relacionada"] == "doctrina_dgt"
        assert body["ambito"] == "doctrina_dgt"
        assert "V0992-20" in body["descripcion"]


# ---------------------------------------------------------------------------
# GET /v1/micro-obligaciones/by-obligacion/{obligacion_codigo} — mapeo
# ---------------------------------------------------------------------------


class TestMicroObligacionesPorObligacion:
    """Pruebas del endpoint de mapeo por obligacion."""

    @pytest.mark.asyncio
    async def test_mapeo_obligacion_cnmv(self, client):
        resp = await client.get(
            "/v1/micro-obligaciones/by-obligacion/CNMV-IR-RESERVADA"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "obligacion" in body
        assert "micro_obligaciones" in body
        assert body["obligacion"]["codigo"] == "CNMV-IR-RESERVADA"
        assert len(body["micro_obligaciones"]) > 0

    @pytest.mark.asyncio
    async def test_mapeo_obligacion_sepblac(self, client):
        resp = await client.get(
            "/v1/micro-obligaciones/by-obligacion/SEPBLAC-INDICIO-M19"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["micro_obligaciones"]) > 0

    @pytest.mark.asyncio
    async def test_mapeo_obligacion_no_encontrada(self, client):
        resp = await client.get(
            "/v1/micro-obligaciones/by-obligacion/NO_EXISTE"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_mapeo_respuesta_tiene_obligacion(self, client):
        resp = await client.get(
            "/v1/micro-obligaciones/by-obligacion/CNMV-IR-RESERVADA"
        )
        body = resp.json()
        obligacion = body["obligacion"]
        assert "codigo" in obligacion
        assert "nombre" in obligacion
        assert "fuente" in obligacion

    @pytest.mark.asyncio
    async def test_mapeo_micro_obligaciones_tienen_campos(self, client):
        resp = await client.get(
            "/v1/micro-obligaciones/by-obligacion/CNMV-IR-RESERVADA"
        )
        body = resp.json()
        first = body["micro_obligaciones"][0]
        assert "codigo" in first
        assert "nombre" in first
        assert "descripcion" in first
        assert "regulacion_relacionada" in first
        assert "ambito" in first


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Casos borde."""

    @pytest.mark.asyncio
    async def test_listado_regulacion_vacia(self, client):
        resp = await client.get("/v1/micro-obligaciones?regulacion=noexiste")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert len(body["micro_obligaciones"]) == 0

    @pytest.mark.asyncio
    async def test_listado_ambito_vacio(self, client):
        resp = await client.get("/v1/micro-obligaciones?ambito=noexiste")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0

    @pytest.mark.asyncio
    async def test_detalle_codigo_vacio(self, client):
        resp = await client.get("/v1/micro-obligaciones/empty-code")
        assert resp.status_code == 404
