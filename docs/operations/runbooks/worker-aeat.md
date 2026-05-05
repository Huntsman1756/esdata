# Worker AEAT

## Objetivo

Validar y operar `worker-aeat` contra `sede.agenciatributaria.gob.es` desde un entorno con red compatible.

## Estado actual

- El worker existe en codigo y despliegue.
- El servicio Compose disponible para ejecucion manual es `worker-aeat`.
- El servicio solo se expone via `profile` manual `aeat`.
- No arranca con `docker compose up` por defecto.
- La validacion live no puede hacerse desde el entorno de desarrollo actual por bloqueo/resolucion DNS de AEAT fuera de IP espanola.

## Precondiciones

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml ps
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml \
  exec postgres psql -U esdata -d esdata \
  -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'modelo_recurso' LIMIT 5;"
```

Si `modelo_recurso` no existe o no devuelve filas:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml \
  --profile ops run --rm ops alembic upgrade head
```

## Ejecucion manual

Modo normal:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml \
  --profile aeat run --rm worker-aeat 2>&1 | tee /tmp/aeat_run.log
```

Forzando Playwright:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml \
  --profile aeat run --rm \
  -e WORKER_CMD="python aeat_models.py --run-once --force-playwright" \
  worker-aeat 2>&1 | tee /tmp/aeat_run.log
```

## Que revisar en el log

Decision de cliente:

```bash
grep -E "HTTP client|Playwright|FallbackRequired|Using Playwright|Using HTTP" /tmp/aeat_run.log
```

Modelos descubiertos:

```bash
grep -i "discovered\|modelo" /tmp/aeat_run.log | head -20
```

Recursos y versionado:

```bash
grep -Ei "sha256|recurso|tipo_recurso|rotated|unchanged|inserted" /tmp/aeat_run.log | head -20
```

Errores:

```bash
grep -Ei "error|exception|failed|traceback" /tmp/aeat_run.log
```

## Verificaciones SQL post-run

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml \
  exec postgres psql -U esdata -d esdata \
  -c "SELECT codigo, activo, url_listado FROM aeat_modelo ORDER BY codigo LIMIT 10;"

docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml \
  exec postgres psql -U esdata -d esdata \
  -c "SELECT m.codigo, c.campana, c.estado_publicacion
      FROM modelo_campana c JOIN aeat_modelo m ON m.id = c.modelo_id
      ORDER BY m.codigo, c.campana DESC LIMIT 10;"

docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml \
  exec postgres psql -U esdata -d esdata \
  -c "SELECT campana_id, tipo_recurso, formato, LEFT(sha256_contenido, 12) AS sha_prefix, activa
      FROM modelo_recurso ORDER BY first_seen_at DESC LIMIT 10;"

docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml \
  exec postgres psql -U esdata -d esdata \
  -c "SELECT worker, documentos_processed, documentos_upserted, articulos_upserted, errors, created_at
      FROM sync_log WHERE worker = 'worker-aeat-modelos'
      ORDER BY created_at DESC LIMIT 5;"
```

## Criterio de exito

- `modelo_recurso` tiene al menos una fila nueva.
- `sha256_contenido` no es nulo.
- `sync_log` contiene una fila para `worker-aeat-modelos`.
- Idealmente `errors = 0`.
- El log deja claro si se uso `httpx` o `Playwright`.

## Fallos comunes

### `DNS resolution failed`

- comprobar resolucion desde el VPS:

```bash
dig www.sede.agenciatributaria.gob.es +short
curl -A "Mozilla/5.0" -I "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/"
```

### `playwright._impl._errors.TimeoutError`

- el selector `a[href*='modelo']` no aparecio en 15s
- ajustar selector en `apps/workers/aeat_models.py`

### `FallbackRequired`

- `httpx` no obtuvo HTML util
- reintentar con `--force-playwright`

### `UniqueViolation` en `modelo_recurso`

- revisar schema e indices:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml \
  exec postgres psql -U esdata -d esdata -c "\d+ modelo_recurso"
```

## Limitacion explicita

`worker-aeat-modelos` no debe marcarse como validado live hasta ejecutar este runbook desde una IP espanola o desde el VPS de produccion.
