# Operacion

## Objetivo

Centralizar la operacion recurrente de `esdata` sobre Docker Compose para que otro equipo pueda operar el sistema sin conocimiento implicito.

## Comprobaciones rapidas

### Compose

- `docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml ps`
- `docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml logs --tail 100 api`

### API

- `curl http://127.0.0.1:8000/health`
- `curl http://127.0.0.1:8000/status`
- `curl -H "X-API-Key: $ESDATA_API_KEY" http://127.0.0.1:8000/v1/modelos`

### Web

- abrir `http://127.0.0.1:3000`
- verificar `/buscar`, `/modelo/100`, `/admin/cambios`, `/admin/workflow`

### Migraciones

- `docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic current`
- `docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops python scripts/maintenance/verify_schema.py`

## Scheduling

Los servicios `cron-*` definidos en Compose son jobs one-shot. No planifican su propia ejecucion.

La estrategia activa de scheduling debe ser externa:

- `systemd` via `infra/deploy/systemd/*`, o
- cron del host llamando `docker compose run --rm cron-*`

No usar `docker compose --profile cron up -d` como sustituto de un scheduler.

## Runbooks vivos

- `docs/operations/OPERATIONS.md`
- `docs/operations/runbooks/deploy-compose.md`
- `docs/operations/runbooks/backup-restore.md`
- `docs/operations/runbooks/worker-boe.md`
- `docs/operations/runbooks/worker-dgt-teac.md`
- `docs/operations/runbooks/worker-modelos.md`
- `docs/operations/metrics.md`
- `docs/operations/worker-failures.md`

## Regla de uso

Si un runbook o indice contradice `docs/master-execution-roadmap.md`, `AGENTS.md` o el Compose productivo, debe corregirse antes de considerarse valido para handoff.
