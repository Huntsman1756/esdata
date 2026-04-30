# Deploy checklist — Docker Compose en VPS

## Antes del deploy

- [ ] `git pull origin main` en el VPS
- [ ] `cp infra/deploy/compose.env.example .env` y verificar variables
- [ ] Variables críticas que no pueden estar vacías:
  - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
  - `SECRET_KEY`, `ESDATA_API_KEY`, `MCP_API_KEY`
  - `TEAC_SEED_URLS`, `BDE_SEED_URLS`, `CENDOJ_SEED_URLS`, `AEPD_SEED_URLS`
  - `WORKER_REQUEST_DELAY`
- [ ] `docker compose -f infra/deploy/docker-compose.prod.yml config`
  (valida el compose sin arrancar)

## Deploy

- [ ] `docker compose --env-file infra/deploy/.env.prod --profile prod -f infra/deploy/docker-compose.prod.yml up -d --build`
- [ ] Verificar que api arranca con migraciones:
  `docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml logs api | grep MIGRATION`
- [ ] Verificar healthcheck postgres:
  `docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml ps postgres`

## Post-deploy smoke test

- [ ] `curl -s https://tudominio.com/health` → `{"status":"ok"}`
- [ ] `curl -s https://tudominio.com/metrics` → 200 con métricas Prometheus
- [ ] `docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml logs backup`
  → confirmar primer backup programado

## Rollback

- [ ] `git revert HEAD && git push`
- [ ] `docker compose --env-file infra/deploy/.env.prod --profile prod -f infra/deploy/docker-compose.prod.yml up -d --build`
