"""HTTP integration tests for ai_audit_log, human_review, data_lineage, and model_registry routers (Fase 30.2)."""

# ruff: noqa: E402, I001

import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

# Use a temp file-based SQLite DB (memory DB creates fresh DB per connection)
_TMP_DB = Path(tempfile.gettempdir()) / f"esdata_gov_test_{os.getpid()}.db"
if _TMP_DB.exists():
    try:
        _TMP_DB.unlink()
    except PermissionError:
        pass
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ESDATA_API_KEY", "test-secret-key")
os.environ.setdefault("MCP_API_KEY", "test-mcp-key")
os.environ.setdefault("ESDATA_ALLOW_INSECURE_TEST_AUTH", "true")

# Import and patch the real db module (same pattern as conftest.py)
import db as _db_module  # noqa: E402
test_engine = create_engine(
    os.environ["DATABASE_URL"],
    future=True,
    connect_args={"check_same_thread": False},
)
_db_module.engine = test_engine
_db_module.SessionLocal = _db_module.sessionmaker(
    bind=test_engine, autoflush=False, autocommit=False, future=True,
)

@contextmanager
def _patched_db_session():
    db = _db_module.SessionLocal()
    try:
        yield db
    finally:
        db.close()

_db_module.db_session = _db_module.contextmanager(_patched_db_session)

# Import test bootstrap first (needed for SQLite schema), then patch all service modules
from governance_bootstrap import bootstrap_governance_tables  # noqa: E402
import services.persistence as _persistence  # noqa: E402

# Create all governance tables BEFORE importing other service modules
# (services/model_registry has a module-level singleton that queries these tables)
bootstrap_governance_tables(test_engine)

# Now patch service modules and import them (singleton init will find tables)
import services.ai_audit as _ai_audit  # noqa: E402
import services.human_review as _human_review  # noqa: E402
import services.model_registry as _model_registry  # noqa: E402
import services.data_lineage as _data_lineage  # noqa: E402
import services.query_audit as _query_audit  # noqa: E402

for _mod in (_persistence, _ai_audit, _human_review, _model_registry, _data_lineage, _query_audit):
    _mod.engine = test_engine

from main import app
from services.ai_audit import reset_audit_store
from services.data_lineage import reset_data_lineage_service
from services.human_review import reset_review_store
from services.model_registry import reset_model_registry


@pytest.fixture(autouse=True)
def clean_all():
    reset_audit_store()
    reset_data_lineage_service()
    reset_review_store()
    reset_model_registry()
    yield
    reset_audit_store()
    reset_data_lineage_service()
    reset_review_store()
    reset_model_registry()


# --- AI Audit Log ---

@pytest.mark.asyncio
async def test_ai_audit_log_list_empty():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/audit-log")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["entries"] == []


@pytest.mark.asyncio
async def test_ai_audit_log_list_with_entries():
    from services.ai_audit import get_audit_store

    store = get_audit_store()
    store.log_ai_decision(
        componente="consulta",
        accion="query",
        request_id="req-ai-001",
        latencia_ms=120.0,
        resultado_resumen="3 resultados",
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/audit-log")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    entry = data["entries"][0]
    assert entry["request_id"] == "req-ai-001"
    assert entry["componente"] == "consulta"
    assert entry["latencia_ms"] == 120.0


@pytest.mark.asyncio
async def test_ai_audit_log_by_request_id():
    from services.ai_audit import get_audit_store

    store = get_audit_store()
    store.log_ai_decision(
        componente="consulta",
        accion="query",
        request_id="req-ai-detail",
        latencia_ms=50.0,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/audit-log/req-ai-detail")

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == "req-ai-detail"
    assert data["total"] == 1


# --- Human Review ---

@pytest.mark.asyncio
async def test_human_review_pending_empty():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/human-review/pending")

    assert response.status_code == 200
    data = response.json()
    # Endpoint returns a raw list of pending reviews
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_human_review_pending_with_entries():
    from services.human_review import get_review_store

    store = get_review_store()
    store.create_review(
        request_id="req-hr-001",
        decision_type="faithfulness",
        ai_confidence=0.45,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/human-review/pending")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["request_id"] == "req-hr-001"
    assert data[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_human_review_stats():
    from services.human_review import get_review_store

    store = get_review_store()
    store.create_review(request_id="r1", decision_type="faithfulness", ai_confidence=0.3)
    store.create_review(request_id="r2", decision_type="faithfulness", ai_confidence=0.4)
    store.create_review(request_id="r3", decision_type="faithfulness", ai_confidence=0.95)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/human-review/stats")

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "by_status" in data
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_human_review_decide():
    from services.human_review import get_review_store

    store = get_review_store()
    review = store.create_review(
        request_id="req-hr-decide",
        decision_type="faithfulness",
        ai_confidence=0.3,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.post(
            f"/v1/ai/human-review/{review.review_id}/decide",
            params={"action": "approve", "reviewer_id": "human-1", "notes": "ok"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "approve"
    assert data["reviewer_id"] == "human-1"

    # Verify status changed
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/human-review/pending")
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


# --- Data Lineage ---

@pytest.mark.asyncio
async def test_data_lineage_empty():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/data/lineage?tabla=nonexistent")

    assert response.status_code == 200
    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_data_lineage_with_entries():
    from services.data_lineage import get_data_lineage_service

    svc = get_data_lineage_service()
    svc.record_lineage(
        tabla="articulo",
        campo="contenido",
        fuente_origen="worker-ingestion",
        transformacion="normalizacion",
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/data/lineage?tabla=articulo")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["tabla"] == "articulo"
    assert data[0]["campo"] == "contenido"


@pytest.mark.asyncio
async def test_data_catalog_empty():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/data/catalog")

    assert response.status_code == 200
    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_data_catalog_with_entries():
    from services.data_lineage import get_data_lineage_service

    svc = get_data_lineage_service()
    svc.record_lineage(
        tabla="test_catalog_table",
        campo="field1",
        fuente_origen="test",
        transformacion="none",
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/data/catalog")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    tables = [e["tabla"] for e in data]
    assert "test_catalog_table" in tables


# --- Model Registry ---

@pytest.mark.asyncio
async def test_model_registry_list_empty():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/models")

    assert response.status_code == 200
    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_model_registry_register_and_list():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.post(
            "/v1/ai/models",
            params={
                "nombre": "test-llm",
                "version": "v1.0",
                "tipo": "llm",
                "proveedor": "internal",
                "hash_modelo": "abc123",
                "descripcion": "Test model",
            },
            json={"configuracion": {"temperature": 0.7}},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["model_id"] == "test-llm-v1.0"
    assert data["nombre"] == "test-llm"
    assert data["version"] == "v1.0"
    assert data["activo"] is False

    # Verify it appears in list
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/models")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["model_id"] == "test-llm-v1.0"


@pytest.mark.asyncio
async def test_model_registry_activate():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        await client.post(
            "/v1/ai/models",
            params={
                "nombre": "test-llm-2",
                "version": "v2.0",
                "tipo": "llm",
                "proveedor": "internal",
                "hash_modelo": "def456",
            },
        )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.post("/v1/ai/models/test-llm-2-v2.0/activate")

    assert response.status_code == 200
    data = response.json()
    assert data["activo"] is True

    # Verify active model
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/models/active")

    assert response.status_code == 200
    assert response.json()["model_id"] == "test-llm-2-v2.0"


@pytest.mark.asyncio
async def test_model_registry_config_history():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        await client.post(
            "/v1/ai/config/update",
            params={
                "hybrid_weight": "0.6",
                "rrf_k": "50.0",
                "cambiado_por": "test-user",
            },
        )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/config/history")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[-1]["hybrid_weight"] == 0.6
    assert data[-1]["cambiado_por"] == "test-user"


@pytest.mark.asyncio
async def test_model_registry_upsert_postgres_compatible():
    """Verify INSERT ... ON CONFLICT works (PostgreSQL fix for Fase 30.2)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        # Register first time
        await client.post(
            "/v1/ai/models",
            params={
                "nombre": "upsert-test",
                "version": "v1",
                "tipo": "llm",
                "proveedor": "internal",
                "hash_modelo": "hash1",
            },
        )
        # Register again with same model_id (upsert)
        response = await client.post(
            "/v1/ai/models",
            params={
                "nombre": "upsert-test",
                "version": "v1",
                "tipo": "llm",
                "proveedor": "updated-provider",
                "hash_modelo": "hash2",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["proveedor"] == "updated-provider"
    assert data["hash_modelo"] == "hash2"

    # Verify only one entry exists
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/ai/models")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["proveedor"] == "updated-provider"
