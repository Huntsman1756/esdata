# Deploy checklist — Docker Compose en VPS

## Antes del deploy

- [ ] `git pull origin main` en el VPS
- [ ] `sudo mkdir -p /etc/esdata && sudo cp infra/deploy/compose.env.example /etc/esdata/esdata.env && sudo chmod 600 /etc/esdata/esdata.env`
- [ ] Variables críticas que no pueden estar vacías:
  - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
  - `ESDATA_API_KEY`, `MCP_API_KEY`
  - `TEAC_SEED_URLS`, `BDE_SEED_URLS`, `CENDOJ_SEED_URLS`, `AEPD_SEED_URLS`
  - `WORKER_REQUEST_DELAY`
- [ ] `docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml config`
  (valida el compose sin arrancar)

## Deploy

- [ ] `bash scripts/ops/deploy-hetzner.sh`
- [ ] Verificar que `ops` aplico migraciones y gate de esquema:
  `docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic current`
- [ ] Verificar healthcheck postgres:
  `docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml ps postgres`

## Post-deploy smoke test

- [ ] `curl -s https://tudominio.com/health` → `{"status":"ok"}`
- [ ] `curl -s https://tudominio.com/metrics` → 200 con métricas Prometheus
- [ ] `docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml logs backup`
  → confirmar primer backup programado

## Rollback

- [ ] `git revert HEAD && git push`
- [ ] `bash scripts/ops/deploy-hetzner.sh`
