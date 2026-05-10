# MCP/VPS audit - 2026-05-10

## Verdict

**CONDITIONAL PASS after hotfix.** The MCP/API, core ingestion data, Hermes
monitoring loop, and principal regulatory datasets are operational in local and
VPS. The audit did find real blockers; the database RLS blocker was fixed and
verified during this audit. Infrastructure hardening remains required before a
production-ready verdict.

## Fixed during audit

- Added Alembic revision `20260510_0067_monitoring_rls_closure`.
- Applied the RLS closure locally and on VPS for:
  - `data_freshness_alerts`
  - `source_freshness_snapshot`
  - `sync_dead_letter`
- Verification SQL returned:
  - each target table: `relrowsecurity=true`
  - policies: `esdata_all:esdata`, `service_role_all:service_role`
  - all public tables without RLS: `0`
  - public/anon policies on target tables: `0`
  - Alembic head: `20260510_0067_monitoring_rls_closure`

## Runtime evidence

- Local API `/status`: `api=ok`, `database=ok`, `modelos.total=219`.
- Local focal test suite: `60 passed, 4 warnings`.
- Local RLS SQL: `disabled_count|0`.
- VPS RLS SQL: `disabled_count|0`.
- VPS Hermes: API health OK, domain availability OK, all workers healthy, DLQ below alert threshold.
- Core VPS row counts observed during audit:
  - `casp`: 192 rows, 191 active
  - `giin_registry`: 508593 rows
  - `screening_entries`: 18947 rows
  - `articulo`: 902 rows
  - `aeat_modelo`: 219 rows
  - `modelo_casilla`: 28875 rows

## Remaining blockers before production-ready

- SSH root login and password authentication remain enabled on the VPS.
- `/srv/esdata` deployment tree is world-writable and not a clean git checkout.
- No verified ESData database backup/restore loop was found.
- Extra public ports remain exposed: 8080, 8501, 8502.
- Alertmanager is not running even though alert rules exist.
- Docker log rotation is not enforced globally.
- Scheduled jobs need non-overlap locks and runtime caps.
- HTTP MCP works, but the implementation still depends on private `fastapi-mcp`
  internals and stdio tool listing is not yet aligned with stdio dispatch.

## Maintenance decision

- Keep Hermes-style monitor deployed with read-only DB/API access plus safe
  service-status checks.
- Add tester/healer jobs for schema/tool/output regression tests; remediation
  must be limited to infrastructure-level reversible actions.
- Add regulatory awareness watcher for BOE/AEAT/ESMA/OFAC/IRS source changes;
  it may create review tasks and freshness warnings but must not silently mutate
  compliance data.
- Do not deploy any autonomous agent with unrestricted write access to tax or
  legal records.
