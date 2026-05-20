# A-10b runtime DB role hardening - 2026-05-20

## Scope

A-10 found that production API runtime used PostgreSQL role `esdata`, which is a superuser and has `rolbypassrls=true`. This made `query_audit_log` append-only enforcement dependent on triggers only, not on least-privilege role design.

A-10b moved the API runtime to a dedicated non-superuser DB role while keeping Alembic/migration access on the privileged deployment role.

Production target:

```text
root@212.227.227.64
/srv/esdata
```

Evidence artifacts:

```text
/root/a10b-runtime-role-20260520
```

## Code changes

### API runtime URL separated from migration URL

`infra/deploy/docker-compose.prod.yml` now injects:

```text
DATABASE_URL=${API_DATABASE_URL}
ALEMBIC_DATABASE_URL=${ALEMBIC_DATABASE_URL}
```

for the `api` service.

Workers and cron services continue to use:

```text
DATABASE_URL=${DATABASE_URL}
```

This keeps ingestion/upsert jobs on the existing privileged operational URL while the public API runtime uses a restricted role.

### API container startup separated Alembic/runtime credentials

`apps/api/Dockerfile` now runs Alembic with `ALEMBIC_DATABASE_URL`, then restores runtime `DATABASE_URL` before starting Uvicorn.

Effective production API container environment:

```text
DATABASE_URL=postgresql+psycopg://esdata_api:***@postgres:5432/esdata
ALEMBIC_DATABASE_URL=postgresql+psycopg://esdata:***@postgres:5432/esdata
```

## Production DB changes

Created or updated role:

```sql
esdata_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS
```

Granted:

- `CONNECT` on database `esdata`
- `USAGE` on schema `public`
- `SELECT, INSERT` on all public tables
- `USAGE, SELECT` on all public sequences
- `SELECT, INSERT` on `query_audit_log`
- `USAGE, SELECT` on `query_audit_log_id_seq`
- `EXECUTE` on `modelo_campana_activa(integer)`

Revoked from `query_audit_log` for runtime role:

- `UPDATE`
- `DELETE`
- `TRUNCATE`
- `TRIGGER`

RLS:

- Added `esdata_api_select` policy to public RLS tables.
- Added `esdata_api_insert` policy to public RLS tables.
- No `UPDATE` or `DELETE` policies were added for `esdata_api`.

## Runtime role verification

Verified as `esdata_api`:

| Check | Result |
|---|---|
| `rolsuper` | `false` |
| `rolcreaterole` | `false` |
| `rolcreatedb` | `false` |
| `rolreplication` | `false` |
| `rolbypassrls` | `false` |
| `query_audit_log SELECT` | `true` |
| `query_audit_log INSERT` | `true` |
| `query_audit_log UPDATE` | `false` |
| `query_audit_log DELETE` | `false` |
| `query_audit_log TRUNCATE` | `false` |
| `query_audit_log TRIGGER` | `false` |

Negative tests as `esdata_api`:

| Attempt | Result |
|---|---|
| `UPDATE query_audit_log ...` | fails with permission denied |
| `DELETE FROM query_audit_log ...` | fails with permission denied |
| `DROP TABLE query_audit_log` | fails; role is not owner |

## API verification

Health:

```json
{"status":"ok","database":"ok"}
```

MCP audit write still works:

| Check | Result |
|---|---:|
| `query_audit_log` before MCP call | 8134 |
| `query_audit_log` after MCP call | 8135 |
| MCP tool call | `get_articulo(LIVA, 1)` |
| MCP HTTP | 200 |

Latest audit row:

| Field | Value |
|---|---|
| `id` | `8135` |
| `request_id` | `a10b-mcp-20260520183126` |
| `tool_name` | `get_articulo` |
| `path` | `/v1/legislacion/LIVA/articulos/1` |

## Drift fixed during validation

The first post-role `mcp_validation_suite` run exposed unrelated production data drift:

- Weak duplicate `norma.codigo='DORA_2022_2535'`
- Weak duplicate `norma.codigo='MICA_2023_1114'`
- `cnmv_obligation_link` had only 6 `modelo_normalizado_esi` links while 8 `modelo_esi_cnmv` documents existed.

Fix applied on VPS:

- Deleted weak duplicate DORA/MiCA rows after confirming no `obligacion_perfil` references.
- Re-ran idempotent `scripts/data/seed_sprint_l_04_cnmv_modelo_esi_links.sql`, inserting 2 missing CNMV model links.

## Validation

Local:

```text
pytest apps/ -q --basetemp .pytest-tmp
3153 passed, 2 skipped, 34 warnings
```

VPS:

```text
mcp_validation_suite.py --read-only --base-url http://api:8000
ok=true

mcp_deep_contract_audit.py --base-url http://api:8000
ok=true
```

Known validation caveat:

```text
python -m pytest scripts/tests/test_compose_env_example.py -q
```

still fails because `infra/deploy/compose.env.example` is already missing several Compose variables unrelated to A-10b (`HC_PING_URL_CRON_ESMA_*`, `AEPD_GUIDES_INDEX_URL`, `BORME_DAYS_BACK`, etc.). This is pre-existing env-template drift and should be handled separately.

## Result

A-10b PASS.

The production API runtime now uses a non-superuser DB role. `query_audit_log` is protected by both permissions and the existing append-only triggers.
