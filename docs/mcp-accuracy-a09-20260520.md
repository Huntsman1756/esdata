# A-09 MCP tool accuracy spot-check - 2026-05-20

## Scope

Audit performed against production VPS `root@212.227.227.64`, repo `/srv/esdata`, API `http://localhost:8000`, through the stateful MCP HTTP endpoint `/mcp`.

Evidence artifacts were captured on the VPS under:

```text
/root/a09-mcp-spot-20260520
```

## Tool contract check

`tools/list` returned `77` MCP tools.

Contract checks:

| Check | Result |
|---|---:|
| Tools returned | 77 |
| Missing `outputSchema` object | 0 |
| Missing `annotations.readOnlyHint=true` | 0 |

Relevant tools inspected:

- `get_articulo`
- `obtener_obligaciones_perfil`
- `buscar_norma_eu`
- `buscar_legislacion`
- `buscar`

The increase from the previous `70` tools baseline is expected after the MiCA CASP and `emisor_token` sprints. The new profile-routing surface keeps complete read-only tool metadata.

## MCP accuracy cases

### LIVA art. 1

Tool call:

```json
{"name":"get_articulo","arguments":{"codigo":"LIVA","numero":"1"}}
```

Result:

- HTTP: `200`
- `boe_reference`: `BOE-A-1992-28740`
- `source_url`: `https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a1`
- Text includes the official heading and body for `Articulo 1. Naturaleza del impuesto.`
- `verified=true`
- `completeness=completa`

Status: PASS.

### Repealed provision handling

Two checks were relevant:

- `LIVA art. 140` has historical repealed versions, but the MCP correctly returns the current article text, not the historical repealed version.
- `LIVA art. 150` is currently represented as repealed and returns explicit text `(Derogado)`.

Tool call:

```json
{"name":"get_articulo","arguments":{"codigo":"LIVA","numero":"150"}}
```

Result:

- HTTP: `200`
- Text contains `(Derogado)`
- `boe_reference`: `BOE-A-1992-28740`
- `source_url`: `https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a150`
- `verified=true`

Status: PASS. The contract does not expose a separate `derogado=true` boolean, but the repealed status is explicit in the returned official text.

### Absent article

Tool call:

```json
{"name":"get_articulo","arguments":{"codigo":"LIVA","numero":"9999"}}
```

Result:

- MCP HTTP transport: `200`
- Tool result: `isError=true`
- Tool message includes `Status code: 404`
- Tool message includes `Articulo no encontrado`
- No 500 or silent empty response.

Status: PASS.

### `emisor_token` MiCA obligations

Tool call:

```json
{"name":"obtener_obligaciones_perfil","arguments":{"codigo":"emisor_token","dominio":"ALL","verified":true}}
```

Result:

| Check | Result |
|---|---:|
| Obligations returned | 8 |
| `verified=false` rows | 0 |
| Missing `source_url` rows | 0 |
| Missing `norma_codigo` rows | 0 |

Articles returned:

```text
art. 18, art. 48, art. 55, art. 25, art. 35, art. 45, art. 19, art. 51
```

All rows use:

- `norma_codigo=32023R1114`
- `source_url=https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32023R1114`
- `verified=true`

Note: these are EU/MiCA obligations, so `boe_reference` is not the canonical identifier for the obligation rows. The authoritative reference is the CELEX-backed `norma_codigo=32023R1114` plus the EUR-Lex `source_url`. This is expected and should not be filled with a synthetic BOE reference.

Status: PASS-WITH-CAVEAT for the user-requested `boe_reference` wording, because CELEX is the correct canonical reference here.

## MCP transport note

The stateful MCP endpoint behavior observed in A-08 remains valid for A-09:

- Initial direct `GET /mcp` can return `400 Missing session ID`.
- It still emits an `mcp-session-id`.
- JSON-RPC calls after `initialize` with `Mcp-Session-Id` work normally.

This is expected stateful MCP protocol behavior, not a tool accuracy bug. It should be documented in A-11 or the final audit report to avoid misclassifying direct `GET /mcp` probes as production failures.

## Result

A-09 passes with one explicit caveat: MiCA `emisor_token` obligations expose CELEX/EUR-Lex references, not BOE references. No contract or data mutation was required.
