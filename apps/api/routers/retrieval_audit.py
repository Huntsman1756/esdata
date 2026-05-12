from __future__ import annotations

from typing import Any

from fastapi import Request

from request_context import get_request_id, get_user_id
from services.query_audit import get_query_audit_service


def _value(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def build_document_chunks(items: list[dict[str, Any]], *, limit: int = 20) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for item in items[:limit]:
        source_url = _value(item, "source_url", "url_fuente", "url_aepd", "url_cnmv")
        referencia = _value(item, "referencia", "codigo", "celex", "registration_number", "name")
        chunk = {
            "referencia": referencia,
            "title": _value(item, "titulo", "name"),
            "source_url": source_url,
            "boe_referencia": _value(item, "boe_referencia", "referencia_boe", "boe_reference"),
            "tipo_documento": _value(item, "tipo_documento", "coverage_status", "quality_signal"),
        }
        chunks.append({key: value for key, value in chunk.items() if value not in (None, "")})
    return [chunk for chunk in chunks if chunk]


def record_retrieval_query_audit(
    request: Request,
    *,
    path: str,
    query_text: str,
    tool_name: str,
    items: list[dict[str, Any]],
    total: int,
    verified: bool,
    completeness: str = "parcial",
    response_summary: str | None = None,
) -> None:
    get_query_audit_service().record_query(
        request_id=get_request_id(request),
        user_id=get_user_id(request),
        path=path,
        query_text=query_text,
        retrieved_chunks=build_document_chunks(items),
        response_summary=response_summary or f"total={total}; returned={len(items)}",
        tool_name=tool_name,
        confidence={"score": 0.9 if verified and items else 0.5 if items else 0.0},
        completeness=completeness,
        verified=verified,
    )
