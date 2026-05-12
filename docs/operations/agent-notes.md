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

### 2026-05-12 - BORME: discovery oficial no debe ser seed-only

- Scope: `apps/workers/borme.py`, `cron-borme-weekly`, tabla `sync_log`.
- Hallazgo: BORME puede descubrir PDFs individuales desde el endpoint oficial `https://www.boe.es/datosabiertos/api/borme/sumario/YYYYMMDD`; depender solo de `BORME_SEED_URLS` deja el corpus minimo y puede hacer que el worker parezca sano aunque no ingiera nada nuevo.
- Impacto: si no hay URLs y el worker sale sin `sync_log`, Prometheus/Hermes solo ven stale/silent worker despues, sin causa operacional clara.
- Regla practica: usar discovery oficial como camino primario, limitar `BORME_DAYS_BACK`/`BORME_MAX_URLS_PER_RUN`, descartar `BORME-S` agregado salvo caso manual, y escribir `sync_log status=partial` cuando no haya URLs. La fuente PDF es oficial, pero la extraccion de empresas/roles sigue siendo heuristica y debe tratarse como `partial/official_best_effort`.

### 2026-05-12 - EUR-Lex deep ingestion debe ir por CELEX allowlist

- Scope: `apps/workers/eurlex.py`, `cron-eurlex-weekly`, `/v1/eurlex`.
- Hallazgo: el patron reutilizable de MCP externos no es copiar corpus ni usar navegador por defecto, sino presupuestar la ingesta por CELEX y degradar con evidencia limitada cuando no hay articulado. En VPS se probo `EURLEX_FETCH_ARTICLES=true`, `EURLEX_ONLY_CELEX=32014L0065`, `EURLEX_MAX_CELEX_PER_RUN=1`.
- Impacto: MiFID II ya expone articulado real (`article_text_available`), pero otros CELEX pueden seguir `metadata_only`; el agente no debe extrapolar cobertura global EUR-Lex.
- Regla practica: cualquier ampliacion EUR-Lex debe anadir CELEXs de forma acotada, revisar `sync_log` (`fetch_errors=0`, `seed_selected=N`) y confirmar `/v1/eurlex/<referencia>` antes de marcar una norma como consultable con texto.

### 2026-05-12 - AEAT PDFs de diseno: parsear solo tablas deterministas

- Scope: `apps/workers/aeat_current_designs.py`, modelos AEAT 1XX/2XX, tabla `modelo_casilla`.
- Hallazgo: los PDFs oficiales AEAT usan al menos dos formatos parseables con seguridad: tabla `Nº/Posic./Lon/Tipo/Descripcion` y tabla `POSICIONES/NATURALEZA/DESCRIPCION`. En algunos PDFs la naturaleza aparece con punto (`Numerico.`), y debe aceptarse. Otros PDFs son esquemas visuales o documentos de ayuda/normativa sin tabla de campos fiable; no deben convertirse en casillas inventadas.
- Impacto: sin parser PDF, muchos modelos con recurso oficial quedaban `casillas_total=0`; con parser demasiado agresivo, se poblarian casillas falsas desde manuales, FAQ o diagramas.
- Regla practica: ampliar el parser solo con patrones oficiales observados y test rojo previo. Si el PDF no tiene filas de diseno deterministas, dejar el modelo como `evidence_limited`/parcial y documentar el residuo.

### 2026-05-06 - Cron semanales en produccion: `--no-deps` en systemd rompe jobs y `WorkerSilent` no puede usar 48h fijo

- Scope: `infra/deploy/systemd/esdata-job@.service`, `infra/observability/alerts.yml`, VPS Compose/productivo
- Hallazgo: si el unit instalado de `esdata-job@.service` deriva y ejecuta `docker compose ... run --rm --no-deps %i`, varios `cron-*` semanales pueden fallar antes de arrancar el worker real con el error `container ... is not connected to the network deploy_esdata-internal`; en ese estado no hay fila nueva en `sync_log` porque el fallo sucede antes del codigo Python.
- Impacto: los cron one-shot quedan rotos aunque los timers `systemd` sigan disparando, y la monitorizacion se vuelve enganosa si `WorkerSilent` se basa en `worker_lag_seconds > 172800` en lugar de usar el contrato real de stale ya calculado por la API.
- Regla practica: el unit instalado debe mantenerse alineado con el repo y ejecutar `docker compose ... run --rm %i` sin `--no-deps`; `WorkerSilent` debe evaluar `worker_stale_status == 1`; y tras cambiar reglas de Prometheus hay que refrescar `/status` antes de validar alertas.

### 2026-05-03 - EUR-Lex: validar seeds contra `resource/celex` RDF antes de asumir que el numero es correcto

- Scope: `apps/workers/eurlex.py`, `EURLEX_NORMAS`, `publications.europa.eu/resource/celex/*`
- Hallazgo: en la curacion de seeds EUR-Lex hay dos trampas distintas. Primera: algunos CELEX simplemente no existen como recurso oficial y `http://publications.europa.eu/resource/celex/<CELEX>` devuelve `404` tambien con `Accept: application/rdf+xml`; ejemplo confirmado: `32021R1689`, que estaba mal sembrado para DAC7 y hubo que corregir a `32021L0514`. Segunda: otros CELEX si existen oficialmente y resuelven RDF (`200`) pero `eur-lex.europa.eu/legal-content/.../TXT/XML/?uri=CELEX:...` puede seguir devolviendo `202` con cuerpo vacio, asi que ese `202` no basta para descartar el CELEX; ejemplo confirmado: `32024L1760` existe y no debe sustituirse por `32024L1619`, que es otra directiva distinta.
- Hallazgo adicional: tras la poda de la seed curada, `EURLEX_NORMAS` queda en `28` CELEX y los `28` responden `200` en `resource/celex` RDF. Los dos casos retirados no eran buenos candidatos para esta seed: `APM_2020_683` apuntaba en realidad a `32020R0683`, que es un reglamento de homologacion y vigilancia de mercado de vehiculos, no un acto de metricas financieras alternativas; `ESG_RATINGS_2023_2819` tampoco existe como reglamento en `resource/celex` y el numero `2023/2819` aparece en el repo asociado a `DAC8` como directiva y en EUR-Lex search como una decision del BCE, no como un reglamento de ESG ratings.
- Impacto: si se corrige una seed solo por intuicion del numero o por un `202` vacio del endpoint `TXT/XML`, es facil sustituir una norma valida por otra distinta o dejar un CELEX inexistente en la seed curada, manteniendo `SKIP ... has no index` silenciosos.
- Regla practica: antes de cambiar un CELEX en `EURLEX_NORMAS`, comprobar primero `resource/celex/<CELEX>` con `Accept: application/rdf+xml`. Si da `404`, el CELEX es candidato a corregirse o salir de la seed. Si da `200`, tratarlo como CELEX valido aunque `TXT/XML` responda `202` vacio; en ese caso revisar titulo/ELI/RDF antes de sustituirlo.

### 2026-05-03 - EUR-Lex en produccion: el HTML publico sigue inutil, pero la consolidacion oficial si sirve con redirects + parser por `eli-subdivision`

- Scope: `apps/workers/eurlex.py`, VPS Compose, `publications.europa.eu`
- Hallazgo: el camino util para EUR-Lex en produccion no es el HTML publico de `eur-lex.europa.eu/legal-content/.../TXT/` sino `legal-content/.../TXT/XML/?uri=CELEX:...` para descubrir la manifestacion y luego `publications.europa.eu/resource/consolidation/...SPA.xhtml` + su item XHTML real. Hay tres traps no obvios: (1) `httpx` debe usar `follow_redirects=True` para los `303` de `publications.europa.eu`; (2) la fecha de vigencia del bloque oficial se tiene que derivar de la URL de consolidacion (`...%2FYYYYMMDD_...SPA.xhtml`) o `upsert_articulo()` rompe con `invalid input syntax for type date: ""`; (3) el XHTML actual encapsula los articulos en `div.eli-subdivision > p.title-article-norm`, asi que buscar solo headings de primer nivel en `body` devuelve `0` bloques aunque el documento sea valido.
- Hallazgo adicional: cuando `legal-content/.../TXT/XML` devuelve `202` vacio para un CELEX que si existe oficialmente, el worker ya no debe quedarse en `SKIP`. El fallback que funciono de verdad fue: consultar `resource/celex/<CELEX>` en RDF, extraer varias candidatas de `resource/consolidation/...`, probarlas en orden hasta encontrar una manifestacion viva, resolver desde ahi el item XHTML real y solo entonces parsear bloques. Elegir una unica manifestacion "mejor" no basta: varias candidatas revisionadas responden `404`, pero una candidata anterior puede seguir siendo valida y devolver articulado util.
- Impacto: sin esos tres ajustes, el worker parece seguir bloqueado por upstream/WAF y deja `0` bloques o crashea en Postgres, aunque la fuente oficial ya este devolviendo RDF/XHTML util.
- Regla practica: para diagnosticar EUR-Lex en VPS, validar el flujo completo dentro del contenedor `cron-eurlex-weekly`: primero `TXT/XML`; si llega vacio o `202`, saltar a `resource/celex/<CELEX>` RDF; de ahi sacar varias candidatas `resource/consolidation/...`; probarlas hasta obtener RDF de manifestacion y item XHTML `DOC_1`; luego exigir `_get_official_consolidation_blocks()` con conteo > 0. Tras este fallback multi-candidato el slice mejoro materialmente: `cron-eurlex-weekly` ya pudo cerrar con `bloques_processed=998`, `articulos_upserted=905`, `rows_processed=998` y la DB quedo con `22` normas EUR-Lex con articulado persistido.

### 2026-05-12 - Repos MCP externos: patrones utiles sin importar datos

- `EU_compliance_MCP` confirma el trap de EUR-Lex: los endpoints publicos pueden devolver desafio AWS WAF en vez de HTML real. Su `ingest-eurlex-browser.ts` usa navegador y valida tamano/contenido; en ESData eso debe ser fallback opt-in, no default, porque el camino preferente sigue siendo Publications Office (`resource/celex` -> `resource/consolidation` -> item XHTML).
- `anamtb/boe-mcp` aporta un patron util para documentos BOE no consolidados: probar legislacion consolidada, caer a `diario_boe/xml.php?id=...`, y solo si el texto es insuficiente extraer PDF. En ESData debe ir separado de `worker-boe` consolidado para no mezclar calidad de fuentes.
- Regla nueva de contrato: una norma EUR-Lex con metadata pero sin articulado no puede devolver `texto=""` sin contexto. API/MCP debe marcar `coverage_status=metadata_only`, `verified=false`, `completeness=parcial` y `evidence_notice` con `evidence_limited`.
- Estado VPS observado en este slice tras despliegues/reset posteriores: `norma.tipo_fuente='eurlex'=32`, pero `articulo=0` y `version_articulo=0`; por tanto S-06 debe reactivar ingesta profunda de forma acotada antes de reclamar corpus EUR-Lex completo.

### 2026-05-03 - EUR-Lex: `sync_log` ya distingue `unchanged`, `no_index` y `fetch_errors` sin falsear fallos

- Scope: `apps/workers/eurlex.py`, tabla `sync_log`
- Hallazgo: antes, un run EUR-Lex con `error_msg` poblado para explicar el estado implicaba `errors=1`, aunque el worker hubiera terminado bien. Eso hacia dificil separar un error real de un run sano con muchos bloques ya idempotentes. Ahora el worker registra un resumen estructurado en `error_msg` incluso cuando el estado es `ok`, pero controla `errors` explicitamente.
- Impacto: `sync_log` ya permite distinguir entre tres situaciones operativas distintas sin leer logs crudos: `unchanged` alto (run sano, poco trabajo nuevo), `no_index` alto (retrieval aun insuficiente para algunos CELEX) y `fetch_errors` > 0 (fallo real del ciclo o de parte del retrieval). Ejemplo fresco en produccion: `cron-eurlex-weekly` -> `status=ok`, `bloques_processed=1625`, `articulos_upserted=2`, `rows_processed=1625`, `errors=0`, `error_msg='summary: unchanged=1623; no_index=0; fetch_errors=0'`.
- Hallazgo adicional: `/status` ya expone este resumen estructurado en `workers.<worker>.sync_summary` cuando `error_msg` sigue el formato `summary: unchanged=X; no_index=Y; fetch_errors=Z`. Si el `error_msg` no sigue ese formato, `sync_summary` queda en `null` y el campo `error` conserva el texto original.
- Hallazgo adicional: `/metrics` ya exporta estos mismos contadores como gauge `worker_sync_summary{worker="...",kind="unchanged|no_index|fetch_errors"}`. Evidencia fresca remota: `worker_sync_summary{kind="unchanged",worker="cron-eurlex-weekly"} 1623.0`, `worker_sync_summary{kind="no_index",worker="cron-eurlex-weekly"} 0.0`, `worker_sync_summary{kind="fetch_errors",worker="cron-eurlex-weekly"} 0.0`.
- Regla practica: al revisar `sync_log` de EUR-Lex, no interpretar `error_msg` como fallo por si solo. La combinacion correcta es: `status` + `errors` + resumen estructurado. Si `status=ok` y `errors=0`, el run es sano aunque `articulos_upserted` sea bajo; usar `unchanged`, `no_index` y `fetch_errors` para entender por que.

### 2026-05-03 - Alertmanager: prueba manual reproducible via `/api/v2/alerts` requiere `--post-file`, no `--post-data=@-`

- Scope: `deploy-alertmanager-1`, Telegram receiver
- Hallazgo: la forma robusta de inyectar una alerta manual en Alertmanager desde shell es escribir primero el JSON a un fichero y luego usar `wget --post-file=/tmp/alert.json http://127.0.0.1:9093/api/v2/alerts`. El intento previo con `--post-data=@-` devolvia `400 Bad Request`; con `--post-file` y un payload minimo como `[ { "labels": { "alertname": "ManualTelegramTest", "severity": "warning" } } ]` el endpoint devuelve `200` y la alerta aparece activa en `/api/v2/alerts`.
- Evidencia: en el VPS quedaron visibles dos alertas activas `ManualTelegramTest` via `GET /api/v2/alerts`, una con `worker=cron-eurlex-weekly` y otra sin `worker`, ambas con receiver `default`. Los logs historicos de Alertmanager ya mostraban `Notify success` para `alertname="ManualTelegramTest"`, por lo que el canal Telegram esta funcional; lo que faltaba era el procedimiento de inyeccion reproducible.
- Regla practica: despues de una prueba manual, resolverla explicitamente posteando el mismo `alertname` con `endsAt` inmediato para no dejar ruido operativo.

### 2026-05-03 - EUR-Lex: limpiar filas obsoletas en DB cuando la seed activa ya no las usa

- Scope: tabla `norma`, fuente `eurlex`
- Hallazgo: tras podar la seed activa, seguian dos filas obsoletas en produccion (`APM_2020_683`, `ESG_RATINGS_2023_2819`) con `0` articulos y `0` versiones. No aportaban cobertura real y ensuciaban la lectura de huecos pendientes.
- Accion: eliminadas de `norma` en produccion. Verificacion fresca: `total_eurlex_normas = 28`, `obsolete_rows = 0`.

### 2026-05-03 - BOE en produccion: advisory lock de sesion requiere `AUTOCOMMIT` y cuidado con `docker compose run --rm`

- Scope: `apps/workers/boe.py`, `infra/deploy/docker-compose.prod.yml`, VPS Compose
- Hallazgo: en Postgres, mantener el advisory lock BOE con `engine.connect()` normal deja una transaccion abierta solo por ejecutar `SELECT pg_try_advisory_lock(...)`; el fix correcto es abrir esa conexion con `execution_options(isolation_level="AUTOCOMMIT")`. Ademas, si un `docker compose run --rm cron-boe-daily` viejo queda colgado, el contenedor oneshot puede seguir vivo y retener lock + sesion DB aunque los contenedores BOE nuevos ya esten desplegados.
- Impacto: el lock evita solapes nuevos, pero un proceso residual puede dejar `BOE sync already in progress` en cascada y falsos `DEADLOCK_RISK` hasta que se limpie ese contenedor viejo.
- Regla practica: si BOE queda bloqueado tras un redeploy, comprobar `docker network inspect deploy_esdata-internal` para mapear la `client_addr` de `pg_stat_activity` al contenedor `deploy-cron-boe-daily-run-*`, pararlo y solo entonces repetir la verificacion. La evidencia buena es doble: `sync_log` con `partial` al solaparse y `pg_stat_activity` en `0 rows` para `state = 'idle in transaction'` tras una ejecucion limpia.

### 2026-05-01 - Despliegue Compose en VPS: traps reales de runtime y Caddy

- Scope: `apps/api/main.py`, `apps/api/Dockerfile`, `infra/deploy/Caddyfile`, `infra/deploy/.env.prod`, despliegue Compose en VPS
- Hallazgo: el despliegue Compose puede parecer correcto (`postgres`, `web`, workers) y aun asi fallar por tres traps no obvios: (1) `apps/api/main.py` asumía `Path(__file__).resolve().parents[2]` y rompia en contenedor (`/app/main.py`) con `IndexError`; (2) la imagen API no incluia `docs/openapi-gpt.json`; (3) `Caddyfile` tenia sintaxis invalida para Caddy v2 (`/api/* { ... }`) y ademas falla en seco si `CADDY_EMAIL` queda vacio.
- Impacto: la API queda `unhealthy`, `caddy` entra en restart loop, HTTPS no responde y el bloqueo parece de DNS/red cuando en realidad es un bug del runtime/proxy.
- Regla practica: al retomar un VPS Compose de este repo, validar en este orden: `docker compose ps`, `docker compose logs api`, `docker compose logs caddy`, `curl http://127.0.0.1:8000/health`, `curl http://127.0.0.1:3000/`. Si `caddy` no levanta, mirar primero `CADDY_EMAIL` y luego validar `Caddyfile` con `docker run --rm -v /srv/esdata/infra/deploy/Caddyfile:/etc/caddy/Caddyfile:ro caddy:2-alpine caddy adapt --config /etc/caddy/Caddyfile`.

### 2026-05-01 - Integracion real: OpenCode usa MCP, ChatGPT usa Actions

- Scope: `docs/integrations/opencode-local-and-vps.md`, `docs/integrations/chatgpt-business-actions.md`, despliegue remoto HTTPS controlado
- Hallazgo: para este stack, `OpenCode` y `ChatGPT` no consumen la misma superficie. `OpenCode` debe conectarse a `https://api.desuscribir.es/mcp` con `MCP_API_KEY`; `ChatGPT` debe importar `https://api.desuscribir.es/gpt-actions/modelos/openapi.json` y autenticar contra los endpoints REST con `ESDATA_API_KEY` en cabecera `X-API-Key`.
- Impacto: si se intenta conectar ChatGPT a `/mcp` o se reutiliza `MCP_API_KEY` en Actions, la integracion falla o mezcla dominios de riesgo.
- Regla practica: recordar siempre este mapeo: `OpenCode -> MCP -> MCP_API_KEY`; `ChatGPT -> OpenAPI/Actions -> ESDATA_API_KEY`. Si el builder de ChatGPT da guerra con OpenAPI 3.1, preparar la variante `docs/openapi-gpt-3.0.json`.

### 2026-05-03 - Handshake MCP HTTP en produccion: 400 inicial esperado

- Scope: `apps/api/mcp_security.py`, `apps/api/tests/test_mcp_private.py`, `https://api.desuscribir.es/mcp`
- Hallazgo: en este stack, el transporte MCP HTTP no se valida con un `POST /mcp` directo. La secuencia correcta es `GET /mcp` con `Accept: text/event-stream` y `X-API-Key`; ese `GET` puede responder `400 Bad Request: Missing session ID` y aun asi incluir `Mcp-Session-Id`. Con ese header, el cliente ya puede hacer `POST /mcp` con `MCP-Session-ID` para `initialize` y `tools/list`.
- Impacto: si se prueba MCP con `Authorization: Bearer ...` o con un `POST` directo sin `MCP-Session-ID`, parece un fallo de auth o de endpoint cuando en realidad el backend esta funcionando segun contrato.
- Regla practica: para verificar MCP remoto, usar siempre `X-API-Key`, no `Authorization`; capturar `Mcp-Session-Id` incluso en respuestas `400`; luego llamar `initialize` y `tools/list` con `MCP-Session-ID`. Si hace falta una prueba rapida, el `GET /mcp` con `400 Missing session ID` mas header de sesion ya cuenta como evidencia de handshake vivo.

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

### 2026-04-30 - DGT: cola persistente con `source_revision` evita crash por idle-in-transaction

- Scope: `apps/workers/dgt.py`, `apps/workers/change_detection.py`, DB Postgres
- Hallazgo: el worker DGT crashaba por `idle-in-transaction-session-timeout` porque toda la fase de discovery + processing corria en una sola transaccion gigante. Cada restart perdía todo el progreso (discovery empezaba desde V0001).
- Solucion: `source_revision` como cola persistente con status `pending`/`processed`. Discovery inserta URLs en DB (1 query inicial para cargar existing_ids en memoria + batch inserts por año). Processing lee batches de 100 con transacciones independientes. Sin crash, idempotente por URL.
- Regla practica: workers de crawling/discovery deben usar tabla como cola persistente, nunca listas en memoria. Pattern: `INSERT ... ON CONFLICT DO NOTHING` para discovery, `SELECT ... WHERE status='pending' LIMIT N` para processing, `UPDATE SET status='done'` tras cada commit.
- Invariantes: nunca `log_sync(None, ...)` sin guard — en `boe.py:log_sync` añadir `if conn is None: return`. `_mark_done` nunca usar `now()` PostgreSQL-only en queries que corren en tests SQLite — siempre parametrizar con `datetime.now(UTC).isoformat()`.
- Estado: worker desplegado, discovery corriendo 2026→2017, 11 documentos DGT ya procesados, 10 URLs en cola procesadas sin crash.
- Proximo paso: ampliar `_extract_target_normas` (dgt.py:147) de solo LIVA/LIS a LIRPF, LGT, LIRNR, LITPAJD, LISD, LIAE. Actualmente filtra ~70% del corpus DGT.

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

### 2026-04-30 - Heartbeat dentro de run_sync marca workers unhealthy

- Scope: `apps/workers/*.py`, `infra/deploy/docker-compose.prod.yml`
- Hallazgo: el healthcheck de Docker requiere `/tmp/worker_heartbeat` con < 300s. Si el heartbeat se toca al FINAL de `run_sync()` (dentro del bucle), un worker que tarda > 300s se marca unhealthy aunque este trabajando. En DGT con discovery de 10 anos, esto ocurria cada ciclo.
- Impacto: Docker marca todos los workers como unhealthy. Si hay `restart: always`, Docker reinicia workers que estan funcionando correctamente.
- Regla practica: el heartbeat debe tocarse al INICIO de cada iteracion del bucle `while True`, fuera de `run_sync()`. Para workers con discovery largo (DGT), el healthcheck threshold debe ser >= tiempo maximo de un ciclo completo (7200s para DGT).

### 2026-04-30 - Advisory lock per-entity_id vs per-worker en change_detection

- Scope: `apps/workers/change_detection.py`, funcion `record_revision()`
- Hallazgo: un lock advisory per-worker (`f"{worker}:source_revision"`) previene deadlocks pero serializa TODAS las escrituras al mismo worker, incluso para entity_ids distintos. Para CNMV (72 docs) o DGT (279+ descubiertos), esto es una serializacion innecesaria.
- Impacto: deadlocks resueltos pero throughput reducido para workers de alto volumen.
- Regla practica: usar lock per-entity_id (`f"{worker}:{tipo}:{entity_id}"`). Solo se serializan escrituras al mismo entity_id, permitiendo paralelismo entre entidades distintas. El deadlock del log fue entre dos conexiones del pool del mismo proceso, no entre workers distintos.

### 2026-04-30 - EUR-Lex SPARQL PREFIXeli typo causa 400 silencioso

- Scope: `apps/workers/eurlex.py`, funcion `_sparql_directives()`
- Hallazgo: la query SPARQL tenia `PREFIXeli:` (sin espacio) en lugar de `PREFIX eli:`. El endpoint `data.europa.eu/sparql` devuelve 400 con error de sintaxis. Este typo estaba ahi desde antes del cambio de endpoint.
- Impacto: SPARQL discovery fallaba con 400 Bad Request, 0 CELEXs nuevos descubiertos. El worker no crashea (exception capturada), asi que el fallo era silencioso.
- Regla practica: validar queries SPARQL contra el endpoint antes de deploy. Un typo de espacio en un PREFIX es invalido y el endpoint lo rechaza con 400, no con un error de parsing en el cliente.

### 2026-04-30 - EUR-Lex API REST bloquea requests automatizados

- Scope: `apps/workers/eurlex.py`, funcion `fetch_index()`
- Hallazgo: EUR-Lex devuelve HTTP 202 con 0 bytes tanto para HTML como para la API REST `rest.tx.legal-acts-index`. El sitio requiere JavaScript rendering. No hay forma de obtener el indice de bloques via API automatizada.
- Impacto: El worker upserta las 30 normas seed correctamente pero 0 bloques/articulos porque el indice de bloques no se puede obtener.
- Regla practica: para EUR-Lex se necesita corpus local de textos completos (archivos `.txt` o `.html` descargados manualmente) como fuente de verdad para los articulos. El SPARQL discovery es un complemento, no la fuente principal.

### 2026-04-30 - docker-compose env var override default value en codigo

- Scope: `infra/deploy/docker-compose.prod.yml`, linea 291 (SPARQL_BASE)
- Hallazgo: el codigo en `eurlex.py` tenia el default correcto (`https://data.europa.eu/sparql`) pero el docker-compose tenia `SPARQL_BASE: ${SPARQL_BASE:-http://publications.europa.eu/webapi/rdf/sparql}`. La variable de entorno en el container override el default del codigo, asi que el fix en el codigo no surtio efecto hasta actualizar el compose.
- Impacto: el worker usaba el endpoint viejo aunque el codigo estuviera corregido.
- Regla practica: cuando un codigo usa `os.getenv("VAR", default_value)`, verificar que el docker-compose no tenga un default value diferente. El compose siempre tiene prioridad sobre el default del codigo.

### 2026-04-30 - Feedback loop auto-correctivo

- Scope: `scripts/feedback_loop.py`, `scripts/auto_test.sh`, `.feedback_loop/`
- Hallazgo: cada sesion de agente pierde el historial de "intento → error → fix". Sin memoria de intentos previos, el agente repite los mismos errores.
- Impacto: cada nueva sesion empieza desde cero, repitiendo bugs ya resueltos en sesiones anteriores.
- Regla practica: antes de empezar una tarea nueva, ejecutar `python3 scripts/feedback_loop.py --show-latest` para ver si hay intentos previos. Durante la tarea, usar `./scripts/auto_test.sh <test_patterns>` para el loop auto-correctivo. El estado se persiste en `.feedback_loop/latest.json` y cada intento en `.feedback_loop/YYYY-MM-DD_HHMMSS_attempt_N.json`.

### 2026-04-30 - Protecciones anti-flaky en auto_test.sh

- Scope: `scripts/auto_test.sh`
- Hallazgo: los feedback loops auto-correctivos son vulnerables a "test hacking" — el agente puede "arreglar" un test flaky suprimiendo aserciones o agregando `@pytest.mark.skip` en lugar de corregir el codigo real. Esto es clasificado por Spotify como el fallo mas peligroso de los loops: pasa CI pero esta funcionalmente roto.
- Impacto: el loop termina verde con tests que ya no prueban nada. El bug sigue en produccion.
- Regla practica: `auto_test.sh` ahora tiene 3 protecciones: (1) `count_assertions()` cuenta asserts por intento, si un intento pasa con menos asserts que el anterior → exit 2 (no retry, revision manual); (2) detecta `@pytest.mark.skip/xfail/flaky` y `@unittest.skip` agregados entre intentos; (3) exit 2 diferenciado del exit 1 (max attempts) para que el agente sepa que es un fallo de integridad. `.feedback_loop/` esta en `.gitignore` porque los JSONs con stdout acumulado crecen rapido.

### 2026-05-01 - Routers fantasma: docs los venden, `main.py` no los monta

- Scope: `apps/api/main.py`, `apps/api/routers/{cnmv,bde,aepd,cendoj}.py`, `apps/api/schemas.py`, `docs/manual-usuario/{03,09}.md`
- Hallazgo: 4 routers verticales existian como ficheros con SQL real contra `documento_interpretativo`, el manual los listaba como endpoints disponibles, y la doc de arquitectura los mencionaba — pero `main.py` no los importaba porque hacian `from .schemas import DocInterpretativoListResponse` y ese symbol no existia en `apps/api/schemas.py`. Resultado: arranque del API ok, contrato documental falso, violacion silenciosa de S-TIER #16 (vender target-state como implementado). Detectado por inspeccion estatica, no por test, porque no hay test que cargue `main.py` y verifique que los prefijos prometidos en docs estan montados.
- Impacto: cualquier cliente que siguiese el manual recibia 404 en `/v1/{cnmv,bde,aepd,cendoj}/*`. La trampa es invisible si solo se mira `main.py` (los imports comentados/ausentes parecen intencionales) o solo el router (compila aislado pero falla al importarse).
- Regla practica: cuando el manual de usuario o `repository-structure.md` listen un prefijo `/v1/<dominio>`, validar en una sola pasada: (1) `grep -n "router" apps/api/main.py` confirma `include_router` para ese prefijo; (2) `python -c "from apps.api.main import app; print([r.path for r in app.router.routes])"` lista todas las rutas reales; (3) si falla import, leer el traceback completo — suele ser un schema faltante en `apps/api/schemas.py`, no un bug del router. Antes de cerrar cualquier sprint que toque routers, ejecutar el paso (2) y diff contra el listado del manual; cualquier divergencia = router fantasma o doc desactualizada.

### 2026-05-12 - `sync_log` productivo y SSH stdin

- Scope: VPS Docker Compose, `sync_log`, scripts Ralph ejecutados por SSH.
- Hallazgo: el esquema productivo de `sync_log` usa `finished_at`, no `ended_at`. Las consultas de frescura deben usar `COALESCE(finished_at, started_at)`.
- Impacto: una verificacion con `ended_at` falla aunque la telemetria este sana, generando falso negativo en auditorias de cron/workers.
- Regla practica: en scripts remotos que se pasan por `ssh ... "bash -s"`, cualquier `docker compose exec -T ...` debe terminar con `< /dev/null`; si no, Compose puede consumir el resto del script desde stdin y truncar la evidencia. Para scripts largos, generar un fichero LF temporal, copiarlo por `scp` y ejecutarlo con `bash`.
