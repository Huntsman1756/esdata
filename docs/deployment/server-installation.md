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
cd /opt
sudo git clone https://github.com/tuusuario/esdata.git
cd esdata
```

## Paso 3: Configurar `.env.prod`

Crear archivo `infra/deploy/.env.prod` a partir de `infra/deploy/compose.env.example`:

```bash
cat > infra/deploy/.env.prod << 'EOF'
# --- Base de datos ---
POSTGRES_USER=esdata
POSTGRES_PASSWORD=<contraseña_segura>
POSTGRES_DB=esdata
DATABASE_URL=postgresql+psycopg://esdata:${POSTGRES_PASSWORD}@postgres:5432/esdata

# --- Dominios ---
API_DOMAIN=api.tudominio.com
WEB_DOMAIN=tudominio.com
CADDY_EMAIL=tuemail@ejemplo.com

# --- Frontend ---
ESDATA_API_BASE_URL=https://api.tudominio.com
ESDATA_API_KEY=<api_key_obligatoria>

# --- BOE ---
BOE_API_BASE=https://www.boe.es/datosabiertos/api/legislacion-consolidada
BOE_LEGISLACION_NORMAS=LIVA,LIRPF,LIS,LGT,ITPAJD,IRNR,IIEE,HL,DAC6,DAC6RD,DAC6EU
BOE_SYNC_INTERVAL_SECONDS=3600

# --- Fuentes ---
BDNS_SEED_URLS=
BORME_SEED_URLS=
CNMV_SEED_URLS=https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133
SEPBLAC_SEED_URLS=https://www.sepblac.es/es/,https://www.sepblac.es/es/publicaciones/
CENDOJ_SEED_URLS=
EURLEX_SEED_URLS=
BDE_SEED_URLS=https://www.bde.es/wbe/es/publicaciones/informacion-estadistica/
AEPD_SEED_URLS=

# --- DGT ---
DGT_SSL_VERIFY=false

# --- TEAC ---
TEAC_SEED_URLS=https://serviciostelematicosext.hacienda.gob.es/TEAC/DYCTEA/

# --- Modelos ---
MODELOS_SYNC_INTERVAL=86400

# --- Cloudflare/MCP ---
MCP_API_KEY=<mcp_api_key_obligatoria>
MCP_SECRET_ACTIVE=
MCP_SECRET_PREVIOUS=
CLOUDFLARE_ZONE_ID=
CLOUDFLARE_API_TOKEN=

# --- Healthchecks (opcional, recomendado para crons) ---
HC_PING_URL_CRON_BOE_DAILY=
HC_PING_URL_CRON_DGT_WEEKLY=
HC_PING_URL_CRON_TEAC_WEEKLY=
HC_PING_URL_CRON_MODELOS_DAILY=
HC_PING_URL_CRON_BDNS_WEEKLY=
HC_PING_URL_CRON_BORME_WEEKLY=
HC_PING_URL_CRON_CNMV_WEEKLY=
HC_PING_URL_CRON_SEPBLAC_WEEKLY=
HC_PING_URL_CRON_BDE_WEEKLY=
HC_PING_URL_CRON_CENDOJ_WEEKLY=
HC_PING_URL_CRON_AEPD_WEEKLY=
HC_PING_URL_CRON_EURLEX_WEEKLY=
EOF
```

## Paso 4: Levantar servicios

```bash
# Construir imagenes
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml build

# Levantar Postgres primero
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d postgres

# Verificar estado
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml ps
```

## Paso 5: Verificar healthchecks

```bash
# Esperar a que todos los servicios esten healthy
sleep 30
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml ps

# Verificar API
curl -s https://api.tudominio.com/health

# Verificar Web
curl -s https://tudominio.com | head -20
```

## Paso 6: Migraciones

```bash
# Aplicar migraciones y verificar esquema desde el contenedor ops
docker compose -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic upgrade head
docker compose -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops python scripts/maintenance/verify_schema.py
```

## Paso 7: Levantar API y frontend

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d api web caddy worker-boe worker-dgt worker-teac worker-modelos worker-bdns worker-borme worker-cnmv worker-sepblac worker-cendoj worker-eurlex worker-bde worker-aepd
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml ps
```

## Paso 8: Ingestion inicial

```bash
# Ejecutar worker BOE (ingesta principal)
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm worker-boe python boe.py --run-once

# Ejecutar otros workers segun necesidad
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm worker-dgt python dgt.py --run-once
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm worker-modelos python aeat_models.py --run-once
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm worker-cnmv python cnmv.py --run-once
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm worker-sepblac python sepblac.py --run-once
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm worker-bde python bde.py --run-once
```

## Paso 9: Verificar datos

```bash
# Contar documentos ingeridos
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT COUNT(*) FROM version_articulo; SELECT COUNT(*) FROM norma;"
```

## Post-instalacion

### Cron jobs automaticos

Los workers corren en modo continuo por defecto. Para ejecutarlos como cron:

```bash
# Opcion 1: Ejecutar cron manualmente
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-boe-daily

# Opcion 2: Instalar timers systemd para todos los cron soportados
sudo cp infra/deploy/systemd/esdata-job@.service /etc/systemd/system/
sudo cp infra/deploy/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now esdata-boe-daily.timer esdata-modelos-daily.timer esdata-dgt-weekly.timer esdata-teac-weekly.timer esdata-bdns-weekly.timer esdata-borme-weekly.timer esdata-cnmv-weekly.timer esdata-sepblac-weekly.timer esdata-bde-weekly.timer esdata-cendoj-weekly.timer esdata-aepd-weekly.timer esdata-eurlex-weekly.timer
systemctl cat esdata-job@.service
python scripts/ops/worker_scheduler_guard.py check --repo-root /srv/esdata --installed-unit /etc/systemd/system/esdata-job@.service

# Opcion 3: Usar cron del sistema con docker compose run
```

Si se usa Healthchecks, cada servicio `cron-*` enviara `start`, `success` y `fail`
automaticamente cuando `HC_PING_URL_CRON_*` este definido en `.env`.

En el VPS la materializacion operativa del entorno vive en `/etc/esdata/esdata.env`. `infra/deploy/.env.prod` sigue siendo la referencia del repo para Compose y documentacion, pero el unit instalado debe apuntar al fichero externalizado del host. Si `systemctl cat esdata-job@.service` muestra `--no-deps`, hay drift operativo y debe corregirse antes de confiar en los cron semanales.

### Backup automatico

```bash
# Agregar al crontab del servidor
crontab -e

# Backup diario a las 3am
0 3 * * * cd /opt/esdata && docker compose -f infra/deploy/docker-compose.prod.yml exec postgres pg_dump -U esdata esdata | gzip > /backups/esdata_$(date +\%Y\%m\%d_\%H\%M\%S).sql.gz
0 3 * * * find /backups -name "esdata_*.sql.gz" -mtime +30 -delete
```

### Monitorizacion

```bash
# Ver logs en tiempo real
docker compose -f infra/deploy/docker-compose.prod.yml logs -f

# Ver consumo de recursos
docker stats

# Verificar salud de contenedores
docker compose -f infra/deploy/docker-compose.prod.yml ps

# Verificar ultimos cron jobs monitorizados
docker compose -f infra/deploy/docker-compose.prod.yml run --rm \
  -e WORKER_CMD="python --version" \
  ops python scripts/maintenance/validate-cron-run.py --db-url "$DATABASE_URL"
```

## Solucion de problemas comunes

### Postgres no arranca

```bash
docker compose -f infra/deploy/docker-compose.prod.yml logs postgres
# Verificar que POSTGRES_PASSWORD esta definido correctamente
```

### API no responde

```bash
docker compose -f infra/deploy/docker-compose.prod.yml logs api
# Verificar DATABASE_URL
# Verificar que postgres esta healthy antes de api
```

### Workers no ingieren datos

```bash
docker compose -f infra/deploy/docker-compose.prod.yml logs worker-boe
# Verificar que hay migraciones aplicadas
docker compose -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic current
```

### SSL no funciona

```bash
# Verificar que el dominio apunta al servidor
dig api.tudominio.com

# Verificar Caddy logs
docker compose -f infra/deploy/docker-compose.prod.yml logs caddy

# Verificar que puertos 80/443 estan abiertos
sudo ss -tlnp | grep -E ':(80|443)'
```

## Referencias

- `infra/deploy/docker-compose.prod.yml` — configuracion completa
- `infra/deploy/Caddyfile` — reverse proxy
- `infra/deploy/compose.env.example` — variables de referencia
- `docs/deployment/rollback.md` — rollback
- `docs/operations/README.md` — operacion diaria
