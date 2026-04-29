# Variables de entorno

## Resumen

esdata usa variables de entorno para configurar todas las dependencias externas y el comportamiento de los servicios. Las variables se cargan via `.env` (local) o desde el orchestrator Docker.

## Archivo de referencia

`.env.example` contiene el unico template permitido dentro del repo.
Los secretos reales no deben vivir en el workspace del repo ni en `.env` anidados.

## Clasificacion

### Runtime compartido

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `DATABASE_URL` | Si | `postgresql+psycopg://user:password@host:5432/dbname` | URL de conexion a PostgreSQL | API + Workers |
| `DATABASE_PUBLIC_URL` | No | | URL publica de la DB (para scripts auxiliares) | Scripts |

### Frontend web

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `ESDATA_API_BASE_URL` | No | `http://localhost:8000` | URL base de la API para el frontend | Next.js |

### API / Operacion general

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `APP_ENV` | No | `development` | Entorno de la aplicacion | API |
| `API_DOMAIN` | No | | Dominio publico de la API servido por Caddy | Infra |
| `WEB_DOMAIN` | No | | Dominio publico del frontend servido por Caddy | Infra |
| `CADDY_EMAIL` | No | | Email usado por Caddy para certificados | Infra |
| `ESDATA_CORS_ORIGINS` | No | `http://localhost:3000,http://localhost:8000` | Origenes permitidos por CORS | API |
| `ESDATA_API_KEY` | Si fuera de `APP_ENV=test` | | API key obligatoria para todas las rutas protegidas de la API | API |
| `ESDATA_RATE_LIMIT_ENABLED` | No | `true` | Activa o desactiva rate limiting general | API |
| `ESDATA_HSTS_ENABLED` | No | `false` | Activa cabecera HSTS | API |
| `ESDATA_SENTRY_DSN` | No | | DSN de Sentry para errores | API |
| `POSTGRES_BIND_ADDRESS` | No | `127.0.0.1` | Bind local del servicio PostgreSQL | Infra |
| `POSTGRES_USER` | No | `esdata` | Usuario del contenedor PostgreSQL | Infra |
| `POSTGRES_PASSWORD` | Si | | Password del contenedor PostgreSQL | Infra |
| `POSTGRES_DB` | No | `esdata` | Base de datos principal del contenedor PostgreSQL | Infra |
| `POSTGRES_PORT` | No | `5432` | Puerto publicado por PostgreSQL | Infra |
| `API_BIND_ADDRESS` | No | `127.0.0.1` | Bind local del servicio API | Infra |
| `API_PORT` | No | `8000` | Puerto publicado por la API | Infra |
| `WEB_BIND_ADDRESS` | No | `127.0.0.1` | Bind local del frontend web | Infra |
| `WEB_PORT` | No | `3000` | Puerto publicado por el frontend web | Infra |

### BOE / Legislacion

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `BOE_API_BASE` | No | `https://www.boe.es/datosabiertos/api/legislacion-consolidada` | URL base de la API del BOE | Worker BOE |
| `BOE_LEGISLACION_NORMAS` | No | `LIVA,LIRPF,LIS,LGT,ITPAJD,IRNR,IIEE,HL,DAC6,DAC6RD,DAC6EU` | Lista de normas a sincronizar | Worker BOE |
| `SYNC_INTERVAL_SECONDS` | No | `3600` | Intervalo de sincronizacion en segundos | Worker BOE |
| `BOE_SYNC_INTERVAL_SECONDS` | No | `3600` | Intervalo de sincronizacion dedicado para BOE | Worker BOE |
| `BOE_ONLY_BLOCK_IDS` | No | | IDs de bloques BOE a procesar (filtro opcional) | Worker BOE |

### Fuentes de ingestion

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `BDNS_SEED_URLS` | No | | URLs de semilla para BDNS (subvenciones), separadas por coma | Worker BDNS |
| `BDNS_SYNC_INTERVAL_SECONDS` | No | `604800` | Intervalo de sincronizacion semanal para BDNS | Worker BDNS |
| `BORME_SEED_URLS` | No | | URLs de semilla para BORME, separadas por coma | Worker BORME |
| `BORME_SYNC_INTERVAL_SECONDS` | No | `604800` | Intervalo de sincronizacion semanal para BORME | Worker BORME |
| `CNMV_SEED_URLS` | No | | URLs de semilla para CNMV, separadas por coma | Worker CNMV |
| `CNMV_SYNC_INTERVAL_SECONDS` | No | `604800` | Intervalo de sincronizacion semanal para CNMV | Worker CNMV |
| `SEPBLAC_SEED_URLS` | No | | URLs de semilla para SEPBLAC, separadas por coma | Worker SEPBLAC |
| `SEPBLAC_SYNC_INTERVAL_SECONDS` | No | `604800` | Intervalo de sincronizacion semanal para SEPBLAC | Worker SEPBLAC |
| `CENDOJ_SEED_URLS` | No | | URLs de semilla para CENDOJ, separadas por coma | Worker CENDOJ |
| `CENDOJ_SYNC_INTERVAL_SECONDS` | No | `604800` | Intervalo de sincronizacion semanal para CENDOJ | Worker CENDOJ |
| `EURLEX_SEED_URLS` | No | | URLs de semilla para EURLEX (ya no se usan, CELEXs hardcodeados). Dejando por compatibilidad | Worker EURLEX |
| `EURLEX_SYNC_INTERVAL_SECONDS` | No | `604800` | Intervalo de sincronizacion semanal para EURLEX | Worker EURLEX |
| `SPARQL_BASE` | No | `http://publications.europa.eu/webapi/rdf/sparql` | Endpoint SPARQL para discovery de CELEXs nuevos | Worker EURLEX |
| `BDE_SEED_URLS` | No | | URLs de semilla para BDE, separadas por coma | Worker BDE |
| `BDE_SYNC_INTERVAL_SECONDS` | No | `604800` | Intervalo de sincronizacion semanal para BDE | Worker BDE |
| `AEPD_SEED_URLS` | No | | URLs de semilla para AEPD, separadas por coma | Worker AEPD |
| `AEPD_SYNC_INTERVAL_SECONDS` | No | `604800` | Intervalo de sincronizacion semanal para AEPD | Worker AEPD |

### DGT / Doctrina

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `DGT_SSL_VERIFY` | No | `true` | Si verificar SSL contra sede DGT (`true|1|yes`) | Worker DGT |
| `DGT_SYNC_INTERVAL_SECONDS` | No | `604800` | Intervalo de sincronizacion semanal para DGT | Worker DGT |

### TEAC

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `TEAC_SEED_URLS` | No | | URLs de semilla para TEAC, separadas por coma | Worker TEAC |
| `TEAC_SYNC_INTERVAL_SECONDS` | No | `604800` | Intervalo de sincronizacion semanal para TEAC | Worker TEAC |

### Modelos AEAT

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `MODELOS_SYNC_INTERVAL` | No | `86400` | Intervalo de sincronizacion de modelos en segundos (24h) | Worker Modelos |

### Cloudflare / MCP perimetral

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `MCP_API_KEY` | Si fuera de `APP_ENV=test` | | API key obligatoria para proteger `/mcp` por HTTP | MCP Server |
| `MCP_RATE_LIMIT_PER_MINUTE` | No | `60` | Limite de peticiones por minuto en `/mcp` | MCP Server |
| `MCP_SECRET_ACTIVE` | No | | MCP secret actualmente activo | MCP Server |
| `MCP_SECRET_PREVIOUS` | No | | MCP secret anterior (para rotacion) | MCP Server |
| `CLOUDFLARE_ZONE_ID` | No | | ID del zone en Cloudflare | Cloudflare Workers |
| `CLOUDFLARE_API_TOKEN` | No | | Token de API de Cloudflare | Cloudflare Workers |

### Agent monitor

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `AGENT_MONITOR_ENABLED` | No | `false` | Activa el monitor interno de agentes | API |
| `AGENT_MONITOR_INTERVAL` | No | `300` | Intervalo de escaneo en segundos | API |
| `AGENT_MONITOR_ENTIDAD` | No | `sociedad_valores` | Entidad base del monitor | API |
| `AGENT_MONITOR_PRIORIDAD` | No | `media` | Prioridad base del monitor | API |

### Postgres (variables alternativas a DATABASE_URL)

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `PGHOST` | No | | Host de PostgreSQL | SQLAlchemy |
| `PGPORT` | No | `5432` | Puerto de PostgreSQL | SQLAlchemy |
| `PGUSER` | No | | Usuario de PostgreSQL | SQLAlchemy |
| `PGPASSWORD` | No | | Password de PostgreSQL | SQLAlchemy |
| `PGDATABASE` | No | | Nombre de la base de datos | SQLAlchemy |

### Observabilidad / Otros

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `REDIS_URL` | No | | URL de Redis (para cache, colas) | API |
| `SECRET_KEY` | No | | Clave secreta para JWT/sesion | API |
| `LOG_LEVEL` | No | `INFO` | Nivel de log (DEBUG, INFO, WARNING, ERROR) | Todos los servicios |
| `LOG_FORMAT` | No | `text` | Formato de logs (`text` o `json`) | Todos los servicios |
| `SLACK_WEBHOOK_URL` | No | | Webhook de Slack para alertas | Scripts/Workers |

## Uso en Docker Compose

Las variables se pasan a los contenedores via entorno del host o archivo externo fuera del repo.
No se acepta como estado normal de trabajo mantener `.env` runtime dentro del repo.

```yaml
services:
  api:
    environment:
      DATABASE_URL: ${DATABASE_URL}
  worker-boe:
    environment:
      DATABASE_URL: ${DATABASE_URL}
```

O directamente en el docker-compose.yml con `environment:`.

## Notas operativas de seguridad

- La API ya no debe arrancar en modo `fail-open` por omision. Fuera de `APP_ENV=test`, `ESDATA_API_KEY` es obligatoria.
- La superficie `/mcp` tampoco debe arrancar sin `MCP_API_KEY` fuera de `APP_ENV=test`.
- `ESDATA_AUTH_ENABLED` deja de ser un control operativo valido para abrir o cerrar auth; el comportamiento seguro es auth obligatoria en runtime normal.
- `/metrics` no debe considerarse una ruta publica por defecto.

## Seguridad

- Nunca hardcodear secretos en codigo ni en el repo.
- Nunca exponer secretos en frontend (no usar `NEXT_PUBLIC_*`).
- Nunca crear ni conservar `.env` anidados dentro del repo.
- `.env.example` solo contiene valores de ejemplo sin credenciales reales.
- Si aparece un `.env` runtime en el repo, el estado correcto es `BLOQUEADO` hasta eliminarlo o recibir instruccion explicita del usuario.

## Referencias

- `.env.example` — listado canonical de todas las variables
- `apps/api/db.py` — carga de `DATABASE_URL`
- `apps/workers/boe.py` — carga de `BOE_API_BASE`, `SYNC_INTERVAL_SECONDS`
- `apps/workers/runtime.py` — utilidad `get_database_url()`
