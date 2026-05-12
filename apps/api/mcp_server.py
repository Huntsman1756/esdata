import json
from typing import Any

import httpx
from fastapi_mcp import FastApiMCP
from mcp_catalog import HTTP_MCP_OPERATIONS, apply_http_tool_contract
from mcp_request_context import get_mcp_request_id, get_mcp_user_id, mcp_internal_request


class ESDataFastApiMCP(FastApiMCP):
    async def _execute_api_tool(
        self,
        client,
        tool_name: str,
        arguments: dict[str, Any],
        operation_map: dict[str, dict[str, Any]],
        http_request_info=None,
    ) -> dict[str, Any]:
        content = await super()._execute_api_tool(
            client=client,
            tool_name=tool_name,
            arguments=arguments,
            operation_map=operation_map,
            http_request_info=http_request_info,
        )
        if not content:
            return {}
        first = content[0]
        text_value = getattr(first, "text", "")
        try:
            result = json.loads(text_value)
        except (TypeError, json.JSONDecodeError):
            return {"text": text_value}
        if isinstance(result, dict):
            return result
        return {"items": result}


def mount_mcp(app) -> None:
    class MCPInternalAsyncClient(httpx.AsyncClient):
        async def request(self, *args, **kwargs):
            headers = dict(kwargs.pop("headers", {}) or {})
            request_id = get_mcp_request_id()
            user_id = get_mcp_user_id()
            if request_id:
                headers.setdefault("x-request-id", request_id)
            if user_id:
                headers.setdefault("x-user-id", user_id)
            with mcp_internal_request():
                return await super().request(*args, headers=headers, **kwargs)

    mcp = ESDataFastApiMCP(
        app,
        http_client=MCPInternalAsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://apiserver",
            timeout=10.0,
        ),
        include_operations=HTTP_MCP_OPERATIONS,
        headers=["authorization", "x-request-id", "x-user-id"],
    )
    apply_http_tool_contract(mcp.tools)
    mcp.mount_http(mount_path="/mcp")
    app.state._mcp = mcp
    app.state._mcp_http_transport = mcp._http_transport
