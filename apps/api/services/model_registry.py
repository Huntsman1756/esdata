"""Durable model registry and AI config versioning service."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import Any

from db import engine
from pydantic import BaseModel, Field
from services.persistence import (
    dumps_json,
    ensure_governance_tables,
    loads_json,
    rows_to_dicts,
)
from sqlalchemy import text

logger = logging.getLogger(__name__)


class ModelType(StrEnum):
    EMBEDDING = "embedding"
    LLM = "llm"
    RERANKER = "reranker"
    CLASSIFIER = "classifier"


class ReviewMode(StrEnum):
    STRICT = "strict"
    RELAXED = "relaxed"
    OFF = "off"


class AIModelEntry(BaseModel):
    model_id: str = Field(description="Unique model identifier")
    nombre: str = Field(description="Model name")
    version: str = Field(description="Semantic version string")
    tipo: str = Field(description="Model type")
    proveedor: str = Field(description="Provider")
    hash_modelo: str = Field(description="SHA256 hash of model weights")
    descripcion: str = Field(default="", description="What the model does")
    fecha_despliegue: str = Field(description="Deployment timestamp (ISO 8601)")
    activo: bool = Field(default=False, description="Whether this is the active version")
    configuracion: dict[str, Any] = Field(default_factory=dict, description="Model hyperparameters")


class AIConfigVersion(BaseModel):
    version_id: str = Field(description="Unique config version identifier")
    hybrid_weight: float = Field(ge=0, le=1, default=0.3)
    rrf_k: float = Field(gt=0, default=60.0)
    limit_default: int = Field(gt=0, default=10)
    modo_review: str = Field(default="off")
    fecha_cambio: str = Field(description="Change timestamp (ISO 8601)")
    cambiado_por: str = Field(default="system")
    configuracion_completa: dict[str, Any] = Field(default_factory=dict)


class ModelRegistry:
    def __init__(self):
        ensure_governance_tables()
        self._model_cache: dict[str, AIModelEntry] = {}
        self._config_cache: dict[str, AIConfigVersion] = {}
        self._ensure_initial_config()

    def _map_model(self, row: dict) -> AIModelEntry:
        cached = self._model_cache.get(row["model_id"])
        if cached is not None:
            cached.nombre = row["nombre"]
            cached.version = row["version"]
            cached.tipo = row["tipo"]
            cached.proveedor = row["proveedor"]
            cached.hash_modelo = row["hash_modelo"]
            cached.descripcion = row["descripcion"]
            cached.fecha_despliegue = row["fecha_despliegue"]
            cached.activo = bool(row["activo"])
            cached.configuracion = loads_json(row["configuracion"], {})
            return cached
        return AIModelEntry(
            model_id=row["model_id"],
            nombre=row["nombre"],
            version=row["version"],
            tipo=row["tipo"],
            proveedor=row["proveedor"],
            hash_modelo=row["hash_modelo"],
            descripcion=row["descripcion"],
            fecha_despliegue=row["fecha_despliegue"],
            activo=bool(row["activo"]),
            configuracion=loads_json(row["configuracion"], {}),
        )

    def _map_config(self, row: dict) -> AIConfigVersion:
        cached = self._config_cache.get(row["version_id"])
        if cached is not None:
            cached.hybrid_weight = row["hybrid_weight"]
            cached.rrf_k = row["rrf_k"]
            cached.limit_default = row["limit_default"]
            cached.modo_review = row["modo_review"]
            cached.fecha_cambio = row["fecha_cambio"]
            cached.cambiado_por = row["cambiado_por"]
            cached.configuracion_completa = loads_json(row["configuracion_completa"], {})
            return cached
        return AIConfigVersion(
            version_id=row["version_id"],
            hybrid_weight=row["hybrid_weight"],
            rrf_k=row["rrf_k"],
            limit_default=row["limit_default"],
            modo_review=row["modo_review"],
            fecha_cambio=row["fecha_cambio"],
            cambiado_por=row["cambiado_por"],
            configuracion_completa=loads_json(row["configuracion_completa"], {}),
        )

    def _query_models(self, sql: str, params: dict[str, Any] | None = None) -> list[AIModelEntry]:
        with engine.begin() as conn:
            rows = rows_to_dicts(conn.execute(text(sql), params or {}))
        return [self._map_model(row) for row in rows]

    def _query_configs(self, sql: str, params: dict[str, Any] | None = None) -> list[AIConfigVersion]:
        with engine.begin() as conn:
            rows = rows_to_dicts(conn.execute(text(sql), params or {}))
        return [self._map_config(row) for row in rows]

    def _ensure_initial_config(self) -> None:
        with engine.begin() as conn:
            count = int(conn.execute(text("SELECT COUNT(*) FROM ai_config_version")).scalar_one())
        if count == 0:
            self._create_config_version(
                hybrid_weight=0.3,
                rrf_k=60.0,
                limit_default=10,
                modo_review="off",
                cambiado_por="system",
                configuracion_completa={},
            )

    def register_model(
        self,
        nombre: str,
        version: str,
        tipo: str,
        proveedor: str,
        hash_modelo: str,
        descripcion: str = "",
        configuracion: dict[str, Any] | None = None,
    ) -> AIModelEntry:
        model_id = f"{nombre}-{version}".replace(" ", "-").lower()
        entry = AIModelEntry(
            model_id=model_id,
            nombre=nombre,
            version=version,
            tipo=tipo,
            proveedor=proveedor,
            hash_modelo=hash_modelo,
            descripcion=descripcion or f"Modelo {nombre} v{version}",
            fecha_despliegue=datetime.now(UTC).isoformat(),
            activo=False,
            configuracion=configuracion or {},
        )
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT OR REPLACE INTO ai_model_registry
                    (model_id, nombre, version, tipo, proveedor, hash_modelo, descripcion, fecha_despliegue, activo, configuracion)
                    VALUES
                    (:model_id, :nombre, :version, :tipo, :proveedor, :hash_modelo, :descripcion, :fecha_despliegue, :activo, :configuracion)
                    """
                ),
                {
                    "model_id": entry.model_id,
                    "nombre": entry.nombre,
                    "version": entry.version,
                    "tipo": entry.tipo,
                    "proveedor": entry.proveedor,
                    "hash_modelo": entry.hash_modelo,
                    "descripcion": entry.descripcion,
                    "fecha_despliegue": entry.fecha_despliegue,
                    "activo": 1 if entry.activo else 0,
                    "configuracion": dumps_json(entry.configuracion),
                },
            )
        self._model_cache[entry.model_id] = entry
        logger.info("Registered model: %s v%s (%s)", nombre, version, tipo)
        return entry

    def get_model(self, model_id: str) -> AIModelEntry | None:
        if model_id in self._model_cache:
            return self._model_cache[model_id]
        entries = self._query_models("SELECT * FROM ai_model_registry WHERE model_id = :model_id", {"model_id": model_id})
        if entries:
            self._model_cache[model_id] = entries[0]
            return entries[0]
        return None

    def get_all_models(self, tipo: str | None = None) -> list[AIModelEntry]:
        sql = "SELECT * FROM ai_model_registry"
        params: dict[str, Any] = {}
        if tipo:
            sql += " WHERE tipo = :tipo"
            params["tipo"] = tipo.value if isinstance(tipo, Enum) else str(tipo)
        sql += " ORDER BY nombre ASC, version ASC"
        return self._query_models(sql, params)

    def get_active_model(self) -> AIModelEntry | None:
        entries = self._query_models("SELECT * FROM ai_model_registry WHERE activo = 1 ORDER BY fecha_despliegue DESC LIMIT 1")
        if not entries:
            return None
        self._model_cache[entries[0].model_id] = entries[0]
        return entries[0]

    def activate_model(self, model_id: str) -> AIModelEntry | None:
        entry = self.get_model(model_id)
        if not entry:
            return None
        with engine.begin() as conn:
            conn.execute(text("UPDATE ai_model_registry SET activo = 0 WHERE activo = 1"))
            conn.execute(text("UPDATE ai_model_registry SET activo = 1 WHERE model_id = :model_id"), {"model_id": model_id})
        for cached in self._model_cache.values():
            cached.activo = False
        entry.activo = True
        self._model_cache[model_id] = entry
        logger.info("Activated model: %s", model_id)
        return entry

    def deactivate_model(self, model_id: str) -> bool:
        entry = self.get_model(model_id)
        if not entry:
            return False
        with engine.begin() as conn:
            conn.execute(text("UPDATE ai_model_registry SET activo = 0 WHERE model_id = :model_id"), {"model_id": model_id})
        entry.activo = False
        logger.info("Deactivated model: %s", model_id)
        return True

    def compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _next_config_version_id(self) -> str:
        with engine.begin() as conn:
            count = int(conn.execute(text("SELECT COUNT(*) FROM ai_config_version")).scalar_one())
        return f"v{count + 1:04d}"

    def _create_config_version(
        self,
        hybrid_weight: float = 0.3,
        rrf_k: float = 60.0,
        limit_default: int = 10,
        modo_review: str = "off",
        cambiado_por: str = "system",
        configuracion_completa: dict[str, Any] | None = None,
    ) -> AIConfigVersion:
        config = AIConfigVersion(
            version_id=self._next_config_version_id(),
            hybrid_weight=hybrid_weight,
            rrf_k=rrf_k,
            limit_default=limit_default,
            modo_review=modo_review,
            fecha_cambio=datetime.now(UTC).isoformat(),
            cambiado_por=cambiado_por,
            configuracion_completa=configuracion_completa or {},
        )
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ai_config_version
                    (version_id, hybrid_weight, rrf_k, limit_default, modo_review, fecha_cambio, cambiado_por, configuracion_completa)
                    VALUES
                    (:version_id, :hybrid_weight, :rrf_k, :limit_default, :modo_review, :fecha_cambio, :cambiado_por, :configuracion_completa)
                    """
                ),
                {
                    "version_id": config.version_id,
                    "hybrid_weight": config.hybrid_weight,
                    "rrf_k": config.rrf_k,
                    "limit_default": config.limit_default,
                    "modo_review": config.modo_review,
                    "fecha_cambio": config.fecha_cambio,
                    "cambiado_por": config.cambiado_por,
                    "configuracion_completa": dumps_json(config.configuracion_completa),
                },
            )
        self._config_cache[config.version_id] = config
        logger.info("Created config version: %s", config.version_id)
        return config

    def update_config(
        self,
        config_update: dict[str, Any],
        cambiado_por: str = "system",
    ) -> AIConfigVersion:
        current = self.get_current_config()
        hybrid_weight = config_update.get("hybrid_weight", current.hybrid_weight)
        rrf_k = config_update.get("rrf_k", current.rrf_k)
        limit_default = config_update.get("limit_default", current.limit_default)
        modo_review = config_update.get("modo_review", current.modo_review)

        completa = current.configuracion_completa.copy()
        completa.update(config_update)
        completa["hybrid_weight"] = hybrid_weight
        completa["rrf_k"] = rrf_k
        completa["limit_default"] = limit_default
        completa["modo_review"] = modo_review

        return self._create_config_version(
            hybrid_weight=hybrid_weight,
            rrf_k=rrf_k,
            limit_default=limit_default,
            modo_review=modo_review,
            cambiado_por=cambiado_por,
            configuracion_completa=completa,
        )

    def get_config(self, version_id: str) -> AIConfigVersion | None:
        if version_id in self._config_cache:
            return self._config_cache[version_id]
        entries = self._query_configs("SELECT * FROM ai_config_version WHERE version_id = :version_id", {"version_id": version_id})
        if entries:
            self._config_cache[version_id] = entries[0]
            return entries[0]
        return None

    def get_current_config(self) -> AIConfigVersion:
        entries = self._query_configs("SELECT * FROM ai_config_version ORDER BY id ASC")
        if entries:
            return entries[-1]
        return self._create_config_version()

    def get_config_history(self) -> list[AIConfigVersion]:
        return self._query_configs("SELECT * FROM ai_config_version ORDER BY id ASC")

    def rollback_config(self, version_id: str) -> AIConfigVersion | None:
        target = self.get_config(version_id)
        if not target:
            return None
        return self._create_config_version(
            hybrid_weight=target.hybrid_weight,
            rrf_k=target.rrf_k,
            limit_default=target.limit_default,
            modo_review=target.modo_review,
            cambiado_por=f"rollback-from-{version_id}",
            configuracion_completa=target.configuracion_completa,
        )

    @property
    def model_count(self) -> int:
        with engine.begin() as conn:
            return int(conn.execute(text("SELECT COUNT(*) FROM ai_model_registry")).scalar_one())

    @property
    def config_version_count(self) -> int:
        with engine.begin() as conn:
            return int(conn.execute(text("SELECT COUNT(*) FROM ai_config_version")).scalar_one())


_registry = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    return _registry


def reset_model_registry() -> None:
    global _registry
    ensure_governance_tables()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM ai_model_registry"))
        conn.execute(text("DELETE FROM ai_config_version"))
    _registry = ModelRegistry()
