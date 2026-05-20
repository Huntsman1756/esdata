# Stale worker audit - 2026-05-20

## Scope

Audit performed against VPS `root@212.227.227.64`, repo `/srv/esdata`, after historical Telegram alerts from 2026-05-11 for:

- `cron-psd2-weekly`
- `official-regulatory-references`
- `cron-pgc-boe-monthly`

Current date during audit: 2026-05-20.

## Alertmanager

Current Alertmanager state: no active alerts.

The 2026-05-11 alerts are not currently firing. They are treated as historical incidents plus regression checks.

## P-01 cron-psd2-weekly

Result: PASS, no code fix required.

Evidence:

- `apps/workers/psd2.py` imports and calls `ensure_database_connection`.
- Ephemeral debug container network: `deploy_esdata-internal`.
- Manual run succeeded and wrote fresh `sync_log` row:
  - `id=1621`
  - `worker='cron-psd2-weekly'`
  - `status='ok'`
  - `rows_processed=11`

Observed caveat: EBA EUCLID JSON discovery is not directly usable by the worker, so it falls back to BdE-verified seed data. This is logged explicitly and is not a silent failure.

## P-02 official-regulatory-references

Result: PASS, no code fix required.

Evidence:

- `apps/workers/official_regulatory_references.py` imports and calls `ensure_database_connection`.
- Ephemeral debug container network: `deploy_esdata-internal`.
- Manual run succeeded and wrote fresh `sync_log` row:
  - `id=1622`
  - `worker='official-regulatory-references'`
  - `status='ok'`

## P-03 cron-pgc-boe-monthly

Result: PASS, no code fix required.

Evidence:

- `apps/workers/pgc_boe.py` imports and calls `ensure_database_connection`.
- Ephemeral debug container network: `deploy_esdata-internal`.
- Manual run succeeded and wrote fresh `sync_log` row:
  - `id=1623`
  - `worker='cron-pgc-boe-monthly'`
  - `status='ok'`
  - `rows_processed=888`

Systemd note: `esdata-pgc-boe-monthly.timer` is active and scheduled for 2026-06-03. It had no previous timer-fired `LAST` because it was installed after the monthly run window; manual `sync_log` rows already existed from 2026-05-11.

## A-01 retry coverage

Result: PASS after documentation refresh.

The code-level guard already passed: every `apps/workers/*.py` file that creates a SQLAlchemy engine with `create_engine(...)` includes `ensure_database_connection`.

Documentation drift fixed:

- `docs/worker-db-retry-coverage.md` now records 68 in-scope worker files.
- Added current in-scope workers that were missing from the document: `eurlex_market.py`, `eu_sanctions.py`, `worker_esma_dlt.py`, `worker_esma_firds.py`, `worker_esma_mifir_reporting.py`.

Verification:

```powershell
python -m pytest scripts/tests/test_worker_db_retry_coverage.py -q --basetemp .pytest-tmp
```

Result: `3 passed`.

## A-02 systemd timers

Result: PASS after VPS operational fix.

Finding:

- Compose defines `cron-eu-sanctions-weekly`.
- Repo already contains `infra/deploy/systemd/esdata-eu-sanctions-weekly.timer`.
- VPS did not have `/etc/systemd/system/esdata-eu-sanctions-weekly.timer` installed.

Fix applied on VPS:

```bash
install -m 0644 /srv/esdata/infra/deploy/systemd/esdata-eu-sanctions-weekly.timer \
  /etc/systemd/system/esdata-eu-sanctions-weekly.timer
systemd-analyze verify /etc/systemd/system/esdata-eu-sanctions-weekly.timer \
  /etc/systemd/system/esdata-job@.service
systemctl daemon-reload
systemctl enable --now esdata-eu-sanctions-weekly.timer
```

Verification:

- `systemd-analyze verify /etc/systemd/system/esdata-*.timer /etc/systemd/system/esdata-job@.service` exited 0.
- `esdata-eu-sanctions-weekly.timer` is active and next scheduled for 2026-05-25 03:25 Europe/Madrid.

## A-03 cron Docker networks

Result: PASS.

All cron services in `infra/deploy/docker-compose.prod.yml`, including `official-regulatory-references`, declare:

```text
['esdata-internal']
```

Spot-checked ephemeral production containers:

- `cron-psd2-weekly`
- `official-regulatory-references`
- `cron-pgc-boe-monthly`

All joined Docker network:

```text
deploy_esdata-internal
```

No evidence of `deploy_default` attachment was found.
