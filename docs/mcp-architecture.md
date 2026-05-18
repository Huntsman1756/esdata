# MCP architecture

ESData exposes two MCP transport surfaces that must stay aligned.

## Transports

- HTTP MCP is mounted at `/mcp` through `fastapi_mcp.FastApiMCP`.
- stdio MCP is implemented by `apps/api/mcp_stdio.py`.

HTTP MCP reads tool names and descriptions from FastAPI OpenAPI metadata: route
`summary` and `description` in `apps/api/routers/`.

stdio MCP reads tool definitions from `get_stdio_tool_definitions()` in
`apps/api/mcp_catalog.py`. Tool contracts live in:

- `apps/api/mcp_tools_perfil.py`
- `apps/api/mcp_tools_aeat_catalogo.py`
- `apps/api/mcp_tools_eu.py`

## Verify what agents receive

stdio:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python apps/api/mcp_stdio.py \
  | jq '.result.tools[] | {name, description_length: (.description | length)}'
```

HTTP MCP uses JSON-RPC over `/mcp`. Start a session with the MCP handshake, then
call `tools/list` on `/mcp` with the returned `MCP-Session-ID`. There is no
separate stable `/mcp/tools` REST endpoint in this stack.

## Validation environments

Local Docker Desktop environments may use a minimal database for focused seed
development. The MCP validation suites assume the complete production-like
corpus is present.

Run `mcp_validation_suite.py` and `mcp_deep_contract_audit.py` for sprint
closure on the VPS, from the `ops` service, after applying the sprint data
seeds to the VPS database. A local minimal corpus is valid for focused checks,
but not for final `ok=true` suite acceptance.

## Routing policy

`MCP_TOOL_ROUTING_POLICY` is defined once in `apps/api/mcp_catalog.py`.

It is injected into stdio descriptions for:

- `obtener_obligaciones_perfil`
- `calendario_obligaciones_perfil`

The HTTP surface mirrors the same policy in router descriptions for:

- `GET /v1/perfil/{codigo}/obligaciones`
- `GET /v1/perfil/{codigo}/obligaciones/calendario`
- `GET /v1/perfil/{codigo}/obligaciones/calendario/{quarter}`

Edit both surfaces whenever changing routing language. If only one surface is
changed, agents can choose different tools depending on the transport.
