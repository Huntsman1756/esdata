# A-10 query_audit_log append-only and MCP coverage - 2026-05-20

## Scope

Audit performed against production VPS `root@212.227.227.64`, repo `/srv/esdata`, API `http://localhost:8000`, through the stateful MCP HTTP endpoint `/mcp`.

Evidence artifacts were captured on the VPS under:

```text
/root/a10-query-audit-20260520
```

## 1. Coverage: MCP call creates `query_audit_log`

MCP call executed:

```json
{"name":"get_articulo","arguments":{"codigo":"LIVA","numero":"1"}}
```

Result:

| Check | Result |
|---|---:|
| Count before | 8133 |
| Count after | 8134 |
| New row id | 8134 |
| MCP tool HTTP | 200 |

Latest row:

| Field | Value |
|---|---|
| `id` | `8134` |
| `request_id` | `a10-mcp-20260520181648` |
| `user_id` | `anonymous` |
| `tool_name` | `get_articulo` |
| `path` | `/v1/legislacion/LIVA/articulos/1` |
| `query_text` | `LIVA:1` |
| `created_at` | `2026-05-20T16:16:49.461205+00:00` |
| `verified` | `1` |
| `response_summary` | `articulo=LIVA:1` |

Status: PASS.

## 2. Runtime append-only enforcement

The audit attempted to mutate the freshly-created row as the current DB role used by production DB access.

Update attempt:

```sql
UPDATE query_audit_log
SET tool_name='tamper_a10'
WHERE id=8134;
```

Result:

```text
ERROR: query_audit_log is append-only: UPDATE not permitted (row id=8134)
```

Delete attempt:

```sql
DELETE FROM query_audit_log
WHERE id=8134;
```

Result:

```text
ERROR: query_audit_log is append-only: DELETE not permitted (row id=8134)
```

Post-check:

| Check | Result |
|---|---:|
| Row still exists | 1 |
| `tool_name` after tamper attempt | `get_articulo` |

Active triggers:

- `trg_query_audit_log_no_update`
- `trg_query_audit_log_no_delete`

Both call:

```text
query_audit_log_append_only()
```

Status: PASS for runtime trigger enforcement.

## 3. Schema check

Relevant production columns:

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | `integer` | `NO` | sequence-backed |
| `entry_id` | `text` | `NO` | audit entry identifier |
| `request_id` | `text` | `NO` | request correlation |
| `tool_name` | `text` | `NO` | MCP/API tool name |
| `path` | `text` | `NO` | endpoint path |
| `query_text` | `text` | `NO` | query parameters equivalent |
| `retrieved_chunks` | `json` | `NO` | retrieval evidence |
| `created_at` | `text` | `NO` | timestamp equivalent |
| `sources` | `text` | `NO` | serialized sources |
| `response_payload` | `text` | `NO` | final response reconstruction |

Notes:

- The table uses `created_at` as the timestamp field; it does not have a literal `timestamp` column.
- The table uses `query_text`, `path`, `retrieved_chunks`, `sources`, and `response_payload` as the query/context reconstruction fields.
- No `user_agent` column is present in this table.

Status: PASS-WITH-CAVEAT. Core audit reconstruction fields are present and `NOT NULL`; the schema does not match the PRD wording literally for `timestamp`/`user_agent`.

## 4. Permission and role hardening finding

The production API container uses:

```text
DATABASE_URL=postgresql+psycopg://esdata:***@postgres:5432/esdata
```

PostgreSQL reports for role `esdata`:

| Attribute | Value |
|---|---|
| `rolsuper` | `true` |
| `rolcreaterole` | `true` |
| `rolcreatedb` | `true` |
| `rolreplication` | `true` |
| `rolbypassrls` | `true` |

`information_schema.role_table_grants` shows `esdata` has table privileges including:

- `DELETE`
- `UPDATE`
- `TRUNCATE`
- `TRIGGER`
- `INSERT`
- `SELECT`

This means the current production append-only behavior is enforced by triggers during normal DML, but the app DB role is still too privileged. A superuser can disable triggers or bypass intended least-privilege controls.

Status: FAIL for least-privilege append-only guarantee.

## Result

A-10 coverage and runtime append-only behavior are verified. The audit also found a real hardening gap:

```text
The production API uses superuser role esdata.
```

This should be remediated as a separate story before treating `query_audit_log` append-only as a strong database-level guarantee.

Recommended follow-up:

```text
A-10b - create/use least-privileged API DB role for runtime, revoke UPDATE/DELETE/TRUNCATE on query_audit_log, keep INSERT/SELECT only, preserve migrations/admin under a separate privileged role.
```
