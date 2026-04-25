# Variables de entorno

## Resumen

esdata usa variables de entorno para configurar todas las dependencias externas y el comportamiento de los servicios. Las variables se cargan via `.env` (local) o desde el orchestrator Docker.

## Archivo de referencia

`.env.example` contiene todas las variables documentadas del proyecto.

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

### BOE / Legislacion

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `BOE_API_BASE` | No | `https://www.boe.es/datosabiertos/api/legislacion-consolidada` | URL base de la API del BOE | Worker BOE |
| `BOE_LEGISLACION_NORMAS` | No | `LIVA,LIRPF,LIS,LGT,ITPAJD,IRNR,IIEE,HL,DAC6,DAC6RD,DAC6EU` | Lista de normas a sincronizar | Worker BOE |
| `SYNC_INTERVAL_SECONDS` | No | `3600` | Intervalo de sincronizacion en segundos | Worker BOE |
| `BOE_ONLY_BLOCK_IDS` | No | | IDs de bloques BOE a procesar (filtro opcional) | Worker BOE |

### Fuentes de ingestion

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `BDNS_SEED_URLS` | No | | URLs de semilla para BDNS (subvenciones), separadas por coma | Worker BDNS |
| `BORME_SEED_URLS` | No | | URLs de semilla para BORME, separadas por coma | Worker BORME |
| `CNMV_SEED_URLS` | No | | URLs de semilla para CNMV, separadas por coma | Worker CNMV |
| `SEPBLAC_SEED_URLS` | No | | URLs de semilla para SEPBLAC, separadas por coma | Worker SEPBLAC |
| `CENDOJ_SEED_URLS` | No | | URLs de semilla para CENDOJ, separadas por coma | Worker CENDOJ |
| `EURLEX_SEED_URLS` | No | | URLs de semilla para EURLEX, separadas por coma | Worker EURLEX |
| `BDE_SEED_URLS` | No | | URLs de semilla para BDE, separadas por coma | Worker BDE |
| `AEPD_SEED_URLS` | No | | URLs de semilla para AEPD, separadas por coma | Worker AEPD |

### DGT / Doctrina

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `DGT_SSL_VERIFY` | No | `false` | Si verificar SSL contra sede DGT (`true|1|yes`) | Worker DGT |

### TEAC

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `TEAC_SEED_URLS` | No | | URLs de semilla para TEAC, separadas por coma | Worker TEAC |

### Modelos AEAT

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `MODELOS_SYNC_INTERVAL` | No | `86400` | Intervalo de sincronizacion de modelos en segundos (24h) | Worker Modelos |

### Cloudflare / MCP perimetral

| Variable | Requerida | Default | Descripcion | Uso |
|----------|-----------|---------|-------------|-----|
| `MCP_SECRET_ACTIVE` | No | | MCP secret actualmente activo | MCP Server |
| `MCP_SECRET_PREVIOUS` | No | | MCP secret anterior (para rotacion) | MCP Server |
| `CLOUDFLARE_ZONE_ID` | No | | ID del zone en Cloudflare | Cloudflare Workers |
| `CLOUDFLARE_API_TOKEN` | No | | Token de API de Cloudflare | Cloudflare Workers |

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
| `SLACK_WEBHOOK_URL` | No | | Webhook de Slack para alertas | Scripts/Workers |

## Uso en Docker Compose

Las variables se pasan a los contenedores via archivo `.env` en la raiz del proyecto:

```yaml
services:
  api:
    env_file:
      - .env
  worker-boe:
    env_file:
      - .env
```

O directamente en el docker-compose.yml con `environment:`.

## Seguridad

- Nunca hardcodear secretos en codigo ni en el repo.
- Nunca exponer secretos en frontend (no usar `NEXT_PUBLIC_*`).
- `.env` esta en `.gitignore`.
- `.env.example` solo contiene valores de ejemplo sin credenciales reales.

## Referencias

- `.env.example` — listado canonical de todas las variables
- `apps/api/db.py` — carga de `DATABASE_URL`
- `apps/workers/boe.py` — carga de `BOE_API_BASE`, `SYNC_INTERVAL_SECONDS`
- `apps/workers/runtime.py` — utilidad `get_database_url()`
