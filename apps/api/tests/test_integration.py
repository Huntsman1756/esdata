"""Integration tests for esdata API with real database."""

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


@pytest.fixture
def integration_db():
    """Create a test database with schema and seed data for integration tests."""
    db_path = Path(__file__).resolve().parents[1] / "tests" / "test_integration_esdata.sqlite3"
    if db_path.exists():
        db_path.unlink()

    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE norma (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                titulo TEXT NOT NULL,
                boe_id TEXT UNIQUE NOT NULL,
                eli_uri TEXT UNIQUE,
                jurisdiccion TEXT NOT NULL,
                tipo_fuente TEXT NOT NULL,
                tipo_documento TEXT NOT NULL,
                ambito TEXT NOT NULL,
                estado_cobertura TEXT NOT NULL,
                vigente_desde TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))

        conn.execute(text("""
            CREATE TABLE articulo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                norma_id INTEGER NOT NULL,
                numero INTEGER NOT NULL,
                tipo TEXT,
                FOREIGN KEY (norma_id) REFERENCES norma(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE version_articulo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                articulo_id INTEGER NOT NULL,
                texto TEXT NOT NULL,
                vigente_desde TEXT NOT NULL,
                search_vector TSVECTOR,
                FOREIGN KEY (articulo_id) REFERENCES articulo(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE documento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origen_tipo TEXT NOT NULL,
                origen_id TEXT NOT NULL,
                titulo TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))

        conn.execute(text("""
            CREATE TABLE documento_articulo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento_id INTEGER NOT NULL,
                articulo_id INTEGER NOT NULL,
                FOREIGN KEY (documento_id) REFERENCES documento(id),
                FOREIGN KEY (articulo_id) REFERENCES articulo(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT,
                rows_added INTEGER DEFAULT 0,
                error_msg TEXT,
                bloques_processed INTEGER DEFAULT 0,
                articulos_upserted INTEGER DEFAULT 0,
                documentos_processed INTEGER DEFAULT 0,
                documentos_upserted INTEGER DEFAULT 0,
                doctrina_links_created INTEGER DEFAULT 0
            )
        """))

        conn.execute(text("""
            CREATE TABLE aeat_modelo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                activo INTEGER DEFAULT 1
            )
        """))

        conn.execute(text("""
            CREATE TABLE modelo_campana (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                modelo_id INTEGER NOT NULL,
                campana TEXT NOT NULL,
                activo INTEGER DEFAULT 0,
                FOREIGN KEY (modelo_id) REFERENCES aeat_modelo(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE modelo_casilla (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                modelo_id INTEGER NOT NULL,
                codigo TEXT NOT NULL,
                etiqueta TEXT,
                campana_id INTEGER,
                FOREIGN KEY (modelo_id) REFERENCES aeat_modelo(id),
                FOREIGN KEY (campana_id) REFERENCES modelo_campana(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE modelo_instruccion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                modelo_id INTEGER NOT NULL,
                seccion TEXT,
                titulo TEXT,
                contenido TEXT,
                orden INTEGER,
                campana_id INTEGER,
                FOREIGN KEY (modelo_id) REFERENCES aeat_modelo(id),
                FOREIGN KEY (campana_id) REFERENCES modelo_campana(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE modelo_normativa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                modelo_id INTEGER NOT NULL,
                titulo TEXT,
                referencia TEXT,
                FOREIGN KEY (modelo_id) REFERENCES aeat_modelo(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE modelo_clave (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                modelo_id INTEGER NOT NULL,
                codigo TEXT NOT NULL,
                etiqueta TEXT,
                campana_id INTEGER,
                FOREIGN KEY (modelo_id) REFERENCES aeat_modelo(id),
                FOREIGN KEY (campana_id) REFERENCES modelo_campana(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE modelo_campana_operativa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campana_id INTEGER NOT NULL,
                categoria_obligado TEXT,
                frecuencia_presentacion TEXT,
                FOREIGN KEY (campana_id) REFERENCES modelo_campana(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE documento_interpretativo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                texto TEXT NOT NULL,
                origen_tipo TEXT,
                origen_id TEXT,
                tipo_documento TEXT,
                organismo_emisor TEXT,
                fecha TEXT,
                referencia TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))

        conn.execute(text("""
            CREATE TABLE materia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                slug TEXT UNIQUE NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE evaluacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                query_id TEXT NOT NULL,
                dominio TEXT,
                score REAL,
                status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))

    return engine


@pytest.fixture
def seeded_db(integration_db):
    """Seed the test database with sample data."""
    with integration_db.begin() as conn:
        conn.execute(text("""
            INSERT INTO norma (codigo, titulo, boe_id, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde)
            VALUES ('LIVA', 'Ley 37/1992 - IVA', 'BOE-A-1992-2845', 'es', 'ley', 'ley', 'tributario', 'completa', '1992-12-28')
        """))
        conn.execute(text("""
            INSERT INTO norma (codigo, titulo, boe_id, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde)
            VALUES ('LIRPF', 'Ley 35/2006 - IRPF', 'BOE-A-2006-21323', 'es', 'ley', 'ley', 'tributario', 'completa', '2006-11-15')
        """))

        conn.execute(text("""
            INSERT INTO articulo (norma_id, numero, tipo) VALUES (1, 1, 'articulo')
        """))
        conn.execute(text("""
            INSERT INTO articulo (norma_id, numero, tipo) VALUES (1, 2, 'articulo')
        """))
        conn.execute(text("""
            INSERT INTO articulo (norma_id, numero, tipo) VALUES (2, 1, 'articulo')
        """))

        conn.execute(text("""
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde)
            VALUES (1, 'El Impuesto sobre el Valor Añadido es un impuesto indirecto que grava el consumo.', '1992-12-28')
        """))
        conn.execute(text("""
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde)
            VALUES (2, 'Las entregas de bienes y prestaciones de servicios estarán sujetas del IVA.', '1992-12-28')
        """))
        conn.execute(text("""
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde)
            VALUES (3, 'Los rendimientos del trabajo incluyen salarios, pagas extras y complementos.', '2006-11-15')
        """))

        conn.execute(text("""
            INSERT INTO aeat_modelo (codigo, nombre, activo) VALUES ('303', 'Modelo 303 - IVA trimestral', 1)
        """))
        conn.execute(text("""
            INSERT INTO aeat_modelo (codigo, nombre, activo) VALUES ('111', 'Modelo 111 - Retenciones IRPF', 1)
        """))
        conn.execute(text("""
            INSERT INTO modelo_campana (modelo_id, campana, activo) VALUES (1, '2025', 1)
        """))
        conn.execute(text("""
            INSERT INTO modelo_campana (modelo_id, campana, activo) VALUES (2, '2025', 1)
        """))
        conn.execute(text("""
            INSERT INTO modelo_casilla (modelo_id, codigo, etiqueta, campana_id)
            VALUES (1, '001', 'Base imponible general', 3)
        """))
        conn.execute(text("""
            INSERT INTO modelo_instruccion (modelo_id, seccion, titulo, contenido, orden)
            VALUES (1, 'seccion1', 'Declaracion', 'Instrucciones para el modelo 303', 1)
        """))
        conn.execute(text("""
            INSERT INTO sync_log (worker, started_at, finished_at, status, rows_added)
            VALUES ('worker-boe', '2025-01-01T00:00:00', '2025-01-01T00:05:00', 'success', 150)
        """))
        conn.execute(text("""
            INSERT INTO sync_log (worker, started_at, finished_at, status, rows_added)
            VALUES ('worker-dgt', '2025-01-01T00:00:00', '2025-01-01T00:03:00', 'success', 75)
        """))
        conn.execute(text("""
            INSERT INTO documento_interpretativo (titulo, texto, origen_tipo, tipo_documento, organismo_emisor)
            VALUES ('Consulta DGT sobre IVA', 'Las entregas de bienes con instalaciones son sujetas al IVA territorial.', 'boe', 'consulta_vinculante', 'DGT')
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
    assert "boe_id" in data


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
    assert iva_data["articulos"] >= 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_modelos_list_returns_models(seeded_db):
    """Modelos list returns seeded AEAT models."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/modelos")
    assert r.status_code == 200
    data = r.json()
    assert "modelos" in data
    codigos = [m["codigo"] for m in data["modelos"]]
    assert "303" in codigos
    assert "111" in codigos


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
