from pathlib import Path
import sys

from httpx import ASGITransport, AsyncClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


@pytest.mark.asyncio
async def test_workflow_endpoint_lists_cases_for_changes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/compliance/workflow")

    assert r.status_code == 200


@pytest.mark.asyncio
async def test_workflow_case_exposes_owner_status_and_checklist():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/compliance/workflow")

    data = r.json()["items"]
    caso = data[0]
    assert caso["cambio_codigo"] == "CAMBIO-CNMV-001"
    assert caso["estado"] == "pendiente_revision"
    assert caso["owner_rol"] == "compliance"
    assert caso["evidencia_requerida"] == ["analisis_impacto", "actualizacion_calendario"]
    assert caso["checklist"] == [
        "validar impacto normativo",
        "asignar responsable",
        "confirmar fecha objetivo",
    ]


@pytest.mark.asyncio
async def test_workflow_case_exposes_target_date():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/compliance/workflow")

    data = r.json()["items"]
    assert data[0]["fecha_objetivo"] == "2026-05-05"


@pytest.mark.asyncio
async def test_workflow_case_exposes_resultado_revision():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/compliance/workflow")

    data = r.json()["items"]
    caso = data[0]
    assert "resultado_revision" in caso
    assert caso["resultado_revision"] is None


@pytest.mark.asyncio
async def test_workflow_case_exposes_notas():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/compliance/workflow")

    data = r.json()["items"]
    caso = data[0]
    assert "notas" in caso
    assert caso["notas"] is None


@pytest.mark.asyncio
async def test_workflow_case_exposes_accion_recomendada_confirmada():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/compliance/workflow")

    data = r.json()["items"]
    caso = data[0]
    assert "accion_recomendada_confirmada" in caso
    assert caso["accion_recomendada_confirmada"] is None


@pytest.mark.asyncio
async def test_workflow_case_exposes_workflow_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/compliance/workflow")

    data = r.json()["items"]
    caso = data[0]
    assert "workflow_id" in caso
    assert caso["workflow_id"] == "WF-001"
