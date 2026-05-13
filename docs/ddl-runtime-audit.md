# Runtime DDL Audit

Date: 2026-05-13
Story: P-01
Scope: `apps/workers/` and `apps/api/`

This audit inventories runtime DDL found in worker/API code before moving schema
ownership fully to Alembic. Runtime code should read and write data only; schema
creation, schema repair, indexes, extensions and RLS should be migration-owned.

## Scan

Command used:

```bash
rg -n --glob '*.py' "(?i)\b(CREATE\s+EXTENSION|CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE|CREATE\s+(UNIQUE\s+)?INDEX|ADD\s+COLUMN|DROP\s+COLUMN)\b" apps/workers apps/api \
  | rg -v "(apps[\\/]api[\\/]tests|apps[\\/]workers[\\/]tests|__pycache__|# )"
```

Test fixtures under `apps/api/tests` and `apps/workers/tests` were excluded from
the risk table because they create ephemeral test schemas, not production runtime
schemas.

## Summary

| classification | count | meaning |
|---|---:|---|
| RISK-DESTRUCTIVE | 0 | No unguarded `DROP TABLE`, `DROP COLUMN`, or destructive runtime DDL found in the scanned runtime files. |
| RISK-IDEMPOTENT | 15 grouped findings | Runtime schema creation/repair remains in workers/API. Most is guarded with `IF NOT EXISTS`, dialect checks, information_schema checks, or index existence checks, but should still be removed from production runtime paths. |
| SAFE | 6 grouped findings | DDL strings exist but production PostgreSQL path is assertion-only or Alembic-owned; SQLite/test compatibility remains local-only. |

## Inventory

| file | lines | statement/object | idempotent | alembic coverage | classification | action |
|---|---:|---|---|---|---|---|
| `apps/workers/boe_modelos_worker.py` | 166-184 | `CREATE TABLE IF NOT EXISTS sync_log` | yes | `20260416_0001_baseline_schema.py`, `20260501_0053_absorb_runtime_table_drift.py` | RISK-IDEMPOTENT | Remove runtime create in P-03; replace with startup assertion that `sync_log` exists. |
| `apps/workers/boe.py` | 96-123 | SQLite-only `CREATE TABLE IF NOT EXISTS sync_log` | yes | production table is Alembic-owned | SAFE | Leave only if strictly needed for unit tests; no production PostgreSQL DDL here. |
| `apps/workers/boe.py` | 845 | `CREATE EXTENSION IF NOT EXISTS pg_trgm` | yes | baseline migrations use trigram indexes but extension ownership is implicit | RISK-IDEMPOTENT | Move/confirm extension ownership in Alembic; runtime should assert availability. |
| `apps/workers/boe.py` | 851-863 | `CREATE INDEX idx_version_articulo_texto_trgm ...` after pg_indexes check | yes, guard by existence query | `20260416_0001_baseline_schema.py` | RISK-IDEMPOTENT | Remove runtime repair in P-03; assert index exists or rely on migration. |
| `apps/workers/boe.py` | 879-991 | SQLite compatibility schema: `norma`, `articulo`, `version_articulo`, `materia`, `articulo_materia`, `documento_interpretativo`, `documento_articulo` | yes | production tables are Alembic-owned | SAFE | Keep scoped to SQLite tests only, or move fixtures to tests later. |
| `apps/workers/change_detection.py` | 109-139 | SQLite-only `source_revision`, `dgt_url`, indexes | yes | `20260501_0053_absorb_runtime_table_drift.py` | SAFE | Production path is explicit no-op; no Alembic work required for PostgreSQL. |
| `apps/workers/dgt.py` | 367-386 | SQLite-only `dgt_queue`, `idx_dgt_queue_pending` | yes | `20260504_0057_dgt_queue_split.py` | SAFE | Production path is explicit no-op; no Alembic work required for PostgreSQL. |
| `apps/workers/ley13_2023.py` | 311-345 | `sync_log` create plus guarded `ADD COLUMN rows_processed/errors/duration_ms` | yes, guarded by existing column query | sync_log is Alembic-owned, but these helper-specific columns need confirmation against current migration state | RISK-IDEMPOTENT | Move remaining column drift to Alembic or remove if obsolete; replace with assertion. |
| `apps/workers/prospectos.py` | 179-213 | same `sync_log` create plus guarded helper columns | yes, guarded by existing column query | sync_log is Alembic-owned, helper columns need confirmation | RISK-IDEMPOTENT | Same as `ley13_2023.py`. |
| `apps/workers/csdr.py` | 177 | `CREATE TABLE IF NOT EXISTS sync_log` | yes | sync_log is Alembic-owned | RISK-IDEMPOTENT | Remove runtime create in P-03; use shared logging/assertion helper. |
| `apps/workers/dac_directives.py` | 139 | `CREATE TABLE IF NOT EXISTS sync_log` | yes | sync_log is Alembic-owned | RISK-IDEMPOTENT | Remove runtime create in P-03; use shared logging/assertion helper. |
| `apps/workers/eurlex.py` | 1093 | `CREATE TABLE IF NOT EXISTS sync_log` | yes | sync_log is Alembic-owned | RISK-IDEMPOTENT | Remove runtime create in P-03; use shared logging/assertion helper. |
| `apps/workers/ley112009_socimi.py` | 124 | `CREATE TABLE IF NOT EXISTS sync_log` | yes | sync_log is Alembic-owned | RISK-IDEMPOTENT | Remove runtime create in P-03; use shared logging/assertion helper. |
| `apps/workers/ley222014_lecr.py` | 137 | `CREATE TABLE IF NOT EXISTS sync_log` | yes | sync_log is Alembic-owned | RISK-IDEMPOTENT | Remove runtime create in P-03; use shared logging/assertion helper. |
| `apps/workers/jurisprudencia.py` | 377 | `CREATE TABLE IF NOT EXISTS documento_interpretativo` | yes | `20260416_0001_baseline_schema.py`, plus later metadata/provenance migrations | RISK-IDEMPOTENT | Remove runtime create in P-03; assert table and required columns exist. |
| `apps/workers/entity_identity.py` | 53-80 | `entity_identifiers`, `entity_aliases` | yes | `20260426_0011_entity_identity.py` | RISK-IDEMPOTENT | Remove runtime create in P-03; assert migration-owned tables exist. |
| `apps/workers/screening.py` | 320-358 | `screening_lists`, `screening_entries`, `screening_matches` | yes | `20260426_0012_screening.py` | RISK-IDEMPOTENT | Remove runtime create in P-03; assert migration-owned tables exist. |
| `apps/workers/screening_real.py` | 333-348 | `screening_lists`, `screening_entries` | yes | `20260426_0012_screening.py` | RISK-IDEMPOTENT | Same as `screening.py`; avoid duplicate schema bootstrap. |
| `apps/api/services/webhook_verification.py` | 80-86 | `CREATE TABLE IF NOT EXISTS webhook_events` | yes | none found | RISK-IDEMPOTENT | Highest priority schema gap: add Alembic migration + RLS, then remove runtime create. |
| `apps/api/services/persistence.py` | 15-156 | governance table/index DDL template | yes | `20260426_0030_ai_governance_persistence.py`, `20260511_0068_freshness_tables_schema.py`, `20260503_0055_query_audit_response_payload.py`, `20260509_0061_audit_append_only.py` | SAFE | Production PostgreSQL path verifies schema and returns; DDL executes only for SQLite compatibility. |
| `apps/api/services/persistence.py` | 285-315 | guarded query_audit_log `ADD COLUMN` repair | yes, guarded by existing columns and only reached after SQLite path | `20260503_0055_query_audit_response_payload.py` and grounding migrations | SAFE | No PostgreSQL runtime DDL because `ensure_governance_tables` returns after schema verification. |

## P-02 candidates

No `RISK-DESTRUCTIVE` entries were found in the runtime scan. P-02 should confirm
this against production before marking pass, but there is no destructive DDL to
move based on the local code search.

## P-03 candidates

P-03 should remove all `RISK-IDEMPOTENT` runtime DDL from production paths. The
first batch should be:

1. `apps/api/services/webhook_verification.py`: create Alembic migration for
   `webhook_events`, enable RLS/service-role policy, then replace runtime create
   with assertion.
2. `apps/workers/boe_modelos_worker.py`: remove `sync_log` creation and use a
   shared `assert_table_exists("sync_log")` or shared logging runtime helper.
3. `apps/workers/ley13_2023.py` and `apps/workers/prospectos.py`: confirm
   `rows_processed`, `errors`, `duration_ms` are migration-owned; if not, add a
   migration, then remove runtime `ALTER TABLE`.
4. Remaining workers with local `_ensure_*` table creation for migration-owned
   tables should be converted to assertions or shared helpers.

## P-03 resolution

Implemented on 2026-05-13:

- Added migration `20260513_0073_webhook_events.py` so `webhook_events` is
  Alembic-owned and RLS-protected.
- Removed runtime table creation from `apps/api/services/webhook_verification.py`;
  it now asserts the migration-owned table and columns exist.
- Converted production schema bootstrap paths in the RISK-IDEMPOTENT workers to
  `assert_table_exists`, `assert_postgres_extension`, and `assert_postgres_index`.
- Kept SQLite-only test compatibility in explicit helpers under
  `apps/workers/runtime.py`; these are not used by PostgreSQL production paths.
- Verification: targeted DDL gate over all RISK-IDEMPOTENT files returned no
  runtime DDL hits, and the full app test suite passed with `3011 passed,
  2 skipped`.

## Notes

- The scan included `CREATE EXTENSION` in addition to the requested table/index
  patterns because extensions are schema-level DDL and should also be
  migration-owned.
- The codebase already contains an earlier drift-absorption migration for
  `sync_log` and `source_revision` (`20260501_0053_absorb_runtime_table_drift.py`);
  this audit shows several old runtime bootstraps still need to be deleted.
- This story intentionally made no runtime code changes.
