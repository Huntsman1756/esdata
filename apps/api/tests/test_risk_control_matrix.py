"""Tests for Risk-Control Matrix endpoints — Fase 22.

Covers:
- riesgo_regulatorio CRUD + filters
- control_interno CRUD + filters
- riesgo_control_link create + list + detail
- prueba_control create + list
- control_gaps aggregate view
"""

import sys
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app

# ---------------------------------------------------------------------------
# Shared test client fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers — create resources and return IDs
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def riesgo_id(client):
    """Create a test risk and return its ID."""
    uid = uuid4().hex[:8]
    codigo = f"RCM-TEST-{uid}"
    r = await client.post("/v1/risk-control/riesgos", json={
        "codigo": codigo,
        "nombre": "Riesgo de prueba RCM",
        "descripcion": "Descripcion del riesgo de prueba RCM",
        "obligacion_codigo": "OBL-001",
        "categoria": "compliance",
        "severidad": "alta",
        "probabilidad": "probable",
        "area_responsable": "compliance",
        "owner_rol": "compliance_officer",
        "estado": "abierto",
    })
    assert r.status_code == 200
    return {"id": r.json()["id"], "codigo": codigo}


@pytest_asyncio.fixture
async def control_id(client):
    """Create a test control and return its ID."""
    uid = uuid4().hex[:8]
    codigo = f"RCM-CTRL-{uid}"
    r = await client.post("/v1/risk-control/controles", json={
        "codigo": codigo,
        "nombre": "Control de prueba RCM",
        "descripcion": "Descripcion del control de prueba RCM",
        "tipo_control": "preventivo",
        "frecuencia": "mensual",
        "owner_rol": "compliance_officer",
        "sistema_apoyo": "test-system",
        "estado": "activo",
    })
    assert r.status_code == 200
    return {"id": r.json()["id"], "codigo": codigo}


@pytest_asyncio.fixture
async def link_id(client, riesgo_id, control_id):
    """Create a risk-control link and return its ID."""
    r = await client.post("/v1/risk-control/links", json={
        "riesgo_id": riesgo_id["id"],
        "control_id": control_id["id"],
        "efectividad": "efectivo",
        "riesgo_residual": "bajo",
        "frecuencia_prueba": "mensual",
        "criterio_suficiencia": "100% cobertura",
        "caducidad_dias": 365,
    })
    assert r.status_code == 200
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Riesgo regulatorio — create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crear_riesgo(client):
    r = await client.post("/v1/risk-control/riesgos", json={
        "codigo": "RC-NEW-001",
        "nombre": "Nuevo riesgo",
        "obligacion_codigo": "OBL-NEW",
        "categoria": "operativo",
        "severidad": "media",
        "estado": "abierto",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "RC-NEW-001"
    assert data["nombre"] == "Nuevo riesgo"
    assert data["estado"] == "abierto"
    assert "id" in data


@pytest.mark.asyncio
async def test_crear_riesgo_duplicate_code(client):
    uid = uuid4().hex[:8]
    r = await client.post("/v1/risk-control/riesgos", json={
        "codigo": f"RCM-DUP-{uid}",
        "nombre": "Riesgo duplicado",
        "obligacion_codigo": "OBL-001",
        "categoria": "compliance",
        "severidad": "alta",
        "estado": "abierto",
    })
    assert r.status_code == 200
    r2 = await client.post("/v1/risk-control/riesgos", json={
        "codigo": f"RCM-DUP-{uid}",
        "nombre": "Riesgo duplicado 2",
        "obligacion_codigo": "OBL-001",
        "categoria": "compliance",
        "severidad": "alta",
        "estado": "abierto",
    })
    assert r2.status_code == 409


# ---------------------------------------------------------------------------
# Riesgo regulatorio — list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_listar_riesgos_returns_200(client):
    r = await client.get("/v1/risk-control/riesgos")
    assert r.status_code == 200
    data = r.json()
    assert "riesgos" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_listar_riesgos_filters_by_severity(client):
    r = await client.get("/v1/risk-control/riesgos", params={"severidad": "critica"})
    assert r.status_code == 200
    data = r.json()
    for riesgo in data["riesgos"]:
        assert riesgo["severidad"] == "critica"


@pytest.mark.asyncio
async def test_listar_riesgos_filters_by_category(client):
    r = await client.get("/v1/risk-control/riesgos", params={"categoria": "compliance"})
    assert r.status_code == 200
    data = r.json()
    for riesgo in data["riesgos"]:
        assert riesgo["categoria"] == "compliance"


@pytest.mark.asyncio
async def test_listar_riesgos_search_by_name(client):
    r = await client.get("/v1/risk-control/riesgos", params={"q": "prueba"})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Riesgo regulatorio — detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_riesgo_detail(client, riesgo_id):
    r = await client.get(f"/v1/risk-control/riesgos/{riesgo_id['id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == riesgo_id["id"]
    assert data["codigo"] == riesgo_id["codigo"]
    assert "controles" in data


@pytest.mark.asyncio
async def test_get_riesgo_not_found(client):
    r = await client.get("/v1/risk-control/riesgos/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Riesgo regulatorio — update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_actualizar_riesgo(client, riesgo_id):
    r = await client.patch(f"/v1/risk-control/riesgos/{riesgo_id['id']}", json={
        "estado": "cerrado",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["estado"] == "cerrado"


@pytest.mark.asyncio
async def test_actualizar_riesgo_partial(client, riesgo_id):
    r = await client.patch(f"/v1/risk-control/riesgos/{riesgo_id['id']}", json={
        "area_responsable": "auditoria",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["area_responsable"] == "auditoria"


@pytest.mark.asyncio
async def test_actualizar_riesgo_no_fields(client, riesgo_id):
    r = await client.patch(f"/v1/risk-control/riesgos/{riesgo_id['id']}", json={})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_actualizar_riesgo_not_found(client):
    r = await client.patch(
        "/v1/risk-control/riesgos/00000000-0000-0000-0000-000000000000",
        json={"estado": "cerrado"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Control interno — create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crear_control(client):
    r = await client.post("/v1/risk-control/controles", json={
        "codigo": "CTRL-NEW-001",
        "nombre": "Nuevo control",
        "tipo_control": "detectivo",
        "frecuencia": "trimestral",
        "owner_rol": "auditor",
        "estado": "activo",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "CTRL-NEW-001"
    assert data["estado"] == "activo"


@pytest.mark.asyncio
async def test_crear_control_duplicate_code(client, control_id):
    r = await client.post("/v1/risk-control/controles", json={
        "codigo": control_id["codigo"],
        "nombre": "Control de prueba RCM duplicado",
        "tipo_control": "preventivo",
        "frecuencia": "mensual",
        "owner_rol": "compliance_officer",
        "estado": "activo",
    })
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# Control interno — list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_listar_controles_returns_200(client):
    r = await client.get("/v1/risk-control/controles")
    assert r.status_code == 200
    data = r.json()
    assert "controles" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_listar_controles_filters_by_type(client):
    r = await client.get("/v1/risk-control/controles", params={"tipo": "preventivo"})
    assert r.status_code == 200
    data = r.json()
    for control in data["controles"]:
        assert control["tipo_control"] == "preventivo"


@pytest.mark.asyncio
async def test_listar_controles_filters_by_owner(client):
    r = await client.get("/v1/risk-control/controles", params={"owner_rol": "compliance_officer"})
    assert r.status_code == 200
    data = r.json()
    for control in data["controles"]:
        assert control["owner_rol"] == "compliance_officer"


# ---------------------------------------------------------------------------
# Control interno — detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_control_detail(client, control_id):
    r = await client.get(f"/v1/risk-control/controles/{control_id['id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == control_id["id"]
    assert data["codigo"] == control_id["codigo"]
    assert "pruebas" in data


@pytest.mark.asyncio
async def test_get_control_not_found(client):
    r = await client.get("/v1/risk-control/controles/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Control interno — update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_actualizar_control(client, control_id):
    r = await client.patch(f"/v1/risk-control/controles/{control_id['id']}", json={
        "estado": "inactivo",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["estado"] == "inactivo"


@pytest.mark.asyncio
async def test_actualizar_control_no_fields(client, control_id):
    r = await client.patch(f"/v1/risk-control/controles/{control_id['id']}", json={})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Riesgo-Control link — create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crear_link(client, riesgo_id, control_id):
    r = await client.post("/v1/risk-control/links", json={
        "riesgo_id": riesgo_id["id"],
        "control_id": control_id["id"],
        "efectividad": "efectivo",
        "riesgo_residual": "bajo",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["riesgo_codigo"] is not None
    assert data["control_codigo"] is not None
    assert "pruebas" in data


@pytest.mark.asyncio
async def test_crear_link_risk_not_found(client, control_id):
    r = await client.post("/v1/risk-control/links", json={
        "riesgo_id": "00000000-0000-0000-0000-000000000000",
        "control_id": control_id["id"],
        "efectividad": "efectivo",
    })
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_crear_link_control_not_found(client, riesgo_id):
    r = await client.post("/v1/risk-control/links", json={
        "riesgo_id": riesgo_id["id"],
        "control_id": "00000000-0000-0000-0000-000000000000",
        "efectividad": "efectivo",
    })
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_crear_link_duplicate(client, link_id, riesgo_id, control_id):
    r = await client.post("/v1/risk-control/links", json={
        "riesgo_id": riesgo_id["id"],
        "control_id": control_id["id"],
        "efectividad": "efectivo",
    })
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# Riesgo-Control link — list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_listar_links_returns_200(client, riesgo_id, control_id):
    r = await client.get("/v1/risk-control/links")
    assert r.status_code == 200
    data = r.json()
    assert "links" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_listar_links_filters_by_riesgo(client, riesgo_id):
    r = await client.get("/v1/risk-control/links", params={"riesgo_id": riesgo_id["id"]})
    assert r.status_code == 200
    data = r.json()
    for link in data["links"]:
        assert link["riesgo_id"] == riesgo_id["id"]


@pytest.mark.asyncio
async def test_listar_links_filters_by_control(client, control_id):
    r = await client.get("/v1/risk-control/links", params={"control_id": control_id["id"]})
    assert r.status_code == 200
    data = r.json()
    for link in data["links"]:
        assert link["control_id"] == control_id["id"]


@pytest.mark.asyncio
async def test_listar_links_filters_by_effectiveness(client, riesgo_id, control_id):
    r = await client.get("/v1/risk-control/links", params={"efectividad": "efectivo"})
    assert r.status_code == 200
    data = r.json()
    for link in data["links"]:
        assert link["efectividad"] == "efectivo"


# ---------------------------------------------------------------------------
# Riesgo-Control link — detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_link_detail(client, link_id):
    r = await client.get(f"/v1/risk-control/links/{link_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == link_id
    assert "pruebas" in data


@pytest.mark.asyncio
async def test_get_link_not_found(client):
    r = await client.get("/v1/risk-control/links/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Prueba control — create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crear_prueba(client, link_id):
    r = await client.post("/v1/risk-control/pruebas", json={
        "link_id": link_id,
        "fecha_prueba": "2025-06-15",
        "resultado": "aprobado",
        "evidencia_descripcion": "Revision de documentos",
        "ejecutado_por": "auditor_test",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["link_id"] == link_id
    assert data["resultado"] == "aprobado"
    assert data["fecha_prueba"] == "2025-06-15"


@pytest.mark.asyncio
async def test_crear_prueba_invalid_date(client, link_id):
    r = await client.post("/v1/risk-control/pruebas", json={
        "link_id": link_id,
        "fecha_prueba": "not-a-date",
        "resultado": "aprobado",
        "evidencia_descripcion": "Test",
        "ejecutado_por": "auditor",
    })
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_crear_prueba_link_not_found(client):
    r = await client.post("/v1/risk-control/pruebas", json={
        "link_id": "00000000-0000-0000-0000-000000000000",
        "fecha_prueba": "2025-06-15",
        "resultado": "aprobado",
        "evidencia_descripcion": "Test",
        "ejecutado_por": "auditor",
    })
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Prueba control — list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_listar_pruebas(client, link_id):
    # Create a test first
    await client.post("/v1/risk-control/pruebas", json={
        "link_id": link_id,
        "fecha_prueba": "2025-06-15",
        "resultado": "aprobado",
        "evidencia_descripcion": "Test evidence",
        "ejecutado_por": "auditor",
    })

    r = await client.get("/v1/risk-control/pruebas", params={"link_id": link_id})
    assert r.status_code == 200
    data = r.json()
    assert "pruebas" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_listar_pruebas_filters_by_result(client, link_id):
    # Create two tests with different results
    await client.post("/v1/risk-control/pruebas", json={
        "link_id": link_id,
        "fecha_prueba": "2025-06-15",
        "resultado": "aprobado",
        "evidencia_descripcion": "Test",
        "ejecutado_por": "auditor",
    })
    await client.post("/v1/risk-control/pruebas", json={
        "link_id": link_id,
        "fecha_prueba": "2025-07-15",
        "resultado": "reprobado",
        "evidencia_descripcion": "Test",
        "ejecutado_por": "auditor",
    })

    r = await client.get("/v1/risk-control/pruebas", params={
        "link_id": link_id,
        "resultado": "reprobado",
    })
    assert r.status_code == 200
    data = r.json()
    for prueba in data["pruebas"]:
        assert prueba["resultado"] == "reprobado"


@pytest.mark.asyncio
async def test_listar_pruebas_link_not_found(client):
    r = await client.get("/v1/risk-control/pruebas", params={
        "link_id": "00000000-0000-0000-0000-000000000000",
    })
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Control gaps — aggregate view
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_control_gaps_returns_200(client):
    r = await client.get("/v1/risk-control/gaps")
    assert r.status_code == 200
    data = r.json()
    assert "gaps" in data
    assert "total" in data
    assert "resumen" in data


@pytest.mark.asyncio
async def test_control_gaps_resumen_structure(client):
    r = await client.get("/v1/risk-control/gaps")
    data = r.json()
    resumen = data["resumen"]
    assert "sin_control" in resumen
    assert "parcial" in resumen
    assert "completo" in resumen
    assert "total" in resumen


@pytest.mark.asyncio
async def test_control_gaps_filters_by_area(client):
    r = await client.get("/v1/risk-control/gaps", params={"area": "compliance"})
    assert r.status_code == 200
    data = r.json()
    for gap in data["gaps"]:
        # Each gap should have info about the risk
        assert "riesgo_codigo" in gap
        assert "estado" in gap


@pytest.mark.asyncio
async def test_control_gaps_filters_by_estado(client):
    r = await client.get("/v1/risk-control/gaps", params={"estado": "sin_control"})
    assert r.status_code == 200
    data = r.json()
    for gap in data["gaps"]:
        assert gap["estado"] == "sin_control"


@pytest.mark.asyncio
async def test_control_gap_fields(client):
    r = await client.get("/v1/risk-control/gaps")
    data = r.json()
    if data["gaps"]:
        gap = data["gaps"][0]
        assert "riesgo_codigo" in gap
        assert "riesgo_nombre" in gap
        assert "severidad" in gap
        assert "obligacion_codigo" in gap
        assert "controles_asignados" in gap
        assert "controles_efectivos" in gap
        assert "estado" in gap
