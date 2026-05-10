# Instalacion en servidor

## Ruta canonica

El checkout operativo vive en `/srv/esdata` y los secretos reales viven fuera del repo en `/etc/esdata/esdata.env`.

```bash
cd /srv
git clone https://github.com/tuusuario/esdata.git
cd /srv/esdata
sudo install -d -m 700 /etc/esdata
sudo cp infra/deploy/compose.env.example /etc/esdata/esdata.env
sudo chmod 600 /etc/esdata/esdata.env
```

Editar `/etc/esdata/esdata.env` en el host y no commitear secretos.

## Deploy

La ruta soportada es el script canonico:

```bash
cd /srv/esdata
bash scripts/ops/deploy-hetzner.sh
```

El script ejecuta, en orden: `build ops`, `up postgres`, `alembic upgrade head`, `python scripts/maintenance/verify_schema.py`, y despues levanta servicios.

Equivalente manual para diagnostico:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml config
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d postgres
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic upgrade head
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops python scripts/maintenance/verify_schema.py
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d api web caddy worker-boe worker-boe-modelos worker-dgt worker-teac worker-modelos worker-bdns worker-borme worker-cnmv worker-sepblac worker-cendoj worker-eurlex worker-bde worker-cdi worker-aepd
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml ps
```

## Ingestion inicial controlada

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-boe python boe.py --run-once
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-boe-modelos python boe_modelos_worker.py --run-once
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-dgt python dgt.py --run-once
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-teac python teac.py --run-once
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-modelos python aeat_models.py --run-once
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-bdns python bdns.py --run-once
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-borme python borme.py --run-once
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-cnmv python cnmv.py --run-once
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-sepblac python sepblac.py --run-once
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-cendoj python cendoj.py --run-once
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-eurlex python eurlex.py --run-once
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-bde python bde.py --run-once
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-cdi python cdi.py --run-once
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-aepd python aepd.py --run-once
```

## Timers systemd

```bash
sudo cp infra/deploy/systemd/*.service /etc/systemd/system/
sudo cp infra/deploy/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now esdata-boe-daily.timer esdata-boe-modelos-daily.timer esdata-modelos-daily.timer esdata-dgt-weekly.timer esdata-teac-weekly.timer esdata-bdns-weekly.timer esdata-borme-weekly.timer esdata-cnmv-weekly.timer esdata-sepblac-weekly.timer esdata-bde-weekly.timer esdata-cendoj-weekly.timer esdata-aepd-weekly.timer esdata-eurlex-weekly.timer esdata-cdi-weekly.timer esdata-reg-watch-daily.timer esdata-psd2-weekly.timer esdata-mcp-validation.timer
systemctl cat esdata-job@.service
python scripts/ops/worker_scheduler_guard.py check --repo-root /srv/esdata --installed-unit /etc/systemd/system/esdata-job@.service
```

Cron one-shot manual:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-boe-daily
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-cnmv-weekly
```

## Verificacion

```bash
curl -s https://api.tudominio.com/health
curl -s -H "X-API-Key: $ESDATA_API_KEY" https://api.tudominio.com/status
python scripts/maintenance/mcp_validation_suite.py --read-only --base-url https://api.tudominio.com
```
