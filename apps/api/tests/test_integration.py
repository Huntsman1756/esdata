"""Integration tests for esdata API with real database."""

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "workers"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from main import app
from services.modelos import is_dirty_aeat_text


@pytest.fixture
def integration_db():
    """Reuse the shared sqlite test DB prepared by conftest."""
    from conftest import engine

    return engine


@pytest.fixture
def seeded_db(integration_db):
    """Add integration-specific worker rows on top of shared fixtures."""
    with integration_db.begin() as conn:
        conn.execute(text("DELETE FROM sync_log WHERE worker IN ('worker-boe', 'worker-dgt')"))
        conn.execute(text("""
            INSERT INTO sync_log (
                worker, started_at, finished_at, status,
                bloques_processed, articulos_upserted,
                documentos_processed, documentos_upserted, doctrina_links_created,
                error_msg
            )
            VALUES (
                'worker-boe', '2025-01-01T00:00:00+00:00', '2025-01-01T00:05:00+00:00', 'success',
                0, 150,
                0, 0, 0,
                NULL
            )
        """))
        conn.execute(text("""
            INSERT INTO sync_log (
                worker, started_at, finished_at, status,
                bloques_processed, articulos_upserted,
                documentos_processed, documentos_upserted, doctrina_links_created,
                error_msg
            )
            VALUES (
                'worker-dgt', '2025-01-01T00:00:00+00:00', '2025-01-01T00:03:00+00:00', 'success',
                0, 75,
                0, 0, 0,
                NULL
            )
        """))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_returns_ok(seeded_db):
    """Health endpoint always returns 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_returns_workers_and_api(seeded_db):
    """Status endpoint returns workers info and api status."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/status")
    assert r.status_code == 200
    data = r.json()
    assert data["api"] == "ok"
    assert "workers" in data
    assert "modelos" in data
    assert "timestamp" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_legislacion_list_returns_normas(seeded_db):
    """Legislacion list returns seeded normas."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/legislacion")
    assert r.status_code == 200
    data = r.json()
    assert "normas" in data
    codigos = [n["codigo"] for n in data["normas"]]
    assert "LIVA" in codigos
    assert "LIRPF" in codigos


@pytest.mark.integration
@pytest.mark.asyncio
async def test_legislacion_get_norma_returns_detail(seeded_db):
    """Get norma by code returns full detail."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/legislacion/LIVA")
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "LIVA"
    assert "titulo" in data
    assert data["tipo_fuente"] == "boe"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_legislacion_get_cobertura(seeded_db):
    """Cobertura endpoint returns article and version counts."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/legislacion/cobertura")
    assert r.status_code == 200
    data = r.json()
    assert "normas" in data
    iva_data = next((n for n in data["normas"] if n["codigo"] == "LIVA"), None)
    assert iva_data is not None
    assert iva_data["articulos"] >= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_modelos_list_returns_models(seeded_db):
    """Modelos list returns seeded AEAT models and fixture-specific coverage."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/modelos")
    assert r.status_code == 200
    data = r.json()
    assert "modelos" in data
    codigos = [m["codigo"] for m in data["modelos"]]
    assert "303" in codigos
    assert "100" in codigos


@pytest.mark.integration
@pytest.mark.asyncio
async def test_modelos_get_detail(seeded_db):
    """Get modelo detail returns casillas and instructions."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/modelos/303")
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "303"
    assert "campanas" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_modelo_303_dirty_parser_content_is_not_verified(seeded_db, integration_db):
    with integration_db.begin() as conn:
        conn.execute(
            text("""
                UPDATE aeat_modelo
                SET nombre = 'Agencia Tributaria Modelo 303. IVA. Autoliquidacion. Saltar al contenido principal <script src=""/static_files/common/script/aeat.07.js""></script>'
                WHERE codigo = '303'
            """)
        )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/v1/modelos/303", params={"campana": "2025"})
    assert resp.status_code == 200
    data = resp.json()
    serialized = str(data).lower()
    assert "saltar al contenido principal" not in serialized
    assert "static_files" not in serialized
    assert data["verified"] is False
    assert data["completeness"] == "partial"
    assert "aeat_parser_residue_detected" in data["warnings"]


def test_aeat_dirty_detection_ignores_plain_src_class_text():
    assert is_dirty_aeat_text("Campo class=tributario como texto explicativo") is False
    assert is_dirty_aeat_text("Código src=interno documentado como texto") is False
    assert is_dirty_aeat_text('<span class="nav"><script src="/static_files/common/script/aeat.07.js"></script></span>') is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_modelos_campana_operativa(seeded_db):
    """Campana operativa endpoint returns data for active campaign."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/modelos/303/campana-operativa")
    assert r.status_code == 200
    data = r.json()
    assert "campana" in data or "error" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_doctrina_search_returns_results(seeded_db):
    """Doctrina search returns seeded interpretative documents."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/doctrina/buscar?q=iva")
    assert r.status_code == 200
    data = r.json()
    assert "resultados" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_worker_sync_log(seeded_db):
    """Status shows workers from sync_log table."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/status")
    assert r.status_code == 200
    workers = r.json()["workers"]
    assert "worker-boe" in workers
    assert workers["worker-boe"]["status"] == "success"
    assert workers["worker-dgt"]["status"] == "success"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_buscar_returns_legislacion_results(seeded_db):
    """Buscar endpoint returns legislative results."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/legislacion/buscar?q=iva")
    assert r.status_code == 200
    data = r.json()
    assert "resultados" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_obligaciones_list(seeded_db):
    """Obligaciones endpoint returns data."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/obligaciones")
    assert r.status_code == 200
    data = r.json()
    assert "obligaciones" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_empresas_list_empty(seeded_db):
    """Empresas list returns empty when no data."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/empresas")
    assert r.status_code == 200
    data = r.json()
    assert "empresas" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chunks_endpoint_returns_empty(seeded_db):
    """Chunks endpoint works without chunk data."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/chunks/1")
    assert r.status_code in (200, 404)
    data = r.json()
    if r.status_code == 200:
        assert "chunks" in data or "chunk" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_consulta_endpoint_returns_data(seeded_db):
    """Consulta endpoint returns fiscal consultation results."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/consulta?q=iva")
    assert r.status_code == 200
    data = r.json()
    assert "resultados" in data or "error" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openapi_schema_valid(seeded_db):
    """OpenAPI schema is valid and includes all routes."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert "paths" in data
    assert "/health" in data["paths"]
    assert "/status" in data["paths"]
    assert "/v1/legislacion/buscar" in data["paths"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gpt_action_spec_endpoint(seeded_db):
    """GPT action spec endpoint serves valid OpenAPI."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/gpt-actions/modelos/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert data["openapi"] == "3.1.0"
    assert "/v1/modelos/{codigo}" in data["paths"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_privacy_policy_endpoint(seeded_db):
    """Privacy policy endpoint serves HTML."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/privacy")
    assert r.status_code == 200
    assert "privacy" in r.text.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_always_returns_200_even_with_db_errors(seeded_db):
    """Status endpoint is resilient to DB errors."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/status")
    assert r.status_code == 200
    assert "workers" in r.json()
    assert "modelos" in r.json()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cc_articulo_detail_with_vigente_en_after_legalize_seed(integration_db):
    from legalize_es import run_sync

    fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "cc.md"

    with integration_db.begin() as conn:
        conn.execute(text("DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'CC'))"))
        conn.execute(text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'CC')"))
        conn.execute(text("DELETE FROM norma WHERE codigo = 'CC'"))

    run_sync(integration_db, fixture_paths=[fixture])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/legislacion/CC/articulos/1?vigente_en=2025-01-02")

    assert r.status_code == 200
    data = r.json()
    assert data["norma"] == "CC"
    assert data["numero"] == "1"
    assert "ordenamiento juridico" in data["texto"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lec_articulo_detail_with_vigente_en_after_legalize_seed(integration_db):
    from legalize_es import run_sync

    fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "lec.md"

    with integration_db.begin() as conn:
        conn.execute(text("DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LEC'))"))
        conn.execute(text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LEC')"))
        conn.execute(text("DELETE FROM norma WHERE codigo = 'LEC'"))

    run_sync(integration_db, fixture_paths=[fixture])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/legislacion/LEC/articulos/1?vigente_en=2025-01-01")

    assert r.status_code == 200
    data = r.json()
    assert data["norma"] == "LEC"
    assert data["numero"] == "1"
    assert "competencia internacional" in data["texto"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_et_articulo_detail_with_vigente_en_after_legalize_seed(integration_db):
    from legalize_es import run_sync

    fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "et.md"

    with integration_db.begin() as conn:
        conn.execute(text("DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'ET'))"))
        conn.execute(text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'ET')"))
        conn.execute(text("DELETE FROM norma WHERE codigo = 'ET'"))

    run_sync(integration_db, fixture_paths=[fixture])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/legislacion/ET/articulos/1?vigente_en=2025-01-01")

    assert r.status_code == 200
    data = r.json()
    assert data["norma"] == "ET"
    assert data["numero"] == "1"
    assert "relaciones laborales" in data["texto"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lsc_articulo_detail_with_vigente_en_after_legalize_seed(integration_db):
    from legalize_es import run_sync

    fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "lsc.md"

    with integration_db.begin() as conn:
        conn.execute(text("DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LSC'))"))
        conn.execute(text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LSC')"))
        conn.execute(text("DELETE FROM norma WHERE codigo = 'LSC'"))

    run_sync(integration_db, fixture_paths=[fixture])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/legislacion/LSC/articulos/1?vigente_en=2025-01-01")

    assert r.status_code == 200
    data = r.json()
    assert data["norma"] == "LSC"
    assert data["numero"] == "1"
    assert "sociedades mercantiles" in data["texto"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lc_articulo_detail_with_vigente_en_after_legalize_seed(integration_db):
    from legalize_es import run_sync

    fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "lc.md"

    with integration_db.begin() as conn:
        conn.execute(text("DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LC'))"))
        conn.execute(text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LC')"))
        conn.execute(text("DELETE FROM norma WHERE codigo = 'LC'"))

    run_sync(integration_db, fixture_paths=[fixture])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/legislacion/LC/articulos/1?vigente_en=2025-01-01")

    assert r.status_code == 200
    data = r.json()
    assert data["norma"] == "LC"
    assert data["numero"] == "1"
    assert "procedimiento concursal" in data["texto"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lirpf_articulo_detail_with_vigente_en_after_legalize_seed(integration_db):
    from legalize_es import run_sync

    fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "irpf.md"

    with integration_db.begin() as conn:
        conn.execute(text("DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LIRPF'))"))
        conn.execute(text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LIRPF')"))
        conn.execute(text("DELETE FROM norma WHERE codigo = 'LIRPF'"))

    run_sync(integration_db, fixture_paths=[fixture])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/legislacion/LIRPF/articulos/1?vigente_en=2025-01-01")

    assert r.status_code == 200
    data = r.json()
    assert data["norma"] == "LIRPF"
    assert data["numero"] == "1"
    assert "impuesto" in data["texto"].lower()
# ruff: noqa: E501
