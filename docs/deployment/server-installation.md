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

## Paso 3: Configurar .env

Crear archivo `.env` en la raiz del repo:

```bash
cat > .env << 'EOF'
# --- Base de datos ---
POSTGRES_USER=esdata
POSTGRES_PASSWORD=<contraseña_segura>
POSTGRES_DB=esdata
DATABASE_URL=postgresql+psycopg://esdata:${POSTGRES_PASSWORD}@localhost:5432/esdata

# --- Dominios ---
API_DOMAIN=api.tudominio.com
WEB_DOMAIN=tudominio.com
CADDY_EMAIL=tuemail@ejemplo.com

# --- Frontend ---
ESDATA_API_BASE_URL=https://api.tudominio.com

# --- BOE ---
BOE_API_BASE=https://www.boe.es/datosabiertos/api/legislacion-consolidada
BOE_LEGISLACION_NORMAS=LIVA,LIRPF,LIS,LGT,ITPAJD,IRNR,IIEE,HL,DAC6,DAC6RD,DAC6EU
SYNC_INTERVAL_SECONDS=3600

# --- Fuentes ---
BDNS_SEED_URLS=
BORME_SEED_URLS=
CNMV_SEED_URLS=
SEPBLAC_SEED_URLS=
CENDOJ_SEED_URLS=
EURLEX_SEED_URLS=
BDE_SEED_URLS=
AEPD_SEED_URLS=

# --- DGT ---
DGT_SSL_VERIFY=false

# --- TEAC ---
TEAC_SEED_URLS=

# --- Modelos ---
MODELOS_SYNC_INTERVAL=86400

# --- Cloudflare/MCP ---
MCP_SECRET_ACTIVE=
MCP_SECRET_PREVIOUS=
CLOUDFLARE_ZONE_ID=
CLOUDFLARE_API_TOKEN=
EOF
```

## Paso 4: Levantar servicios

```bash
# Construir imagenes
docker compose -f infra/deploy/docker-compose.prod.yml build

# Levantar todo
docker compose -f infra/deploy/docker-compose.prod.yml up -d

# Verificar estado
docker compose -f infra/deploy/docker-compose.prod.yml ps
```

## Paso 5: Verificar healthchecks

```bash
# Esperar a que todos los servicios esten healthy
sleep 30
docker compose -f infra/deploy/docker-compose.prod.yml ps

# Verificar API
curl -s https://api.tudominio.com/health

# Verificar Web
curl -s https://tudominio.com | head -20
```

## Paso 6: Migraciones

```bash
# Aplicar migraciones Alembic
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic upgrade head
```

## Paso 7: Ingestion inicial

```bash
# Ejecutar worker BOE (ingesta principal)
docker compose -f infra/deploy/docker-compose.prod.yml run --rm worker-boe python boe.py --run-once

# Ejecutar otros workers segun necesidad
docker compose -f infra/deploy/docker-compose.prod.yml run --rm worker-dgt python dgt.py --run-once
docker compose -f infra/deploy/docker-compose.prod.yml run --rm worker-modelos python modelos.py --run-once
```

## Paso 8: Verificar datos

```bash
# Contar documentos ingeridos
docker compose -f infra/deploy/docker-compose.prod.yml exec db psql -U esdata -d esdata -c \
  "SELECT COUNT(*) FROM version_articulo; SELECT COUNT(*) FROM norma;"
```

## Post-instalacion

### Cron jobs automaticos

Los workers corren en modo continuo por defecto. Para ejecutarlos como cron:

```bash
# Opcion 1: Usar perfil cron (contenedores one-shot)
docker compose -f infra/deploy/docker-compose.prod.yml --profile cron up -d

# Opcion 2: Configurar systemd timers (ver systemd/)
# Opcion 3: Usar cron del sistema con docker compose run
```

### Backup automatico

```bash
# Agregar al crontab del servidor
crontab -e

# Backup diario a las 3am
0 3 * * * cd /opt/esdata && docker compose -f infra/deploy/docker-compose.prod.yml exec db pg_dump -U esdata esdata | gzip > /backups/esdata_$(date +\%Y\%m\%d_\%H\%M\%S).sql.gz
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
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic current
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
