# Diseno - Fase 6.3 checklist go/no-go para release MCP

## Objetivo

Crear un runbook manual de go/no-go que permita decidir si la superficie MCP esta lista para tratarse como release-ready en el estado actual del repo, usando solo gates, tests y contratos que ya existen hoy, sin introducir automatizacion nueva ni cambios de runtime.

## Problema confirmado

- `Fase 6.1` ya alineo la documentacion activa entre `REST/OpenAPI`, `HTTP MCP`, `stdio MCP` y `OpenCode -> HTTP MCP`.
- `Fase 6.2` ya anadio un gate pequeno para detectar drift documental en esas fronteras.
- Sigue faltando un checklist operativo unico que diga a un humano que debe ejecutar antes de declarar la release MCP como apta, con criterios claros de `GO` o `NO-GO`.
- `docs/reference/mcp-remediation-plan.md` define explicitamente `6.3` como la fase para crear `docs/operations/runbooks/mcp-release-gate.md`.
- No existe hoy una runbook MCP equivalente centrada en decision de release; hay evidencia dispersa en roadmap, tests y gates, pero no una checklist unificada.

## Decision

- `Fase 6.3` sera solo documental.
- Se anadira `docs/operations/runbooks/mcp-release-gate.md` como runbook manual de go/no-go.
- El runbook reutilizara solo comandos y gates ya existentes en el repo.
- El runbook sera fail-closed: cualquier check rojo o inconcluso fuerza `NO-GO`.
- La automatizacion posterior en CI se reserva para `Fase 6.4`.

## Alcance aprobado

Incluye:

- crear `docs/operations/runbooks/mcp-release-gate.md`
- definir precondiciones operativas minimas antes de ejecutar el gate
- enumerar checks requeridos y la evidencia que debe capturarse
- definir criterios explicitos de `GO` y `NO-GO`
- actualizar `docs/master-execution-roadmap.md` para reclamar y cerrar `6.3`

No incluye:

- cambios en `.github/workflows/ci.yml`
- scripts nuevos
- nuevos tests de runtime o regression
- cambios en `apps/api/`, `apps/workers/` o `infra/`

## Runbook a crear

### Archivo

- `docs/operations/runbooks/mcp-release-gate.md`

### Proposito

Servir como checklist unica para una persona que necesite decidir si el MCP puede considerarse apto para release con base en evidencia local y reproducible.

### Estructura esperada

#### 1. Alcance del gate

- dejar claro que el gate cubre readiness minima de release MCP
- dejar claro que no sustituye CI completo ni sign-off global del producto
- recordar que `HTTP MCP` y `stdio MCP` siguen siendo superficies distintas

#### 2. Preconditions

- worktree limpio o al menos comprendido
- entorno local preparado para ejecutar los comandos listados
- ruta de trabajo explicita desde la raiz del repo activa

#### 3. Checks requeridos

El checklist debe reutilizar solo comprobaciones que ya existen en el repo actual. Como minimo:

- gate documental:
  - `python scripts/maintenance/verify-doc-contracts.py`
- regresion MCP privada / transporte:
  - `python -m pytest apps/api/tests/test_mcp_private.py -q`
- gate estructural de deploy/runtime:
  - `python scripts/maintenance/verify_schema.py`

Si al revisar el repo hay un comando mas pequeno o mas preciso ya asentado para alguno de esos dominios, el runbook puede escogerlo, pero no debe inventar nuevas piezas.

#### 4. Evidencia a registrar

Para cada check:

- comando exacto
- resultado observado
- fecha/hora
- branch, worktree o SHA usado para la decision

#### 5. Interpretacion

- explicar brevemente por que importa cada check
- decir explicitamente que cualquier fallo, warning bloqueante o resultado inconcluso implica `NO-GO`

#### 6. Decision final

##### `GO`

- todos los checks requeridos en verde
- evidencia registrada
- sin ambiguedad abierta sobre boundaries entre `REST/OpenAPI`, `HTTP MCP` y `stdio MCP`

##### `NO-GO`

- cualquier check falla
- cualquier check no puede reproducirse
- cualquier resultado es ambiguo o no deja evidencia suficiente

#### 7. Lo que este gate no prueba

- no demuestra cobertura total de CI
- no sustituye el wiring automatico de `6.4`
- no equivale a aprobacion integral del producto fuera del alcance MCP

## Roadmap

`docs/master-execution-roadmap.md` debe:

- reclamar `6.3` mientras se redacta el runbook
- cerrar `6.3` cuando el runbook exista y se haya leido de vuelta para validar contenido y rutas
- dejar `6.4` como siguiente paso exacto para automatizacion en CI

## Verificacion prevista

- lectura completa de `docs/operations/runbooks/mcp-release-gate.md`
- comprobacion de que todas las rutas y comandos referenciados existen en el repo actual
- lectura del resumen vivo del roadmap para confirmar reclamo y cierre correctos

## Aceptacion

- existe una checklist MCP unica y localizable en `docs/operations/runbooks/mcp-release-gate.md`
- el runbook dice exactamente que ejecutar, que evidencias guardar y cuando declarar `GO` o `NO-GO`
- el runbook no inventa automatizacion nueva ni depende de target-state futuro
- `docs/master-execution-roadmap.md` queda listo para cerrar `6.3` y apuntar a `6.4`
