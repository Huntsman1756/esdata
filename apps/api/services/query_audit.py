"""Durable query audit log service."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from db import engine
from mcp_catalog import infer_query_audit_tool_name
from pydantic import BaseModel, Field
from sqlalchemy import text

from services.persistence import (
    dumps_json,
    dumps_json_list,
    ensure_governance_tables,
    loads_json,
    rows_to_dicts,
)


class QueryAuditEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    request_id: str
    tool_name: str
    user_id: str | None = None
    path: str
    query_text: str
    retrieved_chunks: list[dict] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    response_summary: str = ""
    confidence: dict[str, Any] = Field(default_factory=dict)
    completeness: str = "parcial"
    verified: bool = False
    model_version: str | None = None
    config_version: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    grounding_status: str | None = None
    prompt_injection_detected: bool = False
    grounding_summary: dict[str, Any] = Field(default_factory=dict)
    response_payload: dict[str, Any] = Field(default_factory=dict)


def _build_sources_from_chunks(retrieved_chunks: list[dict]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()

    for chunk in retrieved_chunks:
        source: dict[str, Any] = {}
        for key in (
            "chunk_id",
            "title",
            "url",
            "source_url",
            "norma",
            "numero",
            "referencia",
            "organismo_emisor",
        ):
            value = chunk.get(key)
            if value not in (None, ""):
                normalized_key = "url" if key == "source_url" else key
                source[normalized_key] = value
        if not source:
            continue
        marker = dumps_json(source)
        if marker in seen:
            continue
        seen.add(marker)
        sources.append(source)

    return sources


def _normalize_confidence(
    confidence: dict[str, Any] | None,
    grounding_status: str | None,
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    if confidence:
        return confidence

    if grounding_status == "full" and sources:
        return {"score": 0.9, "label": "alta"}
    if grounding_status == "partial" or sources:
        return {"score": 0.5, "label": "media"}
    if grounding_status in {"none", "empty"}:
        return {"score": 0.0, "label": "baja"}
    return {"score": 0.0, "label": "no_verificado"}


def _normalize_completeness(
    completeness: str | None,
    grounding_status: str | None,
) -> str:
    if completeness:
        return completeness
    if grounding_status == "full":
        return "completa"
    return "parcial"


def _normalize_verified(
    verified: bool | None,
    grounding_status: str | None,
    sources: list[dict[str, Any]],
) -> bool:
    if verified is not None:
        return verified
    return grounding_status == "full" and bool(sources)


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
        tool_name: str | None = None,
        sources: list[dict[str, Any]] | None = None,
        confidence: dict[str, Any] | None = None,
        completeness: str | None = None,
        verified: bool | None = None,
        model_version: str | None = None,
        config_version: str | None = None,
        grounding_status: str | None = None,
        prompt_injection_detected: bool = False,
        grounding_summary: dict[str, Any] | None = None,
        response_payload: dict[str, Any] | None = None,
    ) -> QueryAuditEntry:
        normalized_sources = sources or _build_sources_from_chunks(retrieved_chunks)
        entry = QueryAuditEntry(
            request_id=request_id,
            tool_name=tool_name or infer_query_audit_tool_name(path),
            user_id=user_id,
            path=path,
            query_text=query_text,
            retrieved_chunks=retrieved_chunks,
            sources=normalized_sources,
            response_summary=response_summary,
            confidence=_normalize_confidence(confidence, grounding_status, normalized_sources),
            completeness=_normalize_completeness(completeness, grounding_status),
            verified=_normalize_verified(verified, grounding_status, normalized_sources),
            model_version=model_version,
            config_version=config_version,
            grounding_status=grounding_status,
            prompt_injection_detected=prompt_injection_detected,
            grounding_summary=grounding_summary or {},
            response_payload=response_payload or {},
        )
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO query_audit_log
                    (
                        entry_id,
                        request_id,
                        tool_name,
                        user_id,
                        path,
                        query_text,
                        retrieved_chunks,
                        sources,
                        response_summary,
                        confidence,
                        completeness,
                        verified,
                        model_version,
                        config_version,
                        created_at,
                        grounding_status,
                        prompt_injection_detected,
                        grounding_summary,
                        response_payload
                    )
                    VALUES
                    (
                        :entry_id,
                        :request_id,
                        :tool_name,
                        :user_id,
                        :path,
                        :query_text,
                        :retrieved_chunks,
                        :sources,
                        :response_summary,
                        :confidence,
                        :completeness,
                        :verified,
                        :model_version,
                        :config_version,
                        :created_at,
                        :grounding_status,
                        :prompt_injection_detected,
                        :grounding_summary,
                        :response_payload
                    )
                    """
                ),
                {
                    "entry_id": entry.entry_id,
                    "request_id": entry.request_id,
                    "tool_name": entry.tool_name,
                    "user_id": entry.user_id,
                    "path": entry.path,
                    "query_text": entry.query_text,
                    "retrieved_chunks": dumps_json_list(entry.retrieved_chunks),
                    "sources": dumps_json_list(entry.sources),
                    "response_summary": entry.response_summary,
                    "confidence": dumps_json(entry.confidence),
                    "completeness": entry.completeness,
                    "verified": 1 if entry.verified else 0,
                    "model_version": entry.model_version,
                    "config_version": entry.config_version,
                    "created_at": entry.created_at,
                    "grounding_status": entry.grounding_status or "",
                    "prompt_injection_detected": 1 if entry.prompt_injection_detected else 0,
                    "grounding_summary": dumps_json(entry.grounding_summary),
                    "response_payload": dumps_json(entry.response_payload),
                },
            )
        return entry

    def _map_entry(self, row: dict) -> QueryAuditEntry:
        sources = loads_json(row.get("sources"), [])
        grounding_status = row.get("grounding_status") or None
        return QueryAuditEntry(
            entry_id=row["entry_id"],
            request_id=row["request_id"],
            tool_name=row.get("tool_name") or infer_query_audit_tool_name(row["path"]),
            user_id=row["user_id"],
            path=row["path"],
            query_text=row["query_text"],
            retrieved_chunks=loads_json(row["retrieved_chunks"], []),
            sources=sources,
            response_summary=row["response_summary"],
            confidence=_normalize_confidence(loads_json(row.get("confidence"), {}), grounding_status, sources),
            completeness=_normalize_completeness(row.get("completeness"), grounding_status),
            verified=_normalize_verified(
                bool(row.get("verified", 0)) if row.get("verified") is not None else None,
                grounding_status,
                sources,
            ),
            model_version=row["model_version"],
            config_version=row["config_version"],
            created_at=row["created_at"],
            grounding_status=grounding_status,
            prompt_injection_detected=bool(row.get("prompt_injection_detected", 0)),
            grounding_summary=loads_json(row.get("grounding_summary"), {}),
            response_payload=loads_json(row.get("response_payload"), {}),
        )

    def count_entries(self, path: str | None = None) -> int:
        sql = "SELECT COUNT(*) FROM query_audit_log"
        params: dict[str, object] = {}
        if path:
            sql += " WHERE path = :path"
            params["path"] = path
        with engine.begin() as conn:
            return int(conn.execute(text(sql), params).scalar() or 0)

    def get_entries(
        self,
        path: str | None = None,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[QueryAuditEntry]:
        sql = "SELECT * FROM query_audit_log"
        params: dict[str, object] = {}
        if path:
            sql += " WHERE path = :path"
            params["path"] = path
        sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
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
    import os

    from services.persistence import ensure_governance_tables

    # Append-only in production for compliance; allow reset in test mode only.
    if os.environ.get("APP_ENV", "").lower() == "test":
        ensure_governance_tables()
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM query_audit_log"))
        global _service
        _service = QueryAuditService()
    else:
        logger = logging.getLogger(__name__)
        logger.warning("reset_query_audit_service() is disabled: audit logs must be append-only for compliance")
