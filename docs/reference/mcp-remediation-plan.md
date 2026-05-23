# MCP Remediation Plan

## Objetivo

Llevar `esdata` a un estado en el que el MCP solo pueda devolver respuestas:

- trazables
- auditables extremo a extremo
- conservadoras cuando falte base
- explicitamente parciales o `NO VERIFICADO` cuando la cobertura no sea suficiente
- reproducibles en runtime y en deploy

## Resultado esperado

1. toda tool MCP soportada deja audit trail E2E
2. stdio y HTTP MCP quedan alineados o separados de forma explicita
3. `/v1/consulta` falla en cerrado ante retrieval critico roto o grounding insuficiente
4. los modelos AEAT no aparentan completitud si faltan instrucciones o recursos oficiales
5. los workers materializan cobertura parcial en estados legibles por API/MCP
6. el deploy real aplica migraciones, verifica esquema y ejecuta smoke checks
7. existe una suite de regresion para preguntas de alto riesgo
8. existe una matriz CI MCP ampliada para transporte, auditoria y regresion factual
9. `stdio MCP` entra de forma explicita en el criterio de release cuando se declara soportado
10. existe un gate de release que diferencia confianza `media-alta` de confianza `alta`

## Principios

- priorizar exactitud sobre exhaustividad
- preferir `NO VERIFICADO` a una conclusion operativa debil
- no mezclar superficies MCP ni corpus oficiales/curados sin marcarlo
- cada fase debe cerrar con evidencia fresca del scope afectado

## Nota de compatibilidad MCP 2026-07-28

El plan base de remediacion MCP sigue aplicando al transporte actual `2025-03-26`. La RC `2026-07-28` introduce un core stateless con breaking changes: elimina `initialize`, `Mcp-Session-Id` y sesiones de protocolo. La auditoria activa vive en `docs/reference/mcp-2026-07-28-compatibility-audit.md`.

Regla: no usar este plan para sustituir `/mcp` en caliente. La compatibilidad `2026-07-28` debe trabajarse como bloque separado de transporte/versionado, manteniendo las tools y contratos fiscales intactos.

## Fases

### Fase 0 - Congelar la superficie de verdad

Objetivo: decidir y documentar la superficie MCP real antes de seguir corrigiendo capas inferiores.

#### 0.1 Superficie MCP canonica

- Decidir que tools existen en HTTP MCP y cuales en stdio
- Documentar cuales estan soportadas en produccion y cuales no
- Eliminar o explicitar el drift entre catalogos

Archivos a tocar:

- `apps/api/mcp_catalog.py`
- `apps/api/mcp_stdio.py`
- `apps/api/mcp_server.py`
- `docs/manual-usuario/07-mcp-y-clientes.md`
- `docs/integrations/opencode-local-and-vps.md`
- `docs/architecture.md`

Verificacion minima:

- `python -m pytest apps/api/tests/test_mcp_private.py apps/api/tests/test_mcp_contract.py apps/api/tests/test_mcp_comprehensive.py -q`

#### 0.2 Contrato minimo obligatorio de respuesta MCP

- Fijar estructura minima por respuesta: `request_id`, `tool_name`, `sources`, `confidence`, `completeness`, `verified/no_verificado`
- Si falta base suficiente, devolver estructura negativa explicita y no silencio

Archivos a tocar:

- `apps/api/schemas.py`
- `apps/api/mcp_catalog.py`
- `apps/api/services/query_audit.py`
- `apps/api/routers/query_audit.py`
- `docs/architecture.md`

#### 0.3 Suite de preguntas de alto riesgo

- Crear una suite fija de regresion para preguntas historicamente peligrosas

Casos iniciales:

- `como rellenar el modelo 296`
- `casilla 0490 del modelo 100`
- `FACTA/FATCA entidad pasiva USA`
- `dime casilla a casilla el modelo 100`
- `si no hay instrucciones oficiales, que me puedes decir del modelo X`

Archivos a tocar:

- `apps/api/tests/test_mcp_truth_regressions.py`
- `apps/api/tests/test_modelos_truth_contract.py`
- `apps/api/tests/conftest.py` si hace falta fixture especifico

### Fase 1 - Auditoria E2E obligatoria en toda la superficie MCP

Objetivo: que ninguna tool MCP relevante responda sin rastro auditable.

#### 1.1 Auditar todas las operaciones HTTP MCP expuestas

Herramientas/paths prioritarios:

- `buscar_legislacion`
- `get_norma`
- `get_articulo`
- `get_articulo_historial`
- `get_doctrina`
- `get_modelo`
- `get_modelo_casillas`
- `get_modelo_claves`
- `get_modelo_instrucciones`
- `get_modelo_fuentes_oficiales`

Archivos a tocar:

- `apps/api/routers/buscar.py`
- `apps/api/routers/legislacion.py`
- `apps/api/routers/doctrina.py`
- `apps/api/routers/modelos.py`
- `apps/api/services/query_audit.py`

Verificacion minima:

- `python -m pytest apps/api/tests/test_query_audit.py apps/api/tests/test_query_audit_http.py apps/api/tests/test_governance_http.py -q`

#### 1.2 Hacer auditable stdio MCP

- Propagar `request_id` real desde stdio a subrequests REST
- Persistir `tool_name`, argumentos, fuentes y resultado final
- Eliminar `retrieved_chunks=[]` artificial cuando si hubo retrieval
- No tragarse fallos de audit

Archivos a tocar:

- `apps/api/mcp_stdio.py`
- `apps/api/mcp_request_context.py`
- `apps/api/services/query_audit.py`
- tests nuevos tipo `apps/api/tests/test_mcp_stdio_audit.py`

#### 1.3 Exponer confianza real en `/v1/ai/query-audit`

- Exponer `grounding_status`, `prompt_injection_detected`, `grounding_summary`, `completeness`, `verified`

Archivos a tocar:

- `apps/api/routers/query_audit.py`
- `apps/api/services/query_audit.py`
- `apps/api/schemas.py`

#### 1.4 Persistir mejor la respuesta final

- Guardar payload final suficiente para reconstruir lo que vio el usuario
- Esta tarea puede requerir migracion Alembic

Archivos a tocar:

- nueva migracion
- `apps/api/services/query_audit.py`
- `apps/api/routers/consulta.py`
- `apps/api/mcp_stdio.py`

### Fase 2 - Consulta y retrieval: quitar falsos positivos de confianza

Objetivo: evitar respuestas seguras con evidencia circular, parcial o rota.

#### 2.1 Corregir lifecycle DB en `consulta`

Archivos a tocar:

- `apps/api/db.py`
- `apps/api/routers/consulta.py`

Verificacion minima:

- `python -m pytest apps/api/tests/test_integration.py apps/api/tests/test_query_audit.py apps/api/tests/test_reranker.py -q`

#### 2.2 Convertir fallos criticos en fail-closed

- Sustituir `except Exception` silenciosos por degradacion explicita o error

Archivos a tocar:

- `apps/api/routers/consulta.py`
- `apps/api/services/unified_multi_source_search.py`
- `apps/api/tests/test_consulta_fail_closed.py`

#### 2.3 Arreglar `unified_multi_source_search`

- Corregir alias SQL, parametros y swallowing de errores por fuente

Archivos a tocar:

- `apps/api/services/unified_multi_source_search.py`
- `apps/api/tests/test_unified_multi_source_search.py`

#### 2.4 Unificar abstention logic

- Reutilizar una sola implementacion para claim-level abstention en runtime real

Archivos a tocar:

- `apps/api/routers/consulta.py`
- `apps/api/services/grounding.py`
- `apps/api/tests/test_grounding_e2e.py`
- `apps/api/tests/test_reranker.py`

#### 2.5 Rebajar o rehacer `faithfulness_score`

- Tratarlo como advisory hasta que use la respuesta final real

Archivos a tocar:

- `apps/api/services/faithfulness.py`
- `apps/api/routers/consulta.py`
- `apps/api/tests/test_faithfulness.py`

### Fase 3 - Modelos AEAT: provenance, completitud y bloqueo de datos dudosos

Objetivo: impedir que el MCP trate metadata curada o incompleta como instruccion oficial.

#### 3.1 Elegir una via canonica de seed AEAT

- Sacar del flujo productivo las seeds legacy o marcarlas como no autoritativas

Archivos a tocar:

- `scripts/data/seed_modelos.py`
- `scripts/data/seed_modelo_articulo.py`
- `scripts/seed-modelos-v2.py`
- `scripts/seed-fiscal-modelos.sql`
- `docs/operations/agent-notes.md`

#### 3.2 Endurecer `modelo_articulo`

- No resolver por numero de articulo solamente
- Exigir `(norma, numero)` y provenance fuerte

Archivos a tocar:

- nueva migracion
- `scripts/data/seed_modelo_articulo.py`
- `apps/api/services/modelos.py`
- `apps/api/schemas.py`
- `scripts/tests/test_seed_modelo_articulo.py`

#### 3.3 Gating de completitud en runtime de modelos

- Si faltan instrucciones o recursos oficiales, devolver `NO VERIFICADO` o `cobertura_parcial`

Archivos a tocar:

- `apps/api/services/modelos.py`
- `apps/api/routers/modelos.py`
- `apps/api/schemas.py`
- `apps/api/tests/test_modelos_truth_contract.py`

#### 3.4 Detector de contaminacion en CI

- Crear chequeos para hostnames no canonicos, modelos/impuestos sospechosos, mappings sin fuente, metadata curada presentada como oficial

Archivos a tocar:

- `scripts/maintenance/check_model_data_quality.py`
- `.github/workflows/ci.yml`

### Fase 4 - Workers: convertir huecos silenciosos en estados explicitos

Objetivo: que el corpus nunca aparente completitud si no la tiene.

#### 4.1 Separar estado de cola y estado de revision en DGT

Archivos a tocar:

- `apps/workers/dgt.py`
- migracion si aplica
- tests DGT

#### 4.2 Marcar `partial` real cuando falten recursos/documentos

Archivos a tocar:

- `apps/workers/cnmv.py`
- `apps/workers/aeat_models.py`
- `apps/workers/dgt.py`
- `apps/workers/runtime.py`

#### 4.3 Completeness y provenance por fila

Archivos a tocar:

- migraciones nuevas
- workers por fuente
- `apps/api/services/source_manifest.py`
- `apps/api/routers/source_manifest.py`

#### 4.4 Separar enlaces heurísticos de exactos

Archivos a tocar:

- `apps/workers/boe.py`
- `apps/workers/borme.py`
- servicios/retrieval relacionados

#### 4.5 Activar validacion real de vocabularios

Archivos a tocar:

- `apps/workers/vocabulary_validation.py`
- call sites en workers
- tests de vocabulary

### Fase 5 - Deploy, runtime y reproducibilidad

Objetivo: que produccion corra exactamente lo que el equipo cree que corre.

#### 5.1 Migraciones obligatorias en deploy

Archivos a tocar:

- `scripts/ops/deploy-hetzner.sh`
- `.github/workflows/deploy-hetzner.yml`
- `docs/deployment/server-installation.md`
- `docs/operations/runbooks/deploy-compose.md`

#### 5.2 Expandir `verify_schema.py`

Archivos a tocar:

- `scripts/maintenance/verify_schema.py`
- tests del script

#### 5.3 Alinear env vars reales con runtime

Archivos a tocar:

- `infra/deploy/docker-compose.prod.yml`
- `infra/deploy/compose.env.example`
- `docs/environment-variables.md`

#### 5.4 Alinear worker set del deploy con el scope real

Archivos a tocar:

- `scripts/ops/deploy-hetzner.sh`
- `infra/deploy/docker-compose.prod.yml`
- `docs/deployment/server-installation.md`
- `docs/operations/runbooks/deploy-compose.md`

#### 5.5 Sacar secretos reales del checkout y alinear el contrato operativo

Archivos a tocar:

- `/etc/esdata/esdata.env` (generado desde `infra/deploy/compose.env.example` y fuera del checkout)
- docs operativas asociadas

### Fase 6 - Docs, contratos y gates de release

Objetivo: que la documentacion no sobreprometa, que exista un gate real antes de usar el MCP como superficie fiable y que el siguiente endurecimiento de confianza quede definido de forma explicita.

Las fases `6.1` a `6.4` cierran la remediacion base. Las fases `6.5` a `6.8` endurecen el MCP desde una confianza operativa `media-alta` hasta una `alta`.

#### 6.1 Alinear docs con comportamiento real

Archivos a tocar:

- `docs/architecture.md`
- `docs/manual-usuario/06-api-y-ejemplos.md`
- `docs/manual-usuario/07-mcp-y-clientes.md`
- `docs/integrations/opencode-local-and-vps.md`

#### 6.2 Añadir tests de contrato documental

Archivos a tocar:

- nuevos tests en `apps/api/tests/`
- opcional `scripts/maintenance/verify-doc-contracts.py`

#### 6.3 Crear checklist go/no-go para release MCP

Archivos a tocar:

- `docs/operations/runbooks/mcp-release-gate.md`
- `docs/master-execution-roadmap.md`
- CI/CD si se automatiza

#### 6.4 Suite de regresion MCP en CI

Archivos a tocar:

- `.github/workflows/ci.yml`
- tests de golden questions y contratos

#### 6.5 Ampliar la matriz CI MCP con suites ya existentes

Objetivo:

- pasar de una senal MCP minima en CI a una matriz MCP mas representativa usando suites ya presentes en el repo

Archivos a tocar:

- `.github/workflows/ci.yml`
- `apps/api/tests/test_mcp_transport.py`
- `apps/api/tests/test_mcp_audit.py`
- `apps/api/tests/test_http_mcp_audit_phase_1_1.py`
- `docs/master-execution-roadmap.md`

Por que existe:

- el bloque MCP actual en CI solo cubre contrato minimo y no valida todavia de forma explicita transporte HTTP MCP ni auditoria MCP mas rica

Evidencia minima esperada:

- lectura del workflow mostrando estas suites MCP dentro de `test-python` o del gate MCP equivalente
- verificacion de que las rutas de tests referenciadas siguen existiendo y forman parte del workflow actualizado

Riesgo residual:

- la cobertura estructural MCP mejora, pero la confianza factual sigue dependiendo de regresiones de verdad y de la abstencion correcta

#### 6.6 Convertir la regresion factual MCP en gate explicito

Objetivo:

- fijar en CI la regresion factual de consultas MCP historicamente peligrosas y las respuestas fail-closed cuando falte base suficiente

Archivos a tocar:

- `.github/workflows/ci.yml`
- `apps/api/tests/test_mcp_truth_regressions.py`
- `apps/api/tests/test_modelos_truth_contract.py` si la ampliacion factual lo requiere
- `docs/master-execution-roadmap.md`

Por que existe:

- una superficie MCP puede estar bien documentada, autenticada y auditada, y aun asi producir respuestas operativas malas si la logica factual o la abstencion fallan

Evidencia minima esperada:

- workflow con bloque explicito para la regresion factual MCP
- suite verde para las preguntas de riesgo fijadas

Riesgo residual:

- la confianza factual mejora materialmente, pero `stdio MCP` puede seguir siendo una superficie menos endurecida si no entra aun en el gate explicito

#### 6.7 Endurecer cobertura explicita de `stdio MCP`

Objetivo:

- asegurar que `stdio MCP` deja de ser una superficie implicita o secundaria en el criterio de confianza alta

Archivos a tocar:

- `.github/workflows/ci.yml`
- `apps/api/tests/test_mcp_stdio_audit.py`
- `docs/operations/runbooks/mcp-release-gate.md`
- `docs/master-execution-roadmap.md`

Por que existe:

- parte del riesgo historico del repo vino precisamente de mezclar o desalinear `HTTP MCP` y `stdio MCP`

Evidencia minima esperada:

- suite `stdio` verde y visible en CI o en el gate definido por la fase
- documentacion de release dejando claro que `HTTP MCP` y `stdio MCP` se validan explicitamente

Riesgo residual:

- quedara aun pendiente convertir el gate de release de minimo a fuerte, con una definicion mas dura de confianza operativa alta

#### 6.8 Gate de release mas fuerte y criterio de confianza alta

Objetivo:

- convertir el estado MCP de usable con confianza `media-alta` a release-ready con confianza `alta` mediante un gate de release mas exigente y una definicion operativa clara de esa confianza

Archivos a tocar:

- `docs/operations/runbooks/mcp-release-gate.md`
- `docs/master-execution-roadmap.md`
- `.github/workflows/ci.yml` si el gate fuerte se automatiza adicionalmente

Por que existe:

- el gate de release MCP actual es correcto pero minimo; sirve para uso serio, pero no equivale todavia a una postura de confianza alta y cobertura amplia

Evidencia minima esperada:

- runbook actualizado con el nuevo criterio de `GO / NO-GO`
- roadmap dejando explicito que el frente MCP ya no esta solo remediado, sino endurecido hasta confianza alta

Riesgo residual:

- cualquier ampliacion posterior ya seria mejora incremental o nueva cobertura de dominio, no el cierre de la brecha principal entre confianza `media-alta` y `alta`

## Orden de ejecucion recomendado

1. Fase 0.1
2. Fase 0.2
3. Fase 1.1
4. Fase 1.2
5. Fase 1.3
6. Fase 2.1
7. Fase 2.2
8. Fase 2.3
9. Fase 2.4
10. Fase 3.1
11. Fase 3.2
12. Fase 3.3
13. Fase 4.1
14. Fase 4.2
15. Fase 4.4
16. Fase 5.1
17. Fase 5.2
18. Fase 5.3
19. Fase 5.4
20. Fase 5.5
21. Fase 6.1
22. Fase 6.2
23. Fase 6.3
24. Fase 6.4
25. Fase 6.5
26. Fase 6.6
27. Fase 6.7
28. Fase 6.8

## Primer sprint recomendado

Objetivo: cerrar la capa minima de confianza antes de tocar corpus profundo.

Tareas:

1. Fase 0.1 superficie MCP canonica
2. Fase 1.1 auditar `get_norma`, `get_articulo`, `get_doctrina`, `get_modelo*`
3. Fase 1.3 exponer `grounding_status` y `grounding_summary`
4. Fase 2.1 arreglar DB lifecycle en `consulta`
5. Fase 2.2 fail-closed en retrieval
6. Crear `apps/api/tests/test_mcp_truth_regressions.py`

Verificacion minima del sprint:

- `python -m pytest apps/api/tests/test_mcp_private.py apps/api/tests/test_mcp_transport.py apps/api/tests/test_mcp_audit.py apps/api/tests/test_mcp_contract.py apps/api/tests/test_query_audit.py apps/api/tests/test_reranker.py apps/api/tests/test_mcp_truth_regressions.py -q`

## Definicion de hecho

La remediacion no se considera cerrada hasta que se cumplan estas condiciones:

1. toda tool MCP soportada deja audit trail E2E
2. `/v1/ai/query-audit` muestra grounding/confianza/completitud reales
3. stdio y HTTP MCP estan alineados o separados de forma explicita
4. `consulta` falla en cerrado ante retrieval critico roto
5. los modelos AEAT parciales se marcan como parciales
6. no hay `modelo_articulo` sin provenance fuerte
7. deploy aplica migraciones y smoke tests obligatorios
8. las golden questions no producen respuestas operativas sin base
9. la CI MCP cubre de forma explicita contrato, transporte, auditoria y regresiones factuales del scope soportado
10. `stdio MCP` entra en la validacion explicita de release cuando se declara soportado
11. el gate de release define y exige el salto de confianza `media-alta` a `alta`
