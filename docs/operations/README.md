# Operación

## Objetivo

Centralizar la operación recurrente de `esdata` para reducir dependencia de conocimiento implícito.

## Comprobaciones rápidas

### API

- `curl https://esdata-production.up.railway.app/health`
- `curl https://esdata-production.up.railway.app/status`
- `curl https://esdata-production.up.railway.app/v1/legislacion/cobertura`
- `curl https://esdata-production.up.railway.app/v1/modelos`

### Web

- abrir `https://web-production-ecb5.up.railway.app`
- comprobar que el frontend resuelve datos desde la API esperada

### Railway

- `python verify_railway.py`
- `railway logs --service esdata --tail 50`
- `railway logs --service worker-boe --tail 50`
- `railway logs --service worker-modelos --tail 50`

### Migraciones

- `deploy.yml` ejecuta `alembic upgrade head` antes del deploy de la API.
- En GitHub Actions, las migraciones usan `DATABASE_PUBLIC_URL` si existe y caen a `DATABASE_URL` solo como fallback.
- Para conexiones pÃºblicas desde GitHub Actions, el workflow fuerza `PGSSLMODE=require`.
- El mismo workflow ejecuta `python scripts/verify_schema.py` y falla si falta `modelo_campana_operativa` o las columnas de procedencia.
- Si este paso falla, no debe llegar código nuevo a Railway.

## Validaciones de datos

### Cron y doctrina

- `python scripts/validate-cron-run.py --db-url ...`

### Smoke checks HTTP

- `python scripts/smoke-check.py --base-url https://esdata-production.up.railway.app`

### Bootstrap local de base de datos

- `make bootstrap-db`

## Comandos de trabajo raíz

- `make test`
- `make test-api`
- `make test-workers`
- `make test-web`
- `make lint`
- `make build-web`
- `make smoke-check API_BASE=https://esdata-production.up.railway.app`
- `make worker-boe`
- `make worker-dgt`
- `make worker-teac`
- `make worker-modelos`

## Runbooks

- `docs/operations/OPERATIONS.md`
- `docs/operations/LOGGING.md`
- `docs/operations/DATA-POLICY.md`
- `docs/operations/DEPENDENCIES.md`
- `docs/operations/SECRETS.md`
- `docs/operations/runbooks/deploy-compose.md`
- `docs/operations/runbooks/worker-boe.md`
- `docs/operations/runbooks/worker-dgt-teac.md`
- `docs/operations/runbooks/worker-modelos.md`

## Incidencias conocidas a vigilar

1. cambios de HTML en fuentes externas DGT, TEAC o AEAT
2. semántica poco clara de `DGT_SSL_VERIFY` entre workers
3. necesidad de ampliar observabilidad si aumenta el volumen operativo
