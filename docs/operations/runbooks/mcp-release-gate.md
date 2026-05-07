# Runbook: MCP Release Gate

## Objetivo

Checklist manual para decidir si MCP queda en `GO minimo`, `GO confianza alta` o `NO-GO` basandose en evidencia local reproducible y en la matriz MCP del repo activo.

## Alcance

- Este gate define dos umbrales validos para MCP: `GO minimo` y `GO confianza alta`.
- No sustituye el CI completo ni el sign-off global de producto.
- `HTTP MCP` y `stdio MCP` siguen siendo superficies distintas.
- El `GO minimo` conserva el gate manual pequeno cerrado en `6.3`.
- El `GO confianza alta` exige ademas las evidencias cerradas en `6.5`, `6.6` y `6.7`.
- Como `stdio MCP` esta declarado como superficie soportada en el repo activo, su validacion explicita no es opcional en `GO confianza alta`.

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
- Si cualquiera de esas evidencias falta o esta roja, no conceder `GO confianza alta`.

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

## Relacion con `6.5+`

- `6.5` amplia la matriz CI MCP con suites ya existentes de transporte y auditoria.
- `6.6` convierte la regresion factual MCP en gate explicito.
- `6.7` mete `stdio MCP` en la validacion explicita de release mediante `apps/api/tests/test_mcp_stdio_audit.py` y deja documentado que `HTTP MCP` y `stdio MCP` se validan por separado.
- `6.8` convierte esas evidencias en un criterio operativo explicito para distinguir `GO minimo` de `GO confianza alta`.

## Referencias

- `docs/reference/mcp-remediation-plan.md`
- `docs/operations/OPERATIONS.md`
- `docs/operations/runbooks/deploy-compose.md`
- `docs/master-execution-roadmap.md`
