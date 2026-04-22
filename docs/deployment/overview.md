# Deployment Overview

## Estado actual

El despliegue de referencia hoy es Railway, con servicios declarados en `railway.toml` y workflows en `.github/workflows/`.

## Objetivo de futuro

Mantener compatibilidad con Railway mientras se prepara un despliegue portable para servidor empresarial.

## Componentes desplegables

- API FastAPI
- Web Next.js
- Workers continuos
- Cron jobs
- PostgreSQL
- Cloudflare opcional para cache y proteccion MCP

## Recomendacion

Primer aterrizaje empresarial recomendado:

1. contenedores por servicio
2. PostgreSQL separado
3. scheduler externo para crons
4. proxy inverso corporativo
5. secretos gestionados fuera del repo

## Artefactos disponibles en el repo

- `infra/deploy/docker-compose.prod.yml`
- `infra/deploy/Caddyfile`
- `infra/deploy/Dockerfile.ops`
- `infra/deploy/systemd/*`
- `infra/deploy/compose.env.example`
- `docs/operations/runbooks/deploy-compose.md`
- `docs/deployment/railway-to-hetzner-v2.md`
- `alembic.ini`
- `alembic/versions/20260416_0001_baseline_schema.py`
