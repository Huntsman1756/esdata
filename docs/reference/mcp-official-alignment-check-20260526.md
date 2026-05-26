# MCP official alignment check - 2026-05-26

Estado: validacion local del scope MCP soportado. No despliega VPS y no cambia datos productivos.

Commit local: `c2b3c9c8`.

## Objetivo

Comprobar que los cambios recientes de contrato fiscal AEAT, incluida
`technical_exercise_coverage`, siguen construidos sobre el criterio oficial de
MCP sin vender conformidad completa.

La validacion distingue tres niveles:

1. contrato interno ESData para `tools`, seguridad y fail-closed fiscal;
2. prueba focal con la suite oficial `@modelcontextprotocol/conformance`;
3. gaps oficiales conocidos que siguen fuera del scope actual del producto.

## Fuentes oficiales MCP revisadas

- Organizacion oficial MCP: <https://github.com/modelcontextprotocol>
- Especificacion MCP `2025-06-18`, `server/tools`:
  <https://modelcontextprotocol.io/specification/2025-06-18/server/tools>
- Especificacion MCP `2025-06-18`, `server/resources`:
  <https://modelcontextprotocol.io/specification/2025-06-18/server/resources>

Lectura aplicada:

- ESData declara y valida una superficie de `tools` de producto.
- `resources`, `prompts`, `completion`, `logging`, `progress`, `sampling` y
  `elicitation` no quedan soportados por el mero hecho de exponer contexto por
  herramientas.
- Un recurso o artefacto oficial no prueba por si solo una campana fiscal; el
  rol probatorio debe ser campo de dominio, no inferencia del cliente MCP.

## Resultado interno

Comando ejecutado:

```powershell
python -m pytest apps\api\tests\test_mcp_private.py apps\api\tests\test_mcp_transport.py apps\api\tests\test_mcp_stdio_integration.py apps\api\tests\test_mcp_stdio_audit.py apps\api\tests\test_mcp_routing_policy.py apps\api\tests\test_tools_list_output.py apps\api\tests\test_mcp_20260728_contract.py apps\api\tests\test_modelos_truth_contract.py scripts\tests\test_mcp_campaign_assertion_contract.py -q
```

Resultado:

```text
110 passed, 5 xfailed, 2 warnings
```

Lectura:

- `HTTP MCP` mantiene handshake, `initialize`, `tools/list`, `tools/call`,
  API key, rate limit y `Host`/`Origin` hardening.
- `stdio MCP` sigue validado como superficie separada.
- Todas las tools exponen contrato read-only mediante anotaciones.
- El contrato AEAT sigue fail-closed: `technical_exercise_coverage` no alimenta
  `campana_afirmable`, `campana_safe_to_assert=true` ni
  `ASSERTABLE_DIRECT_OFFICIAL`.
- Los 5 `xfail` corresponden a la fase futura MCP `2026-07-28` stateless y no
  deben interpretarse como soporte implementado.

## Resultado documental/estructural

Comando:

```powershell
python scripts\maintenance\verify-doc-contracts.py
```

Resultado:

```text
docs contracts verified
```

Comando no ejecutable en este entorno local:

```powershell
python scripts\maintenance\verify_schema.py
```

Resultado:

```text
SCHEMA VERIFICATION FAILED: DATABASE_URL is not set
```

Lectura: no se reclama gate estructural completo local porque falta
`DATABASE_URL`. Ese check debe ejecutarse en VPS/ops o en un entorno con DB
configurada antes de cualquier despliegue.

## Prueba focal oficial MCP

Se consulto la CLI oficial:

```powershell
npx --yes @modelcontextprotocol/conformance server --help
```

La CLI ofrece `--url`, `--scenario`, `--suite`, `--expected-failures`,
`--output-dir` y `--spec-version`, pero no cabeceras custom para `X-API-Key`.
Por eso la prueba local se ejecuto contra Uvicorn en `APP_ENV=test`, sin exigir
API key productiva.

Escenarios ejecutados:

```powershell
npx --yes @modelcontextprotocol/conformance server --url http://127.0.0.1:8792/mcp --scenario server-initialize
npx --yes @modelcontextprotocol/conformance server --url http://127.0.0.1:8792/mcp --scenario tools-list
```

Resultado material:

```text
server-initialize: Passed: 1/1, 0 failed, 0 warnings
tools-list:        Passed: 1/1, 0 failed, 0 warnings
```

Limitacion local:

En Windows, el primer proceso `npx` imprimio despues del resultado correcto:

```text
Assertion failed: !(handle->flags & UV_HANDLE_CLOSING), file src\win\async.c, line 76
EXIT_CODE=-1073740791
```

No se interpreta como fallo del servidor porque la propia suite imprimio
`Passed: 1/1` antes del crash del proceso Node/libuv. Para un gate formal de
release debe repetirse en VPS/Linux con proxy local autenticado, como ya exige
`docs/operations/runbooks/mcp-release-gate.md`.

## Dictamen

ESData sigue alineado con el criterio oficial MCP para el scope que declara hoy:
`tools` read-only de producto sobre transporte legacy.

No cumple ni debe reclamar conformidad oficial completa MCP mientras sigan fuera
de scope:

- `resources`;
- `prompts`;
- `completion`;
- `logging`;
- `progress`;
- `sampling`;
- `elicitation`;
- fixtures multimedia/JSON Schema de la suite oficial;
- transporte stateless MCP `2026-07-28`.

La frase correcta sigue siendo:

> MCP legacy estable para el scope soportado de ESData.

La frase prohibida sigue siendo:

> ESData cumple MCP oficial completo.

## Impacto sobre `technical_exercise_coverage`

El campo nuevo es compatible con MCP porque se publica como parte del resultado
estructurado de tools de dominio, no como capability MCP `resources`.

Regla mantenida:

- `technical_exercise_coverage.proves_campaign = false`
- `technical_exercise_coverage.evidence_role = technical_exercise_coverage`
- nunca alimenta `campana_afirmable`
- nunca activa `campana_safe_to_assert`
- nunca permite `ASSERTABLE_DIRECT_OFFICIAL`

Por tanto, el cliente MCP puede leer cobertura tecnica oficial como contexto,
pero no puede convertirla en afirmacion fiscal.

## Siguiente accion

Antes de desplegar este slice en VPS:

1. ejecutar `verify_schema.py` con `DATABASE_URL`;
2. ejecutar el gate MCP del runbook en VPS/ops;
3. si se quiere reclamar alineacion oficial nueva, crear un baseline fechado con
   `@modelcontextprotocol/conformance` y expected-failures versionados.
