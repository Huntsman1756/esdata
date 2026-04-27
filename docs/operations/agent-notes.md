# Agent Notes

## Objetivo

Este archivo acumula memoria operativa pequena y reutilizable para agentes futuros.

No guarda estado activo del proyecto. Para estado actual, riesgos vivos y siguiente paso, la fuente sigue siendo `../master-execution-roadmap.md`.

Aqui solo deben entrar hallazgos que ahorran tiempo o evitan regresiones porque no son obvios al leer solo el codigo.

## Cuando actualizarlo

- cuando un fix descubre una restriccion no evidente del repo
- cuando un test falla por una trampa recurrente de fixtures, imports o contratos
- cuando un modulo requiere una precaucion concreta para no romper otros tests
- cuando un endpoint debe degradar de forma especial en entornos de prueba o desarrollo

## Lo que no debe ir aqui

- estado de fase o siguiente paso
- handoffs largos o narrativos
- decisiones de producto para usuarios
- runbooks completos de operacion repetible

## Formato recomendado

Usar notas cortas con este esquema:

- Scope: modulo, test o endpoint afectado
- Hallazgo: que se aprendio
- Impacto: que se rompe o que error aparece si se ignora
- Regla practica: que debe hacer el siguiente agente

## Notas actuales

### 2026-04-27 - Drift de HTML AEAT en modelos

- Scope: `apps/workers/modelos.py`, `apps/workers/modelos_support.py`, `apps/workers/tests/test_modelos.py`
- Hallazgo: el worker de modelos puede detectar una campana nueva y scrapea casillas/claves/instrucciones desde HTML AEAT, pero si AEAT cambia la estructura del HTML una campana nueva puede devolver `0` casillas aunque el modelo tuviera casillas validas en campanas previas.
- Impacto: sin guardrail explicito, el fallo parece un sync "correcto" pero deja la campana nueva sin contenido util y el problema solo aparece despues en runtime cuando una consulta por casilla devuelve vacio sin contexto.
- Regla practica: cuando una campana nueva devuelve `0` casillas y el modelo ya tenia casillas historicas, tratarlo como `DRIFT_AEAT`, registrar error explicito y no considerar la extraccion como sync sano hasta revisar manualmente el HTML de AEAT.

### 2026-04-26 - Integration tests API

- Scope: `apps/api/tests/test_integration.py`, `apps/api/tests/conftest.py`
- Hallazgo: la suite de integration debe reutilizar la SQLite compartida que `conftest.py` inicializa al importarse. Recrear `STATEMENTS` o `PGC_SCHEMA_STATEMENTS` encima del mismo `engine` provoca errores tipo `table norma already exists`.
- Impacto: el archivo puede fallar entero en setup aunque el runtime este bien.
- Regla practica: en tests de integration de `apps/api/tests`, preferir reutilizar `engine` y fixtures compartidas de `conftest.py` antes de bootstrappear esquema propio.

### 2026-04-26 - Chunks en SQLite de tests

- Scope: `apps/api/routers/chunks.py`
- Hallazgo: no todas las SQLite de tests crean tablas de chunks (`documento_fragmento`, `documento_seccion`).
- Impacto: consultar `/v1/chunks/{id}` en esos entornos puede lanzar `500` por `no such table` si el router asume que el schema existe siempre.
- Regla practica: cuando el entorno de test no carga el schema de chunks, el endpoint debe degradar a `404` y no romper la suite con error interno.

### 2026-04-26 - Tests heredados vs contrato actual

- Scope: `apps/api/tests/test_integration.py`, `apps/api/routers/legislacion.py`, contratos Pydantic en `apps/api/schemas.py`
- Hallazgo: parte de la deuda actual viene de tests que seguian esperando payloads o campos antiguos en lugar del contrato expuesto hoy.
- Impacto: es facil tocar runtime correcto para satisfacer asserts viejos y abrir regresiones en otras rutas.
- Regla practica: ante un test rojo, comprobar primero el contrato actual del endpoint y los schemas antes de cambiar runtime. Si el endpoint y el schema estan alineados, ajustar el test heredado.

### 2026-04-27 - Grounding gate en consulta

- Scope: `apps/api/routers/consulta.py`, `apps/api/tests/test_reranker.py`
- Hallazgo: el falso positivo mas peligroso no estaba en `normalize_rerank_score()` sino en una excepcion de gating que dejaba pasar consultas con solo resultados de tipo `modelo`.
- Impacto: queries fuera de corpus como `normativa fiscal de Marte` podian devolver modelos espurios aunque el reranker diera scores normalizados muy bajos.
- Regla practica: en `GET /v1/consulta`, no usar la presencia de sugerencias `modelo` como sustituto de grounding factual; si el mejor `rerank_score` normalizado queda bajo el umbral, la respuesta debe abstenerse aunque existan matches heuristicas.

### 2026-04-27 - Faithfulness en consulta

- Scope: `apps/api/services/faithfulness.py`, `apps/api/routers/consulta.py`, `apps/api/tests/test_faithfulness.py`
- Hallazgo: el `faithfulness_score` inline original era demasiado plano porque media heuristicas de evidencia y relevancia, no contraste real entre respuesta y chunks.
- Impacto: respuestas malas podian quedar cerca de respuestas buenas en el score y debilitar la segunda puerta de seguridad de `consulta`.
- Regla practica: validar cualquier cambio en `faithfulness_score` con tests directos de pares bueno/inventado. No basta con mirar solo smokes del endpoint; tiene que existir una prueba donde el scorer distinga explicitamente entre una respuesta anclada y otra inventada.

### 2026-04-27 - Fallback BOE sin `documento_fragmento`

- Scope: `apps/api/services/search.py`, `apps/api/routers/consulta.py`, `apps/api/tests/test_search_legislacion.py`, `apps/api/tests/test_reranker.py`
- Hallazgo: cuando la DB Postgres solo tiene `version_articulo`, el retrieval puede ser correcto pero el reranker castiga el articulo completo con scores negativos; si `consulta.py` exige superar `GROUNDING_THRESHOLD` sin considerar que la evidencia oficial sigue siendo fuerte, vacia falsamente consultas validas como `plazo prescripción LGT`.
- Impacto: `/v1/consulta` puede responder `total_resultados=0` aunque `search_legislacion()` ya haya recuperado articulos oficiales BOE con `faithfulness_score=1.0`.
- Regla practica: en el fallback sin chunks finos, no usar el `rerank_score` como unica puerta. Si el resultado normativo viene con `source_url` + `source_hash` oficiales, sin `chunk_id`, y mantiene `faithfulness_score` alto, la respuesta debe conservarse.

### 2026-04-27 - Lifecycle de `/mcp` en tests HTTP

- Scope: `apps/api/mcp_server.py`, `apps/api/main.py`, `apps/api/tests/test_mcp_contract.py`
- Hallazgo: `ASGITransport(app=app)` contra el `app` global puede ejecutar `GET /mcp` sin haber inicializado el `task_group` interno de `fastapi-mcp`; el resultado visible era un `500` con `RuntimeError: Task group is not initialized`.
- Impacto: probes HTTP o tests de contrato sobre `/mcp` podian romper antes de llegar al contrato real del transporte, aunque el flujo con `lifespan_context` si funcionara.
- Regla practica: en `/mcp`, un `GET` sin `Accept: text/event-stream` debe cortocircuitarse a `406` antes de tocar el session manager. El arranque lazy del manager tambien debe esperar a que el `task_group` exista realmente antes de delegar la request.

### 2026-04-27 - Carga minima de `LIS` para `IS`

- Scope: `apps/workers/boe.py`, DB Postgres local BOE, `/v1/consulta`
- Hallazgo: la query `deducción gastos representación IS` queda resuelta con una carga minima de `LIS` sobre `a14,a15,a16`; no hace falta indexar la norma completa para desbloquear este caso.
- Impacto: el fallback sobre `version_articulo` ya responde con grounding suficiente (`faithfulness_score=1.0`) y deja de abstener donde antes faltaba corpus.
- Regla practica: para queries quirurgicas de `IS`, cargar primero `a14,a15,a16`. `art. 15` es la referencia clave para atenciones a clientes/proveedores; `art. 16` suele subir mas por solape lexical con `deducción` y `gastos financieros`, asi que no asumir que el top-1 semantico coincide siempre con el articulo juridicamente principal.

### 2026-04-27 - Alembic: validacion segura antes de tocar la DB local

- Scope: `alembic/env.py`, `alembic/versions/*.py`, DB Postgres local, DB desechable `pg_test`
- Hallazgo: la cadena Alembic de este repo no debe ejecutarse primero sobre la DB local con datos reales. La secuencia segura es: auditar por familias de error, validar `upgrade head` en una DB desechable limpia (`pg_test` en `127.0.0.1:54330`), y solo entonces aplicar `stamp` + `upgrade` sobre la DB local.
- Impacto: ejecutar migraciones directamente sobre la DB local puede mezclar bugs de migracion con datos reales (`LGT`, `LIVA`, `LIS`) y dejar el entorno en un estado ambiguo o parcialmente migrado.
- Regla practica: antes de cualquier `upgrade` local, exigir estas pruebas frescas: `pytest apps/api/tests/test_alembic_integrity.py -q`, `alembic heads` con head unico, y `alembic upgrade head` completo en desechable.

### 2026-04-27 - Alembic: traps tecnicos ya confirmados

- Scope: `alembic/versions/20260425_0006_eval_history.py`, `20260425_0009_workflow_cases.py`, `20260426_0012_screening.py`, `20260426_0016_editorial_internal.py`, `20260426_0017_playbooks_evidencia.py`, `alembic/env.py`
- Hallazgo: los errores recurrentes no son aleatorios; se repiten por familia: imports Alembic invalidos, `op.exec_driver_sql`, `server_default=sa.func.*`, revisiones largas que rompen `alembic_version VARCHAR(32)`, y seeds SQL convertidos a `INSERT ... SELECT` con escaping roto o `WHERE EXISTS/NOT EXISTS` mal colocado.
- Impacto: si no se corrigen por lotes, el trabajo cae en bucle de error -> parche -> rerun -> siguiente error casi identico.
- Regla practica: al retomar este slice, revisar primero `20260426_0016_editorial_internal.py` y `20260426_0017_playbooks_evidencia.py` por comillas dobles `''...''` y seeds multilinea antes del siguiente rerun desechable. Para este repo, `sa.func.now()` y `sa.func.current_date` en migraciones deben tratarse como bugs potenciales y convertirse a `sa.text("NOW()")` / `sa.text("CURRENT_DATE")`.
