import httpx
from fastapi_mcp import FastApiMCP

from mcp_request_context import mcp_internal_request

from mcp_catalog import HTTP_MCP_OPERATIONS


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
        headers=["authorization", "x-request-id", "x-user-id"],
    )
    mcp.mount_http(mount_path="/mcp")
    app.state._mcp = mcp
    app.state._mcp_http_transport = mcp._http_transport
