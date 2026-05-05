# Diseno - tramo MCP 6.5 a 6.8 para subir de confianza media-alta a alta

## Objetivo

Documentar de forma explicita el siguiente tramo del plan MCP como continuacion `6.5+`, dejando claro fase a fase que queda por hacer para pasar de una confianza operativa `media-alta` a una confianza `alta`, y actualizar los markdowns activos para que el roadmap, el remediation plan y el runbook reflejen ese trabajo pendiente y su motivo.

## Estado de partida confirmado

- El plan MCP activo queda cerrado hasta `Fase 6.4`.
- `docs/master-execution-roadmap.md` deja hoy la remediacion MCP sin nueva fase reclamada.
- La confianza operativa actual es `media-alta`, no `alta`, por tres motivos explicitados:
  - la cobertura MCP en CI sigue siendo minima, no exhaustiva
  - la matriz MCP puede ampliarse con suites ya existentes hoy fuera del bloque minimo
  - la calidad factual final depende de evidencia, citas y abstencion correcta, no solo del transporte MCP o del contrato documental
- El repo ya contiene suites MCP adicionales reutilizables para ese siguiente tramo, por ejemplo:
  - `apps/api/tests/test_mcp_transport.py`
  - `apps/api/tests/test_mcp_audit.py`
  - `apps/api/tests/test_http_mcp_audit_phase_1_1.py`
  - `apps/api/tests/test_mcp_truth_regressions.py`
  - `apps/api/tests/test_mcp_stdio_audit.py`

## Decision

- El siguiente plan quedara como continuacion explicita del remediation plan actual, no como bloque paralelo.
- Se anadira un nuevo tramo `6.5`, `6.6`, `6.7` y `6.8` dentro de `docs/reference/mcp-remediation-plan.md`.
- Este slice actual sera solo documental: define las fases siguientes y actualiza el roadmap y el runbook para que quede claro que la remediacion base esta cerrada pero el endurecimiento de confianza sigue pendiente.

## Alcance aprobado del slice actual

Incluye:

- actualizar `docs/reference/mcp-remediation-plan.md`
- actualizar `docs/master-execution-roadmap.md`
- ajustar `docs/operations/runbooks/mcp-release-gate.md` para dejar visible que el gate actual es minimo y que las fases `6.5+` lo endurecen

No incluye:

- tocar `.github/workflows/ci.yml` en este slice
- ejecutar nuevas fases MCP
- crear tests nuevos o modificar runtime

## Nuevo tramo MCP 6.5 a 6.8

### Fase 6.5 - ampliar la matriz CI MCP con suites ya existentes

Objetivo:

- pasar de una senal MCP minima en CI a una matriz MCP mas representativa usando suites ya presentes en el repo

Trabajo esperado:

- ampliar `.github/workflows/ci.yml`
- cablear al menos estas suites MCP existentes:
  - `apps/api/tests/test_mcp_transport.py`
  - `apps/api/tests/test_mcp_audit.py`
  - `apps/api/tests/test_http_mcp_audit_phase_1_1.py`
- actualizar `docs/master-execution-roadmap.md` con el cierre de la fase

Por que existe:

- el bloque MCP actual en CI solo cubre contrato minimo y no cubre todavia lifecycle HTTP MCP ni auditoria MCP mas rica

Evidencia minima esperada de cierre:

- lectura del workflow mostrando estas suites MCP nuevas dentro de CI
- verificacion de que las rutas de tests siguen existiendo y son ejecutadas por el workflow actualizado

Riesgo residual tras `6.5`:

- la CI tendra mejor cobertura estructural MCP, pero la confianza factual seguira dependiendo de golden regressions y abstencion correcta

### Fase 6.6 - convertir la regresion factual MCP en gate explicito

Objetivo:

- fijar en CI la regresion factual de consultas MCP historicamente peligrosas y las respuestas fail-closed cuando falte base suficiente

Trabajo esperado:

- decidir el rol canonico de `apps/api/tests/test_mcp_truth_regressions.py`
- cablearlo de forma explicita en CI
- si hace falta, ampliar el set de consultas de riesgo dentro de ese mismo archivo o en una extension acotada del mismo dominio
- actualizar `docs/master-execution-roadmap.md` con el cierre de la fase

Por que existe:

- una superficie MCP puede estar bien documentada, autenticada y auditada, y aun asi producir respuestas operativas malas si la logica factual o la abstencion fallan

Evidencia minima esperada de cierre:

- workflow con bloque explicito para la regresion factual MCP
- suite verde para las preguntas de riesgo fijadas

Riesgo residual tras `6.6`:

- la confianza factual mejora materialmente, pero `stdio MCP` puede seguir siendo una superficie menos endurecida si no entra aun en el gate de release

### Fase 6.7 - endurecer cobertura explicita de `stdio MCP`

Objetivo:

- asegurar que `stdio MCP` deja de ser una superficie implícita o secundaria en el criterio de confianza alta

Trabajo esperado:

- decidir y documentar que `stdio MCP` entra en el criterio de release-hardened
- cablear como minimo `apps/api/tests/test_mcp_stdio_audit.py`
- revisar si hace falta documentar o reforzar la separacion `HTTP MCP` vs `stdio MCP` en el gate de release
- actualizar `docs/master-execution-roadmap.md` con el cierre de la fase

Por que existe:

- parte del riesgo historico del repo vino precisamente de mezclar o desalinear ambas superficies MCP

Evidencia minima esperada de cierre:

- suite `stdio` verde y visible en CI o en el gate definido por la fase
- documentacion de release dejando claro que `HTTP MCP` y `stdio MCP` se validan explicitamente

Riesgo residual tras `6.7`:

- quedara aun pendiente convertir el gate de release de minimo a fuerte, con una definicion mas dura de confianza operativa alta

### Fase 6.8 - gate de release mas fuerte y criterio de confianza alta

Objetivo:

- convertir el estado MCP de “usable con confianza media-alta” a “release-ready con confianza alta” mediante un gate de release mas exigente y una definicion operativa clara de esa confianza

Trabajo esperado:

- endurecer `docs/operations/runbooks/mcp-release-gate.md`
- dejar explicito que un `GO` de alta confianza exige:
  - matrix CI MCP ampliada (`6.5`)
  - regresion factual MCP (`6.6`)
  - cobertura explicita de `stdio MCP` si aplica (`6.7`)
  - evidencia suficiente y fail-closed en respuestas sensibles
- actualizar `docs/master-execution-roadmap.md` con el cierre del tramo

Por que existe:

- hoy el gate de release MCP es correcto pero minimo; sirve para uso serio, pero no equivale todavia a una postura de confianza alta y cobertura amplia

Evidencia minima esperada de cierre:

- runbook actualizado con el nuevo criterio de `GO / NO-GO`
- roadmap dejando explicito que el frente MCP ya no esta solo “remediado”, sino endurecido hasta confianza alta

Riesgo residual tras `6.8`:

- cualquier ampliacion posterior ya seria mejora incremental o nueva cobertura de dominio, no el cierre de la brecha principal entre confianza media-alta y alta

## Markdown a actualizar en este slice

### `docs/reference/mcp-remediation-plan.md`

Debe pasar de cerrar en `6.4` a definir el nuevo tramo `6.5` a `6.8`, dejando para cada fase:

- objetivo
- archivos a tocar cuando se ejecute
- por que existe
- evidencia minima esperada

### `docs/master-execution-roadmap.md`

Debe dejar de decir que no hay nueva fase MCP reclamada sin contexto adicional y pasar a reflejar que:

- la remediacion base `6.1` a `6.4` ya esta cerrada
- el siguiente paso exacto MCP es `6.5`
- sigue habiendo trabajo definido para subir de confianza `media-alta` a `alta`

### `docs/operations/runbooks/mcp-release-gate.md`

Debe recibir un ajuste pequeno para que quede claro que el gate actual es el gate minimo correcto del estado presente y que las fases `6.5+` endurecen la confianza, no corrigen un gate roto.

## Aceptacion

- existe un nuevo tramo `6.5+` documentado fase a fase dentro del remediation plan MCP actual
- queda claro que la remediacion base esta cerrada pero la ampliacion de confianza no
- el roadmap vuelve a tener un siguiente paso exacto MCP (`6.5`)
- el runbook de release deja visible que el gate actual es minimo y que las fases posteriores lo endurecen
