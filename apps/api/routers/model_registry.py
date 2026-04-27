"""Model registry router for AI Act compliance (Fase 26.8).

Endpoints for managing AI model registry and configuration versioning.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from services.model_registry import get_model_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ai/models", tags=["AI Model Registry"])


@router.get("")
def list_models(
    tipo: str | None = Query(default=None, description="Filter by model type"),
) -> list[dict]:
    """List all registered AI models.

    Optional `tipo` parameter filters by model type
    (embedding, llm, reranker, classifier).
    """
    registry = get_model_registry()
    models = registry.get_all_models(tipo)
    return [m.model_dump() for m in models]


@router.get("/active")
def get_active_model() -> dict | None:
    """Get the currently active AI model."""
    registry = get_model_registry()
    model = registry.get_active_model()
    if model is None:
        raise HTTPException(status_code=404, detail="No active model registered")
    return model.model_dump()


@router.post("")
def register_model(
    nombre: str,
    version: str,
    tipo: str,
    proveedor: str,
    hash_modelo: str,
    descripcion: str = "",
    configuracion: dict = {},
) -> dict:
    """Register a new AI model version."""
    registry = get_model_registry()
    model = registry.register_model(
        nombre=nombre,
        version=version,
        tipo=tipo,
        proveedor=proveedor,
        hash_modelo=hash_modelo,
        descripcion=descripcion,
        configuracion=configuracion,
    )
    return model.model_dump()


@router.post("/{model_id}/activate")
def activate_model(model_id: str) -> dict:
    """Activate a registered model (deactivates previous active)."""
    registry = get_model_registry()
    model = registry.activate_model(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
    return model.model_dump()


@router.post("/{model_id}/deactivate")
def deactivate_model(model_id: str) -> dict:
    """Deactivate a registered model."""
    registry = get_model_registry()
    success = registry.deactivate_model(model_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
    return {"model_id": model_id, "deactivated": True}


# ---------------------------------------------------------------------------
# Configuration versioning
# ---------------------------------------------------------------------------

config_router = APIRouter(prefix="/v1/ai/config", tags=["AI Config Versioning"])


@config_router.get("/current")
def get_current_config() -> dict:
    """Get the current (most recent) configuration version."""
    registry = get_model_registry()
    config = registry.get_current_config()
    return config.model_dump()


@config_router.get("/{version_id}")
def get_config_version(version_id: str) -> dict:
    """Get a specific configuration version by ID."""
    registry = get_model_registry()
    config = registry.get_config(version_id)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Config version not found: {version_id}")
    return config.model_dump()


@config_router.get("/history")
def get_config_history() -> list[dict]:
    """Get full configuration version history."""
    registry = get_model_registry()
    history = registry.get_config_history()
    return [c.model_dump() for c in history]


@config_router.post("/update")
def update_config(
    hybrid_weight: float | None = None,
    rrf_k: float | None = None,
    limit_default: int | None = None,
    modo_review: str | None = None,
    cambiado_por: str = "api",
    configuracion_completa: dict | None = None,
) -> dict:
    """Update configuration and create a new version.

    Only provided fields are updated; others retain current values.
    """
    registry = get_model_registry()
    update = {}
    if hybrid_weight is not None:
        update["hybrid_weight"] = hybrid_weight
    if rrf_k is not None:
        update["rrf_k"] = rrf_k
    if limit_default is not None:
        update["limit_default"] = limit_default
    if modo_review is not None:
        update["modo_review"] = modo_review
    if configuracion_completa is not None:
        update["configuracion_completa"] = configuracion_completa

    config = registry.update_config(update, cambiado_por=cambiado_por)
    return config.model_dump()


@config_router.post("/rollback")
def rollback_config(
    version_id: str,
) -> dict:
    """Rollback to a previous configuration version."""
    registry = get_model_registry()
    config = registry.rollback_config(version_id)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Config version not found: {version_id}")
    return config.model_dump()
