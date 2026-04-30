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
| Salud del Sistema | `esdata-system-health` | Prometheus + PostgreSQL | Uptime, memoria, CPU, workers activos |

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
    \"UPDATE user SET password = '$2a$10$...', salt = '' WHERE login = 'admin';\""
```

La contraseña se puede cambiar desde la UI en **Administration → Users → Admin** si se tiene acceso.

## Prometheus

- **URL:** `http://localhost:9090` (solo interno, no expuesto al exterior)
- **Targets:** `http://localhost:9090/targets`
- **Config:** `infra/observability/prometheus.yml`
- **Retención:** 30 días
- **Scrape:** cada 15s desde `api:8000/metrics`

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
