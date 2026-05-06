import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi_mcp import FastApiMCP
from mcp_catalog import HTTP_MCP_OPERATIONS
from mcp_request_context import mcp_internal_request
from services.query_audit import QueryAuditService
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MCPToolCallAuditTarget:
    jsonrpc_id: Any
    name: str
    arguments: dict[str, Any]


def _extract_tool_call_targets(payload: object) -> list[MCPToolCallAuditTarget]:
    messages = payload if isinstance(payload, list) else [payload]
    targets: list[MCPToolCallAuditTarget] = []
    for message in messages:
        if not isinstance(message, dict) or message.get("method") != "tools/call":
            continue
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        tool_name = params.get("name")
        if not isinstance(tool_name, str) or not tool_name:
            continue
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        targets.append(
            MCPToolCallAuditTarget(
                jsonrpc_id=message.get("id"),
                name=tool_name,
                arguments=arguments,
            )
        )
    return targets


def _response_by_jsonrpc_id(response_payload: object) -> dict[Any, dict[str, Any]]:
    if not isinstance(response_payload, list):
        return {}
    mapped: dict[Any, dict[str, Any]] = {}
    for item in response_payload:
        if isinstance(item, dict) and "id" in item:
            mapped[item.get("id")] = item
    return mapped


def _tool_call_status(status_code: int, payload: object | None) -> str:
    if 400 <= status_code < 500:
        return "validation_error"
    if status_code >= 500:
        return "internal_error"
    if isinstance(payload, dict) and payload.get("error"):
        return "validation_error"
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict) and payload["result"].get("isError") is True:
        return "internal_error"
    return "success"


class MCPBoundaryAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        raw_body = b""
        payload = None
        tool_calls: list[MCPToolCallAuditTarget] = []
        if request.method == "POST" and request.url.path == "/mcp":
            raw_body = await request.body()
            try:
                payload = json.loads(raw_body.decode("utf-8") or "{}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                payload = None
            tool_calls = _extract_tool_call_targets(payload)

        if raw_body:
            async def receive():
                return {"type": "http.request", "body": raw_body, "more_body": False}

            request._receive = receive

        response = await call_next(request)
        if not tool_calls:
            return response

        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        response_payload: object | None = None
        try:
            response_payload = json.loads(response_body.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            response_payload = None
        response_by_id = _response_by_jsonrpc_id(response_payload)

        request_id = (
            request.headers.get("x-request-id")
            or request.headers.get("X-Request-ID")
            or response.headers.get("x-request-id")
            or response.headers.get("X-Request-ID")
            or uuid.uuid4().hex
        )
        user_id = request.headers.get("x-user-id") or request.headers.get("X-User-ID")
        for tool_call in tool_calls:
            try:
                service = QueryAuditService()
                item_payload = response_by_id.get(tool_call.jsonrpc_id, response_payload)
                service.record_query(
                    request_id=request_id,
                    user_id=user_id,
                    path=f"/mcp/tools/call/{tool_call.name}",
                    query_text=json.dumps(tool_call.arguments, ensure_ascii=False, sort_keys=True),
                    retrieved_chunks=[],
                    response_summary=f"tool={tool_call.name} http_status={response.status_code}",
                    grounding_status=_tool_call_status(response.status_code, item_payload),
                    grounding_summary={"tool": tool_call.name, "http_status": response.status_code},
                )
            except Exception:
                logger.exception("Failed to record MCP boundary audit tool=%s request_id=%s", tool_call.name, request_id)

        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
            background=response.background,
        )


def mount_mcp(app) -> None:
    class MCPInternalAsyncClient(httpx.AsyncClient):
        async def request(self, *args, **kwargs):
            with mcp_internal_request():
                return await super().request(*args, **kwargs)

    mcp = FastApiMCP(
        app,
        http_client=MCPInternalAsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://apiserver",
            timeout=10.0,
        ),
        include_operations=HTTP_MCP_OPERATIONS,
        headers=["authorization", "x-api-key", "x-request-id", "x-user-id"],
    )
    app.add_middleware(MCPBoundaryAuditMiddleware)
    mcp.mount_http(mount_path="/mcp")
# ruff: noqa: E501
