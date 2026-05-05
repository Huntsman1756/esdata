# Instalacion en servidor

## Prerequisitos

- Servidor Linux con 2GB+ RAM, 2+ cores, 10GB+ disco
- Docker Engine 24.0+ instalado
- Docker Compose v2 integrado
- DNS configurado apuntando al servidor
- Puertos 80 y 443 abiertos (o proxies alternativos)

## Paso 1: Instalar Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
sudo systemctl enable --now docker
```

Verificar:

```bash
docker --version
docker compose version
```

## Paso 2: Clonar repo

```bash
cd /srv
sudo git clone https://github.com/Huntsman1756/esdata.git
sudo chown -R "$USER":"$USER" /srv/esdata
cd esdata
```

## Paso 3: Configurar `/etc/esdata/esdata.env`

Partir siempre del template activo del deploy Compose y copiarlo fuera del checkout:

```bash
sudo mkdir -p /etc/esdata
sudo cp infra/deploy/compose.env.example /etc/esdata/esdata.env
sudo chmod 600 /etc/esdata/esdata.env
sudo ${EDITOR:-nano} /etc/esdata/esdata.env
```

Revisar como minimo:

1. `POSTGRES_PASSWORD`
2. `DATABASE_URL` si cambian credenciales, host o nombre de DB
3. `ESDATA_API_KEY`
4. `MCP_API_KEY`
5. `API_DOMAIN`, `WEB_DOMAIN`, `CADDY_EMAIL`
6. `GRAFANA_ADMIN_PASSWORD` y `GRAFANA_ROOT_URL` si vas a activar observabilidad con perfil `prod`
7. `HC_PING_URL_CRON_*` si vas a integrar Healthchecks

No guardar secretos reales dentro de `/srv/esdata` ni en ningun `.env` versionado: el deploy canonico usa `/etc/esdata/esdata.env`.

## Paso 4: Ejecutar deploy canonico

```bash
bash scripts/ops/deploy-hetzner.sh
```

Este script es la ruta canonica de despliegue y exige este orden antes de arrancar la aplicacion:

1. validar `docker compose`
2. construir el contenedor `ops`
3. levantar `postgres`
4. ejecutar `alembic upgrade head`
5. ejecutar `python scripts/maintenance/verify_schema.py`
6. levantar `caddy`, `api`, `web` y todo el worker set continuo definido en Compose

## Paso 5: Levantar servicios manualmente por partes

```bash
# Construir imagenes
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml build

# Levantar Postgres primero
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d postgres

# Verificar estado
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml ps
```

## Paso 6: Migraciones

```bash
# Aplicar migraciones y verificar esquema desde el contenedor ops
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic upgrade head
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops python scripts/maintenance/verify_schema.py
```

## Paso 7: Levantar API y frontend

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d api web caddy worker-boe worker-dgt worker-teac worker-modelos worker-bdns worker-borme worker-cnmv worker-sepblac worker-cendoj worker-eurlex worker-bde worker-aepd
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml ps
```

Si ya ejecutaste `bash scripts/ops/deploy-hetzner.sh`, este paso y el de migraciones ya quedan cubiertos por el flujo canonico.

## Paso 8: Verificar healthchecks

```bash
# Esperar a que todos los servicios esten healthy
sleep 30
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml ps

# Verificar API
curl -s https://api.tudominio.com/health

# Verificar status autenticado
curl -s -H "X-API-Key: $ESDATA_API_KEY" https://api.tudominio.com/status

# Verificar Web
curl -s https://tudominio.com | head -20
```

## Paso 9: Ingestion inicial

```bash
# Ejecutar worker BOE (ingesta principal)
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-boe python boe.py --run-once

# Ejecutar otros workers segun necesidad
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
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm worker-aepd python aepd.py --run-once
```

## Paso 10: Verificar datos

```bash
# Contar documentos ingeridos
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT COUNT(*) FROM version_articulo; SELECT COUNT(*) FROM norma;"
```

## Post-instalacion

### Cron jobs automaticos

Los workers corren en modo continuo por defecto. Los `cron-*` de Compose son one-shot y deben programarse con scheduler externo, preferiblemente `systemd`.

Usar `docker compose run --rm --no-deps cron-*` para que el job one-shot no intente gestionar dependencias ni desmontar la red del stack vivo.

```bash
# Opcion 1: Configurar los systemd timers versionados en el repo
sudo cp infra/deploy/systemd/esdata-job@.service /etc/systemd/system/
sudo cp infra/deploy/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now esdata-boe-daily.timer esdata-modelos-daily.timer esdata-dgt-weekly.timer esdata-teac-weekly.timer esdata-bdns-weekly.timer esdata-borme-weekly.timer esdata-cnmv-weekly.timer esdata-sepblac-weekly.timer
systemctl list-timers --all | grep esdata

# Opcion 2: Usar cron del sistema para cron services adicionales no cubiertos por `infra/deploy/systemd/*.timer`
# Ejemplo manual:
# docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm --no-deps cron-cnmv-weekly
```

Si se usa Healthchecks, cada cron service solo emitira `start`, `success` y `fail`
si su `HC_PING_URL_CRON_*` esta realmente cableado en `infra/deploy/docker-compose.prod.yml` y definido en `/etc/esdata/esdata.env`.

No reiniciar `deploy-alertmanager-1` con la plantilla del repo sin renderizar. En el VPS, `infra/observability/alertmanager.yml` debe contener `bot_token` y `chat_id` ya resueltos.

### Backup automatico

```bash
# Agregar al crontab del servidor
crontab -e

# Backup diario a las 3am
0 3 * * * cd /srv/esdata && docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec postgres pg_dump -U esdata esdata | gzip > /backups/esdata_$(date +\%Y\%m\%d_\%H\%M\%S).sql.gz
0 3 * * * find /backups -name "esdata_*.sql.gz" -mtime +30 -delete
```

### Monitorizacion

```bash
# Ver logs en tiempo real
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml logs -f

# Ver consumo de recursos
docker stats

# Verificar salud de contenedores
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml ps

# Verificar ultimos cron jobs monitorizados
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run --rm \
  -e WORKER_CMD="python --version" \
  ops python scripts/maintenance/validate-cron-run.py --db-url "$DATABASE_URL"
```

## Solucion de problemas comunes

### Postgres no arranca

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml logs postgres
# Verificar que POSTGRES_PASSWORD esta definido correctamente
```

### API no responde

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml logs api
# Verificar DATABASE_URL
# Verificar que postgres esta healthy antes de api
```

### Workers no ingieren datos

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml logs worker-boe
# Verificar que hay migraciones aplicadas
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic current
```

### SSL no funciona

```bash
# Verificar que el dominio apunta al servidor
dig api.tudominio.com

# Verificar Caddy logs
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml logs caddy

# Verificar que puertos 80/443 estan abiertos
sudo ss -tlnp | grep -E ':(80|443)'
```

## Referencias

- `infra/deploy/docker-compose.prod.yml` — configuracion completa
- `infra/deploy/Caddyfile` — reverse proxy
- `infra/deploy/compose.env.example` — variables de referencia
- `docs/deployment/rollback.md` — rollback
- `docs/operations/README.md` — operacion diaria
