# Arquitectura de esdata

## Objetivo

`esdata` es un sistema de datos fiscales espanoles con tres superficies principales:

- API HTTP publica para legislacion, doctrina y modelos AEAT
- frontend web para consulta humana
- workers de ingesta y sincronizacion contra fuentes oficiales

El sistema esta desplegado hoy en Railway, pero la arquitectura ya esta separada por servicios y puede migrarse a un entorno empresarial con contenedores.

## Componentes principales

### 1. API publica

Ubicacion:

- `apps/api/main.py`
- `apps/api/routers/*`
- `apps/api/db.py`
- `apps/api/schemas.py`

Tecnologia:

- FastAPI
- SQLAlchemy
- PostgreSQL

Responsabilidades:

- exponer endpoints de legislacion, doctrina, materias y modelos
- leer datos ya normalizados desde PostgreSQL
- publicar spec OpenAPI
- exponer superficie MCP en `/mcp`
- devolver estado agregado basico del sistema en `/status` y salud en `/health`

Routers actuales:

- `status`
- `buscar`
- `legislacion`
- `materias`
- `doctrina`
- `modelos`

### 2. Workers de ingesta

Ubicacion:

- `apps/workers/boe.py`
- `apps/workers/dgt.py`
- `apps/workers/teac.py`
- `apps/workers/modelos.py`

Tecnologia:

- Python 3.12
- `httpx`
- SQLAlchemy
- PostgreSQL

Responsabilidades:

- descargar y normalizar legislacion desde BOE
- descargar doctrina DGT desde Petete
- descargar resoluciones TEAC desde DYCTEA/URLs semilla
- sincronizar instrucciones, casillas, claves y normativa de modelos AEAT
- dejar traza operativa en `sync_log`

### 3. Frontend web

Ubicacion:

- `apps/web/app/*`
- `apps/web/components/*`
- `apps/web/lib/*`

Tecnologia:

- Next.js 15
- React 19
- TypeScript

Responsabilidades:

- ofrecer buscador y navegacion sobre la API
- renderizar detalle de articulo, doctrina y modelo
- consumir la API mediante la variable de servidor `ESDATA_API_BASE_URL`

### 4. Base de datos

Ubicacion de esquema y cambios:

- `infra/sql/init.sql`
- `infra/sql/002_fulltext_search.sql`
- `infra/sql/003_modelos_aeat.sql`
- `infra/sql/004_modelos_v2.sql`
- `infra/sql/docker-init.sql`

Motor:

- PostgreSQL 16 en local y Railway en produccion

Responsabilidades:

- almacenar legislacion versionada por articulo
- almacenar doctrina interpretativa y sus enlaces a articulos
- almacenar modelos AEAT y sus campanas
- almacenar trazas de ejecucion de workers en `sync_log`

### 5. Capa perimetral y despliegue

Artefactos actuales:

- `railway.toml`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy.yml`
- `.github/workflows/deploy-web.yml`
- `infra/cloudflare/worker.js`
- `verify_railway.py`

Responsabilidades:

- definir servicios y cron jobs en Railway
- ejecutar CI y despliegues automaticos
- aplicar cache y proteccion de `/mcp` en Cloudflare
- verificar el estado del proyecto Railway desde CLI

## Flujo de datos

### Flujo 1. Legislacion BOE

1. `worker-boe` consulta la API de BOE.
2. Inserta o actualiza `norma`, `articulo` y `version_articulo`.
3. Ejecuta auto-linking basico de materias y doctrina.
4. Registra la ejecucion en `sync_log`.
5. La API expone los datos en `/v1/legislacion/*` y `/v1/buscar`.

### Flujo 2. Doctrina DGT

1. `worker-dgt` navega Petete con `httpx`.
2. Extrae referencias, fecha, organo, texto y normativa.
3. Inserta o actualiza `documento_interpretativo`.
4. Ejecuta `auto_link_doctrina` para enlazar doctrina con articulos.
5. Registra resultados en `sync_log`.
6. La API expone resultados en `/v1/doctrina/*`.

### Flujo 3. Doctrina TEAC

1. `worker-teac` parte de `TEAC_SEED_URLS`.
2. Descarga cada resolucion HTML.
3. Inserta o actualiza `documento_interpretativo`.
4. Ejecuta `auto_link_doctrina`.
5. Registra la ejecucion en `sync_log`.

### Flujo 4. Modelos AEAT

1. `worker-modelos` obtiene modelos desde la base de datos.
2. Descarga HTML de paginas de sede AEAT.
3. Detecta campanas.
4. Actualiza `modelo_campana`, `modelo_casilla`, `modelo_clave` y `modelo_instruccion`.
5. Registra una entrada agregada en `sync_log`.
6. La API expone esos datos en `/v1/modelos/*` y el frontend en `/modelo/[codigo]`.

### Flujo 5. Frontend web

1. El usuario accede al frontend Next.js.
2. El servidor Next consulta la API via `ESDATA_API_BASE_URL`.
3. El frontend renderiza informacion de estado, resultados y detalle.

## Servicios desplegados hoy

Servicios declarados en `railway.toml`:

- `esdata`
- `worker-boe`
- `cron-boe-daily`
- `worker-dgt`
- `cron-dgt-weekly`
- `worker-teac`
- `cron-teac-weekly`
- `worker-modelos`
- `cron-modelos-daily`
- `web`

Dependencias externas principales:

- BOE datos abiertos
- Petete DGT
- sede AEAT
- URLs semilla TEAC
- Railway
- Cloudflare

## Modelo operativo actual

### Ejecucion continua

- `worker-boe`
- `worker-dgt`
- `worker-teac`
- `worker-modelos`

### Ejecucion programada

- `cron-boe-daily`
- `cron-dgt-weekly`
- `cron-teac-weekly`
- `cron-modelos-daily`

### Superficies publicas

- API: `https://esdata-production.up.railway.app`
- Web: `https://web-production-ecb5.up.railway.app`
- OpenAPI: `https://esdata-production.up.railway.app/openapi.json`

## Observaciones importantes

### Observabilidad basica en `/status`

El endpoint `/status` informa hoy sobre:

- `worker-boe`
- `cron-boe-daily`
- `worker-dgt`
- `cron-dgt-weekly`
- `worker-teac`
- `cron-teac-weekly`
- `worker-modelos`
- `cron-modelos-daily`

La observabilidad sigue siendo basica, pero ya cubre todos los workers y cron jobs principales del sistema.

### Duplicacion de infraestructura Python

La API y los workers comparten dependencias y patrones de acceso a base de datos, pero todavia no existe una libreria comun. Este es uno de los principales candidatos a refactor de profesionalizacion.

### Migraciones de BD manuales

El sistema usa SQL versionado manualmente. Funciona, pero todavia no hay un framework formal de migraciones ni una estrategia de rollback automatizada.

### Configuracion todavia heterogenea

Existen variables documentadas en `.env.example` que no estan usadas por el runtime actual y tambien existen variables usadas por scripts operativos que no forman parte del contrato principal de la aplicacion. Esto se documenta por separado en `docs/environment-variables.md`.
