"""Tests for model registry / versioning (Fase 26.8)."""

import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from services.model_registry import (
    ModelRegistry,
    ModelType,
    get_model_registry,
    reset_model_registry,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset registry before each test."""
    reset_model_registry()
    yield
    reset_model_registry()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegisterModel:
    def test_register_embedding_model(self):
        registry = get_model_registry()
        model = registry.register_model(
            nombre="paraphrase-multilingual-mpnet-base-v2",
            version="1.0.0",
            tipo=ModelType.EMBEDDING,
            proveedor="sentence-transformers",
            hash_modelo="abc123",
        )
        assert model.model_id == "paraphrase-multilingual-mpnet-base-v2-1.0.0"
        assert model.activo is False
        assert registry.model_count == 1

    def test_register_llm_model(self):
        registry = get_model_registry()
        model = registry.register_model(
            nombre="gpt-4-turbo",
            version="2024-04-09",
            tipo=ModelType.LLM,
            proveedor="openai",
            hash_modelo="def456",
            descripcion="Modelo de lenguaje GPT-4",
        )
        assert model.tipo == ModelType.LLM
        assert model.proveedor == "openai"
        assert model.descripcion == "Modelo de lenguaje GPT-4"

    def test_register_multiple_models(self):
        registry = get_model_registry()
        registry.register_model(
            nombre="model-a", version="1.0.0",
            tipo=ModelType.EMBEDDING, proveedor="provider-a",
            hash_modelo="hash-a",
        )
        registry.register_model(
            nombre="model-b", version="1.0.0",
            tipo=ModelType.RERANKER, proveedor="provider-b",
            hash_modelo="hash-b",
        )
        assert registry.model_count == 2

    def test_register_with_config(self):
        registry = get_model_registry()
        model = registry.register_model(
            nombre="model-a", version="1.0.0",
            tipo=ModelType.EMBEDDING, proveedor="p",
            hash_modelo="h",
            configuracion={"dim": 768, "max_seq": 512},
        )
        assert model.configuracion["dim"] == 768


# ---------------------------------------------------------------------------
# Activation
# ---------------------------------------------------------------------------


class TestActivateModel:
    def test_activate_model(self):
        registry = get_model_registry()
        registry.register_model(
            nombre="m1", version="1.0.0",
            tipo=ModelType.EMBEDDING, proveedor="p",
            hash_modelo="h1",
        )
        model = registry.activate_model("m1-1.0.0")
        assert model.activo is True
        assert registry.get_active_model() is model

    def test_activate_deactivates_previous(self):
        registry = get_model_registry()
        registry.register_model(
            nombre="m1", version="1.0.0",
            tipo=ModelType.EMBEDDING, proveedor="p",
            hash_modelo="h1",
        )
        registry.register_model(
            nombre="m2", version="1.0.0",
            tipo=ModelType.EMBEDDING, proveedor="p",
            hash_modelo="h2",
        )
        registry.activate_model("m1-1.0.0")
        r1 = registry.get_model("m1-1.0.0")

        registry.activate_model("m2-1.0.0")
        assert r1.activo is False
        assert registry.get_active_model().model_id == "m2-1.0.0"

    def test_activate_nonexistent_returns_none(self):
        registry = get_model_registry()
        result = registry.activate_model("nonexistent")
        assert result is None

    def test_deactivate_model(self):
        registry = get_model_registry()
        registry.register_model(
            nombre="m1", version="1.0.0",
            tipo=ModelType.EMBEDDING, proveedor="p",
            hash_modelo="h1",
        )
        registry.activate_model("m1-1.0.0")
        assert registry.deactivate_model("m1-1.0.0") is True
        assert registry.get_active_model() is None

    def test_deactivate_nonexistent(self):
        registry = get_model_registry()
        assert registry.deactivate_model("nonexistent") is False


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


class TestQuery:
    def test_get_all_models(self):
        registry = get_model_registry()
        registry.register_model(
            nombre="m1", version="1.0.0",
            tipo=ModelType.EMBEDDING, proveedor="p",
            hash_modelo="h1",
        )
        registry.register_model(
            nombre="m2", version="1.0.0",
            tipo=ModelType.LLM, proveedor="p",
            hash_modelo="h2",
        )
        all_models = registry.get_all_models()
        assert len(all_models) == 2

    def test_filter_by_tipo(self):
        registry = get_model_registry()
        registry.register_model(
            nombre="m1", version="1.0.0",
            tipo=ModelType.EMBEDDING, proveedor="p",
            hash_modelo="h1",
        )
        registry.register_model(
            nombre="m2", version="1.0.0",
            tipo=ModelType.LLM, proveedor="p",
            hash_modelo="h2",
        )
        embeddings = registry.get_all_models(tipo=ModelType.EMBEDDING)
        assert len(embeddings) == 1
        assert embeddings[0].model_id == "m1-1.0.0"

    def test_get_model_by_id(self):
        registry = get_model_registry()
        registry.register_model(
            nombre="m1", version="1.0.0",
            tipo=ModelType.EMBEDDING, proveedor="p",
            hash_modelo="h1",
        )
        model = registry.get_model("m1-1.0.0")
        assert model is not None
        assert model.nombre == "m1"

    def test_get_nonexistent_model(self):
        registry = get_model_registry()
        assert registry.get_model("nonexistent") is None

    def test_compute_hash(self):
        registry = get_model_registry()
        h = registry.compute_hash("test")
        assert len(h) == 64  # SHA256 hex length

    def test_hash_is_deterministic(self):
        registry = get_model_registry()
        h1 = registry.compute_hash("same")
        h2 = registry.compute_hash("same")
        assert h1 == h2

    def test_hash_different_inputs(self):
        registry = get_model_registry()
        h1 = registry.compute_hash("input1")
        h2 = registry.compute_hash("input2")
        assert h1 != h2


# ---------------------------------------------------------------------------
# Config versioning
# ---------------------------------------------------------------------------


class TestConfigVersioning:
    def test_initial_config_exists(self):
        registry = get_model_registry()
        config = registry.get_current_config()
        assert config is not None
        assert config.version_id == "v0001"
        assert config.hybrid_weight == 0.3

    def test_update_config_creates_new_version(self):
        registry = get_model_registry()
        initial = registry.get_current_config()
        assert initial.version_id == "v0001"

        new = registry.update_config(
            {"hybrid_weight": 0.5},
            cambiado_por="test-user",
        )
        assert new.version_id == "v0002"
        assert new.hybrid_weight == 0.5
        assert registry.config_version_count == 2

    def test_update_partial_config(self):
        registry = get_model_registry()
        registry.update_config({"hybrid_weight": 0.5})
        config = registry.get_current_config()
        assert config.hybrid_weight == 0.5
        assert config.rrf_k == 60.0  # unchanged default

    def test_update_limit_default(self):
        registry = get_model_registry()
        registry.update_config({"limit_default": 20})
        config = registry.get_current_config()
        assert config.limit_default == 20

    def test_update_modo_review(self):
        registry = get_model_registry()
        registry.update_config({"modo_review": "strict"})
        config = registry.get_current_config()
        assert config.modo_review == "strict"

    def test_get_config_by_version(self):
        registry = get_model_registry()
        registry.update_config({"hybrid_weight": 0.5})
        v1 = registry.get_config("v0001")
        v2 = registry.get_config("v0002")
        assert v1.hybrid_weight == 0.3
        assert v2.hybrid_weight == 0.5

    def test_get_nonexistent_config(self):
        registry = get_model_registry()
        assert registry.get_config("nonexistent") is None

    def test_config_history(self):
        registry = get_model_registry()
        registry.update_config({"hybrid_weight": 0.5})
        registry.update_config({"hybrid_weight": 0.7})
        history = registry.get_config_history()
        assert len(history) == 3  # initial + 2 updates

    def test_rollback_config(self):
        registry = get_model_registry()
        registry.update_config({"hybrid_weight": 0.5})
        registry.update_config({"hybrid_weight": 0.7})
        rolled = registry.rollback_config("v0002")
        assert rolled.hybrid_weight == 0.5
        assert registry.config_version_count == 4

    def test_rollback_nonexistent(self):
        registry = get_model_registry()
        assert registry.rollback_config("nonexistent") is None

    def test_cambiado_por_tracked(self):
        registry = get_model_registry()
        registry.update_config({"hybrid_weight": 0.5}, cambiado_por="analyst-1")
        config = registry.get_current_config()
        assert config.cambiado_por == "analyst-1"

    def test_config_completa_tracked(self):
        registry = get_model_registry()
        registry.update_config({"hybrid_weight": 0.5})
        config = registry.get_current_config()
        assert "hybrid_weight" in config.configuracion_completa
        assert config.configuracion_completa["hybrid_weight"] == 0.5


class TestDurablePersistence:
    def test_model_registry_survives_new_instance(self):
        registry = ModelRegistry()
        registry.register_model(
            nombre="durable-model",
            version="1.0.0",
            tipo=ModelType.LLM,
            proveedor="provider-x",
            hash_modelo="hash-durable",
        )

        fresh_registry = ModelRegistry()
        found = fresh_registry.get_model("durable-model-1.0.0")

        assert found is not None
        assert found.proveedor == "provider-x"

    def test_config_versions_survive_new_instance(self):
        registry = ModelRegistry()
        registry.update_config({"hybrid_weight": 0.61}, cambiado_por="tester")

        fresh_registry = ModelRegistry()
        current = fresh_registry.get_current_config()

        assert current.hybrid_weight == 0.61
        assert current.cambiado_por == "tester"
