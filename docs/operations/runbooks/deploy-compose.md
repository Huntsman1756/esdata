# Runbook: Deploy con Docker Compose

## Objetivo

Levantar `esdata` en un servidor usando `infra/deploy/docker-compose.prod.yml` y el contenedor `ops` como runner oficial de migraciones/verificaciones.

## Prerrequisitos

- Docker Engine y Docker Compose v2
- fichero de entorno externo o `infra/deploy/.env.prod` basado en `infra/deploy/compose.env.example`
- salida HTTPS a BOE, DGT, TEAC, CNMV, SEPBLAC, BDE y fuentes activadas

## Pasos

1. preparar el fichero de entorno
2. validar el compose
3. levantar `postgres`
4. ejecutar migraciones y `verify_schema`
5. levantar `api`, `web`, `caddy` y workers base
6. verificar `/health`, `/status` y rutas web principales

## Comandos

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml config
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d postgres
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic upgrade head
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops python scripts/maintenance/verify_schema.py
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d api web caddy worker-boe worker-dgt worker-teac worker-modelos
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/status
```

## Cron jobs

Los servicios `cron-*` son jobs one-shot y necesitan scheduler externo.

En produccion, la unidad instalada debe cargar el entorno real del host desde `/etc/esdata/esdata.env`.

```bash
sudo install -m 0644 infra/deploy/systemd/esdata-job@.service /etc/systemd/system/esdata-job@.service
sudo install -m 0644 infra/deploy/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now esdata-boe-daily.timer esdata-modelos-daily.timer esdata-dgt-weekly.timer esdata-teac-weekly.timer esdata-bdns-weekly.timer esdata-borme-weekly.timer esdata-cnmv-weekly.timer esdata-sepblac-weekly.timer esdata-bde-weekly.timer esdata-cendoj-weekly.timer esdata-aepd-weekly.timer esdata-eurlex-weekly.timer
systemctl cat esdata-job@.service
systemctl list-timers --all | grep esdata
```

Si se gestionan con `systemd`, comprobar siempre la unidad efectiva instalada antes de validar un timer:

```bash
systemctl cat esdata-job@.service
```

Una unidad instalada con `docker compose run --rm --no-deps %i` no es valida para este stack porque puede sacar los jobs semanales de la red `deploy_esdata-internal`.

La validacion correcta del unit instalado es doble: sin `--no-deps` y con `--env-file /etc/esdata/esdata.env`.

Ejemplos manuales:

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-boe-daily
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-dgt-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-teac-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-modelos-daily
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-bdns-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-borme-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-cnmv-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-sepblac-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-bde-weekly
```

Tras cambiar `infra/observability/alerts.yml` en este stack hay que reiniciar o recrear Prometheus para que recargue la regla `WorkerSilent`; editar el repo no basta.

`/metrics` refresca `worker_stale_status` desde `sync_log` en cada scrape del endpoint, y `/status` expone el mismo contrato de stale si hace falta validar el payload HTTP humano.

Validacion operativa minima:

1. el unit instalado debe ejecutar `docker compose --env-file /etc/esdata/esdata.env -f /srv/esdata/infra/deploy/docker-compose.prod.yml run --rm %i`
2. `WorkerSilent` debe evaluarse sobre `worker_stale_status`, no sobre una ventana fija de `48h`
3. tras cambiar `infra/observability/alerts.yml`, hay que reiniciar o recrear `prometheus`
4. `curl /metrics | grep worker_stale_status` debe reflejar el estado recalculado desde `sync_log`

## Verificaciones post-deploy

1. `docker compose ... ps`
2. `curl /health`
3. `curl /status`
4. `curl /metrics | grep worker_stale_status`
5. comprobar `sync_log`
6. revisar logs de `api` y workers activos
