# Fallos habituales por worker

## Resumen

Este documento documenta los patrones de fallo comunes por worker, como detectarlos
y como resolverlos. Todos los workers comparten el patron base de `boe.py`
(sin logica de retry nativa — los fallos crashan el proceso y Docker lo reinicia).

## Patron comun de todos los workers

- **Sin retry**: si una peticion falla, el worker crasha y Docker Compose lo reinicia
- **Sync log**: todos escriben en `sync_log` con `started_at` y `finished_at`
- **Intervalo**: `SYNC_INTERVAL_SECONDS` controla la frecuencia de ejecucion
- **Logging**: usan `esdata_common.logging.configure()` (texto o JSON segun `LOG_FORMAT`)

## Worker BOE (legislacion consolidada)

### Fallos comunes

| Fallo | Causa | Deteccion | Solucion |
|-------|-------|-----------|----------|
| Timeout BOE API | BOE lento o caido | `sync_log` con error `Timeout` | Reintentar con `--run-once`; verificar `BOE_API_BASE` |
| Parsing XML fallido | Cambios en estructura BOE | `sync_log` con error de parsing | Revisar logs del worker; posible fix en parser |
| DB write error | Postgres lento o lleno | `sync_log` con error `IntegrityError` | Verificar disco y conexiones DB |

### Comandos de diagnostico

```bash
# Ver ultimos logs de sincronizacion
docker compose -f infra/deploy/docker-compose.prod.yml logs worker-boe | tail -50

# Verificar ultimo sync
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT worker, started_at, finished_at, documentos_processed, documentos_upserted, rows_processed, errors, left(coalesce(error_msg,''), 220) AS error_excerpt FROM sync_log WHERE worker='boe' ORDER BY started_at DESC LIMIT 5;"

# Ejecutar manualmente
docker compose -f infra/deploy/docker-compose.prod.yml run --rm worker-boe python boe.py --run-once

# Carga acotada de articulos concretos con la pipeline existente
docker compose -f infra/deploy/docker-compose.prod.yml run --rm \
  -e BOE_LEGISLACION_NORMAS=LGT,LIVA \
  -e BOE_ONLY_BLOCK_IDS=a66,a67,a68,a69,a70,a71,a91,a92,a93 \
  worker-boe python boe.py --run-once
```

### Notas especiales

- `apps/workers/boe.py` ya soporta `LGT`, `LIVA` y `LIS` via `DEFAULT_NORMAS`; no hace falta scraper nuevo para estas tres leyes.
- `BOE_ONLY_BLOCK_IDS` filtra a nivel de bloque BOE (`a91`, `a111`, etc.) antes de descargar el XML de detalle; es la forma segura de hacer una carga incremental o de validacion.
- Para expansion de corpus, empezar por `LGT` y `LIVA`; `LIS` puede venir despues si el objetivo inmediato es reducir abstenciones en prescripcion, sanciones y tipos IVA.

## Worker DGT (consultas vinculantes)

### Fallos comunes

| Fallo | Causa | Deteccion | Solucion |
|-------|-------|-----------|----------|
| SSL verification error | DGT con cert invalido | `sync_log` con error SSL | `DGT_SSL_VERIFY=false` (default) |
| Cookie expired | Sesion DGT caducada | `sync_log` con error 401/403 | Reiniciar worker |
| Parsing HTML fallido | Cambios en web DGT | `sync_log` con error de parsing | Revisar logs; posible fix en parser |

### Notas especiales

- Gestiona cookies manualmente (sin session de httpx)
- `DGT_SSL_VERIFY=false` por defecto (no recomendado para produccion a largo plazo)

### Comandos de diagnostico

```bash
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT worker, started_at, finished_at, documentos_processed, documentos_upserted, rows_processed, errors, left(coalesce(error_msg,''), 220) AS error_excerpt FROM sync_log WHERE worker='dgt' ORDER BY started_at DESC LIMIT 5;"

docker compose -f infra/deploy/docker-compose.prod.yml run --rm worker-dgt python dgt.py --run-once
```

## Worker TEAC (resoluciones)

### Fallos comunes

| Fallo | Causa | Deteccion | Solucion |
|-------|-------|-----------|----------|
| Sin seed URLs | `TEAC_SEED_URLS` vacio | `sync_log` sin ejecuciones | Configurar `TEAC_SEED_URLS` |
| Seed manual caducada | `criterio.aspx?id=...` ya no existe | `sync_log` con `El criterio no existe` o sin upserts | Usar `https://serviciostelematicosext.hacienda.gob.es/TEAC/DYCTEA/` como seed estable |
| Parsing HTML fallido | Cambios en web TEAC | `sync_log` con error | Revisar logs; posible fix en parser |

### Comandos de diagnostico

```bash
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT worker, started_at, finished_at, documentos_processed, documentos_upserted, rows_processed, errors, left(coalesce(error_msg,''), 220) AS error_excerpt FROM sync_log WHERE worker='teac' ORDER BY started_at DESC LIMIT 5;"

docker compose -f infra/deploy/docker-compose.prod.yml run --rm worker-teac python teac.py --run-once
```

### Notas especiales

- `TEAC_SEED_URLS` admite la landing `DYCTEA/`; el worker resuelve automaticamente la primera tanda de resoluciones TEAC mediante POST al buscador oficial.
- Para monitorizacion determinista de crons, definir `HC_PING_URL_CRON_*` en el `.env` de despliegue y validar frescura con `python scripts/maintenance/validate-cron-run.py --db-url ...`.

## Worker Modelos AEAT

### Fallos comunes

| Fallo | Causa | Deteccion | Solucion |
|-------|-------|-----------|----------|
| Timeout DGT | DGT lento | `sync_log` con error `Timeout` | Reintentar; verificar `DGT_SSL_VERIFY` |
| Parsing HTML fallido | Cambios en web DGT | `sync_log` con error | Revisar logs; posible fix en parser |

### Notas especiales

- Usa `httpx.Client(timeout=30)` (timeout configurable via httpx)
- Intervalo configurable via `MODELOS_SYNC_INTERVAL` (default 86400 = 24h)

### Comandos de diagnostico

```bash
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT worker, started_at, finished_at, documentos_processed, documentos_upserted, rows_processed, errors, left(coalesce(error_msg,''), 220) AS error_excerpt FROM sync_log WHERE worker='modelos' ORDER BY started_at DESC LIMIT 5;"
```

## Workers de datos reales añadidos

Estos workers complementan seeds y workers base con ingestion desde fuentes oficiales
cuando existe una fuente estable y verificable:

| Worker | Fuente primaria | Uso operativo |
|--------|-----------------|---------------|
| `consumer_credit_real` | EUR-Lex | Directivas y reglamentos de credito al consumo |
| `dac8_real` | EUR-Lex | DAC8/DAC9 y asistencia administrativa fiscal |
| `pgc_real` | BOE | Plan General Contable desde reales decretos BOE |

## Workers de parsing PDF (BORME, CNMV, AEPD, BDE)

### Fallos comunes

| Fallo | Causa | Deteccion | Solucion |
|-------|-------|-----------|----------|
| PDF corrupto/inaccesible | URL rota o PDF invalido | `sync_log` con error `pypdf` | Verificar URL en `*_SEED_URLS`; skip manual |
| Timeout descarga PDF | PDF grande o lento | `sync_log` con error `Timeout` | Reintentar; verificar conectividad |
| Parsing texto fallido | PDF sin texto extraible | `sync_log` con error | Verificar logs del worker |

### Workers afectados

| Worker | Variable seed URL | Fuente |
|--------|-------------------|--------|
| `worker-borme` | `BORME_SEED_URLS` | Boletines oficiales de sociedades |
| `worker-cnmv` | `CNMV_SEED_URLS` | Documentos CNMV |
| `worker-aepd` | `AEPD_SEED_URLS` | Guias AEPD |
| `worker-bde` | `BDE_SEED_URLS` | Informes Banco de Espana |

### Comandos de diagnostico

```bash
# BORME
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT worker, started_at, finished_at, documentos_processed, documentos_upserted, rows_processed, errors, left(coalesce(error_msg,''), 220) AS error_excerpt FROM sync_log WHERE worker='borme' ORDER BY started_at DESC LIMIT 5;"

# CNMV
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT worker, started_at, finished_at, documentos_processed, documentos_upserted, rows_processed, errors, left(coalesce(error_msg,''), 220) AS error_excerpt FROM sync_log WHERE worker='cnmv' ORDER BY started_at DESC LIMIT 5;"
```

## Workers de web scraping (BDNS, SEPBLAC, CENDOJ, EURLEX)

### Fallos comunes

| Fallo | Causa | Deteccion | Solucion |
|-------|-------|-----------|----------|
| HTML structure changed | Cambios en estructura web | `sync_log` con error de parsing | Revisar logs; possible fix en selector |
| Rate limiting | Demasiadas peticiones | `sync_log` con error 429 | Aumentar `SYNC_INTERVAL_SECONDS` |
| Login required | Web requiere auth | `sync_log` con error 401/403 | Configurar credenciales si disponibles |

### Workers afectados

| Worker | Variable seed URL | Fuente |
|--------|-------------------|--------|
| `worker-bdns` | `BDNS_SEED_URLS` | Bolsa de subvenciones |
| `worker-sepblac` | `SEPBLAC_SEED_URLS` | Lista de bloqueos |
| `worker-cendoj` | `CENDOJ_SEED_URLS` | Portal poder judicial |
| `worker-eurlex` | `EURLEX_SEED_URLS` | Legislacion UE |

## Worker Embeddings

### Fallos comunes

| Fallo | Causa | Deteccion | Solucion |
|-------|-------|-----------|----------|
| Modelo no encontrado | `sentence-transformers` no instalado | Crash al iniciar | Verificar `requirements.txt` |
| OOM (Out of Memory) | DB muy grande + embeddings | Crash por memoria | Reducir batch size; mas RAM |
| GPU no disponible | Sin GPU pero se intenta usar | Warning en logs | Forzar CPU en modelo |

### Notas especiales

- Devuelve `None` si `sentence-transformers` no esta instalado (graceful degradation)
- Usa modelo `paraphrase-multilingual-MiniLM-L12-v2` (1536-dim, CPU-friendly)

## Grafico de dependencia de fallos

```
Worker falla
    |
    +--- Timeout HTTP
    |       +--- Causa: destino lento/caido
    |       +--- Impacto: worker crash, Docker reinicia
    |       +--- Resolucion: reintentar automatico
    |
    +--- Parsing error
    |       +--- Causa: fuente cambio estructura
    |       +--- Impacto: datos faltantes, worker crash
    |       +--- Resolucion: fix parser manual
    |
    +--- DB error
    |       +--- Causa: Postgres lento/lleno/conexiones
    |       +--- Impacto: datos no persistidos
    |       +--- Resolucion: verificar DB, vacuum, reiniciar worker
    |
    +--- SSL/TLS error
            +--- Causa: certificado invalido o caducado
            +--- Impacto: worker crash
            +--- Resolucion: verificar SSL_VERIFY o actualizar CA certs
```

## Checklist de diagnostico

Cuando un worker falla:

1. **Verificar logs**: `docker compose logs worker-<nombre> | tail -50`
2. **Verificar sync_log**: revisar `documentos_processed`, `documentos_upserted`, `rows_processed`, `errors`, `duration_ms` y `error_msg` para el worker afectado.
3. **Reiniciar worker**: `docker compose restart worker-<nombre>`
4. **Ejecutar manualmente**: `docker compose run --rm worker-<nombre> python <nombre>.py --run-once`
5. **Verificar fuente externa**: visitar la URL de la fuente manualmente
6. **Verificar conexiones DB**: `docker compose exec postgres psql -U esdata -d esdata -c "SELECT 1;"`

## Referencias

- `docs/operations/README.md` — runbooks operativos
- `docs/operations/metrics.md` — indicadores minimos
- `docs/deployment/rollback.md` — procedimientos de rollback
- `apps/workers/boe.py` — patron base de workers

## Postmortems activos

Cada bug encontrado en produccion se registra aqui. Antes de tocar un worker, revisar esta tabla: si el bug ya fue visto, el fix ya esta aplicado.

| Fecha | Worker | Bug | Root cause | Fix | Estado |
|-------|--------|-----|------------|-----|--------|
| 2026-04-30 | eurlex | SPARQL 400 Bad Request | Endpoint `publications.europa.eu/webapi/rdf/sparql` caido + typo `PREFIXeli:` (sin espacio) en query | Endpoint a `data.europa.eu/sparql` + eliminar linea con `PREFIXeli:` | ✅ Cerrado |
| 2026-04-30 | eurlex | 0 bloques/articulos tras 30 normas upserted | EUR-Lex bloquea API REST (requiere JS) + HTML devuelve 202/0 bytes | Requiere corpus local de textos completos | 🔜 Feature nueva |
| 2026-04-30 | boe | 0 documentos tras 47 runs | `BOE_LEGISLACION_NORMAS` contenia codigos desconocidos (IRNR, IIEE...) → KeyError. Duplicate `fetch_block` shadowing XML fallback | Filtrado de codigos desconocidos + eliminar funcion duplicada | ✅ Cerrado |
| 2026-04-30 | aepd | Deadlock en `source_revision` INSERT | Advisory lock per-row entre dos conexiones del pool del mismo proceso | Lock per-entity_id en `change_detection.py:record_revision()` | ✅ Cerrado |
| 2026-04-30 | todos | 12/12 workers unhealthy | Heartbeat tocado dentro de `run_sync()`, no en bucle `while True`. Workers con ciclos > 300s marcados unhealthy | Heartbeat movido al inicio de cada iteracion del bucle exterior | ✅ Cerrado |
| 2026-04-30 | eurlex | SPARQL endpoint correcto en codigo pero no en container | `docker-compose.prod.yml` tenia `SPARQL_BASE` con default viejo que override el default del codigo | Actualizado default en docker-compose | ✅ Cerrado |
| 2026-04-30 | aepd | Warning `dgt_url column already exists` | Migration `ALTER TABLE ADD COLUMN` no usa `IF NOT EXISTS` | Cambiar a `ADD COLUMN IF NOT EXISTS` | 🔜 Fix de 1 linea |
