# Indicadores minimos de operacion

## Resumen

Este documento define los indicadores minimos que debe monitorizar el equipo
de infraestructura para detectar problemas a tiempo.

## Salud de la API

| Indicador | Fuente | Umbral | Frecuencia |
|-----------|--------|--------|------------|
| `/health` responde 200 | HTTP GET | Siempre 200 | Cada 30s |
| Tiempo respuesta `/health` | `response_time_ms` | < 500ms | Cada 30s |
| `/v1/legislacion/buscar` responde | HTTP GET | < 5s | Cada 5min |
| `/v1/doctrina/buscar` responde | HTTP GET | < 5s | Cada 5min |

### Comandos de verificacion

```bash
# Verificar salud API
curl -s -o /dev/null -w "%{http_code} %{time_total}s" https://api.tudominio.com/health

# Verificar busqueda
curl -s -o /dev/null -w "%{http_code} %{time_total}s" \
  "https://api.tudominio.com/v1/legislacion/buscar?q=iva&limit=1"

# Smoke tests completos
docker compose -f infra/deploy/docker-compose.prod.yml exec api \
  python /app/scripts/smoke_tests.py --base-url http://localhost:8000
```

## Salud de los workers

| Indicador | Fuente | Umbral | Frecuencia |
|-----------|--------|--------|------------|
| Worker activo (Docker ps) | `docker ps` | Todos up | Cada 5min |
| Ultimo sync < intervalo + 1h | `sync_log` | No superar intervalo | Cada 15min |
| Errores en sync_log | `sync_log.errors` y `sync_log.error_msg` | 0 errores consecutivos | Cada 15min |
| Rows processed > 0 | `sync_log.rows_processed` | > 0 en ingesta | Cada ejecucion |

### Consulta de salud de workers

```sql
-- Ultimas ejecuciones por worker (en las ultimas 24h)
SELECT
    worker,
    started_at,
    finished_at,
    documentos_processed,
    documentos_upserted,
    rows_processed,
    errors,
    left(coalesce(error_msg, ''), 220) AS error_excerpt,
    duration_ms / 1000.0 as duration_s
FROM sync_log
WHERE started_at > NOW() - INTERVAL '24 hours'
ORDER BY worker, started_at DESC;

-- Workers que llevan mas de su intervalo sin ejecutar
SELECT
    worker,
    MAX(started_at) as last_run,
    EXTRACT(EPOCH FROM (NOW() - MAX(started_at)))/3600 as hours_since_last
FROM sync_log
GROUP BY worker
HAVING MAX(started_at) < NOW() - INTERVAL '48 hours'
ORDER BY hours_since_last DESC;

-- Errores consecutivos por worker
SELECT
    worker,
    COUNT(*) as consecutive_errors,
    MAX(error_msg) as last_error
FROM sync_log
WHERE coalesce(errors, 0) > 0 OR error_msg IS NOT NULL
GROUP BY worker
ORDER BY consecutive_errors DESC;
```

## Ejecucion de crons

| Indicador | Fuente | Umbral | Frecuencia |
|-----------|--------|--------|------------|
| Worker ejecutado en intervalo | `sync_log` | Cada N horas | Cada 15min |
| Cron profile activo | `docker ps` | Workers cron running | Cada 5min |

### Verificacion de cron

```bash
# Verificar que workers cron estan corriendo
docker compose -f infra/deploy/docker-compose.prod.yml --profile cron ps

# Verificar que cron jobs se ejecutaron hoy
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT worker, COUNT(*) as runs_today FROM sync_log
   WHERE started_at > CURRENT_DATE
   GROUP BY worker ORDER BY runs_today DESC;"
```

## Cobertura de datos

| Indicador | Fuente | Umbral | Frecuencia |
|-----------|--------|--------|------------|
| Total version_articulo | `version_articulo` | > 0 | Diario |
| Total norma | `norma` | > 50 | Diario |
| Total documento | `documento` | > 0 | Diario |
| Total modelo_aeat | `modelo_aeat` | > 0 | Semanal |
| Total sync_log | `sync_log` | Creciente | Diario |

### Consulta de cobertura

```sql
-- Conteo de documentos por tabla
SELECT
    'version_articulo' AS tabla, COUNT(*) AS total FROM version_articulo
    UNION ALL
    SELECT 'norma', COUNT(*) FROM norma
    UNION ALL
    SELECT 'documento', COUNT(*) FROM documento
    UNION ALL
    SELECT 'modelo_aeat', COUNT(*) FROM modelo_aeat
    UNION ALL
    SELECT 'sync_log', COUNT(*) FROM sync_log
    UNION ALL
    SELECT 'documento_fragmento', COUNT(*) FROM documento_fragmento
    UNION ALL
    SELECT 'documento_interpretativo', COUNT(*) FROM documento_interpretativo;

-- Tamanio de base de datos
SELECT pg_size_pretty(pg_database_size('esdata')) AS total_size;

-- Tamanio por tabla
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;
```

## Errores de ingesta

| Indicador | Fuente | Umbral | Frecuencia |
|-----------|--------|--------|------------|
| Errores en sync_log hoy | `sync_log` con error | < 5 | Cada 15min |
| Errores por worker | `sync_log.error` | No worker > 3 | Cada 15min |
| Tasa de éxito de ingesta | rows_added / total intentos | > 90% | Diario |

### Consulta de errores

```sql
-- Errores de las ultimas 24 horas
SELECT
    worker,
    error,
    COUNT(*) as count,
    MAX(started_at) as last_error_at
FROM sync_log
WHERE error IS NOT NULL
  AND started_at > NOW() - INTERVAL '24 hours'
GROUP BY worker, error
ORDER BY count DESC;

-- Tasa de éxito por worker (ultimas 24h)
SELECT
    worker,
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE error IS NULL) as successful,
    ROUND(100.0 * COUNT(*) FILTER (WHERE error IS NULL) / COUNT(*), 1) as success_rate
FROM sync_log
WHERE started_at > NOW() - INTERVAL '24 hours'
GROUP BY worker
ORDER BY success_rate ASC;
```

## Disc space

| Indicador | Fuente | Umbral | Frecuencia |
|-----------|--------|--------|------------|
| Disco usado | `df -h` | < 80% | Cada 1h |
| Volumen Postgres | `docker volume ls` | < 8GB | Diario |
| Logs de contenedores | `docker system df` | < 1GB | Semanal |

### Comandos de verificacion

```bash
# Espacio en disco
df -h

# Tamanio de volumes Docker
docker system df

# Tamanio de volumen Postgres
docker volume ls -f name=esdata-esdata-postgres
du -sh /var/lib/docker/volumes/esdata-esdata-postgres/_data
```

## SSL / Certificados

| Indicador | Fuente | Umbral | Frecuencia |
|-----------|--------|--------|------------|
| Certificado activo | Caddy logs | No expired | Cada dia |
| Dias hasta expiracion | Caddy cert info | > 30 dias | Semanal |

### Comandos de verificacion

```bash
# Verificar certificados en Caddy
docker compose -f infra/deploy/docker-compose.prod.yml exec caddy caddy list-certificates

# Verificar expiracion
curl -s -o /dev/null -w "%{ssl_verify_result}" https://api.tudominio.com
```

## Resumen ejecutivo diario

Generar un resumen diario con:

```bash
#!/bin/bash
# /opt/esdata/scripts/daily_summary.sh

echo "=== RESUMEN DIARIO esdata ==="
echo "Fecha: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

echo "--- Salud API ---"
curl -s -o /dev/null -w "Health: %{http_code} (%{time_total}s)\n" \
  "https://api.tudominio.com/health"

echo ""
echo "--- Workers (ultimas 24h) ---"
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -t -c \
  "SELECT worker, COUNT(*) as runs, ROUND(100.0 * COUNT(*) FILTER (WHERE error IS NULL) / COUNT(*), 1) as pct
   FROM sync_log WHERE started_at > NOW() - INTERVAL '24 hours'
   GROUP BY worker ORDER BY worker;"

echo ""
echo "--- Cobertura de datos ---"
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -t -c \
  "SELECT 'version_articulo', COUNT(*) FROM version_articulo
   UNION ALL SELECT 'norma', COUNT(*) FROM norma
   UNION ALL SELECT 'documento', COUNT(*) FROM documento;"

echo ""
echo "--- Espacio en disco ---"
df -h / | tail -1

echo ""
echo "--- Errores recientes ---"
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -t -c \
  "SELECT worker, error, COUNT(*) FROM sync_log
   WHERE error IS NOT NULL AND started_at > NOW() - INTERVAL '24 hours'
   GROUP BY worker, error ORDER BY COUNT(*) DESC LIMIT 10;"
```

## Integracion con sistemas de monitoring

### Prometheus / Grafana

Para integrar con Prometheus, exponer un endpoint `/metrics` en la API:

```python
# En apps/api/main.py
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter("http_requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_DURATION = Histogram("http_request_duration_seconds", "Request duration")

@app.middleware("http")
async def metrics_middleware(request, call_next):
    response = await call_next(request)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
    return response
```

### Alertas

Configurar alertas para:

1. **API down**: `/health` no responde 200 durante 2 minutos
2. **Worker caido**: worker no aparece en `sync_log` en 2x su intervalo
3. **DB llena**: disco > 85%
4. **SSL expirando**: certificado < 14 dias
5. **Errores ingesta**: > 5 errores en sync_log en 1 hora

## Referencias

- `docs/operations/README.md` — runbooks operativos
- `docs/operations/worker-failures.md` — fallos por worker
- `docs/deployment/overview.md` — arquitectura de despliegue
