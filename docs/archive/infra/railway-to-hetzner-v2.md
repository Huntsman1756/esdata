# [HISTORICAL] Migracion Railway -> Hetzner Cloud (v2)

> Documento historico de transicion. No usar como guia de despliegue activa. La referencia actual es Docker Compose y el estado activo vive en `docs/master-execution-roadmap.md`.

## Objetivo

Esta guia convierte la propuesta inicial de migracion a Hetzner en un plan ejecutable contra el repo real.

El objetivo no es reescribir la arquitectura. El objetivo es:

- salir de Railway con coste mensual mucho mas predecible
- reaprovechar el `docker-compose.prod.yml` ya existente
- mantener `Postgres`, `api`, `web` y workers en una sola VM al inicio
- conservar un camino de rollback sencillo mientras Railway sigue encendido

## Por que esta v2 sustituye a la propuesta anterior

La propuesta inicial iba en la direccion correcta, pero tenia varios desajustes con el repo:

- trataba `worker-boe` como si fuera un job `oneshot`, cuando en realidad es un proceso continuo
- asumia que el contenedor `api` podia ejecutar `alembic upgrade head` y `scripts/maintenance/verify_schema.py`, pero la imagen de `apps/api` no contiene `alembic/` ni `scripts/`
- usaba un inventario parcial de servicios, cuando el repo ya tiene slices adicionales (`BDNS`, `BORME`, `CNMV`, `SEPBLAC`, `modelos`)
- mezclaba nombres de base de datos y usuarios que no coinciden con `compose.env.example`

Esta v2 corrige esos puntos.

## Arquitectura objetivo

### VM unica inicial

- proveedor: Hetzner Cloud
- tamano recomendado inicial: `CPX31`
- sistema operativo: Ubuntu 24.04 LTS

### Servicios en la VM

- `caddy`
- `postgres`
- `api`
- `web`
- `worker-boe`
- `worker-dgt`
- `worker-teac`
- `worker-modelos`
- `worker-bdns`
- `worker-borme`
- `worker-cnmv`
- `worker-sepblac`

### Jobs programados

Los `cron-*` no desaparecen del compose. Se mantienen como servicios `oneshot` y se ejecutan desde `systemd`.

Por que:

- ya encapsulan el comando correcto `--run-once`
- evitan duplicar logica de arranque en archivos `.service`
- reducen el riesgo de que un timer dispare por error un worker continuo

## Cambios introducidos en el repo

### 1. `caddy` en el compose productivo

Archivo: [infra/deploy/docker-compose.prod.yml](</G:/_Proyectos/esdata/infra/deploy/docker-compose.prod.yml:1>)

Se anade `caddy` delante de `api` y `web`.

Por que:

- centraliza TLS y reverse proxy en la propia VM
- evita exponer `api` y `web` directamente en interfaces publicas
- mantiene un camino simple de operacion sin Nginx extra ni LB externo

### 2. Bind local para puertos sensibles

Archivos:

- [infra/deploy/docker-compose.prod.yml](</G:/_Proyectos/esdata/infra/deploy/docker-compose.prod.yml:1>)
- [infra/deploy/compose.env.example](</G:/_Proyectos/esdata/infra/deploy/compose.env.example:1>)

`postgres`, `api` y `web` quedan publicados en `127.0.0.1` por defecto, no en `0.0.0.0`.

Por que:

- Caddy es la unica superficie publica necesaria
- el host sigue pudiendo usar `curl localhost` o `psql localhost`
- reduce exposicion accidental sin complicar el compose

### 3. Servicio `ops` para migraciones y verificaciones

Archivos:

- [infra/deploy/Dockerfile.ops](</G:/_Proyectos/esdata/infra/deploy/Dockerfile.ops:1>)
- [infra/deploy/docker-compose.prod.yml](</G:/_Proyectos/esdata/infra/deploy/docker-compose.prod.yml:1>)

Se crea un contenedor ligero con `alembic`, SQLAlchemy y `scripts/maintenance/verify_schema.py`.

Por que:

- la imagen de `apps/api` no contiene `alembic.ini`, `alembic/` ni `scripts/`
- ejecutar migraciones dentro de `api` era incorrecto para este repo
- `ops` da un punto unico y reproducible para migraciones y checks de esquema

### 4. Deploy por SSH usando script de servidor

Archivos:

- [scripts/ops/deploy-hetzner.sh](</G:/_Proyectos/esdata/scripts/ops/deploy-hetzner.sh:1>)
- [.github/workflows/deploy-hetzner.yml](</G:/_Proyectos/esdata/.github/workflows/deploy-hetzner.yml:1>)

El workflow nuevo hace `git pull` en la VM y ejecuta el script local.

Por que:

- el compose actual usa `build:` y no `image:` desde registry
- `docker compose pull` no resuelve nada util sin GHCR o similar
- construir en la VM es el camino mas corto y consistente con el estado actual del repo

### 5. Timers de `systemd` sobre `cron-*`

Archivos:

- [infra/deploy/systemd/esdata-job@.service](</G:/_Proyectos/esdata/infra/deploy/systemd/esdata-job@.service:1>)
- [infra/deploy/systemd/esdata-boe-daily.timer](</G:/_Proyectos/esdata/infra/deploy/systemd/esdata-boe-daily.timer:1>)
- [infra/deploy/systemd/esdata-dgt-weekly.timer](</G:/_Proyectos/esdata/infra/deploy/systemd/esdata-dgt-weekly.timer:1>)
- [infra/deploy/systemd/esdata-teac-weekly.timer](</G:/_Proyectos/esdata/infra/deploy/systemd/esdata-teac-weekly.timer:1>)
- [infra/deploy/systemd/esdata-modelos-daily.timer](</G:/_Proyectos/esdata/infra/deploy/systemd/esdata-modelos-daily.timer:1>)
- [infra/deploy/systemd/esdata-bdns-weekly.timer](</G:/_Proyectos/esdata/infra/deploy/systemd/esdata-bdns-weekly.timer:1>)
- [infra/deploy/systemd/esdata-borme-weekly.timer](</G:/_Proyectos/esdata/infra/deploy/systemd/esdata-borme-weekly.timer:1>)
- [infra/deploy/systemd/esdata-cnmv-weekly.timer](</G:/_Proyectos/esdata/infra/deploy/systemd/esdata-cnmv-weekly.timer:1>)
- [infra/deploy/systemd/esdata-sepblac-weekly.timer](</G:/_Proyectos/esdata/infra/deploy/systemd/esdata-sepblac-weekly.timer:1>)

Por que:

- `systemd` sustituye la parte scheduler de Railway
- los timers llaman a contenedores `oneshot` ya definidos
- el template `esdata-job@.service` evita duplicacion

### 6. Backup diario de Postgres

Archivo: [scripts/ops/backup-postgres.sh](</G:/_Proyectos/esdata/scripts/ops/backup-postgres.sh:1>)

Por que:

- al salir de Postgres gestionado, la responsabilidad del backup pasa a la VM
- `pg_dump` desde el contenedor `postgres` evita exponer credenciales extra
- la retencion por dias es suficiente como baseline operativa

## Variables de entorno

Archivo base: [infra/deploy/compose.env.example](</G:/_Proyectos/esdata/infra/deploy/compose.env.example:1>)

### Variables minimas obligatorias

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `API_DOMAIN`
- `WEB_DOMAIN`
- `ESDATA_API_BASE_URL`
- `TEAC_SEED_URLS`
- `BDNS_SEED_URLS`
- `BORME_SEED_URLS`
- `CNMV_SEED_URLS`
- `SEPBLAC_SEED_URLS`

### Variables que NO hay que inventarse

No aparecen hoy como contrato runtime principal de este repo:

- `DGT_API_KEY`
- `TEAC_API_KEY`

Por que:

- meter variables no soportadas complica el despliegue y confunde el contrato real
- la referencia valida para runtime es [docs/environment-variables.md](</G:/_Proyectos/esdata/docs/environment-variables.md:15>)

### Variables Railway que quedan fuera del runtime nuevo

Siguen existiendo en CI/documentacion actual, pero no deben entrar en el `.env.prod` de Hetzner salvo casos concretos de operacion:

- `RAILWAY_TOKEN`
- `RAILWAY_PROJECT_ID`
- `RAILWAY_ENVIRONMENT`

Por que:

- son parte del despliegue actual a Railway, no del runtime de la VM

## Secuencia de despliegue recomendada

### 0. Preparar la VM

1. Crear VM `CPX31` en Hetzner.
2. Instalar Docker, plugin de Compose y Git.
3. Clonar el repo en `/srv/esdata`.
4. Copiar `infra/deploy/compose.env.example` a `infra/deploy/.env.prod`.
5. Rellenar dominios, seeds, password y `DATABASE_URL`.

Por que:

- `CPX31` deja margen para `Postgres`, `api`, `web` y workers sin ir al limite desde el primer dia
- el `.env.prod` local a la VM evita meter secretos de produccion en GitHub Actions

### 1. Migrar los datos de Postgres

1. Sacar un dump desde Railway.
2. Levantar solo `postgres` en Hetzner.
3. Restaurar el dump dentro del nuevo Postgres.

Comando orientativo:

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d postgres
cat esdata.dump | docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml exec -T postgres \
  psql -U esdata -d esdata
```

Por que:

- en el compose nuevo la DB por defecto es `esdata`, no `railway`
- restaurar contra nombres reales evita errores tontos de handoff

### 2. Ejecutar migraciones y verificacion de esquema

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm ops alembic upgrade head
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm ops python scripts/maintenance/verify_schema.py
```

Por que:

- asegura que el schema final coincide con el contrato actual del repo
- evita confiar en que el dump ya viene perfectamente alineado

### 3. Levantar el stack

```bash
bash scripts/ops/deploy-hetzner.sh
```

Por que:

- encapsula el orden correcto
- evita repetir comandos largos y reducir errores humanos

### 4. Activar timers

```bash
sudo cp infra/deploy/systemd/esdata-job@.service /etc/systemd/system/
sudo cp infra/deploy/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now esdata-boe-daily.timer
sudo systemctl enable --now esdata-dgt-weekly.timer
sudo systemctl enable --now esdata-teac-weekly.timer
sudo systemctl enable --now esdata-modelos-daily.timer
sudo systemctl enable --now esdata-bdns-weekly.timer
sudo systemctl enable --now esdata-borme-weekly.timer
sudo systemctl enable --now esdata-cnmv-weekly.timer
sudo systemctl enable --now esdata-sepblac-weekly.timer
```

Por que:

- reemplaza el scheduler de Railway sin inventar una capa nueva

## Validaciones post-migracion

### Salud basica

- `curl http://127.0.0.1:8000/health`
- `curl http://127.0.0.1:8000/status`
- `curl https://$API_DOMAIN/health`
- `curl https://$API_DOMAIN/status`

### Web

- abrir `https://$WEB_DOMAIN`

### Timers

- `systemctl list-timers --all | grep esdata`

### Backup

- ejecutar manualmente `bash scripts/ops/backup-postgres.sh`

## Riesgos que siguen abiertos

### 1. `DGT_SSL_VERIFY`

Sigue teniendo semantica poco clara entre workers.

Por que importa:

- un cambio de infraestructura suele aflorar problemas TLS que en Railway quedaban ocultos

### 2. VM unica

`Postgres`, API, web y workers comparten nodo.

Por que se acepta ahora:

- reduce coste y complejidad
- es suficiente para el volumen actual del proyecto

Cuando revisarlo:

- si aumentan trafico, corpus o tiempos de scraping

### 3. Workflow Hetzner manual

El workflow nuevo se deja en `workflow_dispatch`.

Por que:

- evita disparos accidentales mientras Railway siga siendo la referencia activa
- permite validar la VM antes de convertir Hetzner en el deploy por defecto

## Cutover final

No apagar Railway en el primer minuto.

Secuencia recomendada:

1. dejar Hetzner funcionando
2. validar API, web, workers y timers
3. mantener Railway en paralelo 24-48 horas
4. suspender servicios Railway
5. eliminar Railway solo cuando el backup y los timers esten verificados

Por que:

- el rollback mas barato es no haber destruido todavia el entorno viejo
