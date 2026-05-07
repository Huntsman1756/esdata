"""AI audit log service backed by durable SQL storage."""

from __future__ import annotations

from datetime import UTC, datetime

from db import engine
from pydantic import BaseModel, Field
from services.persistence import (
    dumps_json,
    ensure_governance_tables,
    loads_json,
    rows_to_dicts,
)
from sqlalchemy import text


class AIAuditEntry(BaseModel):
    request_id: str = Field(description="Correlation with original request")
    timestamp: str = Field(description="When the event occurred (ISO 8601)")
    componente: str = Field(description="AI component")
    accion: str = Field(description="Action performed")
    configuracion: dict = Field(default_factory=dict)
    resultado_resumen: str = Field(default="")
    latencia_ms: float | None = None
    error: str | None = None
    user_id: str | None = None
    ip_address: str | None = None


class AIAuditLogStore:
    def __init__(self):
        ensure_governance_tables()

    def log_ai_decision(
        self,
        componente: str,
        accion: str,
        request_id: str = "",
        configuracion: dict | None = None,
        resultado_resumen: str = "",
        latencia_ms: float | None = None,
        error: str | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
        timestamp: str | None = None,
    ) -> AIAuditEntry:
        entry = AIAuditEntry(
            request_id=request_id or "",
            timestamp=timestamp or datetime.now(UTC).isoformat(),
            componente=componente,
            accion=accion,
            configuracion=configuracion or {},
            resultado_resumen=resultado_resumen or "",
            latencia_ms=latencia_ms,
            error=error,
            user_id=user_id,
            ip_address=ip_address,
        )
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ai_audit_log
                    (request_id, timestamp, componente, accion, configuracion, resultado_resumen, latencia_ms, error, user_id, ip_address)
                    VALUES
                    (:request_id, :timestamp, :componente, :accion, :configuracion, :resultado_resumen, :latencia_ms, :error, :user_id, :ip_address)
                    """
                ),
                {
                    "request_id": entry.request_id,
                    "timestamp": entry.timestamp,
                    "componente": entry.componente,
                    "accion": entry.accion,
                    "configuracion": dumps_json(entry.configuracion),
                    "resultado_resumen": entry.resultado_resumen,
                    "latencia_ms": entry.latencia_ms,
                    "error": entry.error,
                    "user_id": entry.user_id,
                    "ip_address": entry.ip_address,
                },
            )
        return entry

    def _map_entry(self, row: dict) -> AIAuditEntry:
        return AIAuditEntry(
            request_id=row["request_id"],
            timestamp=row["timestamp"],
            componente=row["componente"],
            accion=row["accion"],
            configuracion=loads_json(row["configuracion"], {}),
            resultado_resumen=row["resultado_resumen"],
            latencia_ms=row["latencia_ms"],
            error=row["error"],
            user_id=row["user_id"],
            ip_address=row["ip_address"],
        )

    def get_entries(
        self,
        desde: str | None = None,
        hasta: str | None = None,
        componente: str | None = None,
        request_id: str | None = None,
    ) -> list[AIAuditEntry]:
        clauses = []
        params: dict[str, object] = {}
        if componente:
            clauses.append("componente = :componente")
            params["componente"] = componente
        if request_id:
            clauses.append("request_id = :request_id")
            params["request_id"] = request_id
        if desde:
            clauses.append("timestamp >= :desde")
            params["desde"] = desde
        if hasta:
            clauses.append("timestamp <= :hasta")
            params["hasta"] = hasta
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with engine.begin() as conn:
            rows = rows_to_dicts(
                conn.execute(
                    text(f"SELECT * FROM ai_audit_log {where} ORDER BY timestamp ASC"),
                    params,
                )
            )
        return [self._map_entry(row) for row in rows]

    def get_by_request_id(self, request_id: str) -> list[AIAuditEntry]:
        return self.get_entries(request_id=request_id)

    @property
    def entries(self) -> list[AIAuditEntry]:
        return self.get_entries()

    @property
    def count(self) -> int:
        with engine.begin() as conn:
            return int(conn.execute(text("SELECT COUNT(*) FROM ai_audit_log")).scalar_one())


_audit_store: AIAuditLogStore | None = None


def get_audit_store() -> AIAuditLogStore:
    global _audit_store
    if _audit_store is None:
        _audit_store = AIAuditLogStore()
    return _audit_store


def reset_audit_store() -> None:
    global _audit_store
    ensure_governance_tables()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM ai_audit_log"))
    _audit_store = AIAuditLogStore()
