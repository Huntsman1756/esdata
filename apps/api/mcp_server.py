from fastapi_mcp import FastApiMCP

from mcp_catalog import HTTP_MCP_OPERATIONS


def mount_mcp(app) -> None:
    mcp = FastApiMCP(
        app,
        include_operations=HTTP_MCP_OPERATIONS,
    )
    mcp.mount_http(mount_path="/mcp")
