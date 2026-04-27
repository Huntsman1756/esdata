from pathlib import Path
import sys

from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


# ---------------------------------------------------------------------------
# Shared test client fixture (session-scoped to reuse DB + app)
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
async def playbook_id(client):
    """Return the ID of the existing seed playbook PLAYBOOK-CNMV-IR."""
    r = await client.get("/v1/playbooks", params={"limit": 100})
    data = r.json()
    found = [pb for pb in data["playbooks"] if pb["codigo"] == "PLAYBOOK-CNMV-IR"]
    if found:
        return found[0]["id"]
    return data["playbooks"][0]["id"]


@pytest_asyncio.fixture
async def step_id(client, playbook_id):
    """Create a step and return its ID for tests."""
    r = await client.post(f"/v1/playbooks/{playbook_id}/steps", json={
        "orden": 1,
        "titulo": "Paso de prueba",
        "descripcion": "Descripcion del paso",
        "tipo_paso": "accion",
        "responsable_rol": "compliance",
    })
    assert r.status_code == 200
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Playbook operativo — list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_listar_playbooks_returns_200(client):
    r = await client.get("/v1/playbooks")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_listar_playbooks_returns_seed_data(client):
    r = await client.get("/v1/playbooks")
    data = r.json()
    assert data["total"] >= 2
    playbooks = data["playbooks"]
    assert len(playbooks) >= 2


@pytest.mark.asyncio
async def test_listar_playbooks_filters_by_estado(client):
    r = await client.get("/v1/playbooks", params={"estado": "activo"})
    data = r.json()
    assert r.status_code == 200
    assert data["total"] >= 1
    for pb in data["playbooks"]:
        assert pb["estado"] == "activo"


@pytest.mark.asyncio
async def test_listar_playbooks_filters_by_obligacion(client):
    r = await client.get("/v1/playbooks", params={"obligacion": "CNMV-IR-RESERVADA"})
    data = r.json()
    assert r.status_code == 200
    assert data["total"] >= 1
    for pb in data["playbooks"]:
        assert pb["obligacion_codigo"] == "CNMV-IR-RESERVADA"


@pytest.mark.asyncio
async def test_listar_playbooks_search_by_name(client):
    r = await client.get("/v1/playbooks", params={"q": "CNMV"})
    data = r.json()
    assert r.status_code == 200
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_listar_playbooks_pagination(client):
    r = await client.get("/v1/playbooks", params={"limit": 1, "skip": 0})
    data = r.json()
    assert r.status_code == 200
    assert len(data["playbooks"]) <= 1


# ---------------------------------------------------------------------------
# Playbook operativo — detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_playbook_returns_200(client):
    r = await client.get("/v1/playbooks")
    data = r.json()
    pb_id = data["playbooks"][0]["id"]
    r = await client.get(f"/v1/playbooks/{pb_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["codigo"] == data["playbooks"][0]["codigo"]
    assert "pasos" in body
    assert "evidencias" in body
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_get_playbook_404(client):
    r = await client.get("/v1/playbooks/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_playbook_has_seed_steps(client):
    r = await client.get("/v1/playbooks")
    data = r.json()
    pb_id = data["playbooks"][0]["id"]
    r = await client.get(f"/v1/playbooks/{pb_id}")
    body = r.json()
    pasos = body["pasos"]
    assert len(pasos) >= 5
    assert pasos[0]["orden"] == 1
    assert pasos[0]["titulo"] == "Recopilar datos contables mensuales"


@pytest.mark.asyncio
async def test_get_playbook_has_seed_evidencias(client):
    r = await client.get("/v1/playbooks")
    data = r.json()
    pb_id = data["playbooks"][0]["id"]
    r = await client.get(f"/v1/playbooks/{pb_id}")
    body = r.json()
    evidencias = body["evidencias"]
    assert len(evidencias) >= 4
    assert evidencias[0]["codigo"] == "EVID-CNMV-IR-001"


# ---------------------------------------------------------------------------
# Playbook operativo — create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crear_playbook(client):
    r = await client.post("/v1/playbooks", json={
        "codigo": "PLAYBOOK-TEST-CREATE",
        "nombre": "Playbook creado por test",
        "obligacion_codigo": "TEST-OB-CREATE",
        "descripcion": "Descripcion de prueba",
        "frecuencia": "anual",
        "owner_rol": "legal",
        "estado": "activo",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["codigo"] == "PLAYBOOK-TEST-CREATE"
    assert body["nombre"] == "Playbook creado por test"
    assert body["estado"] == "activo"
    assert body["version"] == 1
    assert body["pasos"] == []
    assert body["evidencias"] == []

    # Verify persistence
    r2 = await client.get(f"/v1/playbooks/{body['id']}")
    assert r2.status_code == 200
    assert r2.json()["codigo"] == "PLAYBOOK-TEST-CREATE"


@pytest.mark.asyncio
async def test_crear_playbook_duplicate_code(client):
    r = await client.post("/v1/playbooks", json={
        "codigo": "PLAYBOOK-CNMV-IR",
        "nombre": "Intento de duplicado",
        "obligacion_codigo": "CNMV-IR-RESERVADA",
        "estado": "activo",
    })
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# Playbook operativo — update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_actualizar_playbook(client, playbook_id):
    r = await client.patch(f"/v1/playbooks/{playbook_id}", json={
        "estado": "inactivo",
        "nombre": "Playbook actualizado",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["estado"] == "inactivo"
    assert body["nombre"] == "Playbook actualizado"

    # Verify persistence
    r2 = await client.get(f"/v1/playbooks/{playbook_id}")
    assert r2.status_code == 200
    assert r2.json()["estado"] == "inactivo"


@pytest.mark.asyncio
async def test_actualizar_playbook_404(client):
    r = await client.patch("/v1/playbooks/00000000-0000-0000-0000-000000000000", json={
        "estado": "inactivo",
    })
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Playbook steps — list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_listar_pasos_playbook(client, playbook_id):
    r = await client.get(f"/v1/playbooks/{playbook_id}/steps")
    assert r.status_code == 200
    body = r.json()
    assert "pasos" in body
    assert body["playbook_id"] == playbook_id
    assert len(body["pasos"]) >= 5


@pytest.mark.asyncio
async def test_listar_pasos_playbook_filters_by_tipo(client, playbook_id):
    r = await client.get(f"/v1/playbooks/{playbook_id}/steps", params={"tipo": "revision"})
    assert r.status_code == 200
    body = r.json()
    for paso in body["pasos"]:
        assert paso["tipo_paso"] == "revision"


@pytest.mark.asyncio
async def test_listar_pasos_playbook_404(client):
    r = await client.get("/v1/playbooks/00000000-0000-0000-0000-000000000000/steps")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Playbook steps — create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crear_paso_playbook(client, playbook_id):
    r = await client.post(f"/v1/playbooks/{playbook_id}/steps", json={
        "orden": 99,
        "titulo": "Paso creado por test",
        "descripcion": "Descripcion del paso de prueba",
        "tipo_paso": "verificacion",
        "responsable_rol": "auditor",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["orden"] == 99
    assert body["titulo"] == "Paso creado por test"
    assert body["tipo_paso"] == "verificacion"

    # Verify persistence
    r2 = await client.get(f"/v1/playbooks/{playbook_id}/steps")
    assert r2.status_code == 200
    pasos = r2.json()["pasos"]
    assert any(p["id"] == body["id"] for p in pasos)


@pytest.mark.asyncio
async def test_crear_paso_playbook_404(client):
    r = await client.post("/v1/playbooks/00000000-0000-0000-0000-000000000000/steps", json={
        "orden": 1,
        "titulo": "Paso sin playbook",
        "tipo_paso": "accion",
    })
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Playbook steps — update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_actualizar_paso_playbook(client, step_id):
    r = await client.patch(f"/v1/playbooks/steps/{step_id}", json={
        "titulo": "Paso actualizado",
        "activo": False,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["titulo"] == "Paso actualizado"
    assert body["activo"] is False


@pytest.mark.asyncio
async def test_actualizar_paso_playbook_404(client):
    r = await client.patch("/v1/playbooks/steps/00000000-0000-0000-0000-000000000000", json={
        "titulo": "Paso fantasma",
    })
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Evidencia control — list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_listar_evidencias_playbook(client, playbook_id):
    r = await client.get(f"/v1/playbooks/{playbook_id}/evidencias")
    assert r.status_code == 200
    body = r.json()
    assert "evidencias" in body
    assert "total" in body
    assert body["total"] >= 4


@pytest.mark.asyncio
async def test_listar_evidencias_playbook_filters_by_tipo(client, playbook_id):
    r = await client.get(f"/v1/playbooks/{playbook_id}/evidencias", params={"tipo": "documento"})
    body = r.json()
    assert r.status_code == 200
    for ev in body["evidencias"]:
        assert ev["tipo_evidencia"] == "documento"


@pytest.mark.asyncio
async def test_listar_evidencias_playbook_filters_by_obligatoria(client):
    r = await client.get("/v1/playbooks")
    data = r.json()
    pb_id = data["playbooks"][0]["id"]
    r = await client.get(f"/v1/playbooks/{pb_id}/evidencias", params={"obligatoria": True})
    body = r.json()
    assert r.status_code == 200
    for ev in body["evidencias"]:
        assert ev["obligatoria"] is True


@pytest.mark.asyncio
async def test_listar_evidencias_playbook_404(client):
    r = await client.get("/v1/playbooks/00000000-0000-0000-0000-000000000000/evidencias")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Evidencia control — update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_actualizar_evidencia(client, playbook_id):
    # Get first evidence
    r = await client.get(f"/v1/playbooks/{playbook_id}/evidencias")
    evid_id = r.json()["evidencias"][0]["id"]

    # Update it
    r = await client.patch(f"/v1/playbooks/evidencias/{evid_id}", json={
        "estado": "capturado",
        "capturado_en": "2026-04-25",
        "verificado_por": "test_verifier",
        "nota": "Evidencia capturada por test",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["estado"] == "capturado"
    assert body["capturado_en"] == "2026-04-25"
    assert body["verificado_por"] == "test_verifier"
    assert body["nota"] == "Evidencia capturada por test"


@pytest.mark.asyncio
async def test_actualizar_evidencia_404(client):
    r = await client.patch("/v1/playbooks/evidencias/00000000-0000-0000-0000-000000000000", json={
        "estado": "capturado",
    })
    assert r.status_code == 404
