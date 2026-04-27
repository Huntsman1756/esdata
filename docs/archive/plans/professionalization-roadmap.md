# [REFERENCE] Roadmap de profesionalizacion

> Este documento queda como referencia de infraestructura, calidad, despliegue y operacion. La fuente activa unica de estado y ejecucion es `docs/master-execution-roadmap.md`.

## Objetivo

Profesionalizar `esdata` para tres metas simultaneas:

- seguir creciendo sin aumentar deuda tecnica de forma descontrolada
- dejar el sistema listo para operacion por un equipo de infraestructura externo al equipo de producto
- Railway YA NO se usa como plataforma de despliegue (deprecated — HISTORICO)

## Estado actual resumido

Base actual del repo:

- `apps/api`: API FastAPI publica
- `apps/workers`: workers Python de ingesta y sincronizacion
- `apps/web`: frontend Next.js 15
- `infra/sql`: esquema y migraciones SQL manuales
- `docker-compose.yml`: entorno local con Postgres, Redis, API y workers parciales
- `railway.toml` (DEPRECATED — ya no se usa Railway como plataforma de despliegue)
- `.github/workflows/ci.yml`: tests Python y lint basico

Fortalezas actuales:

- separacion clara entre API, workers y web
- despliegue real en produccion
- documentacion funcional ya existente
- Dockerfiles por servicio
- workers separados por fuente y responsabilidad

Gaps principales para un entorno mas profesional:

- falta una capa compartida clara entre `apps/api` y `apps/workers`
- configuracion y variables de entorno todavia dispersas
- migraciones de base de datos manuales y sin framework formal
- documentacion operativa todavia orientada al autor original
- despliegue portable incompleto fuera de Railway (Railway deprecated)
- observabilidad y runbooks poco formalizados

## Principios de ejecucion

- no depender de Railway para despliegue
- hacer cambios pequenos y reversibles
- separar claramente documentacion de producto, documentacion tecnica y documentacion operativa
- preparar el repo para despliegue portable sin dependencias de plataforma
- evitar refactors grandes sin beneficio operativo inmediato

## Estructura objetivo

Objetivo de estructura a medio plazo:

```text
esdata/
|-- apps/
|   |-- api/
|   |-- workers/
|   `-- web/
|-- libs/
|   `-- python/
|       `-- esdata_common/
|           |-- config.py
|           |-- db.py
|           |-- logging.py
|           |-- http.py
|           `-- ...
|-- infra/
|   |-- sql/
|   |-- docker/
|   `-- deploy/
|-- docs/
|   |-- architecture.md
|   |-- repository-structure.md
|   |-- environment-variables.md
|   |-- database.md
|   |-- infrastructure-handoff.md
|   |-- deployment/
|   `-- operations/
|-- scripts/
`-- tests/
```

Notas:

- `libs/python/esdata_common` puede introducirse de forma gradual sin mover toda la logica al principio
- `infra/deploy` debe quedar preparado para Docker Compose productivo o futura adaptacion a Kubernetes
- `docs/operations` debe convertirse en la referencia principal para el equipo de infraestructura

## Roadmap por fases

### Fase 1. Baseline tecnico y documental

Objetivo:

- dejar claro como funciona hoy el sistema y reducir dependencia de conocimiento implicito

Entregables:

- `docs/architecture.md` ✅
- `docs/repository-structure.md` ✅
- `docs/environment-variables.md` ✅
- `docs/infrastructure-handoff.md` ✅
- inventario de servicios, cron jobs, puertos, dependencias externas y secretos ✅
- decision documentada sobre estrategia de migraciones futura ✅

Cambios recomendados:

- mapear flujos principales: ingesta BOE, ingesta DGT, ingesta TEAC, modelos AEAT, API publica y frontend ✅
- documentar cada servicio de infra/deploy/docker-compose.prod.yml con su configuracion equivalente en systemd/cron ✅
- consolidar variables de entorno reales usadas por API, workers y web ✅
- diferenciar documentacion de arranque, despliegue y operacion ✅

Resultado esperado:

- cualquier persona tecnica nueva entiende arquitectura, dependencias y operacion minima del sistema ✅

Estado: ✅ COMPLETA

### Fase 2. Estandarizacion interna

Objetivo:

- reducir duplicacion y preparar el repo para crecimiento de codigo y equipo

Entregables:

- capa comun Python inicial en `libs/python/esdata_common` ✅
- convencion unica de configuracion para Python ✅
- logging unificado para API y workers ✅
- comandos repetibles de desarrollo y validacion ✅
- `.env.example` completo y alineado con docs ✅

Cambios recomendados:

- extraer utilidades compartidas de configuracion, DB, retries HTTP y logging ✅
- definir una convencion de settings por entorno ✅
- revisar dependencias Python compartidas y versionarlas de forma coherente ✅
- introducir `Makefile` o script equivalente para tareas operativas comunes ✅

Quick wins:

- crear `make test`, `make lint`, `make api`, `make worker-modelos`, `make bootstrap-db` ✅
- anadir `.env.example` realmente completo y alineado con docs ✅
- documentar contratos internos entre web, API y workers (pendiente Fase 5)

Resultado esperado:

- menos fragilidad al tocar varios servicios y mejor base para nuevas fuentes de datos

Estado: ✅ COMPLETA

### Fase 3. Base de datos y cambios de esquema

Objetivo:

- profesionalizar la evolucion de schema y reducir riesgo en despliegues

Opciones viables:

- mantener SQL manual muy disciplinado
- migrar a Alembic sobre el estado actual

Recomendacion:

- introducir Alembic de forma gradual y tomar el schema actual como baseline, manteniendo SQL historico como referencia

Entregables:

- estrategia de migraciones documentada ✅
- flujo de alta de nuevas tablas/campos ✅
- guia de bootstrap, upgrade y rollback de base de datos ✅
- validaciones automatizadas de schema en CI si el coste compensa ⏳

Cambios recomendados:

- crear una fotografia base del estado actual de produccion ✅
- definir como se aplica una migracion en local, staging y produccion ✅
- separar claramente seeds de esquema ✅

Resultado esperado:

- el equipo de infraestructura puede desplegar y evolucionar la BD con menos riesgo y mas trazabilidad

Estado: ✅ COMPLETA

### Fase 4. Despliegue portable y handoff a infraestructura

Objetivo:

- permitir despliegue portable sin dependencias de plataforma

Entregables:

- `infra/deploy/docker-compose.prod.yml` o estructura equivalente ✅
- documentacion de instalacion en servidor ✅
- documentacion de actualizacion y rollback ✅
- checklist de handoff a infraestructura ✅

Cambios recomendados:

- endurecer Dockerfiles para uso productivo ✅ (ya aplicados: read_only, tmpfs, security_opt)
- revisar persistencia, networking, healthchecks y arranque ordenado ✅
- definir como ejecutar cron jobs con systemd timers o cron del sistema ✅
- separar configuracion de build y runtime ✅

Contenido minimo del handoff:

- recursos requeridos por servicio ✅
- dependencias de red y DNS ✅
- variables y secretos obligatorios ✅
- estrategia de backups y restauracion ✅
- healthchecks y criterios de aceptacion ✅
- flujo de despliegue y rollback ✅

Resultado esperado:

- el sistema puede montarse en VM o plataforma corporativa sin depender de plataformas PaaS externas

Estado: ✅ COMPLETA

### Fase 5. Operacion, observabilidad y soporte

Objetivo:

- hacer el sistema operable por terceros en el dia a dia

Entregables:

- `docs/operations/README.md` ✅
- runbooks por incidencia y tarea recurrente ✅
- logging estructurado ✅
- verificacion operativa automatizable ✅

Cambios recomendados:

- definir formato unico de logs ✅ (JSON via LOG_FORMAT=json)
- documentar fallos habituales por worker ✅
- anadir scripts de smoke y comprobaciones post deploy ✅
- definir indicadores minimos: salud API, salud workers, ejecucion de crons, cobertura de datos, errores de ingesta ✅

Resultado esperado:

- infraestructura puede operar el sistema con autonomia razonable

Estado: ✅ COMPLETA

### Fase 6. Calidad de ingenieria y escalado

Objetivo:

- cerrar huecos que se vuelven caros a medida que el producto crece

Entregables:

- CI mas completa
- estrategia de tests ampliada
- controles de calidad y seguridad basicos

Cambios recomendados:

- anadir tests de integracion con DB realista ✅
- anadir build del frontend y tests del web en CI ✅
- introducir chequeos de formateo y tipado si el coste compensa ✅
- preparar backlog de hardening: Sentry, metricas, rate limiting, auditoria de secretos ✅

Resultado esperado:

- el repo gana fiabilidad para cambios frecuentes y crecimiento del equipo

Estado: ✅ COMPLETA

### Fase 7. Observabilidad avanzada y enrichment de datos

Objetivo:

- monitorizar errores en produccion con Sentry
- enriquecer dataset golden con queries BORME/BDNS/chunk
- añadir hybrid search para doctrina
- unificar ponderaciones de búsqueda

Entregables:

- Sentry error monitoring en API y todos los workers (13 workers)
- Golden dataset enriquecido: 52 → 70 queries
- Endpoint `/v1/doctrina/buscar/hybrid`
- hybrid_weight unificado a 0.3 en router, service y eval

Cambios realizados:

- `apps/api/main.py`: init_sentry() opcional via ESDATA_SENTRY_DSN ✅
- `apps/workers/runtime.py`: init_sentry() reutilizable ✅
- 13 workers actualizados con init_sentry() ✅
- `apps/api/requirements.txt`: sentry-sdk[fastapi]==2.26.1 ✅
- `apps/workers/requirements.txt`: sentry-sdk==2.26.1 ✅
- `scripts/golden_queries.json`: +18 queries nuevas ✅
- `apps/api/routers/doctrina.py`: endpoint hybrid ✅
- `apps/api/services/semantic_search.py`: default 0.3 ✅
- `scripts/eval_phase3.py`: default 0.3 ✅

Estado: ✅ COMPLETA

## Estado actual

Todas las fases de profesionalizacion estan completas:

| Fase | Estado | Score evaluacion |
|------|--------|------------------|
| 1. Baseline tecnico y documental | ✅ COMPLETA | — |
| 2. Estandarizacion interna | ✅ COMPLETA | — |
| 3. Base de datos y cambios de esquema | ✅ COMPLETA | — |
| 4. Despliegue portable y handoff | ✅ COMPLETA | — |
| 5. Operacion, observabilidad y soporte | ✅ COMPLETA | — |
| 6. Calidad de ingenieria y escalado | ✅ COMPLETA | — |
| 7. Observabilidad avanzada y enrichment | ✅ COMPLETA | 0.9575 |

Resultado evaluacion final: **0.9575** (70 queries, threshold 0.80, gate APROBADO).
Solo 1 fallo historico (int-008, no bloqueante).

## Siguientes pasos recomendados

### Prioridad alta

1. **Configurar ESDATA_SENTRY_DSN en produccion**
   - Activar Sentry para monitorizacion de errores en API y workers
   - Archivos: `.env`, `apps/api/main.py`, `apps/workers/runtime.py`

2. **Tunear HNSW parameters** (`m`, `ef_construction`, `ef_search`)
   - Valores actuales: `m=16`, `ef_construction=64`
   - Investigar si `m=32`, `ef_construction=128` mejoran recall sin afectar latencia
   - Archivos: `infra/sql/006_pgvector.sql`, `apps/api/services/semantic_search.py`

### Prioridad media

3. **Backfill embeddings para doctrina** (`documento_fragmento`)
   - Los chunks de doctrina no tienen embeddings actualmente
   - Ejecutar: `python /app/backfill_embeddings.py --corpus doctrina`
   - Mejora recall en consultas doctrinales

### Prioridad baja

4. **Investigar fallo int-008** (historico Fase 2)
   - Query: "Contractor digital americano vendiendo a Espana"
   - Espera: IRNR | Devuelve: convenios bilaterales
   - No bloquea gate de calidad (score 0.9575)

## Definicion de terminado

Se puede considerar que la profesionalizacion esta completa cuando:

- ✅ arquitectura y estructura documentadas con precision
- ✅ variables y secretos documentados por servicio
- ✅ estrategia de migraciones decidida y documentada (Alembic)
- ✅ despliegue portable sin PaaS definido y documentado (Docker Compose)
- ✅ runbooks minimos disponibles (`docs/operations/`)
- ✅ CI cubre backend, frontend, calidad y evaluacion
- ✅ evaluacion con golden dataset aprobada (score >= 0.80)
- ⏳ el equipo de infraestructura puede instalar, arrancar, verificar y recuperar el sistema sin depender del autor original

## Documentacion generada

| Archivo | Fase | Contenido |
|---------|------|-----------|
| `docs/architecture.md` | 1 | Arquitectura completa, 19 routers, 11 workers |
| `docs/repository-structure.md` | 1 | Arbol de directorios y responsabilidades |
| `docs/environment-variables.md` | 1 | 40+ variables documentadas |
| `docs/infrastructure-handoff.md` | 1 | Handoff infraestructura |
| `docs/database.md` | 3 | 14 tablas, 20+ indices, 8 migraciones, backup |
| `docs/deployment/overview.md` | 4 | Arquitectura despliegue, servicios, compose |
| `docs/deployment/server-installation.md` | 4 | Guia instalacion servidor (8 pasos) |
| `docs/deployment/rollback.md` | 4 | 4 escenarios rollback |
| `docs/operations/README.md` | 5 | Monitoreo, operaciones, mantenimiento |
| `docs/operations/worker-failures.md` | 5 | Patrones de fallo por worker |
| `docs/operations/metrics.md` | 5 | KPIs, umbrales, SQL queries |
| `docs/professionalization-roadmap.md` | — | Este documento |
| `docs/controlled-vocabulary-regulatorio.md` | SV | Vocabulario controlado |
| `docs/sociedad-valores-scope.md` | SV | Scope entidad regulada |
| `docs/source-manifests/sociedad-valores-wave-1.md` | SV | Source manifest Wave 1 |

## Riesgos principales

### Riesgo 1. Latencia de busqueda

- Actual: 1-3s por request `/v1/legislacion/buscar`
- Causa: fulltext + fallback SQLite sin embeddings en doctrina
- Mitigacion: backfill embeddings doctrina, tunear HNSW

### Riesgo 2. Workers sin retry

- Workers crashan en fallos sin recuperacion automatica
- Docker Compose reinicia en crash (supervision basica)
- Mitigacion: añadir retry exponencial en workers criticos (boe, dgt)

### Riesgo 3. Documentacion desactualizada

- El handoff pierde valor si no se actualiza
- Mitigacion: ligar actualizacion docs al flujo de cambios

### Riesgo 4. Falta de Sentry en produccion

- Sin monitorizacion de errores en tiempo real
- Mitigacion: configurar ESDATA_SENTRY_DSN (prioridad alta)

## Next phase proposal

Una vez completada la profesionalizacion base, las siguientes fases naturales serian:

1. **Expansion de corpus**: nuevas fuentes regulatorias (Banco de Espana, DIAN, etc.)
2. **Mejora retrieval**: fine-tuning de embeddings, reranking, RAG con doctrina
3. **Frontend de administracion**: panel para monitorizar ingestion, fallos, calidad
4. **API de versionado**: historico de cambios normativos, tracking de vigencia
5. **Multi-idioma**: soporte catalan, gallego, euskera en busqueda
