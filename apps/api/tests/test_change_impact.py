from pathlib import Path
import sys

from httpx import ASGITransport, AsyncClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


@pytest.mark.asyncio
async def test_change_impact_endpoint_lists_seed_changes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/cambios")

    assert r.status_code == 200


@pytest.mark.asyncio
async def test_change_impact_includes_affected_obligation_codes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/cambios")

    data = r.json()
    assert "obligaciones_afectadas" in data[0]


@pytest.mark.asyncio
async def test_change_impact_exposes_operational_fields():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/cambios")

    data = r.json()
    cambio = data[0]
    assert cambio["accion_recomendada"] == "validar impacto y recalcular calendario de reporting"
    assert cambio["prioridad"] == "alta"
    assert cambio["fecha_detectado"] == "2026-04-25"


@pytest.mark.asyncio
async def test_change_impact_can_filter_by_fuente():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/cambios?fuente=cnmv")

    data = r.json()
    assert r.status_code == 200
    assert len(data) == 1
    assert all(item["fuente"] == "cnmv" for item in data)


@pytest.mark.asyncio
async def test_change_impact_fuente_filter_excludes_non_matching_results():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/cambios?fuente=sepblac")

    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_change_impact_can_filter_by_estado_and_prioridad():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/cambios?estado=nuevo&prioridad=alta")

    data = r.json()
    assert r.status_code == 200
    assert len(data) == 1
    assert data[0]["estado"] == "nuevo"
    assert data[0]["prioridad"] == "alta"


@pytest.mark.asyncio
async def test_change_impact_estado_and_prioridad_filters_exclude_non_matching_results():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/cambios?estado=resuelto&prioridad=baja")

    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_change_impact_can_filter_by_obligacion_afectada():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/cambios?obligacion_afectada=CNMV-IR-RESERVADA")

    data = r.json()
    assert r.status_code == 200
    assert len(data) == 1
    assert "CNMV-IR-RESERVADA" in data[0]["obligaciones_afectadas"]


@pytest.mark.asyncio
async def test_change_impact_obligacion_filter_excludes_non_matching_results():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/cambios?obligacion_afectada=SEPBLAC-INDICIO-M19")

    assert r.status_code == 200
    assert r.json() == []
