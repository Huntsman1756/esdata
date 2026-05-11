# esdata

Plataforma de datos y consulta fiscal-regulatoria con API FastAPI, frontend Next.js, workers de ingestion por fuente y despliegue de referencia en Docker Compose.

## Estado actual

- Despliegue de referencia activo: Docker Compose.
- Fuente activa de estado y roadmap: `docs/master-execution-roadmap.md`.
- Documentacion operativa viva: `docs/`.
- Referencias antiguas de Railway o handoffs previos: solo historicas en `docs/archive/`.

## Componentes

- `apps/api` — backend FastAPI y superficies `/v1/*`, `/mcp`, `/health`, `/status`
- `apps/web` — UI interna Next.js
- `apps/workers` — workers por fuente y entrypoint comun para crons/healthchecks
- `alembic` — migraciones oficiales del esquema
- `infra/deploy` — Compose productivo, Caddy, systemd y contenedor `ops`
- `scripts` — tooling, backup, despliegue y verificaciones
- `docs` — manual, operaciones, despliegue y roadmap

## Arranque rapido

1. Copiar `infra/deploy/compose.env.example` a `/etc/esdata/esdata.env` fuera del repo para un entorno controlado.
2. Ajustar secretos, dominios y seeds.
3. Validar Compose:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml config
```

O usar directamente la ruta canonica:

```bash
bash scripts/ops/deploy-hetzner.sh
```

4. Levantar Postgres y aplicar migraciones:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d postgres
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic upgrade head
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops python scripts/maintenance/verify_schema.py
```

5. Levantar runtime:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d api web caddy worker-boe worker-boe-modelos worker-dgt worker-teac worker-modelos worker-bdns worker-borme worker-cnmv worker-sepblac worker-cendoj worker-eurlex worker-bde worker-cdi worker-aepd
```

## Comandos utiles

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml ps
curl -s http://127.0.0.1:8000/health
curl -s -H "X-API-Key: $ESDATA_API_KEY" http://127.0.0.1:8000/status
```

## Documentacion clave

- `docs/master-execution-roadmap.md` — estado activo y siguiente paso
- `docs/deployment/server-installation.md` — instalacion y despliegue
- `docs/INSTALLATION.md` — despliegue rapido de handoff
- `docs/deployment/overview.md` — topologia y estrategia operativa
- `docs/COMPLIANCE.md` — estado de cumplimiento y gaps reales
- `docs/operations/README.md` — indice de operacion diaria
- `docs/manual-usuario/README.md` — manual vivo para uso e integracion
- `docs/environment-variables.md` — contrato de variables

## Handoff

Para pasar el proyecto a otro equipo, el baseline debe incluir:

- este `README.md`
- `docs/master-execution-roadmap.md`
- `docs/deployment/*`
- `docs/operations/*`
- `docs/manual-usuario/*`

Ningun documento fuera de esas rutas debe tratarse como fuente operativa primaria salvo que el roadmap lo indique expresamente.
