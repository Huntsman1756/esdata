# Installation

## Objetivo

Desplegar `esdata` en modo handoff "llave en mano" usando Docker Compose.

## Tiempo objetivo

Con Docker ya instalado y `/etc/esdata/esdata.env` preparado, el arranque tecnico base cabe en 1 minuto.

## Prerrequisitos

- Docker Engine
- Docker Compose plugin
- puertos disponibles o remapeados para `postgres`, `api`, `web`
- fichero `/etc/esdata/esdata.env` fuera del control del repo y fuera del checkout

## Paso 1. Preparar entorno

Copiar el template:

```bash
sudo mkdir -p /etc/esdata
sudo cp infra/deploy/compose.env.example /etc/esdata/esdata.env
sudo chmod 600 /etc/esdata/esdata.env
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
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml config
```

## Paso 2.1. Despliegue canonico recomendado

```bash
bash scripts/ops/deploy-hetzner.sh
```

Este script ya ejecuta `build ops -> up postgres -> alembic upgrade head -> verify_schema.py -> up servicios` y es la ruta preferida para el deploy real.

## Paso 3. Levantar Postgres

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d postgres
```

## Paso 4. Aplicar migraciones

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic upgrade head
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops python scripts/maintenance/verify_schema.py
```

## Paso 5. Levantar runtime minimo

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d api web caddy worker-boe worker-dgt worker-teac worker-modelos worker-bdns worker-borme worker-cnmv worker-sepblac worker-cendoj worker-eurlex worker-bde worker-aepd
```

## Paso 6. Smoke check

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml ps
curl -s http://127.0.0.1:8000/health
curl -s -H "X-API-Key: $ESDATA_API_KEY" http://127.0.0.1:8000/status
curl -i -H "Accept: text/event-stream" -H "X-API-Key: $MCP_API_KEY" http://127.0.0.1:8000/mcp
```

## Paso 7. Poblar datos operativos

Arranque recomendado tras bootstrap si no usaste el script canonico:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d api web caddy worker-boe worker-dgt worker-teac worker-modelos worker-bdns worker-borme worker-cnmv worker-sepblac worker-cendoj worker-eurlex worker-bde worker-aepd
```

Cron jobs one-shot manuales:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-cnmv-weekly
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-sepblac-weekly
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-bde-weekly
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-teac-weekly
```

## Reinicio sin perdida de estado

La persistencia depende del volumen `esdata-postgres`.

Reinicio seguro:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml restart postgres api web
```

Parada y subida:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml down
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d postgres api web
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
