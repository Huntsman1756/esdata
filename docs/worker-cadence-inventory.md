# Worker Cadence Inventory

Date: 2026-05-13  
Scope: W-01, worker stale-threshold hardening.

## Method

Sources checked:

- Production `sync_log`: 37 distinct worker names.
- Production `/status`: 36 registered worker entries.
- Installed systemd timers: `/etc/systemd/system/esdata-*.timer`.
- Cron entries: `/etc/cron.d/*`, deploy crontab and root crontab.
- Docker Compose cron services: `docker compose --profile cron config --services`.
- Current stale thresholds: `apps/api/routers/status.py`.

Match rule used for W-01:

- `YES`: current threshold is explicit and is at least `expected_cadence_hours * 1.5`, or the worker is a continuous loop where the current threshold is intentionally wider than the loop cadence.
- `NO`: missing explicit threshold, threshold is below `expected_cadence_hours * 1.5`, or the worker only appears as a historical alias.

This intentionally flags tight thresholds before they become 3am false positives.

## Installed Cron And Timer Coverage

- `/etc/cron.d/esdata-weekly-accuracy`: Monday 08:00 Europe/Madrid, runs `scripts/weekly-accuracy-check.sh`.
- deploy crontab: empty.
- root crontab: empty.
- Non-ESData cron entries observed: `e2scrub_all`, `sysstat`, `steamcases-pipeline`.
- Compose cron services found: 23.
- Installed ESData timers found: 24, including `esdata-mcp-validation.timer`.

`cron-boe-modelos-daily` is a scheduled Compose service, but its worker writes `sync_log.worker='worker-boe-modelos'`; it is therefore represented by `worker-boe-modelos` in `/status`.

## Inventory

| worker | source | trigger_type | real_cadence_hours | current_threshold_hours | match | evidence |
| --- | --- | --- | ---: | ---: | --- | --- |
| worker-boe | `/status`, `sync_log`, persistent Compose | event_driven | 1 | 25 | YES | `SYNC_INTERVAL_SECONDS=3600`; last ok 2026-05-13T03:05Z. Threshold is loose but not a false-positive source. |
| cron-boe-daily | `/status`, `sync_log`, systemd | cron_daily | 24 | 25 | NO | `esdata-boe-daily.timer`, `OnCalendar=*-*-* 06:00 Europe/Madrid`; threshold below 36h policy. |
| cron-boe-diario-daily | `/status`, `sync_log`, systemd | cron_daily | 24 | 25 | NO | `esdata-boe-diario-daily.timer`, `OnCalendar=*-*-* 06:30 Europe/Madrid`; threshold below 36h policy. |
| worker-boe-modelos | `/status`, `sync_log`, persistent Compose | cron_daily | 24 | 26 | NO | `BOE_MODELOS_SYNC_INTERVAL=86400`; scheduled alias `cron-boe-modelos-daily`; threshold below 36h policy. |
| worker-modelos | `/status`, `sync_log`, persistent Compose | cron_daily | 24 | 26 | NO | `AEAT_MODELS_SYNC_INTERVAL=86400`; threshold below 36h policy. |
| cron-modelos-daily | `/status`, `sync_log`, systemd | cron_daily | 24 | 26 | NO | `esdata-modelos-daily.timer`, `OnCalendar=*-*-* 05:00 Europe/Madrid`; threshold below 36h policy. |
| cron-aeat-current-daily | `/status`, `sync_log` alias, systemd | cron_daily | 24 | 26 | NO | `esdata-aeat-current-daily.timer`, `OnCalendar=*-*-* 06:30 Europe/Madrid`; threshold below 36h policy. |
| cron-regulatory-daily | `/status`, `sync_log`, systemd | cron_daily | 24 | 25 default | NO | `esdata-reg-watch-daily.timer`, `OnCalendar=*-*-* 07:00 Europe/Madrid`; no explicit threshold in `WORKER_THRESHOLDS_HOURS`. |
| worker-dgt | `/status`, `sync_log`, persistent Compose | cron_weekly | 168 | 192 | NO | `SYNC_INTERVAL_SECONDS=604800`; threshold below 252h policy. |
| cron-dgt-weekly | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-dgt-weekly.timer`, `OnCalendar=Mon 07:00 Europe/Madrid`; threshold below 252h policy. |
| worker-teac | `/status`, `sync_log`, persistent Compose | cron_weekly | 168 | 192 | NO | `SYNC_INTERVAL_SECONDS=604800`; threshold below 252h policy. |
| cron-teac-weekly | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-teac-weekly.timer`, `OnCalendar=Mon 08:00 Europe/Madrid`; threshold below 252h policy. |
| worker-bdns | `/status`, `sync_log`, persistent Compose | cron_weekly | 168 | 192 | NO | `SYNC_INTERVAL_SECONDS=604800`; threshold below 252h policy. |
| cron-bdns-weekly | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-bdns-weekly.timer`, `OnCalendar=Tue 09:00 Europe/Madrid`; threshold below 252h policy. |
| worker-borme | `/status`, `sync_log`, persistent Compose | cron_weekly | 168 | 192 | NO | `SYNC_INTERVAL_SECONDS=604800`; threshold below 252h policy. |
| cron-borme-weekly | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-borme-weekly.timer`, `OnCalendar=Tue 10:00 Europe/Madrid`; threshold below 252h policy. |
| worker-bde | `/status`, `sync_log`, persistent Compose | cron_weekly | 168 | 192 | NO | `SYNC_INTERVAL_SECONDS=604800`; threshold below 252h policy. |
| cron-bde-weekly | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-bde-weekly.timer`, `OnCalendar=Tue 13:00 Europe/Madrid`; threshold below 252h policy. |
| worker-cendoj | `/status`, `sync_log`, persistent Compose | cron_weekly | 168 | 192 | NO | `SYNC_INTERVAL_SECONDS=604800`; threshold below 252h policy. |
| cron-cendoj-weekly | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-cendoj-weekly.timer`, `OnCalendar=Tue 14:00 Europe/Madrid`; threshold below 252h policy. |
| worker-aepd | `/status`, `sync_log`, persistent Compose | cron_weekly | 168 | 192 | NO | `SYNC_INTERVAL_SECONDS=604800`; threshold below 252h policy. |
| cron-aepd-weekly | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-aepd-weekly.timer`, `OnCalendar=Tue 15:00 Europe/Madrid`; threshold below 252h policy. |
| worker-eurlex | `/status`, `sync_log`, persistent Compose | cron_weekly | 168 | 192 | NO | `SYNC_INTERVAL_SECONDS=604800`; threshold below 252h policy. |
| cron-eurlex-weekly | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-eurlex-weekly.timer`, `OnCalendar=Tue 16:00 Europe/Madrid`; threshold below 252h policy. |
| worker-cnmv | `/status`, `sync_log`, persistent Compose | cron_weekly | 168 | 192 | NO | `SYNC_INTERVAL_SECONDS=604800`; threshold below 252h policy. |
| cron-cnmv-weekly | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-cnmv-weekly.timer`, `OnCalendar=Wed 09:00 Europe/Madrid`; threshold below 252h policy. |
| worker-sepblac | `/status`, `sync_log`, persistent Compose | cron_weekly | 168 | 192 | NO | `SYNC_INTERVAL_SECONDS=604800`; threshold below 252h policy. |
| cron-sepblac-weekly | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-sepblac-weekly.timer`, `OnCalendar=Wed 10:00 Europe/Madrid`; threshold below 252h policy. |
| cron-psd2-weekly | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-psd2-weekly.timer`, `OnCalendar=Wed 11:00 Europe/Madrid`; threshold below 252h policy. |
| official-regulatory-references | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-official-regulatory-references-weekly.timer`, `OnCalendar=Wed 11:20 Europe/Madrid`; threshold below 252h policy. |
| worker-cdi | `/status`, `sync_log`, persistent Compose | cron_weekly | 168 | 192 | NO | `CDI_SYNC_INTERVAL_SECONDS=604800`; threshold added after false positive but still below 252h policy. |
| cron-cdi-weekly | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-cdi-weekly.timer`, `OnCalendar=weekly Europe/Madrid`; false positive fixed with 192h, but W-03 policy requires 252h. |
| cron-ofac-sdn-weekly | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-ofac-sdn-weekly.timer`, `OnCalendar=Mon 03:15 Europe/Madrid`; threshold below 252h policy. |
| cron-mica-weekly | `/status`, `sync_log`, systemd | cron_weekly | 168 | 192 | NO | `esdata-mica-weekly.timer`, `OnCalendar=Mon 03:35 Europe/Madrid`; threshold below 252h policy. |
| cron-giin-monthly | `/status`, `sync_log`, systemd | cron_monthly | 720 | 960 | NO | `esdata-giin-monthly.timer`, `OnCalendar=*-*-02 02:00 Europe/Madrid`; threshold below 1080h policy. |
| cron-pgc-boe-monthly | `/status`, `sync_log`, systemd | cron_monthly | 720 | 960 | NO | `esdata-pgc-boe-monthly.timer`, `OnCalendar=*-*-03 02:20 Europe/Madrid`; threshold below 1080h policy. |
| worker-aeat-current-designs | `sync_log` only, canonical alias | manual | 24 | alias -> 26 | NO | Historical alias canonicalized to `cron-aeat-current-daily`; should not remain a separate active worker name. |
| worker-aeat-modelos | `sync_log` only, canonical alias | manual | 24 | alias -> 26 | NO | Historical alias canonicalized to `worker-modelos`; should not remain a separate active worker name. |

## Mismatch Summary

- Total inventory rows: 38.
- `YES`: 1 (`worker-boe`).
- `NO`: 37.
- Direct false-positive class found: daily/weekly/monthly workers with thresholds below the new `1.5x cadence` policy, plus `cron-regulatory-daily` missing an explicit threshold and using the default.
- Scheduler-only service to account for in W-02/W-03: `cron-boe-modelos-daily` writes as `worker-boe-modelos`.

## W-02 Targets

The following are the concrete fixes for the next story:

- Add canonical worker cadence config with explicit cadence and stale threshold for every active `/status` worker.
- Replace the default-driven `cron-regulatory-daily` behavior with explicit config.
- Raise daily cron thresholds to at least 36h.
- Raise weekly worker/cron thresholds to at least 252h.
- Raise monthly thresholds to at least 1080h.
- Keep `worker-boe` explicitly configured as a 1h continuous loop with a deliberate wider threshold.
- Keep historical aliases documented or excluded explicitly so they cannot reintroduce silent default behavior.
