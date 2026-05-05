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

### 2026-05-05 - Cron one-shot en Compose: `run --rm` sin `--no-deps` puede romper el stack vivo

- Scope: `infra/deploy/systemd/esdata-job@.service`, `infra/deploy/docker-compose.prod.yml`, Alertmanager `WorkerSilent`
- Hallazgo: lanzar `cron-*` one-shot con `docker compose run --rm` desde `systemd` puede intentar gestionar dependencias/profile del proyecto y acabar parando `postgres` o tocando `deploy_esdata-internal`, dejando fallos reales en `cron-boe-daily` y `cron-modelos-daily` aunque el stack continuo siga vivo. El fix minimo es doble: (1) `run --rm --no-deps` para no tocar dependencias del stack; y (2) declarar `networks: [esdata-internal]` en cada `cron-*` DB-backed para que el contenedor one-shot siga resolviendo `postgres` por DNS aun con `--no-deps`. Al mismo tiempo, `WorkerSilent` con un umbral fijo de `48h` produce falsos positivos en jobs `weekly` aunque `/status` y `worker_stale_status` ya usan thresholds por worker de hasta `8 dias`.
- Impacto: Telegram mezcla ruido de `weekly` sanos con incidentes reales de `daily`, y el scheduler host puede romper jobs one-shot al interferir con la red Compose compartida.
- Regla practica: para `cron-*` en produccion, usar `docker compose run --rm --no-deps <cron-service>`, verificar que el servicio declara `networks: [esdata-internal]` cuando necesita `postgres` por nombre, y alinear Alertmanager con `worker_stale_status` en vez de recalcular un `lag_seconds` global fijo.

### 2026-05-05 - Deploy canonico: el worker set debe derivarse del Compose activo, no de una lista historica

- Scope: `infra/deploy/docker-compose.prod.yml`, `scripts/ops/deploy-hetzner.sh`, runbooks de deploy, `infra/deploy/systemd/esdata-job@.service`
- Hallazgo: cuando el Compose activo gana workers continuos nuevos, el deploy canonico y los runbooks pueden quedarse congelados en una lista historica parcial y dejar parte del corpus fuera del runtime real aunque los servicios existan en el repo.
- Impacto: el equipo cree que produccion ejecuta todo el scope continuo, pero algunos workers nunca se levantan tras deploy; ademas, los chequeos manuales y el scheduler pueden romperse si cada artefacto usa un root distinto del repo.
- Regla practica: tratar `infra/deploy/docker-compose.prod.yml` como fuente de verdad del worker set continuo (`worker-*` sin `profiles`) y fijar regresiones que comparen contra el comando canonico de deploy. Mantener tambien una sola raiz operativa del repo en docs activas y `systemd` (`/opt/esdata` en este slice).

### 2026-05-05 - Variables de entorno: separar runtime deploy de code-only y legacy

- Scope: `infra/deploy/docker-compose.prod.yml`, `infra/deploy/compose.env.example`, `.env.example`, `docs/environment-variables.md`, deploy docs activas
- Hallazgo: mezclar en un mismo inventario variables del deploy activo, variables solo de codigo/tests y restos historicos crea falsas suposiciones operativas y puede dejar controles de seguridad "documentados" que el runtime no aplica de verdad.
- Impacto: un operador puede creer que una variable no cableada forma parte del deploy Compose activo, o confiar en una env var inexistente para proteger una superficie real como `/metrics`.
- Regla practica: tratar `infra/deploy/docker-compose.prod.yml` como fuente unica del `runtime deploy`; `infra/deploy/compose.env.example` como plantilla exacta de ese boundary; y cualquier inventario amplio (`.env.example`, docs de variables, runbooks) debe explicitar si una variable es `code-only` o `legacy/no cableada` antes de sugerirla como control operativo.

### 2026-05-05 - Secretos de deploy: el fichero runtime vive fuera del checkout

- Scope: `scripts/ops/deploy-hetzner.sh`, `scripts/ops/backup-postgres.sh`, `infra/deploy/docker-compose.prod.yml`, `infra/deploy/systemd/esdata-job@.service`, runbooks activos de deploy/ops
- Hallazgo: aunque Git ignore `.env.*`, seguir usando `infra/deploy/.env.prod` como path operativo deja los secretos reales dentro de `/opt/esdata` y reabre el riesgo de tratarlos como parte normal del repo o de copiar plantillas/renderizados sensibles por error durante handoffs y tareas manuales.
- Impacto: el equipo puede creer que "fuera de Git" equivale a "fuera del repo", cuando el runtime secreto sigue residiendo dentro del checkout productivo y varios artefactos operativos lo refuerzan como convencion canonica.
- Regla practica: para el deploy Compose activo, versionar solo `infra/deploy/compose.env.example` y cargar siempre el runtime real desde `/etc/esdata/esdata.env`. Si un script, unit file o runbook sigue apuntando a `infra/deploy/.env.prod`, tratarlo como drift operativo y corregirlo en el mismo slice.

### 2026-05-05 - verify_schema debe seguir dependencias reales de runtime, no solo columnas nuevas visibles

- Scope: `scripts/maintenance/verify_schema.py`, deploy Compose con contenedor `ops`
- Hallazgo: un gate de esquema basado solo en columnas "obvias" puede seguir dando verde aunque falten claves estructurales que el runtime usa implicitamente, como identificadores auditables, timestamps de ordenacion o unicidad necesaria para `ON CONFLICT`.
- Impacto: el deploy puede parecer sano mientras rompe inserciones de auditoria o colas persistentes una vez que el runtime escribe datos reales.
- Regla practica: cuando un flujo runtime depende de `INSERT`/`SELECT` sobre columnas concretas o de una unicidad contractual (`ON CONFLICT`, ordering persistente, IDs estables), el gate de deploy debe modelar tambien esas dependencias, aunque la fase siga evitando una auditoria estructural completa.

### 2026-05-05 - Deploy canonico: migrar y verificar antes de levantar servicios

- Scope: `scripts/ops/deploy-hetzner.sh`, `.github/workflows/deploy-hetzner.yml`, runbooks de deploy Compose
- Hallazgo: si el deploy valida esquema pero no ejecuta `alembic upgrade head`, el stack puede arrancar con codigo nuevo sobre esquema viejo y fallar de forma parcial o enganosa.
- Impacto: API, workers y checks posteriores pueden parecer sanos aunque falten tablas/columnas requeridas por la revision desplegada.
- Regla practica: en despliegue Docker Compose, tratar `bash scripts/ops/deploy-hetzner.sh` como ruta canonica y exigir siempre este orden: `config`, `build ops`, `up postgres`, `alembic upgrade head`, `verify_schema.py`, y solo despues levantar servicios de aplicacion.

### 2026-05-04 - Fase 4.5 vocabulary validation: validar en el write boundary, no solo en el parser

- Scope: `apps/workers/vocabulary_validation.py`, `upsert_documento_interpretativo(...)` en workers, `apps/workers/vocabulary.py`
- Hallazgo: un vocabulario controlado no esta realmente activo mientras los workers puedan saltarselo con literales en SQL o payloads sin sanear.
- Impacto: comprobar solo `build_document_payload(...)` o helpers de deteccion no garantiza que la DB reciba valores permitidos; la validacion real tiene que vivir justo antes del `INSERT ... ON CONFLICT`.
- Regla practica: dejar que el parser/build use taxonomias locales si ayuda a la extraccion, pero normalizar siempre el `record` final en el boundary de escritura hacia valores ya permitidos por `VOCABULARY`.

### 2026-05-04 - Fase 4.4 link semantics: exacto no significa solo "alta confianza"

- Scope: `documento_articulo.metodo_enlace`, `apps/api/routers/doctrina.py`, `apps/api/routers/dgt_doctrina.py`, `apps/api/services/graph_connectivity.py`, `documento_empresa`
- Hallazgo: un `confianza_enlace` alto no convierte una inferencia contextual en enlace exacto. En este repo, exacto significa referencia canonica explicita suficiente para resolver norma/articulo sin inferencia adicional, y hoy eso solo ocurre con `manual`, `manual_official` o `auto_link_exact`. `documento_empresa` en BORME sigue siendo extraccion heuristica, no anclaje canonico.
- Impacto: si los readers/promociones usan umbral de confianza en vez de `metodo_enlace`, `doctrina` y `dgt_doctrina` pueden marcar `verified/completa` de forma enganosa y la conectividad puede propagar semantica falsa. Si se trata `documento_empresa` como exacto, se sobrevende una relacion societaria extraida por heuristica.
- Regla practica: decidir strong anchors, `verified` y `completeness` solo por presencia de metodos exactos; propagar `da.metodo_enlace` y `da.confianza_enlace` sin cambiar el shape publico; y mantener `documento_empresa` como heuristico hasta que exista un contrato exacto explicito para esa tabla.

### 2026-05-04 - Fase 4.3 row-quality: completeness/provenance vive en la tabla duena de la fila

- Scope: `modelo_recurso`, `documento_interpretativo`, `source_revision`, `sync_log`, `source_manifest`
- Hallazgo: status de sync, revision por hash y row-quality son contratos distintos. Si se mezclan, ops/API/retrieval pueden sobreinterpretar la calidad real de una fila o de un run.
- Impacto: meter completeness/provenance en `source_revision` o inferirla solo desde `sync_log` hace que una revision tecnica o un resultado de run parezcan garantia de calidad por fila cuando no lo son.
- Regla practica: guardar `row_completeness` / `row_provenance` en la tabla que posee la fila persistida; reservar `source_revision` para cambios tecnicos y `sync_log` para outcomes del run. `source_manifest` debe seguir source-level hasta que exista un slice explicito de agregacion row-level.

### 2026-05-04 - Fase 4.2 workers: `partial` solo cuando el run termina con huecos concluidos

- Scope: `apps/workers/runtime.py`, `apps/workers/aeat_models.py`, `apps/workers/cnmv.py`, `apps/workers/dgt.py`
- Hallazgo: mezclar faltantes reales, documentos fuera de target y errores transitorios/reintentables en un mismo contador rompe la semantica de `sync_log.status`. `partial` debe significar "run terminado con huecos reales", no "hubo cualquier skip o retry".
- Impacto: si cualquier excepcion o documento descartado cuenta como faltante, ops/API/MCP pueden interpretar cobertura parcial donde en realidad la cola quedo pendiente o el documento era irrelevante para la fuente.
- Regla practica: usar `finalize_partial_sync_status(...)` solo al cierre del run y pasarle un contador de faltantes concluidos. AEAT/CNMV: contar solo fetch/download failures reales de recursos oficiales/documentos. DGT: contar `search` sin resultados como faltante, no contar documentos fuera de target y no degradar a `partial` por errores transitorios que dejan `dgt_queue` pendiente para retry.

### 2026-05-04 - Fase 4.1 DGT: `source_revision` no debe cargar estado de cola

- Scope: `apps/workers/dgt.py`, `apps/workers/change_detection.py`, `alembic/versions/20260504_0057_dgt_queue_split.py`
- Hallazgo: cuando DGT usa `source_revision.content_hash_sha256` para guardar `pending` o `empty`, rompe el contrato compartido de change detection porque esa columna deja de significar hash real.
- Impacto: `check_content_changed()` puede leer una fila de cola como si fuera revision valida y el corpus aparenta tener una semantica de revision que ya no es cierta.
- Regla practica: cualquier cola persistente nueva o legacy debe vivir fuera de `source_revision`; esa tabla solo admite revisiones reales. Para DGT, usar `dgt_queue` para `pending/processed/empty` y reservar `source_revision` para hashes SHA-256 reales.

### 2026-05-04 - Fase 3.4 modelos: separar chequeos estaticos de drift persistido

- Scope: `scripts/maintenance/check_model_data_quality.py`, `.github/workflows/ci.yml`, tablas `aeat_modelo` / `modelo_*`
- Hallazgo: los problemas peligrosos de `modelos` viven tanto en archivos fuente/seed como en filas ya persistidas en DB.
- Impacto: comprobar solo una de las dos superficies deja fuera la mitad del problema.
- Regla practica: para quality gates de `modelos`, ejecutar siempre chequeos estaticos de seeds/scripts y chequeos DB-backed del contrato persistido actual.

### 2026-05-03 - MCP trust: el riesgo principal no es una sola respuesta mala, sino huecos entre datos, contrato MCP y audit trail

- Scope: `apps/api/*`, `apps/workers/*`, `docs/manual-usuario/*`, `docs/reference/mcp-remediation-plan.md`
- Hallazgo: el repo tiene buena base de grounding, workers y auditoria, pero una respuesta MCP puede seguir siendo peligrosamente segura si se juntan tres cosas: metadata/modelos parciales, surfaces MCP HTTP vs stdio no alineadas, y endpoints/tool calls sin audit E2E completo. El fallo real es de cadena de confianza, no de una sola capa.
- Impacto: un modelo o agente externo puede convertir datos parciales o curados en una conclusion operativa aparentemente verificada. Eso afecta especialmente a `modelos AEAT`, `consulta_fiscal/agente_consulta`, y a cualquier tool que no persista `request_id + fuentes + grounding_status + completitud`.
- Regla practica: antes de corregir prompts o tocar docs, comprobar siempre estas cuatro preguntas: (1) la tool existe en la superficie MCP que usa el cliente real? (2) deja audit trail E2E? (3) la respuesta distingue oficial/curado/heuristico/no verificado? (4) el corpus o modelo tiene bandera de completitud suficiente para una conclusion operativa?

### 2026-05-03 - Fase 1.1 HTTP MCP: no depender de inferencia por path cuando el endpoint ya conoce su operation_id

- Scope: `apps/api/routers/buscar.py`, `apps/api/routers/legislacion.py`, `apps/api/routers/doctrina.py`, `apps/api/routers/modelos.py`, `services/query_audit.py`
- Hallazgo: para la superficie HTTP MCP prioritaria, confiar solo en `infer_query_audit_tool_name(path)` es fragil porque varios endpoints reales incluyen parametros dinamicos en la ruta y otros comparten prefijo pero no operation_id. El hook mas robusto es pasar `tool_name` explicito desde cada handler cuando ese endpoint forma parte del catalogo MCP.
- Impacto: sin `tool_name` explicito, una entrada puede persistirse con nombre derivado del ultimo segmento de la URL o no persistirse en absoluto si el handler nunca llama a `record_query()`, rompiendo la reconstruccion E2E por tool.
- Regla practica: en rutas HTTP que representen operation_ids MCP reales, llamar siempre a `get_query_audit_service().record_query(...)` desde el handler y pasar `tool_name` explicito junto con `path`, `query_text`, `sources/confidence`, `completeness` y `verified`.

### 2026-05-03 - `doctrina/buscar` con `include_boe=true` puede romper filtros semanticos heredados

- Scope: `apps/api/routers/doctrina.py`, `apps/api/tests/test_smoke.py::test_doctrina_buscar_filtra_por_tipo`
- Hallazgo: el buscador de doctrina puede extender resultados con `_buscar_normas_boe(db, q)` cuando `include_boe=true` y no se restringe `organismo_emisor`. Eso hace que una query filtrada por `tipo` doctrinal siga incluyendo normas BOE relacionadas y rompa asserts heredados que esperan homogeneidad total por `tipo_documento`.
- Impacto: algunas smokes antiguas sobre filtrado por `tipo` fallan aunque el nuevo audit trail y el endpoint principal sigan funcionando; no debe confundirse con una regresion del slice de auditoria MCP.
- Regla practica: si aparece un rojo en `test_doctrina_buscar_filtra_por_tipo`, revisar primero la mezcla `doctrina + BOE` del endpoint antes de tocar el audit trail. Es deuda funcional separada de la Fase 1.1.

### 2026-05-03 - Fase 1.2 stdio MCP: la fila auditable debe nacer en `tools/call`, no como post-log sintetico aislado

- Scope: `apps/api/mcp_stdio.py`, `apps/api/tests/test_mcp_stdio_audit.py`
- Hallazgo: el patron anterior de `stdio` registraba una segunda fila con `request_id` aleatorio, `retrieved_chunks=[]` fijo y `except Exception: pass`. Eso rompia la correlacion E2E con el endpoint REST real y permitia responder con exito aunque la auditoria stdio no hubiera quedado persistida.
- Impacto: un cliente local podia ver una respuesta correcta en texto pero sin rastro reconstruible por `request_id`, o peor, con una huella negativa artificial que ocultaba el grounding y las fuentes reales del runtime.
- Regla practica: en `stdio`, generar el `request_id` al entrar en `tools/call`, inyectarlo en todos los subrequests internos (`x-request-id`, `x-user-id`) y persistir la fila `/mcp/tools/<tool_name>` reutilizando la entrada HTTP correlada cuando exista. Si esa persistencia falla, devolver `-32603` y no emitir la respuesta bufferizada como si todo hubiera salido bien.

### 2026-05-03 - Fase 1.3 query-audit: verificar contra runtime real, no solo contra fixtures manuales

- Scope: `apps/api/routers/query_audit.py`, `apps/api/tests/test_query_audit_http.py`
- Hallazgo: el contrato de `/v1/ai/query-audit` ya exponia `grounding_status`, `prompt_injection_detected`, `grounding_summary`, `completeness` y `verified`, pero la cobertura HTTP solo demostraba esos campos con entradas manuales creadas via `record_query()`. Faltaba fijar que tambien salen bien cuando la fila nace del runtime real de `/v1/consulta`.
- Impacto: sin esa cobertura, una futura regresion en serializacion o mapping del router podia pasar desapercibida aunque el schema siguiera aceptando los campos y los tests unitarios del servicio siguieran verdes.
- Regla practica: cuando el roadmap pida "exponer" un campo ya presente en router/schema, no asumir que no hay trabajo. Añadir al menos un test HTTP o E2E que pruebe el dato sobre una fila producida por runtime real, no solo por fixtures o inserts manuales.

### 2026-05-03 - Fase 1.4 query-audit: persistir el payload exacto del cliente, no una variante paralela

- Scope: `apps/api/services/query_audit.py`, `apps/api/routers/consulta.py`, `apps/api/mcp_stdio.py`, `alembic/versions/20260503_0055_query_audit_response_payload.py`
- Hallazgo: para reconstruir de verdad lo que vio el usuario, `query_audit` no debe guardar solo un resumen ni un payload reinterpretado. En `/v1/consulta` el dato correcto es el `ConsultaFiscalResponse` final serializado tal como sale al cliente; en `stdio` el dato correcto es el payload JSON-RPC final bufferizado (`result` o `error`) que se emite por `tools/call`.
- Impacto: si se persiste una variante ad hoc, la auditoria puede seguir siendo incompleta aunque exista una columna nueva, porque la reconstruccion no coincide exactamente con la respuesta entregada.
- Regla practica: cuando un slice pida persistir la respuesta final, reutilizar el response model o payload ya construido para la salida real y persistir ese mismo objeto serializado. Si la suite API en Windows usa `apps/api/tests/conftest.py`, verificar siempre en secuencial para evitar `WinError 32` del SQLite compartido.

### 2026-05-03 - Fase 2.1 DB lifecycle: `next(get_db())` fuera de DI oculta sesiones cerradas hasta que el cierre se vuelve terminal

- Scope: `apps/api/db.py`, `apps/api/routers/consulta.py`, `apps/api/routers/legislacion.py`, `apps/api/routers/jurisprudencia.py`, `apps/api/tests/test_db.py`, `apps/api/tests/test_reranker.py`
- Hallazgo: con la configuracion por defecto de SQLAlchemy, `Session.close()` puede reabrirse silenciosamente y esconder reusos invalidos de sesiones fuera de contexto. Al fijar `SessionLocal(... close_resets_only=False)`, la sesion cerrada pasa a ser terminal y aflora el patron roto: abrir DB con `db = next(get_db())` fuera del ciclo de dependencias de FastAPI o seguir usando `db` tras salir de `with db_session() as db:`.
- Impacto: rutas o bloques tardios pueden parecer sanos en tests o runtime aunque esten usando una sesion ya cerrada; cuando el cierre se endurece, el fallo real emerge como `InvalidRequestError: This Session has been permanently closed and is unable to handle any more transaction requests.`
- Regla practica: fuera de `Depends(get_db)`, no usar `next(get_db())`. Abrir una sesion nueva con `with db_session() as db:` por cada bloque vivo que realmente consulte la DB. Si una ruta necesita una consulta tardia adicional, reabrir otra sesion para ese bloque en vez de reciclar la anterior.

### 2026-05-03 - MCP audit/modelos: un `200` vacio tambien debe dejar rastro E2E si la request fue valida

- Scope: `apps/api/routers/modelos.py`, `apps/api/tests/test_http_mcp_audit_phase_1_1.py`
- Hallazgo: en `get_modelo_casillas`, `get_modelo_claves` y `get_modelo_instrucciones`, una campaña inexistente de un modelo valido devolvia `200` con lista vacia pero sin pasar por `_record_modelo_query_audit(...)`.
- Impacto: la auditoria HTTP MCP quedaba rota precisamente en un caso valido y frecuente de cobertura parcial (`campana` no publicada o no disponible), aunque la respuesta al cliente fuese correcta.
- Regla practica: si un endpoint MCP devuelve `200`, debe registrar `query_audit` tambien cuando el payload sea vacio. El unico caso que no debe registrar como exito es el `404`/error de request invalida.

### 2026-05-03 - Query audit MCP: no dejar que el contrato nuevo dependa solo de `ALTER TABLE` runtime

- Scope: `alembic/versions/20260503_0055_query_audit_response_payload.py`, `apps/api/services/query_audit.py`, `apps/api/tests/test_alembic_integrity.py`
- Hallazgo: el contrato MCP anadido en Fase 0.2 (`tool_name`, `sources`, `confidence`, `completeness`, `verified`) habia quedado soportado en SQLite/runtime por reparacion dinamica, pero no por la nueva migracion Alembic 0055. Ademas, el singleton eager `_service = QueryAuditService()` disparaba `ensure_governance_tables()` en import.
- Impacto: un deploy guiado solo por migraciones podia quedar con drift de esquema respecto al runtime real, y un entorno con permisos restringidos podia fallar antes de arrancar al intentar hacer DDL durante import.
- Regla practica: si un cambio amplia el contrato persistido de `query_audit_log`, respaldarlo en Alembic y no solo en `ensure_governance_tables()`. Para el servicio, preferir singleton lazy (`get_query_audit_service()`) en vez de instanciar con DDL al importar el modulo.

### 2026-05-03 - Reranker: no exponer scores brutos del cross-encoder como si ya estuvieran normalizados

- Scope: `apps/api/routers/consulta.py`, `apps/api/services/reranker.py`, `apps/api/tests/test_reranker.py`
- Hallazgo: `rerank_score` puede venir fuera de `0..1` (incluyendo negativos y valores > 1). Si se serializa directo como `relevance_score` o `claim confidence`, el contrato externo queda semanticamente enganoso aunque el campo exista. Tambien es facil perder `source_url` al construir `claim_citations` si no se arrastra desde la evidencia del resultado original.
- Impacto: el cliente puede ver puntuaciones imposibles o interpretar una confianza cruda como probabilidad normalizada; ademas, `ClaimCitation.source_url` puede salir `null` aunque la fuente exista en el resultado base.
- Regla practica: reutilizar `normalize_rerank_score()` al serializar campos publicos derivados del cross-encoder y propagar `source_url` desde la evidencia original cuando se construyan citas por claim.

### 2026-05-04 - Fase 2.2 retrieval fail-closed: si una fuente critica falla, `consulta` debe abstenerse y no seguir mezclando resultados parciales

- Scope: `apps/api/routers/consulta.py`, `apps/api/services/unified_multi_source_search.py`, `apps/api/tests/test_consulta_fail_closed.py`
- Hallazgo: el patron `except Exception: pass` en `consulta` y en el search unificado permitia responder con resultados aparentemente validos aunque hubiera fallado parte del retrieval critico pedido por el usuario. El caso mas peligroso era `sources=...`: una fuente podia romperse y aun asi sobrevivir un modelo o resultado lateral no pedido, dando falsa sensacion de cobertura suficiente.
- Impacto: el cliente podia recibir una respuesta operativa incompleta sin ninguna senal fuerte de degradacion, justo en el slice donde el usuario habia pedido retrieval dirigido.
- Regla practica: si falla `search_legislacion` o una fuente del retrieval unificado solicitada por `sources`, `/v1/consulta` debe cerrar en abstencion conservadora (`200` + `NO VERIFICADO`, `review_required=true`, `faithfulness_score=0.0`, listas vacias). El servicio unificado no debe tragarse esas excepciones: debe exponer al menos `source_errors` estructurado para que el router decida el fail-closed.

### 2026-05-04 - Fase 2.3 unified retrieval: el handler 31.x debe respetar la fuente pedida y no esconder fallos de embedding

- Scope: `apps/api/services/unified_multi_source_search.py`, `apps/api/tests/test_unified_multi_source_search.py`
- Hallazgo: tras 2.2 el agregador ya exponia `source_errors`, pero el handler compartido de dominios 31.x seguia buscando contra todos los `documento_origen_tipo` a la vez (`IN (...)`) aunque el usuario pidiera solo `mica`, `dac` o cualquier otro dominio. Ademas, `_31x_fulltext()` llevaba un alias roto (`LOWER(t.texto)`) y un parametro distinto al que realmente se cargaba (`:ts_query` vs `:_31x_ts_query`). Por ultimo, varios helpers vectoriales seguian atrapando `Exception` dentro del propio helper, con lo que un fallo real del embedding backend se convertia en `[]` y nunca llegaba al `source_errors` del agregador.
- Impacto: una consulta dirigida a un dominio 31.x podia contaminarse con chunks de otros dominios; el SQL fulltext 31.x podia fallar en runtime por alias/parametro inconsistentes; y un fallo de embedding por fuente podia aparentar simplemente "sin resultados" en vez de degradacion explicita.
- Regla practica: cuando varios source types comparten handler, el dispatcher debe pasar el `source` pedido y el handler debe filtrar por esa fuente exacta. Los helpers internos no deben tragarse excepciones que forman parte del contrato de degradacion por fuente; si el embedding falla, dejar que el agregador convierta ese fallo en `source_errors` y no en lista vacia silenciosa.

### 2026-05-04 - Fase 2.4 abstention: no mantener una implementacion runtime en `consulta` y otra distinta en `services.grounding`

- Scope: `apps/api/services/grounding.py`, `apps/api/routers/consulta.py`, `apps/api/tests/test_grounding_e2e.py`, `apps/api/tests/test_reranker.py`
- Hallazgo: `services.grounding.apply_claim_level_abstention()` solo funcionaba de verdad cuando los tests le inyectaban `_enriched_items` a mano dentro de `grounding_summary`. En runtime real, `validate_claim_grounding()` no devolvia ese contexto y `consulta.py` se veia obligada a mantener `_apply_claim_level_abstention()` propia para no perder el filtrado por claims.
- Impacto: habia dos implementaciones de la misma regla de abstencion claim-level, con riesgo claro de drift: los tests del servicio probaban una forma y el router ejecutaba otra.
- Regla practica: si una fase pide "una sola implementacion en runtime real", el servicio compartido debe exponer todo el contexto que necesita su helper downstream y el router debe delegar ahi, no reimplementar el filtrado. En este repo, `validate_claim_grounding()` debe poder alimentar directamente `apply_claim_level_abstention()` sin estructuras sintéticas solo de test.

### 2026-05-04 - Fase 2.5 faithfulness: no usar `faithfulness_score` como si fuera una señal de control fiable cuando aún no evalúa la respuesta final real

- Scope: `apps/api/services/faithfulness.py`, `apps/api/routers/consulta.py`, `apps/api/tests/test_faithfulness.py`
- Hallazgo: `compute_faithfulness()` sigue operando sobre un `answer_proxy` construido desde los primeros resultados, no sobre el payload final real que ve el usuario. Aun así, `consulta.py` lo usaba para disparar `review_required`, hacer bypass de grounding y vaciar resultados por debajo de umbral.
- Impacto: una señal heurística útil para observabilidad podía provocar abstención o revisión obligatoria incluso cuando las señales duras de evidencia iban por otro camino. Eso mezclaba dos niveles distintos: scoring auxiliar vs. control real de la respuesta.
- Regla practica: mientras `faithfulness_score` no se calcule sobre la respuesta final real, tratarlo como advisory. Mantenerlo visible para auditoría/observabilidad está bien; usarlo para gates duros de runtime no. Las decisiones de control deben depender de señales más fiables: fail-closed explícito, grounding/citas reales y ausencia material de evidencia.

### 2026-05-04 - Fase 3.1 AEAT seeds: `seed-modelos-v2.py` no es bootstrap standalone

- Scope: `scripts/seed-modelos.py`, `scripts/seed-modelos-v2.py`, `scripts/data/seed_all.py`, seeds AEAT legacy
- Hallazgo: en esta rama MCP, `scripts/seed-modelos-v2.py` solo enriquece campañas y recursos asociados; no crea `aeat_modelo`. Si se ejecuta sin haber corrido antes `scripts/seed-modelos.py`, los inserts por campaña degradan a `SKIP` y el seed no queda completo aunque el script termine.
- Impacto: es fácil interpretar `seed-modelos-v2.py` como vía canónica suficiente porque contiene casillas, claves, instrucciones y normativa, pero usarlo solo deja el bootstrap AEAT incompleto. También `scripts/data/seed_all.py` puede dar una falsa sensación de flujo productivo único porque sigue listando seeds AEAT legacy dentro del runner bulk.
- Regla practica: para AEAT en el plan MCP usar siempre esta secuencia: (1) `python scripts/seed-modelos.py --db-url <DATABASE_URL>` y luego (2) `python scripts/seed-modelos-v2.py --db-url <DATABASE_URL> --campana <YEAR>`. Tratar `scripts/data/seed_modelos.py`, `scripts/data/seed_aeat_models.py`, `scripts/data/seed_modelo_articulo.py` y `scripts/seed-fiscal-modelos.sql` como rutas `LEGACY / NO AUTORITATIVO`, no como equivalentes productivos.

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

- Scope: `apps/api/main.py`, `apps/api/Dockerfile`, `infra/deploy/Caddyfile`, `infra/deploy/compose.env.example`, despliegue Compose en VPS
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

### 2026-05-03 - SQLite compartida en Windows: no correr `pytest` del API en paralelo

- Scope: `apps/api/tests/conftest.py`, worktrees Windows, suites `pytest` del API
- Hallazgo: `conftest.py` intenta borrar y recrear `test_esdata.sqlite3` al importarse. En Windows, si se lanzan dos procesos `pytest` a la vez contra `apps/api/tests`, el segundo puede fallar en el `unlink()` con `PermissionError: [WinError 32]` porque el primer proceso mantiene el archivo abierto.
- Impacto: se obtienen fallos falsos de infraestructura de test al verificar slices en paralelo, incluso cuando el runtime y los tests individuales estan bien.
- Regla practica: en este repo, las suites `pytest` que importan `apps/api/tests/conftest.py` deben ejecutarse en secuencial dentro del mismo worktree Windows. Si hace falta paralelizar, usar otro worktree o aislar un DB path distinto por proceso.

### 2026-05-04 - SQLite + audit E2E: no dejar `MappingResult` vivo antes de escribir `query_audit`

- Scope: `apps/api/services/modelos.py`, `apps/api/services/query_audit.py`, endpoints `modelos` con auditoria E2E
- Hallazgo: en SQLite, dejar un `MappingResult` perezoso sin consumir y luego abrir otra conexion para persistir `query_audit` puede bloquear el commit con `sqlite3.OperationalError: database is locked`. Ademas, usar `bool(result)` sobre resultados SQLAlchemy no expresa si hay filas y deja el reader abierto mas tiempo del necesario.
- Impacto: endpoints GET aparentemente inocuos pueden fallar solo al registrar la auditoria, aunque el payload ya este construido y la consulta principal haya devuelto datos.
- Regla practica: cuando solo haga falta existencia, consumir el resultado inmediatamente con `.first() is not None`; cuando haga falta el contenido completo, materializarlo a `list[dict]` antes de cualquier write posterior o auditoria en otra conexion. No usar truthiness sobre resultados lazy de SQLAlchemy como señal de completitud.

### 2026-05-04 - DGT tests: `run_sync(seed_urls=[])` sigue cayendo en `SEED_URLS`

- Scope: `apps/workers/dgt.py`, `apps/workers/tests/test_dgt.py`
- Hallazgo: `run_sync(seed_urls=[])` usa `seed_urls or SEED_URLS`, asi que una lista vacia no desactiva los seeds por defecto del modulo.
- Impacto: un test que pretende correr sin seeds reales puede procesar URLs por defecto, cambiar el conteo del batch y dar falsos `partial` o resultados inesperados.
- Regla practica: en tests que necesiten cero seeds reales, pasar `seed_urls=[]` y ademas hacer `monkeypatch.setattr("dgt.SEED_URLS", [])`.

### 2026-05-04 - CNMV fixtures HTML en Windows: leer con `encoding="utf-8"`

- Scope: `apps/workers/tests/test_cnmv.py`
- Hallazgo: `Path.read_text()` sin encoding explicito puede intentar decodificar fixtures HTML con la code page local de Windows y fallar aunque el fixture este bien.
- Impacto: aparecen `UnicodeDecodeError` falsos en tests de discovery/parseo CNMV sin que el worker ni el fixture esten realmente rotos.
- Regla practica: en fixtures HTML/PDF/texto del worker CNMV, usar siempre `read_text(encoding="utf-8")` si el archivo esta versionado en UTF-8.

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

### 2026-05-02 - Alertmanager en VPS usa config renderizada, no la plantilla del repo

- Scope: `infra/observability/alertmanager.yml`, `docs/operations/runbooks/deploy-compose.md`, despliegue Compose en VPS
- Hallazgo: el repo guarda una plantilla con `${TELEGRAM_BOT_TOKEN}` y `${TELEGRAM_CHAT_ID}`, pero el contenedor `deploy-alertmanager-1` necesita una version ya renderizada en el VPS. Si se copia la plantilla sin renderizar y se reinicia el contenedor, Alertmanager entra en restart loop porque `chat_id` deja de ser un entero valido.
- Impacto: se cae la notificacion operativa aunque Prometheus y la API sigan sanos; el error visible en logs es `cannot unmarshal !!str ${TELEG...} into int64`.
- Regla practica: antes de reiniciar Alertmanager en produccion, verificar que `/srv/esdata/infra/observability/alertmanager.yml` contiene `bot_token` y `chat_id` reales. No desplegar la plantilla del repo directamente sobre el VPS sin un paso explicito de render.
