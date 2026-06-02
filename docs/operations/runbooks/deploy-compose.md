# Runbook: Deploy con Docker Compose

## Objetivo

Levantar `esdata` con `infra/deploy/docker-compose.prod.yml`, usando `/etc/esdata/esdata.env` como fichero externo de entorno y el contenedor `ops` como runner de migraciones.

## Ruta recomendada

```bash
cd /srv/esdata
bash scripts/ops/deploy-hetzner.sh
```

El script valida Compose, reconstruye `ops`, ejecuta `alembic upgrade head`, ejecuta `python scripts/maintenance/verify_schema.py` y levanta el runtime con `--build`.

## Comandos manuales equivalentes

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml config
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml build ops
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d postgres
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic upgrade head
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops python scripts/maintenance/verify_schema.py
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d --build api web caddy worker-boe worker-boe-modelos worker-dgt worker-teac worker-modelos worker-bdns worker-borme worker-cnmv worker-sepblac worker-cendoj worker-eurlex worker-bde worker-cdi worker-aepd
curl http://127.0.0.1:8000/health
curl -H "X-API-Key: $ESDATA_API_KEY" http://127.0.0.1:8000/status
```

Si el despliegue es manual y el commit toca `alembic/versions/`, no sustituyas el ultimo paso por `restart api`: la base puede quedar en una revision que la imagen antigua de `api` no conoce y el contenedor abortara durante `alembic upgrade heads`. Reconstruir `ops` antes de migrar y recrear `api` con `--build` despues de migrar es parte del contrato operativo.

## Cron jobs

Los servicios `cron-*` son one-shot. El template activo debe usar `run --rm` para que cada job se conecte a la red Compose existente sin intentar recrear dependencias.

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-boe-daily
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-dgt-weekly
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-teac-weekly
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-modelos-daily
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-aeat-current-daily
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-boe-modelos-daily
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-bdns-weekly
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-borme-weekly
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-cnmv-weekly
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-sepblac-weekly
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-bde-weekly
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-cendoj-weekly
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-aepd-weekly
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-eurlex-weekly
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-regulatory-daily
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm cron-psd2-weekly
```

## Timers systemd

```bash
sudo cp infra/deploy/systemd/*.service /etc/systemd/system/
sudo cp infra/deploy/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now esdata-boe-daily.timer esdata-boe-modelos-daily.timer esdata-modelos-daily.timer esdata-aeat-current-daily.timer esdata-dgt-weekly.timer esdata-teac-weekly.timer esdata-bdns-weekly.timer esdata-borme-weekly.timer esdata-cnmv-weekly.timer esdata-sepblac-weekly.timer esdata-bde-weekly.timer esdata-cendoj-weekly.timer esdata-aepd-weekly.timer esdata-eurlex-weekly.timer esdata-cdi-weekly.timer esdata-reg-watch-daily.timer esdata-psd2-weekly.timer esdata-mcp-validation.timer esdata-mcp-deep-audit.timer
python scripts/ops/worker_scheduler_guard.py check --repo-root /srv/esdata --installed-unit /etc/systemd/system/esdata-job@.service
```

## Agentes de mantenimiento

`esdata-hermes-monitor.service` queda read-only por defecto (`AUTO_RESTART_ENABLED=false`). Si se habilita reinicio automatico, debe fijarse `RESTART_ALLOWLIST` con servicios concretos y nunca dar permisos de escritura a datos fiscales o legales.

`esdata-mcp-validation.timer` ejecuta `scripts/maintenance/mcp_validation_suite.py --read-only` cada hora.

`esdata-mcp-deep-audit.timer` ejecuta `scripts/maintenance/mcp_deep_contract_audit.py` cada dia a las 08:45 Europe/Madrid desde el contenedor `ops`. Este gate es mas caro que la validacion horaria y comprueba tablas, FK, domain availability, HTTP MCP, GPT Actions OpenAPI y contratos semanticos.

Alertmanager usa `/srv/esdata/infra/observability/alertmanager.yml` como ruta operativa y monta secretos desde `/srv/esdata/infra/deploy/secrets/alertmanager`. Para Telegram debe existir `telegram_bot_token` y `TELEGRAM_CHAT_ID` debe estar definido en `/etc/esdata/esdata.env` antes de levantar el perfil `prod`.
