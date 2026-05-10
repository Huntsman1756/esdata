# MCP/VPS audit - 2026-05-10

## Verdict

**CONDITIONAL PASS after hotfixes.** The MCP/API, core ingestion data, Hermes
monitoring loop, backup loop, Alertmanager process, and principal regulatory
datasets are operational in local and VPS. The audit did find real blockers; the
database RLS blocker and most infrastructure blockers were fixed and verified
during this audit. SSH root/password remains intentionally unchanged because it
is still needed for current operations.

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
- Hardened VPS deploy tree permissions:
  - `/srv/esdata`, `/srv/esdata/infra`, `/srv/esdata/infra/deploy`: `deploy:deploy`, no world write.
  - Remaining `find -perm -0002` entries are symlinks only.
- Closed non-ESData public ports at UFW: `8080/tcp`, `8501/tcp`, `8502/tcp` deny for IPv4/IPv6.
- Enabled Docker json-file log rotation in `/etc/docker/daemon.json`: `max-size=50m`, `max-file=5`.
- Started Alertmanager and made its Compose startup fail-open to a local noop receiver if Telegram token/chat id are missing.
- Started backup service and performed a full restore drill into `esdata_restore_check`.
- Added cron hardening:
  - all `cron-*` services inherit read-only rootfs, `/tmp` tmpfs, no-new-privileges.
  - systemd job units use `flock` locks and `RuntimeMaxSec`.
  - MCP validation unit has a 10 minute runtime cap.

## Runtime evidence

- Local API `/status`: `api=ok`, `database=ok`, `modelos.total=219`.
- Local focal test suite: `60 passed, 4 warnings`.
- Local extended focal test suite after hardening: `93 passed, 4 warnings`.
- Local RLS SQL: `disabled_count|0`.
- VPS RLS SQL: `disabled_count|0`.
- VPS Hermes: API health OK, domain availability OK, all workers healthy, DLQ below alert threshold.
- VPS MCP validation: `ok=true`.
- VPS restore drill:
  - `restore_tables|163`
  - `restore_aeat_modelo|219`
  - `restore_modelo_casilla|28875`
- VPS API status after rebuild: `api|ok`, `database|ok`, `workers|33`.
- Core VPS row counts observed during audit:
  - `casp`: 192 rows, 191 active
  - `giin_registry`: 508593 rows
  - `screening_entries`: 18947 rows
  - `articulo`: 902 rows
  - `aeat_modelo`: 219 rows
  - `modelo_casilla`: 28875 rows

## Remaining blockers before production-ready

- SSH root login and password authentication remain enabled on the VPS.
- Telegram delivery is not active until `/srv/esdata/infra/deploy/secrets/alertmanager/telegram_bot_token` contains a real token and `TELEGRAM_CHAT_ID` is non-empty in `/etc/esdata/esdata.env`. Alertmanager now stays running with noop config instead of crashing.
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
