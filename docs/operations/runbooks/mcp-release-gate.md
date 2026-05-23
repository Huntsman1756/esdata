# Runbook: MCP Release Gate

## Objetivo

Checklist manual para decidir si MCP queda en `GO minimo`, `GO confianza alta` o `NO-GO` basandose en evidencia local reproducible y en la matriz MCP del repo activo.

## Alcance

- Este gate define dos umbrales validos para MCP: `GO minimo` y `GO confianza alta`.
- No sustituye el CI completo ni el sign-off global de producto.
- No equivale por si solo a conformidad oficial completa MCP.
- `HTTP MCP` y `stdio MCP` siguen siendo superficies distintas.
- El `GO minimo` conserva el gate manual pequeno cerrado en `6.3`.
- El `GO confianza alta` exige ademas las evidencias cerradas en `6.5`, `6.6` y `6.7`.
- Como `stdio MCP` esta declarado como superficie soportada en el repo activo, su validacion explicita no es opcional en `GO confianza alta`.

## Estado oficial MCP actual

Estado vigente tras el baseline oficial del 2026-05-23:

- `/mcp` legacy es usable y estable para la superficie de tools de producto soportada.
- El hardening Host/Origin ya esta corregido y validado con la prueba oficial focal `dns-rebinding-protection` (`2/2`).
- ESData no cumple todavia el perfil optimo oficial MCP completo.
- No se puede reclamar conformidad oficial completa mientras el baseline global siga fallando escenarios de `resources`, `prompts`, `completion`, `logging`, `progress`, `sampling`, `elicitation`, fixtures multimedia/JSON Schema o transporte stateless `2026-07-28`.

Regla de comunicacion:

> Decir "MCP legacy soportado y estable para ESData" es correcto cuando este runbook esta verde. Decir "MCP oficialmente conforme/optimo" solo es correcto si se pasa la suite oficial completa acordada o si existe un fichero versionado de expected-failures que delimite explicitamente el scope certificado.

## Preconditions

- Worktree limpio o, como minimo, cambios locales entendidos antes de decidir el release.
- Ejecutar los comandos desde la raiz activa del repo.
- Entorno local listo para ejecutar comandos de Python y `pytest`.

## Checks requeridos para `GO minimo`

### 1. Gate documental

```bash
python scripts/maintenance/verify-doc-contracts.py
```

Verde significa que los boundaries documentales siguen intactos. Rojo significa `NO-GO`.

### 2. Regresion MCP privada

```bash
python -m pytest apps/api/tests/test_mcp_private.py -q
```

Verde significa que el transporte MCP privado y sus checks siguen vigentes. Rojo significa `NO-GO`.

### 3. Gate estructural minimo de runtime

```bash
python scripts/maintenance/verify_schema.py
```

Verde significa que el contrato estructural minimo que el runtime actual exige sigue presente. Rojo significa `NO-GO`.

### 4. Host/Origin MCP

```bash
python -m pytest apps/api/tests/test_mcp_private.py::test_mcp_http_rejects_invalid_host_header \
  apps/api/tests/test_mcp_private.py::test_mcp_http_rejects_invalid_origin_header \
  apps/api/tests/test_mcp_private.py::test_mcp_http_accepts_configured_api_domain_host_and_origin -q
```

Verde significa que el hardening anti DNS rebinding sigue activo en el guard MCP. Rojo significa `NO-GO`.

## Evidencia a registrar

- Comando ejecutado.
- Resultado observado.
- Fecha y hora.
- Rama, worktree o `SHA` usados para tomar la decision.

## Evidencia endurecida obligatoria para `GO confianza alta`

- Evidencia del mismo `SHA`, rama o worktree sobre el que se toma la decision.
- Matriz MCP ampliada visible y verde en `test-python`, incluyendo como minimo:
  - `python -m pytest apps/api/tests/test_mcp_transport.py -q`
  - `python -m pytest apps/api/tests/test_mcp_audit.py -q`
  - `python -m pytest apps/api/tests/test_http_mcp_audit_phase_1_1.py -q`
  - `python -m pytest apps/api/tests/test_mcp_truth_regressions.py -q`
  - `python -m pytest apps/api/tests/test_mcp_stdio_audit.py -q`
- Regresion factual MCP verde para preguntas de riesgo y evidencia de respuesta conservadora / fail-closed cuando falte base suficiente.
- Validacion explicita separada de `HTTP MCP` y `stdio MCP`, sin ambiguedad abierta entre ambas superficies.
- Si el cambio toca `apps/api/mcp_security.py`, `apps/api/mcp_server.py`, `apps/api/main.py`, `infra/deploy/docker-compose.prod.yml` o cabeceras/proxy, repetir en VPS la prueba oficial focal:

```bash
npx --yes @modelcontextprotocol/conformance server \
  --url http://127.0.0.1:8787/mcp \
  --scenario dns-rebinding-protection
```

La prueba debe ejecutarse via proxy local autenticado que inyecte `X-API-Key` desde `/etc/esdata/esdata.env`, tal como documenta `docs/reference/mcp-official-conformance-baseline-20260523.md`.
- Si cualquiera de esas evidencias falta o esta roja, no conceder `GO confianza alta`.

## Gate de conformance oficial

Este gate solo se aplica cuando se quiera medir o reclamar alineacion con el proyecto oficial MCP.

### Baseline completo

Ejecutar contra VPS, no contra una simulacion:

```bash
npx --yes @modelcontextprotocol/conformance server \
  --url http://127.0.0.1:8787/mcp \
  --output-dir /tmp/esdata-mcp-conformance/full
```

Reglas:

- Usar proxy local autenticado si el CLI sigue sin soportar cabecera `X-API-Key`.
- Ejecutar escenarios secuenciales o con rate limit suficientemente alto para no contaminar resultados con `429`.
- Registrar commit, entorno, comando y resumen `pass/fail`.
- No sobreescribir el baseline historico; crear un nuevo baseline fechado cuando cambie el resultado material.

### Expected failures

Si ESData no pretende implementar toda la superficie MCP oficial, crear un fichero versionado de expected-failures antes de usar la suite como gate de CI.

El fichero debe distinguir:

- `out_of_scope_product`: features deliberadamente no ofrecidas, por ejemplo `prompts` si no forman parte del producto.
- `missing_official_conformance`: gaps reales para conformance oficial, por ejemplo `resources`, `completion` o fixtures JSON Schema.
- `security_regression`: nunca debe ir en expected-failures sin una excepcion temporal fechada.
- `transport_migration_pending`: cambios ligados a MCP `2026-07-28` stateless.

No usar expected-failures para esconder regresiones de una feature que ESData declara soportada.

### Reclamaciones permitidas

| Estado | Claim permitido | Claim prohibido |
| --- | --- | --- |
| CI local verde sin conformance oficial | `MCP legacy estable para el scope soportado` | `cumple MCP oficial` |
| Baseline oficial parcial | `conformidad oficial parcial medida` | `optimo oficial` |
| Baseline oficial con expected-failures versionados | `conforme al scope declarado` | `conformidad completa` |
| Suite oficial completa verde sin expected-failures | `conformidad oficial completa para la version medida` | N/A |

## Reglas para futuro desarrollo MCP

- No tocar `/mcp` legacy para implementar `2026-07-28`; usar ruta/modo separado hasta validar clientes reales.
- Todo cambio de transporte debe preservar `test_mcp_private.py`, `test_mcp_transport.py` y `test_mcp_audit.py`.
- Todo cambio de seguridad MCP debe incluir tests negativos antes del fix.
- Todo cambio en Compose que afecte Host/proxy debe confirmar que `API_DOMAIN` sigue llegando al servicio `api`.
- No anadir comodines a `ESDATA_MCP_ALLOWED_HOSTS`.
- No mezclar conformance oficial con curacion fiscal/doctrinal en la misma PR.
- No marcar una feature MCP como soportada si solo existe como roadmap o xfail.
- Si se anade `resources`, `prompts`, `completion`, `logging`, `progress`, `sampling` o `elicitation`, documentar si es feature de producto o fixture de conformance.
- Si se anade `server/discover` o transporte stateless, actualizar `docs/reference/mcp-2026-07-28-compatibility-audit.md` y quitar `xfail` solo cuando haya implementacion real.

## Decision final

### GO confianza alta

Todos los checks de `GO minimo` estan en verde y, ademas, existe evidencia fresca y consistente de la matriz MCP ampliada (`6.5`), de la regresion factual MCP (`6.6`) y de la validacion explicita de `stdio MCP` (`6.7`) sobre el mismo estado del repo. No existe ambiguedad sin resolver entre `REST/OpenAPI`, `HTTP MCP` y `stdio MCP`, y las respuestas sensibles siguen demostrando comportamiento conservador / fail-closed cuando falta base. Este es el unico estado que equivale a confianza operativa `alta` para el scope MCP soportado hoy.

### GO minimo

Los checks requeridos del gate manual pequeno estan en verde y no existe ambiguedad sin resolver entre superficies, pero falta alguna evidencia endurecida de `6.5` a `6.7` o no esta disponible para el mismo `SHA`. Este estado permite hablar de readiness minima correcta, no de confianza operativa `alta`.

### NO-GO

Cualquier check minimo falla, no puede reproducirse, queda ambiguo, o se detecta evidencia insuficiente / roja en el conjunto que se pretende usar para reclamar `GO confianza alta`.

## Este gate no prueba

- Cobertura completa de dominios MCP aun no soportados.
- El sign-off completo del producto fuera del scope MCP.
- Conformance oficial completa si no se ejecuta la suite oficial o si existen expected-failures.

## Relacion con `6.5+`

- `6.5` amplia la matriz CI MCP con suites ya existentes de transporte y auditoria.
- `6.6` convierte la regresion factual MCP en gate explicito.
- `6.7` mete `stdio MCP` en la validacion explicita de release mediante `apps/api/tests/test_mcp_stdio_audit.py` y deja documentado que `HTTP MCP` y `stdio MCP` se validan por separado.
- `6.8` convierte esas evidencias en un criterio operativo explicito para distinguir `GO minimo` de `GO confianza alta`.

## Referencias

- `docs/reference/mcp-remediation-plan.md`
- `docs/reference/mcp-official-conformance-baseline-20260523.md`
- `docs/reference/mcp-2026-07-28-compatibility-audit.md`
- `docs/operations/OPERATIONS.md`
- `docs/operations/runbooks/deploy-compose.md`
- `docs/master-execution-roadmap.md`
