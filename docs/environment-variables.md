# Variables de entorno

## Objetivo

Este documento separa las variables de entorno en tres grupos:

- variables de runtime realmente usadas por el codigo actual
- variables usadas por despliegue, CI o periferia
- variables documentadas pero no consumidas por la aplicacion en su estado actual

Esto es importante porque `.env.example` contiene una mezcla de contratos actuales y futuros.

## Resumen rapido

Variables criticas de runtime hoy:

- `DATABASE_URL`
- `ESDATA_API_BASE_URL`
- `BOE_API_BASE`
- `BOE_LEGISLACION_NORMAS`
- `SYNC_INTERVAL_SECONDS`
- `TEAC_SEED_URLS`
- `MODELOS_SYNC_INTERVAL`
- `DGT_SSL_VERIFY`

Variables operativas usadas por scripts o periferia:

- `DATABASE_PUBLIC_URL`
- `API_DOMAIN`
- `WEB_DOMAIN`
- `CADDY_EMAIL`
- `MCP_SECRET_ACTIVE`
- `MCP_SECRET_PREVIOUS`
- `CLOUDFLARE_ZONE_ID`
- `CLOUDFLARE_API_TOKEN`
- `RAILWAY_TOKEN`
- `RAILWAY_PROJECT_ID`
- `RAILWAY_ENVIRONMENT`

Variables hoy documentadas pero no leidas por el runtime principal:

- `SECRET_KEY`
- `LOG_LEVEL`
- `REDIS_URL`
- `DGT_BASE_URL`
- `DGT_REQUEST_DELAY_SECONDS`
- `WORKER_BOE_BATCH_SIZE`
- `WORKER_RETRY_MAX`
- `WORKER_RETRY_BACKOFF_SECONDS`
- `SLACK_WEBHOOK_URL`

## Runtime de aplicacion

### Compartidas por API y workers

#### `DATABASE_URL`

- uso: conexion principal a PostgreSQL
- leida por:
  - `apps/api/db.py`
  - `apps/workers/boe.py`
  - `apps/workers/dgt.py`
  - `apps/workers/teac.py`
  - `apps/workers/modelos.py`
  - scripts de seed y soporte
- obligatoria: si, salvo que se use el valor local por defecto en desarrollo
- valor por defecto en codigo: `postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata`
- observacion: en tests de API se sustituye temporalmente por SQLite

### API FastAPI

La API no consume hoy variables propias adicionales de runtime aparte de `DATABASE_URL`.

#### `APP_ENV`

- uso real hoy: aparece en CI, `docker-compose.yml`, README y verificaciones auxiliares
- consumo por codigo runtime: no
- estado: variable operativa/documental; hoy se usa en CI y verificaciones, no en la logica principal de FastAPI

### Frontend web

#### `ESDATA_API_BASE_URL`

- uso: URL base de la API consumida por el frontend del lado servidor
- leida por:
  - `apps/web/lib/api.ts`
  - referencias directas adicionales en componentes/paginas de detalle
- obligatoria: si en produccion
- valor por defecto en codigo: `http://localhost:8000`
- observacion: esta pensada para no exponerse al cliente; se usa en render server-side

### Worker BOE

#### `BOE_API_BASE`

- uso: base de la API de BOE datos abiertos
- leida por: `apps/workers/boe.py`
- valor por defecto: `https://www.boe.es/datosabiertos/api/legislacion-consolidada`

#### `SYNC_INTERVAL_SECONDS`

- uso: intervalo de repeticion del worker continuo
- leida por: `apps/workers/boe.py`
- valor por defecto: `3600`

#### `BOE_LEGISLACION_NORMAS`

- uso: lista separada por comas de codigos de norma a sincronizar
- leida por: `apps/workers/boe.py`
- valor por defecto efectivo: `LIVA`
- observacion: en `docker-compose.yml` y docs se usa una lista mas amplia

#### `BOE_ONLY_BLOCK_IDS`

- uso: limitar sincronizacion a bloques concretos para ejecucion parcial o debugging
- leida por: `apps/workers/boe.py`
- obligatoria: no
- valor por defecto: vacio

### Worker DGT

#### `SYNC_INTERVAL_SECONDS`

- uso: intervalo de repeticion del worker continuo
- leida por: `apps/workers/dgt.py`
- valor por defecto: `604800`

#### `DGT_SSL_VERIFY`

- uso: activar o desactivar validacion SSL al consultar DGT
- leida por: `apps/workers/dgt.py`
- valor por defecto: `false`
- semantica actual: se considera `true` si el valor es `1`, `true` o `yes`

### Worker TEAC

#### `TEAC_SEED_URLS`

- uso: URLs semilla separadas por comas para resoluciones TEAC
- leida por: `apps/workers/teac.py`
- obligatoria: si se quiere una ingesta real util
- valor por defecto: vacio

#### `SYNC_INTERVAL_SECONDS`

- uso: intervalo de repeticion del worker continuo
- leida por: `apps/workers/teac.py`
- valor por defecto: `604800`

### Worker Modelos AEAT

#### `MODELOS_SYNC_INTERVAL`

- uso: intervalo de repeticion del worker de modelos
- leida por: `apps/workers/modelos.py`
- valor por defecto: `86400`

#### `DGT_SSL_VERIFY`

- uso real: el worker de modelos la reutiliza para decidir el `verify` de `httpx` al llamar a AEAT
- leida por: `apps/workers/modelos.py`
- valor por defecto: `true`
- advertencia: la semantica esta invertida en este archivo; el codigo hace `== "false"` y luego usa `verify=not DGT_SSL_VERIFY`
- impacto: esta variable necesita aclaracion o refactor antes de un handoff profesional

## Variables usadas por scripts

### `DATABASE_PUBLIC_URL`

- uso: conexion publica o alternativa a PostgreSQL desde scripts auxiliares
- leida por:
  - `scripts/seed-modelos.py`
  - `scripts/seed-modelos-v2.py`
  - `scripts/validate-cron-run.py`
- obligatoria: no, si existe `DATABASE_URL`
- observacion: no es parte del contrato principal del runtime de API/workers

## Variables de despliegue y periferia

### GitHub Actions y Railway

#### `RAILWAY_TOKEN`

- uso: autenticar despliegues CI hacia Railway
- leida por:
  - `.github/workflows/deploy.yml`
  - `.github/workflows/deploy-web.yml`

#### `RAILWAY_PROJECT_ID`

- uso: identificar proyecto Railway en CI
- definida hoy dentro de workflows

#### `RAILWAY_ENVIRONMENT`

- uso: entorno Railway objetivo en CI
- definida hoy dentro de workflows

### Cloudflare

#### `CLOUDFLARE_ZONE_ID`

- uso: purge de cache tras deploy
- leida por: `.github/workflows/deploy.yml`

#### `CLOUDFLARE_API_TOKEN`

- uso: autenticar purge de cache en Cloudflare
- leida por: `.github/workflows/deploy.yml`

#### `MCP_SECRET_ACTIVE`

- uso: token Bearer valido principal para `/mcp`
- leida por: `infra/cloudflare/worker.js`

#### `MCP_SECRET_PREVIOUS`

- uso: token anterior durante ventana de rotacion
- leida por: `infra/cloudflare/worker.js`

### Caddy / Hetzner Compose

#### `API_DOMAIN`

- uso: dominio publico de la API en el `Caddyfile` del despliegue portable
- leida por:
  - `infra/deploy/Caddyfile`
  - `infra/deploy/compose.env.example`

#### `WEB_DOMAIN`

- uso: dominio publico del frontend en el `Caddyfile` del despliegue portable
- leida por:
  - `infra/deploy/Caddyfile`
  - `infra/deploy/compose.env.example`

#### `CADDY_EMAIL`

- uso: email opcional para ACME / Let's Encrypt en Caddy
- leida por:
  - `infra/deploy/Caddyfile`
  - `infra/deploy/compose.env.example`

## Variables documentadas pero no consumidas por el runtime principal

Estas variables aparecen en `.env.example` o `env.example`, pero el codigo actual no las usa directamente en runtime:

- `SECRET_KEY`
- `LOG_LEVEL`
- `REDIS_URL`
- `DGT_BASE_URL`
- `DGT_REQUEST_DELAY_SECONDS`
- `WORKER_BOE_BATCH_SIZE`
- `WORKER_RETRY_MAX`
- `WORKER_RETRY_BACKOFF_SECONDS`
- `SLACK_WEBHOOK_URL`
- `PGHOST`
- `PGPORT`
- `PGUSER`
- `PGPASSWORD`
- `PGDATABASE`

No significa que sobren necesariamente. Significa que hoy no forman parte del contrato ejecutado por la aplicacion y deberian revisarse antes de prometerlas como definitivas al equipo de infraestructura.

## Variables recomendadas por servicio

### API `esdata`

- `DATABASE_URL`

### `worker-boe`

- `DATABASE_URL`
- `BOE_API_BASE`
- `BOE_LEGISLACION_NORMAS`
- `SYNC_INTERVAL_SECONDS`

### `cron-boe-daily`

- `DATABASE_URL`
- `BOE_API_BASE`
- `BOE_LEGISLACION_NORMAS`

### `worker-dgt`

- `DATABASE_URL`
- `SYNC_INTERVAL_SECONDS`
- `DGT_SSL_VERIFY`

### `cron-dgt-weekly`

- `DATABASE_URL`
- `DGT_SSL_VERIFY`

### `worker-teac`

- `DATABASE_URL`
- `SYNC_INTERVAL_SECONDS`
- `TEAC_SEED_URLS`

### `cron-teac-weekly`

- `DATABASE_URL`
- `TEAC_SEED_URLS`

### `worker-modelos`

- `DATABASE_URL`
- `MODELOS_SYNC_INTERVAL`
- `DGT_SSL_VERIFY`

### `cron-modelos-daily`

- `DATABASE_URL`

### `web`

- `ESDATA_API_BASE_URL`

## Recomendaciones para profesionalizacion

1. separar variables de runtime, scripts y despliegue en documentos o secciones distintas
2. eliminar o etiquetar claramente las variables no consumidas por el codigo actual
3. introducir una capa comun de configuracion Python
4. normalizar la semantica de `DGT_SSL_VERIFY`
5. retirar o consolidar `env.example` cuando ya no haga falta como alias heredado
