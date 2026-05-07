"""Durable query audit log service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from db import engine
from pydantic import BaseModel, Field
from services.persistence import (
    dumps_json,
    dumps_json_list,
    ensure_governance_tables,
    loads_json,
    rows_to_dicts,
)
from sqlalchemy import text


class QueryAuditEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    request_id: str
    user_id: str | None = None
    path: str
    query_text: str
    retrieved_chunks: list[dict] = Field(default_factory=list)
    response_summary: str = ""
    model_version: str | None = None
    config_version: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    grounding_status: str | None = None
    prompt_injection_detected: bool = False
    grounding_summary: dict[str, Any] = Field(default_factory=dict)


class QueryAuditService:
    def __init__(self):
        ensure_governance_tables()

    def record_query(
        self,
        request_id: str,
        user_id: str | None,
        path: str,
        query_text: str,
        retrieved_chunks: list[dict],
        response_summary: str,
        model_version: str | None = None,
        config_version: str | None = None,
        grounding_status: str | None = None,
        prompt_injection_detected: bool = False,
        grounding_summary: dict[str, Any] | None = None,
    ) -> QueryAuditEntry:
        entry = QueryAuditEntry(
            request_id=request_id,
            user_id=user_id,
            path=path,
            query_text=query_text,
            retrieved_chunks=retrieved_chunks,
            response_summary=response_summary,
            model_version=model_version,
            config_version=config_version,
            grounding_status=grounding_status,
            prompt_injection_detected=prompt_injection_detected,
            grounding_summary=grounding_summary or {},
        )
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO query_audit_log
                    (entry_id, request_id, user_id, path, query_text, retrieved_chunks, response_summary, model_version, config_version, created_at, grounding_status, prompt_injection_detected, grounding_summary)
                    VALUES
                    (:entry_id, :request_id, :user_id, :path, :query_text, :retrieved_chunks, :response_summary, :model_version, :config_version, :created_at, :grounding_status, :prompt_injection_detected, :grounding_summary)
                    """
                ),
                {
                    "entry_id": entry.entry_id,
                    "request_id": entry.request_id,
                    "user_id": entry.user_id,
                    "path": entry.path,
                    "query_text": entry.query_text,
                    "retrieved_chunks": dumps_json_list(entry.retrieved_chunks),
                    "response_summary": entry.response_summary,
                    "model_version": entry.model_version,
                    "config_version": entry.config_version,
                    "created_at": entry.created_at,
                    "grounding_status": entry.grounding_status or "",
                    "prompt_injection_detected": 1 if entry.prompt_injection_detected else 0,
                    "grounding_summary": dumps_json(entry.grounding_summary),
                },
            )
        return entry

    def _map_entry(self, row: dict) -> QueryAuditEntry:
        return QueryAuditEntry(
            entry_id=row["entry_id"],
            request_id=row["request_id"],
            user_id=row["user_id"],
            path=row["path"],
            query_text=row["query_text"],
            retrieved_chunks=loads_json(row["retrieved_chunks"], []),
            response_summary=row["response_summary"],
            model_version=row["model_version"],
            config_version=row["config_version"],
            created_at=row["created_at"],
            grounding_status=row.get("grounding_status") or None,
            prompt_injection_detected=bool(row.get("prompt_injection_detected", 0)),
            grounding_summary=loads_json(row.get("grounding_summary"), {}),
        )

    def get_entries(self, path: str | None = None) -> list[QueryAuditEntry]:
        sql = "SELECT * FROM query_audit_log"
        params: dict[str, object] = {}
        if path:
            sql += " WHERE path = :path"
            params["path"] = path
        sql += " ORDER BY created_at ASC"
        with engine.begin() as conn:
            rows = rows_to_dicts(conn.execute(text(sql), params))
        return [self._map_entry(row) for row in rows]

    def get_by_request_id(self, request_id: str) -> list[QueryAuditEntry]:
        with engine.begin() as conn:
            rows = rows_to_dicts(
                conn.execute(
                    text("SELECT * FROM query_audit_log WHERE request_id = :request_id ORDER BY created_at ASC"),
                    {"request_id": request_id},
                )
            )
        return [self._map_entry(row) for row in rows]


_service: QueryAuditService | None = None


def get_query_audit_service() -> QueryAuditService:
    global _service
    if _service is None:
        _service = QueryAuditService()
    return _service


def reset_query_audit_service() -> None:
    global _service
    ensure_governance_tables()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM query_audit_log"))
    _service = QueryAuditService()
