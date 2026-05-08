# Grafana — Runbook

## Acceso

- **URL:** `https://tudominio.com/grafana/`
- **Usuario:** `admin`
- **Contraseña:** `${GRAFANA_ADMIN_PASSWORD}` (ver `.env.example`)

## Configuración

Grafana se configura automáticamente vía provisioning en el arranque:

- **DataSource Prometheus:** `http://prometheus:9090` (automático)
- **DataSource PostgreSQL:** `postgres:5432` (automático, usa vars de entorno)
- **Dashboards:** 4 cargados desde `infra/observability/grafana/dashboards/`

## Dashboards disponibles

| Dashboard | UID | Fuente | Descripción |
|-----------|-----|--------|-------------|
| Estado de Workers | `esdata-workers` | PostgreSQL | Último run, errores, corpus por fuente |
| API y Rendimiento | `esdata-api-performance` | Prometheus | Requests, latencia p50/p95/p99 |
| Corpus y Cobertura | `esdata-corpus` | PostgreSQL | Documentos por fuente, ingestión diaria |
| Salud del Sistema | `esdata-system-health` | Prometheus + PostgreSQL | Uptime, memoria, CPU, workers activos y `worker_sync_summary` |

## Añadir un panel nuevo

1. Abrir el dashboard en Grafana → **Edit**
2. Click en **Add panel** (esquina superior derecha)
3. Configurar la query en el panel
4. Guardar dashboard con **Save dashboard** (💾)
5. Exportar a JSON para versionar en el repo (ver abajo)

## Exportar un dashboard como JSON

1. Abrir el dashboard en Grafana
2. **Dashboard settings** (⚙️) → **JSON Model**
3. Copiar el JSON
4. Guardar en `infra/observability/grafana/dashboards/` con nombre `NN_nombre.json`
5. Commit en el repo

Alternativamente:
- Desde el menú del dashboard → **Share** → **Export** → **Save to disk**

## Resetear contraseña de admin

Si se pierde la contraseña de admin:

```bash
# Entrar al contenedor de Grafana
docker compose --env-file infra/deploy/compose.env.example \
  -f infra/deploy/docker-compose.prod.yml exec grafana bash

# Resetear contraseña (cambiar 'nueva_password')
grafana-cli admin reset-admin-password nueva_password

# O directamente desde la DB de Grafana
docker compose --env-file infra/deploy/compose.env.example \
  -f infra/deploy/docker-compose.prod.yml exec grafana \
  sh -c "sqlite3 /var/lib/grafana/grafana.db \
    \"UPDATE user SET password = :bcrypt_hash, salt = '' WHERE login = 'admin';\""
```

La contraseña se puede cambiar desde la UI en **Administration → Users → Admin** si se tiene acceso.

## Prometheus

- **URL:** `http://localhost:9090` (solo interno, no expuesto al exterior)
- **Targets:** `http://localhost:9090/targets`
- **Config:** `infra/observability/prometheus.yml`
- **Retención:** 30 días
- **Scrape:** cada 15s desde `api:8000/metrics`

### Alertas nuevas de observabilidad de workers

Definidas en `infra/observability/alerts.yml`:

- `WorkerFetchErrorsDetected`
  - dispara si `worker_sync_summary{kind="fetch_errors"} > 0` durante 10m
- `EurlexNoIndexHigh`
  - dispara si `worker_sync_summary{worker=~"worker-eurlex|cron-eurlex-weekly",kind="no_index"} > 25` durante 30m

### Paneles nuevos en Salud del Sistema

El dashboard `esdata-system-health` incluye ahora dos series Prometheus nuevas:

- `worker_sync_summary{kind="no_index"}`
- `worker_sync_summary{kind="fetch_errors"}`

Uso recomendado:

1. Si `fetch_errors` sube por encima de `0`, revisar inmediatamente logs del worker afectado.
2. Si `no_index` se mantiene alto en EUR-Lex, revisar el fallback RDF/consolidation antes de tocar seeds.

## Prueba manual de Alertmanager / Telegram

Procedimiento reproducible desde el VPS para inyectar una alerta de prueba:

```bash
cat >/tmp/manual-telegram-test.json <<'EOF'
[
  {
    "labels": {
      "alertname": "ManualTelegramTest",
      "severity": "warning",
      "worker": "cron-eurlex-weekly"
    },
    "annotations": {
      "summary": "Prueba manual reproducible de Telegram",
      "description": "Validacion controlada del receiver Telegram desde Alertmanager usando /api/v2/alerts y post-file."
    }
  }
]
EOF

docker exec -i deploy-alertmanager-1 \
  wget -qO- --header=Content-Type:application/json \
  --post-file=/tmp/manual-telegram-test.json \
  http://127.0.0.1:9093/api/v2/alerts
```

Comprobar la alerta activa:

```bash
docker exec deploy-alertmanager-1 \
  wget -qO- http://127.0.0.1:9093/api/v2/alerts
```

Resolver la alerta de prueba para no dejar ruido:

```bash
cat >/tmp/manual-telegram-resolve.json <<'EOF'
[
  {
    "labels": {
      "alertname": "ManualTelegramTest",
      "severity": "warning",
      "worker": "cron-eurlex-weekly"
    },
    "endsAt": "2026-05-03T14:57:30Z"
  }
]
EOF

docker exec -i deploy-alertmanager-1 \
  wget -qO- --header=Content-Type:application/json \
  --post-file=/tmp/manual-telegram-resolve.json \
  http://127.0.0.1:9093/api/v2/alerts
```

## Troubleshooting

### Dashboards no cargan

```bash
# Verificar que el volumen de dashboards está montado
docker compose --env-file infra/deploy/compose.env.example \
  -f infra/deploy/docker-compose.prod.yml exec grafana \
  ls -la /etc/grafana/provisioning/dashboards/

# Verificar logs de Grafana
docker compose --env-file infra/deploy/compose.env.example \
  -f infra/deploy/docker-compose.prod.yml logs grafana
```

### Prometheus no ve targets

```bash
# Verificar target status
curl http://localhost:9090/targets

# Verificar que la API responde en /metrics
curl http://localhost:8000/metrics | head -20

# Verificar que Prometheus puede alcanzar la API
docker compose --env-file infra/deploy/compose.env.example \
  -f infra/deploy/docker-compose.prod.yml exec prometheus \
  sh -c "wget -qO- http://api:8000/metrics | head -5"
```

### PostgreSQL datasource no conecta

```bash
# Verificar que el datasource existe
docker compose --env-file infra/deploy/compose.env.example \
  -f infra/deploy/docker-compose.prod.yml exec grafana \
  sh -c "curl -s http://admin:${GRAFANA_ADMIN_PASSWORD}@localhost:3000/api/datasources"

# Verificar que Grafana puede alcanzar PostgreSQL
docker compose --env-file infra/deploy/compose.env.example \
  -f infra/deploy/docker-compose.prod.yml exec grafana \
  sh -c "nc -zv postgres 5432"
```
