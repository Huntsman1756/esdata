# Installation

## Objetivo

Desplegar `esdata` en modo handoff "llave en mano" usando Docker Compose.

## Tiempo objetivo

Con Docker ya instalado y un `.env.prod` preparado, el arranque tecnico base cabe en 1 minuto.

## Prerrequisitos

- Docker Engine
- Docker Compose plugin
- puertos disponibles o remapeados para `postgres`, `api`, `web`
- fichero `infra/deploy/.env.prod` fuera del control del repo

## Paso 1. Preparar entorno

Copiar el template:

```bash
cp infra/deploy/compose.env.example infra/deploy/.env.prod
```

Editar como minimo:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `ESDATA_API_KEY`
- `MCP_API_KEY`
- `API_DOMAIN`
- `WEB_DOMAIN`
- `TEAC_SEED_URLS`
- `CNMV_SEED_URLS`
- `SEPBLAC_SEED_URLS`
- `BDE_SEED_URLS`
- `AEPD_SEED_URLS`

## Paso 2. Validar Compose

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml config
```

## Paso 3. Levantar Postgres

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d postgres
```

## Paso 4. Aplicar migraciones

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic upgrade head
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops python scripts/maintenance/verify_schema.py
```

## Paso 5. Levantar runtime minimo

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d api web caddy worker-boe worker-dgt worker-teac worker-modelos
```

## Paso 6. Smoke check

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml ps
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/status
curl -i -H "Accept: text/event-stream" -H "X-API-Key: $MCP_API_KEY" http://127.0.0.1:8000/mcp
```

## Paso 7. Poblar datos operativos

Arranque minimo recomendado tras bootstrap:

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d worker-cnmv worker-sepblac worker-bde worker-aepd
```

Cron jobs one-shot manuales:

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-cnmv-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-sepblac-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-bde-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-teac-weekly
```

## Reinicio sin perdida de estado

La persistencia depende del volumen `esdata-postgres`.

Reinicio seguro:

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml restart postgres api web
```

Parada y subida:

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml down
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d postgres api web
```

## Criterio de aceptacion minima

- `/health` responde `200`
- `/status` responde `200`
- `api`, `web` y `postgres` sanos
- `ops alembic upgrade head` ejecutado
- `verify_schema.py` devuelve OK
- `/mcp` protegido por API key

## Referencias

- `README.md`
- `docs/deployment/overview.md`
- `docs/operations/runbooks/deploy-compose.md`
- `docs/COMPLIANCE.md`
