from pathlib import Path
import sys

from httpx import ASGITransport, AsyncClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


@pytest.mark.asyncio
async def test_participaciones_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/2/participaciones")

    assert r.status_code == 200
    data = r.json()
    assert data["empresa_id"] == 2
    assert "participaciones" in data


@pytest.mark.asyncio
async def test_participaciones_returns_seed_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/2/participaciones")

    data = r.json()
    assert len(data["participaciones"]) >= 3
    tipos = {p["tipo_participacion"] for p in data["participaciones"]}
    assert "directa" in tipos


@pytest.mark.asyncio
async def test_participaciones_404_unknown_empresa():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/99999/participaciones")

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_relaciones_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/2/relaciones")

    assert r.status_code == 200
    data = r.json()
    assert data["empresa_id"] == 2
    assert "relaciones" in data


@pytest.mark.asyncio
async def test_relaciones_includes_expected_types():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/2/relaciones")

    data = r.json()
    tipos = {rel["tipo_relacion"] for rel in data["relaciones"]}
    assert "absorbente" in tipos or "filial" in tipos


@pytest.mark.asyncio
async def test_relaciones_404_unknown_empresa():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/99999/relaciones")

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_beneficiarios_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/2/beneficiarios")

    assert r.status_code == 200
    data = r.json()
    assert data["empresa_id"] == 2
    assert "beneficiarios" in data


@pytest.mark.asyncio
async def test_beneficiarios_returns_ubo_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/2/beneficiarios")

    data = r.json()
    assert len(data["beneficiarios"]) >= 2
    nombres = {b["nombre_persona"] for b in data["beneficiarios"]}
    assert "Carlos Alvarez Garcia" in nombres


@pytest.mark.asyncio
async def test_beneficiarios_404_unknown_empresa():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/99999/beneficiarios")

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_grafo_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/2/grafo")

    assert r.status_code == 200
    data = r.json()
    assert data["empresa_id"] == 2
    assert "nodos" in data
    assert "aristas" in data


@pytest.mark.asyncio
async def test_grafo_has_nodes_and_edges():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/2/grafo")

    data = r.json()
    assert len(data["nodos"]) >= 2
    assert len(data["aristas"]) >= 1


@pytest.mark.asyncio
async def test_grafo_depth_param_respected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r_shallow = await c.get("/v1/ownership/2/grafo?profundidad=1")
        r_deep = await c.get("/v1/ownership/2/grafo?profundidad=5")

    data_shallow = r_shallow.json()
    data_deep = r_deep.json()
    assert len(data_shallow["aristas"]) <= len(data_deep["aristas"])


@pytest.mark.asyncio
async def test_grafo_404_unknown_empresa():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/99999/grafo")

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_grafo_invalid_depth_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/2/grafo?profundidad=0")

    assert r.status_code == 422


@pytest.mark.asyncio
async def test_grafo_invalid_depth_max_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/2/grafo?profundidad=6")

    assert r.status_code == 422


@pytest.mark.asyncio
async def test_buscar_con_ownership_requires_q():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/buscar")

    assert r.status_code == 422


@pytest.mark.asyncio
async def test_buscar_con_ownership_returns_results():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/buscar?q=alvarez")

    assert r.status_code == 200
    data = r.json()
    assert data["q"] == "alvarez"
    assert len(data["resultados"]) >= 1
    nombres = [r["nombre"] for r in data["resultados"]]
    assert "ALVAREZ GARCIA GANADERIA, S.L." in nombres


@pytest.mark.asyncio
async def test_buscar_con_ownership_solo_con_participaciones():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/buscar?q=murillo&solo_con_participaciones=true")

    assert r.status_code == 200
    data = r.json()
    assert len(data["resultados"]) >= 1
    for res in data["resultados"]:
        assert res["tiene_participaciones"] is True


@pytest.mark.asyncio
async def test_buscar_con_ownership_solo_con_ubos():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/buscar?q=murillo&solo_con_ubos=true")

    assert r.status_code == 200
    data = r.json()
    assert len(data["resultados"]) >= 1
    for res in data["resultados"]:
        assert res["tiene_ubos"] is True


@pytest.mark.asyncio
async def test_buscar_con_ownership_no_match():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/ownership/buscar?q=empresa_que_no_existe_12345")

    assert r.status_code == 200
    data = r.json()
    assert data["resultados"] == []
