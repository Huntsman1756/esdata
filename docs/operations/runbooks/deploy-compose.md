# Runbook: Deploy con Docker Compose

## Objetivo

Levantar `esdata` fuera de Railway usando `infra/deploy/docker-compose.prod.yml`.

## Prerrequisitos

- Docker y Docker Compose instalados
- salida HTTPS a BOE, DGT, AEAT y TEAC
- fichero `.env` generado a partir de `infra/deploy/compose.env.example`

## Pasos

1. copiar `infra/deploy/compose.env.example` a `infra/deploy/.env`
2. completar `POSTGRES_PASSWORD`, `DATABASE_URL`, `ESDATA_API_BASE_URL` y `TEAC_SEED_URLS`
3. validar el compose:
   - `docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml config`
4. levantar core:
   - `docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml up -d postgres api web worker-boe worker-dgt worker-teac worker-modelos`
5. validar salud:
   - `curl http://localhost:8000/health`
   - `curl http://localhost:8000/status`
   - abrir `http://localhost:3000`

## Cron jobs

Los servicios `cron-*` estan definidos con perfil `cron` y pensados para ejecucion externa programada.

Ejemplos:

- `docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml run --rm cron-boe-daily`
- `docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml run --rm cron-dgt-weekly`
- `docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml run --rm cron-teac-weekly`
- `docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml run --rm cron-modelos-daily`

## Verificaciones post-deploy

1. comprobar `docker compose ps`
2. revisar logs de API y workers
3. comprobar que `sync_log` recibe entradas nuevas
4. validar rutas clave de API y web
