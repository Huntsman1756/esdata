# Diseno: MCP Fase 4.2 - Marcar `partial` real cuando falten recursos o documentos

## Objetivo

Hacer que los workers afectados dejen de aparentar una sincronizacion completa cuando en realidad faltaron recursos o documentos durante el run.

La fase es deliberadamente estrecha: el objetivo no es persistir estado por item ni crear un framework general de outcomes. El objetivo exacto es que el `sync_log` refleje `partial` con un mensaje concreto cuando un run termina pero ha perdido parte del corpus esperado.

## Contexto

El plan MCP fija en 4.2 que varios workers hoy convierten huecos reales en silencio operativo.

Estado actual confirmado:

- `apps/workers/aeat_models.py` ya degrada correctamente a `partial` cuando faltan recursos oficiales o no se descubren modelos.
- `apps/workers/cnmv.py` traga fallos por URL dentro del bucle y aun asi cierra el run como `ok`.
- `apps/workers/dgt.py` traga fallos de fetch/parse y tambien trata como run sano el caso de consultas sin documento encontrado.
- `apps/workers/runtime.py` no tiene un helper pequeno compartido para normalizar el cierre `ok` vs `partial` en estos casos.

El hueco no es de persistencia detallada; es de veracidad del estado final del run.

## Decision de diseno

Se adopta un enfoque `sync-log only` con un helper pequeno en `apps/workers/runtime.py` y contadores locales por worker.

La implementacion se apoya en tres reglas:

1. si el run termina y no hubo fallos de artefactos perdidos, el estado final sigue siendo `ok`
2. si el run termina pero hubo recursos o documentos que faltaron o no pudieron recuperarse, el estado final pasa a `partial`
3. el `error_msg` debe decir exactamente cuantos artefactos faltaron y de que fuente son

No se crea schema nuevo ni se persiste detalle por fila fuera de `sync_log`.

## Alcance aprobado

Archivos obligatorios:

- `apps/workers/runtime.py`
- `apps/workers/aeat_models.py`
- `apps/workers/cnmv.py`
- `apps/workers/dgt.py`
- `apps/workers/tests/test_runtime.py`
- `apps/workers/tests/test_aeat_models.py`
- `apps/workers/tests/test_cnmv.py`
- `apps/workers/tests/test_dgt.py`
- `docs/master-execution-roadmap.md`
- `docs/operations/agent-notes.md`

Archivos documentales de esta fase:

- `docs/superpowers/specs/2026-05-04-mcp-fase-4-2-partial-sync-state-design.md`
- `docs/superpowers/plans/2026-05-04-mcp-fase-4-2-partial-sync-state.md`

## Runtime aprobado

### Helper compartido

`apps/workers/runtime.py` gana un helper pequeno que, dado un estado base, un contador de artefactos faltantes y una etiqueta de fuente, devuelve:

- `status` final (`ok` o `partial`)
- `error_msg` final (`None` o mensaje explicito)

Contrato minimo del helper:

- si `missing_count == 0`, devolver estado base intacto y no inventar mensaje
- si `missing_count > 0` y el estado base es `ok`, degradar a `partial`
- si `missing_count > 0`, construir mensaje estable del estilo `Skipped N <source label> after fetch failures`
- si el caller ya trae `error_msg` base, no ocultarlo accidentalmente; el helper solo cubre el caso de cierre exitoso/partial del run, no el path `error`

El helper no debe saber nada de tablas ni de workers concretos fuera de este contrato minimo.

### AEAT models

`apps/workers/aeat_models.py` ya tiene semantica correcta en esencia y solo debe alinearse con el helper compartido para evitar duplicar la logica de `partial` por recursos faltantes.

No se cambia la semantica existente:

- lock ya retenido -> `partial`
- sin modelos descubiertos -> `partial`
- recursos oficiales no recuperables -> `partial`

### CNMV

`apps/workers/cnmv.py` debe contar artefactos faltantes dentro del bucle por URL y degradar el cierre final si alguno falla.

En esta fase se consideran artefactos faltantes de CNMV:

- `client.get(url)` o la refetch del `resolved_url` fallan
- `build_document_payload(...)` o el parseo previo lanzan excepcion y no se obtiene documento usable

No se introduce clasificacion fina por tipo de excepcion. Para 4.2 basta con que el run deje de cerrar como `ok` cuando una URL esperada no pudo convertirse en documento.

### DGT

`apps/workers/dgt.py` debe contar artefactos faltantes y degradar el cierre final si alguno falta.

En esta fase se consideran artefactos faltantes de DGT:

- `fetch_search_html(...)` o `fetch_document_html(...)` fallan para una referencia de la cola
- `parse_search_results(...)` no devuelve resultados para una referencia esperada en cola
- cualquier excepcion por item que hoy se traga con `continue`

No se consideran artefactos faltantes:

- documentos que se recuperan y parsean bien pero quedan fuera del target de `normas_objetivo`

Justificacion:

- ese caso no significa ausencia de documento, sino documento real pero irrelevante para este worker
- marcarlo como `partial` generaria ruido y mezclaria incompletitud de fuente con filtro funcional del worker

## Estrategia de tests aprobada

La implementacion se hace con TDD.

### Runtime

`apps/workers/tests/test_runtime.py` debe fijar primero:

1. `missing_count = 0` conserva `ok` y `error_msg = None`
2. `missing_count > 0` degrada `ok -> partial`
3. el mensaje generado incluye el contador y la etiqueta de fuente

### AEAT

`apps/workers/tests/test_aeat_models.py` ya fija un caso real de `partial` por recursos oficiales perdidos.

La fase puede dejar ese test como cobertura primaria o anadir una asercion pequena sobre el helper solo si la refactorizacion lo exige. No hace falta ampliar mas el alcance AEAT si la semantica permanece estable.

### CNMV

`apps/workers/tests/test_cnmv.py` debe ganar un caso rojo donde una URL falla y el run:

- sigue terminando sin excepcion global
- registra `sync_log.status = 'partial'`
- registra un `error_msg` concreto tipo `Skipped 1 CNMV documents after fetch failures`

### DGT

`apps/workers/tests/test_dgt.py` debe ganar al menos dos casos rojos:

1. una referencia en cola sin resultados de busqueda o con fallo de fetch -> cierre `partial` con mensaje concreto
2. un documento fuera de `normas_objetivo` sigue cerrando sin contaminar el estado a `partial`

## Mensajes aprobados

Mensajes concretos aprobados para 4.2:

- AEAT: `Skipped N AEAT official resources after fetch failures`
- CNMV: `Skipped N CNMV documents after fetch failures`
- DGT: `Skipped N DGT documents after fetch failures`

La fase busca mensajes estables y contables, no taxonomias ricas de error.

## Fuera de alcance

4.2 no debe:

- crear tablas nuevas
- persistir detalle por documento perdido
- ampliar contratos HTTP/API
- introducir una jerarquia general de outcomes de worker
- reclasificar documentos no target como si fueran fallos de retrieval
- reescribir discovery entero de CNMV o DGT

## Riesgos y decisiones explicitas

- algunos fallos individuales hoy atrapados con `except Exception` mezclan causas distintas; 4.2 acepta esa aproximacion porque el objetivo es veracidad del estado final, no taxonomia forense completa
- la semantica de `partial` en esta fase significa `run terminado con huecos`, no necesariamente `run inutil`
- si un worker ya usa `partial` con la semantica correcta, 4.2 debe alinearlo al helper minimo sin cambiarle el comportamiento observable

## Criterio de cierre

4.2 se podra cerrar cuando:

- exista el helper minimo compartido en `runtime.py`
- `cnmv.py` y `dgt.py` dejen de cerrar como `ok` cuando falten artefactos durante el run
- `aeat_models.py` siga verde y alineado con la misma semantica de `partial`
- haya tests rojos->verdes para runtime/CNMV/DGT y evidencia fresca del scope
- el roadmap deje preparado el siguiente paso exacto hacia 4.3 o el siguiente slice MCP decidido
