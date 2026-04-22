# Next Session Handoff - 2026-04-22

## Objetivo de la siguiente sesion

Continuar desde un entorno local ya arrancable, sin depender de Railway, y decidir si pasar a Nivel 2 (workers puntuales) o seguir saneando el modo local.

## Estado actual confirmado

- `docker compose up -d postgres api` ya funciona en local.
- `GET /health` responde `200`.
- `GET /status` responde `200`.
- `GET /v1/buscar?q=IVA` responde `200`.
- `GET /v1/modelos` responde `200`, pero sin datos todavia.

## Cambios hechos en esta sesion

### 1. `docker-compose.yml` local corregido

Se ajusto para que el build local refleje el layout real del repo:

- `api` ahora builda desde `./apps/api`
- workers buildan desde `./apps/workers`
- se quito `--reload` del `api` local
- se corrigieron comandos de workers para el layout actual del contenedor

Por que:

- el compose local estaba desalineado con el repo actual
- el build de `api` fallaba al no encontrar `requirements.txt`
- `uvicorn --reload` fallaba con el bind mount en Windows

### 2. `apps/api/main.py` hecho robusto en local

Se reemplazo la resolucion fija:

- antes: `Path(__file__).resolve().parents[2]`
- ahora: deteccion defensiva del root buscando `docs/`

Por que:

- en el contenedor local `main.py` vive en `/app/main.py`
- esa profundidad fija rompia con `IndexError`

### 3. Base local saneada sobre volumen existente

El volumen local de Postgres ya tenia datos viejos y no volvia a ejecutar el bootstrap inicial.

Se aplicaron manualmente:

- `002_fulltext_search.sql`
- `003_modelos_aeat.sql`
- `004_modelos_v2.sql`
- `004_norma_classification.sql`
- y un `ALTER TABLE sync_log ... ADD COLUMN IF NOT EXISTS ...`

Por que:

- faltaba `search_vector` en `version_articulo`
- faltaban columnas nuevas en `sync_log`
- faltaban piezas del dominio de modelos/clasificacion

## Comandos que funcionaron

### Nivel 1 - Arranque minimo

```powershell
docker compose up -d --build postgres api
docker compose ps
curl http://localhost:8001/health
curl http://localhost:8001/status
curl "http://localhost:8001/v1/buscar?q=IVA"
```

### Reparacion del volumen local ya existente

```powershell
docker compose exec -T postgres psql -U esdata -d esdata -f /docker-entrypoint-initdb.d/002_fulltext_search.sql
docker compose exec -T postgres psql -U esdata -d esdata -f /docker-entrypoint-initdb.d/003_modelos_aeat.sql
docker compose exec -T postgres psql -U esdata -d esdata -f /docker-entrypoint-initdb.d/004_modelos_v2.sql
docker compose exec -T postgres psql -U esdata -d esdata -f /docker-entrypoint-initdb.d/004_norma_classification.sql
docker compose exec -T postgres psql -U esdata -d esdata -c "ALTER TABLE sync_log ADD COLUMN IF NOT EXISTS documentos_processed INTEGER; ALTER TABLE sync_log ADD COLUMN IF NOT EXISTS documentos_upserted INTEGER; ALTER TABLE sync_log ADD COLUMN IF NOT EXISTS doctrina_links_created INTEGER;"
```

## Modo local - orden recomendado

### Nivel 1

Solo `postgres` + `api`.

Usar para:

- probar API
- validar busqueda y estado
- trabajar sin coste y sin workers corriendo

### Nivel 2

Mantener `postgres` + `api` arriba y ejecutar workers puntuales.

Siguiente paso recomendado:

```powershell
make worker-modelos
curl http://localhost:8001/v1/modelos
curl http://localhost:8001/status
```

Despues:

```powershell
make worker-boe
```

Por que ese orden:

- ahora mismo `modelos` sigue vacio
- `worker-modelos` da senal inmediata de si la ingesta local funciona
- `worker-boe` es mas pesado y no hace falta correrlo antes de validar lo facil

### Nivel 3

Probar `infra/deploy/docker-compose.prod.yml` localmente con `postgres`, `api`, `web`, `caddy`.

No se llego a ejecutar en esta sesion.

## Riesgos y notas

### 1. Volumen local viejo

Si vuelven a aparecer errores raros de esquema, lo mas probable es que el volumen local tenga estado historico y falten migraciones SQL.

Comando para comprobar columnas concretas:

```powershell
docker compose exec -T postgres psql -U esdata -d esdata -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'version_articulo';"
```

### 2. `worker-modelos` puede depender de HTML externo

Si falla, no asumir bug interno de primeras:

- revisar logs del worker
- comprobar si AEAT cambio markup o respuesta

### 3. Railway no se ha tocado

La produccion actual sigue siendo Railway.

Los cambios de Hetzner dejados en esta sesion son preparatorios:

- `infra/deploy/docker-compose.prod.yml`
- `infra/deploy/Caddyfile`
- `infra/deploy/Dockerfile.ops`
- `infra/deploy/systemd/*`
- `scripts/deploy-hetzner.sh`
- `scripts/backup-postgres.sh`
- `.github/workflows/deploy-hetzner.yml`
- `docs/deployment/railway-to-hetzner-v2.md`

## Si hubiera que rehacer el entorno local desde cero

Opcion limpia:

```powershell
docker compose down -v
docker compose up -d --build postgres api
```

Por que:

- fuerza bootstrap limpio de Postgres
- evita perseguir residuos de volumen viejo

Solo hacerlo si no hace falta conservar el estado local actual.
