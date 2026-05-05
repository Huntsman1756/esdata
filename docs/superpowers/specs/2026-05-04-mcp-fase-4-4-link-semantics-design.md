# Diseno: MCP Fase 4.4 - Separar enlaces heuristicos de exactos

## Objetivo

Separar la semantica de enlaces exactos frente a enlaces heuristicos en las superficies de linking que hoy alimentan retrieval, conectividad y detalle doctrinal.

La fase es deliberadamente estrecha:

- afecta primero a `BOE`, `BORME` y a los consumidores API/retrieval relacionados
- no introduce migracion nueva
- no cambia el shape publico salvo donde ya existe `metodo_enlace`

El objetivo exacto es que el runtime deje de tratar como equivalentes un enlace sustentado por una referencia canonica explicita y un enlace best-effort inferido por contexto.

## Contexto

El plan MCP fija en `4.4` que hace falta separar enlaces heuristicos de exactos.

Estado actual confirmado tras `4.3`:

- `apps/workers/boe.py:auto_link_doctrina()` persiste enlaces exactos y heuristicos con el mismo `metodo_enlace='auto_link'`.
- `_extract_doctrina_refs()` ya distingue de facto entre patrones explicitos y fallback contextual, pero esa diferencia se pierde al persistir.
- `apps/api/routers/doctrina.py` y `apps/api/routers/dgt_doctrina.py` calculan hoy `has_strong_anchor` solo desde `max(confianza_enlace) >= 0.85`.
- `apps/api/services/connectivity.py` y `apps/api/services/graph_connectivity.py` exponen `metodo_enlace` y `confianza_enlace`, pero no operan con una frontera semantica fiable porque ambos tipos de enlace pueden llegar con el mismo metodo.
- `apps/workers/borme.py` ya persiste `documento_empresa` como extraccion heuristica mediante `confianza_extraccion` y `nota`, pero esa frontera aun no queda declarada como decision explicita del slice.

El hueco real no es de ausencia de links. El hueco es de veracidad semantica:

- un enlace exacto y uno heuristico pueden verse iguales para el runtime
- un enlace heuristico fuerte puede elevar `verified` o el nivel de confianza como si fuera una cita explicita
- la auditoria E2E puede registrar `verified=true` aunque el anclaje real sea best-effort

## Alcance aprobado

Archivos obligatorios:

- `apps/workers/boe.py`
- `apps/workers/borme.py`
- `apps/api/routers/doctrina.py`
- `apps/api/routers/dgt_doctrina.py`
- `apps/api/services/connectivity.py`
- `apps/api/services/graph_connectivity.py`
- tests de workers/API afectados
- `docs/master-execution-roadmap.md`
- `docs/operations/agent-notes.md`

Archivos documentales de esta fase:

- `docs/superpowers/specs/2026-05-04-mcp-fase-4-4-link-semantics-design.md`

## Enfoques considerados

### Opcion 1 - reetiquetar metodos existentes y endurecer lectores

Separar la escritura de links exactos y heuristicos mediante valores distintos de `metodo_enlace`, y hacer que los lectores consuman esa semantica en vez de depender solo de `confianza_enlace`.

Ventajas:

- cambio pequeno y sin migracion
- corrige la causa real del problema en escritura y lectura
- conserva el shape publico actual

Inconvenientes:

- la taxonomia sigue viviendo en strings de `metodo_enlace`
- obliga a tocar varios lectores para evitar drift

### Opcion 2 - anadir una columna explicita `link_kind`

Crear una migracion nueva para guardar `exact` vs `heuristic` fuera de `metodo_enlace`.

Ventajas:

- semantica mas clara y durable
- menos dependencia de convenciones en strings

Inconvenientes:

- slice mas grande
- introduce schema nuevo fuera de la necesidad minima de `4.4`
- abre mas superficie en migraciones, SQLite de tests y contratos

### Opcion 3 - mantener storage y reinterpretar en runtime

No cambiar como se escribe y anadir solo un helper que deduzca si algo es exacto o heuristico a partir de `metodo_enlace` + `confianza_enlace`.

Ventajas:

- cambio inicial muy pequeno

Inconvenientes:

- no corrige el problema de origen
- mantiene exactos y heuristicos persistidos bajo el mismo metodo
- deja mas espacio a drift futuro

## Decision aprobada

Se aprueba la opcion 1.

`4.4` separara enlaces exactos y heuristicos en la escritura del worker `boe` y hara que los lectores doctrinales/de conectividad consuman esa nueva semantica. `BORME` queda explicitamente fijado como linking heuristico en esta fase y no se promociona a exacto.

## Contrato semantico aprobado

La fase adopta una regla unica:

- `exacto` solo cuando la fuente trae un identificador o una referencia canonica explicita suficiente para resolver el destino sin inferencia contextual adicional

Aplicado a `BOE`/doctrina:

- `LIVA 91`, `art. 91 LIVA`, `articulo 91 de la Ley 37/1992`, `art. 111 LGT`, `articulo 45.1.a) de la Ley 35/2006 del IRPF` son exactos
- referencias resueltas por contexto como `IVA + base imponible`, `Ley del IVA` sin anclaje suficiente, o articulo desnudo apoyado en una sola norma contextual son heuristicas

Aplicado a `BORME`:

- extraccion de empresa, domicilio, rol y relaciones desde texto libre de anuncios sigue siendo heuristica en este slice
- `documento_empresa` no debe presentarse ni reinterpretarse como linking exacto en `4.4`

## Runtime aprobado

### `apps/workers/boe.py`

`_extract_doctrina_refs()` debe dejar de devolver solo `(codigo, numero, confianza)` y pasar a devolver tambien la clase semantica del enlace.

Contrato aprobado para la persistencia:

- patrones explicitos -> `metodo_enlace='auto_link_exact'`, `confianza_enlace=1.0`
- fallback contextual o inferido -> `metodo_enlace='auto_link_heuristic'`, `confianza_enlace` existente (`0.85`, `0.75`, etc.)

`auto_link_doctrina()` debe persistir el metodo exacto o heuristico segun el caso.

Regla de upgrade aprobada:

- si ya existe un enlace heuristico y aparece uno exacto para el mismo `(documento_id, articulo_id)`, el exacto debe reemplazarlo
- si ya existe un exacto, un heuristico no debe degradarlo
- la prioridad deja de ser solo `confianza_enlace`; la semantica exacto vs heuristico debe formar parte de la comparacion de mejora

No se cambia el destino de persistencia (`documento_articulo`) ni se anaden columnas nuevas.

### `apps/workers/borme.py`

`BORME` no gana linking exacto en esta fase.

La fase deja explicito que:

- `documento_empresa.confianza_extraccion` y `nota` siguen representando extraccion heuristica
- las relaciones `principal`, `absorbente`, `absorbida`, etc. siguen siendo utiles, pero no deben confundirse con enlaces exactos derivados de IDs canonicos

Si hace falta una aclaracion pequena en codigo/tests para fijar esta frontera, es valida dentro del slice. No se anade taxonomia nueva a `documento_empresa`.

### `apps/api/routers/doctrina.py`

El detalle de doctrina debe distinguir entre:

- existencia de cualquier enlace (`has_any_anchor`)
- existencia de al menos un enlace exacto (`has_exact_anchor`)

Regla aprobada:

- `has_exact_anchor` deja de depender de `max_confidence >= 0.85`
- `has_exact_anchor` pasa a depender de la presencia de al menos un `metodo_enlace` exacto

Efectos aprobados sobre el runtime y la auditoria:

- `confianza.nivel` alto solo si hay anclaje exacto
- `confidence.score` / `label` del `query_audit` reflejan el mismo criterio
- `verified=true` solo si existe al menos un enlace exacto; con solo enlaces heuristicos debe quedar `false`
- `completeness='completa'` solo si existe al menos un enlace exacto suficiente; con solo enlaces heuristicos o sin enlaces debe quedar `parcial`

La respuesta sigue exponiendo `articulos_relacionados` con `metodo_enlace` y `confianza_enlace`; no se anade un campo nuevo `exacto` en el payload.

### `apps/api/routers/dgt_doctrina.py`

Debe alinearse exactamente con la misma semantica que `doctrina.py` para evitar dos contratos distintos sobre el mismo tipo de linking.

Regla aprobada:

- `has_strong_anchor` deja de ser umbral de confianza
- pasa a ser presencia de al menos un metodo exacto

### `apps/api/services/connectivity.py`

No cambia el shape devuelto.

La ganancia esperada en `4.4` es que `metodo_enlace` ya reflejara si el link es exacto o heuristico, con lo que conectividad dejara de propagar dos clases semanticas distintas como si fueran el mismo tipo de edge.

No se aprueba introducir filtrado nuevo por defecto ni colapsar resultados heuristicos fuera del payload actual.

### `apps/api/services/graph_connectivity.py`

Tampoco cambia el shape del grafo.

La fase solo exige que los properties ya expuestos (`da.metodo_enlace`, `da.confianza_enlace`) salgan ahora con la nueva semantica fiable desde persistencia.

## Estrategia de tests aprobada

La implementacion se hace con TDD.

Casos minimos a fijar:

1. `boe`: un match explicito persiste `auto_link_exact`
2. `boe`: un match contextual persiste `auto_link_heuristic`
3. `boe`: un exacto reemplaza un heuristico previo para el mismo articulo
4. `doctrina`: un detalle con solo enlaces heuristicos no cuenta como anclaje fuerte/verificado
5. `doctrina`: un detalle con enlace exacto si cuenta como anclaje fuerte/verificado
6. `dgt_doctrina`: misma semantica que `doctrina`
7. `connectivity` / `graph_connectivity`: reflejan los nuevos `metodo_enlace` sin romper el shape actual
8. `borme`: las relaciones `documento_empresa` siguen fijadas como heuristicas y no se reinterpretan como exactas

La cobertura puede vivir en:

- `apps/workers/tests/test_boe.py`
- `apps/workers/tests/test_borme.py`
- `apps/api/tests/test_smoke.py`
- `apps/api/tests/test_api_dgt_doctrina.py`
- `apps/api/tests/test_graph_connectivity.py`
- tests nuevos pequenos en API si hiciera falta para el detalle doctrinal

## Fuera de alcance

`4.4` no debe:

- crear una migracion nueva para `link_kind`
- cambiar el shape publico de `doctrina`, `dgt_doctrina`, `connectivity` o `graph_connectivity` con campos nuevos
- generalizar la taxonomia exacto/heuristico a todos los dominios del repo
- reclasificar `modelo_articulo` o tocar `manual_official` de AEAT
- convertir `documento_empresa` de BORME en un sistema de linking exacto
- introducir una taxonomia rica (`manual`, `regex`, `llm`, etc.) mas alla de la separacion minima necesaria del slice

## Riesgos y decisiones explicitas

- la semantica exacto/heuristico seguira viviendo en strings de `metodo_enlace`; se acepta porque evita una migracion nueva y resuelve el hueco real del runtime
- algun test heredado o fixture puede seguir sembrando `auto_link`; si ese fixture representa un enlace exacto u heuristico dentro del scope doctrinal, debe actualizarse para no dejar ambiguedad en la suite
- `BORME` entra en el slice sobre todo para dejar explicitamente fijado que sus relaciones empresa-documento siguen siendo heuristicas
- `query_audit` de doctrina debe alinearse con la nueva semantica; no vale corregir el payload y dejar `verified/completeness` en la logica anterior

## Criterio de cierre

`4.4` se podra cerrar cuando:

- `boe.py` deje de persistir enlaces exactos y heuristicos bajo el mismo `metodo_enlace`
- `doctrina.py` y `dgt_doctrina.py` dejen de tratar un heuristico fuerte como anclaje exacto
- `connectivity.py` y `graph_connectivity.py` propaguen la nueva semantica sin cambiar su shape
- `borme.py` / sus tests dejen explicitamente fijado que `documento_empresa` sigue siendo heuristico
- existan tests rojos->verdes del scope y evidencia fresca del slice
