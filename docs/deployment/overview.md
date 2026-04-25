# Despliegue — Overview

## Resumen

esdata se despliega con Docker Compose sin dependencias de plataforma PaaS.
Todo corre en una sola VM o servidor con Docker Engine instalado.

## Arquitectura de despliegue

```
                    ┌──────────┐
                    │  Caddy   │
                    │  (TLS)   │
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
        ┌─────▼────┐ ┌──▼────┐ ┌───▼────┐
        │  API     │ │  Web  │ │ Workers│
        │ :8000    │ │ :3000 │ │ :8000  │
        └─────┬────┘ └──┬────┘ └───┬────┘
              │          │         │
              └──────────┼─────────┘
                         │
                   ┌─────▼─────┐
                   │ Postgres  │
                   │ :5432     │
                   │ + pgvector│
                   └───────────┘
```

## Servicios

| Servicio | Imagen | Puerto | Memoria estimada | CPU estimada |
|----------|--------|--------|------------------|--------------|
| `caddy` | `caddy:2-alpine` | 80/443 | <5MB | <0.1 |
| `postgres` | `pgvector/pgvector:pg16` | 5432 | 512MB-2GB | 0.5-2 |
| `api` | `apps/api:Dockerfile` | 8000 | 128-512MB | 0.2-0.5 |
| `web` | `apps/web:Dockerfile` | 3000 | 64-256MB | 0.1-0.3 |
| `worker-*` (13x) | `apps/workers:Dockerfile` | — | 64-256MB c/u | 0.1-0.5 c/u |

### Requerimientos minima de servidor

- **RAM**: 2GB (funcional), 4GB (recomendado)
- **CPU**: 2 cores (funcional), 4 cores (recomendado)
- **Disco**: 10GB minimo (DB + volumes)
- **SO**: Ubuntu 22.04+, Debian 12+, o equivalente Linux
- **Docker**: Engine 24.0+, Compose v2

## Perfiles Docker Compose

El `docker-compose.prod.yml` usa perfiles para activar/desactivar servicios:

| Perfil | Servicios | Uso |
|--------|-----------|-----|
| default | api, web, postgres, caddy, 13 workers | Produccion completa |
| `cron` | + 8 contenedores cron (one-shot) | Ejecucion manual de workers |
| `ops` | + contenedor ops (alembic, backup) | Operaciones de admin |

### Ejecutar con perfil cron

```bash
docker compose -f infra/deploy/docker-compose.prod.yml --profile cron up -d
```

### Ejecutar con perfil ops

```bash
docker compose -f infra/deploy/docker-compose.prod.yml --profile ops up -d
```

## Variables de entorno obligatorias

Deben definirse en `.env` o `compose.env`:

| Variable | Requerida | Descripcion |
|----------|-----------|-------------|
| `DATABASE_URL` | Si | URL Postgres (o POSTGRES_USER + POSTGRES_PASSWORD + POSTGRES_DB) |
| `POSTGRES_PASSWORD` | Si | Password de Postgres |
| `API_DOMAIN` | Si | Dominio para API |
| `WEB_DOMAIN` | Si | Dominio para Web |
| `CADDY_EMAIL` | No | Email para certificados Let's Encrypt |
| `ESDATA_API_BASE_URL` | Si | URL API para el frontend |

## Flujo de despliegue

1. Preparar servidor (Docker + DNS + SSL)
2. Copiar repo y `.env`
3. Ejecutar `docker compose up -d`
4. Verificar healthchecks
5. Ejecutar migraciones Alembic
6. Ejecutar workers de ingestion inicial

## Flujo de actualizacion

1. `git pull` en el servidor
2. `docker compose build` (si hay cambios en imagenes)
3. `docker compose up -d`
4. `docker compose exec api alembic upgrade head`
5. Verificar healthchecks

## Flujo de rollback

1. `docker compose down`
2. Cambiar imagen/tag a version anterior
3. `docker compose up -d`
4. Aplicar migraciones downgrade si es necesario
5. Restaurar backup de DB si hubo cambios de schema

## Referencias

- `infra/deploy/docker-compose.prod.yml` — configuracion de despliegue
- `infra/deploy/Caddyfile` — reverse proxy y SSL
- `infra/deploy/Dockerfile.ops` — contenedor de operaciones
- `infra/deploy/systemd/` — unit files opcionales
- `infra/deploy/compose.env.example` — variables de entorno de referencia
- `docs/database.md` — estrategia de migraciones
