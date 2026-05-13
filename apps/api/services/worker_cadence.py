"""Canonical worker cadence registry for /status and alert freshness."""

from __future__ import annotations

from typing import TypedDict


class WorkerCadence(TypedDict):
    trigger: str
    expected_cadence_hours: int
    stale_threshold_hours: int
    cron_expression: str
    notes: str


# Every active /status worker must have an explicit cadence entry.
# Rule: stale_threshold_hours >= expected_cadence_hours * 1.5.
WORKER_CADENCE_CONFIG: dict[str, WorkerCadence] = {
    # real schedule: continuous loop every 1h = 1 hour
    "worker-boe": {
        "trigger": "event_driven",
        "expected_cadence_hours": 1,
        "stale_threshold_hours": 25,
        "cron_expression": "SYNC_INTERVAL_SECONDS=3600",
        "notes": "Continuous BOE consolidated legislation worker; wider threshold tolerates quiet weekends/redeploys.",
    },
    # real schedule: systemd daily 06:00 Europe/Madrid = 24 hours
    "cron-boe-daily": {
        "trigger": "cron_daily",
        "expected_cadence_hours": 24,
        "stale_threshold_hours": 36,
        "cron_expression": "*-*-* 06:00:00 Europe/Madrid",
        "notes": "BOE consolidated legislation daily cron.",
    },
    # real schedule: systemd daily 06:30 Europe/Madrid = 24 hours
    "cron-boe-diario-daily": {
        "trigger": "cron_daily",
        "expected_cadence_hours": 24,
        "stale_threshold_hours": 36,
        "cron_expression": "*-*-* 06:30:00 Europe/Madrid",
        "notes": "BOE diario non-consolidated daily cron.",
    },
    # real schedule: persistent loop every 24h; scheduler service cron-boe-modelos-daily also writes here
    "worker-boe-modelos": {
        "trigger": "cron_daily",
        "expected_cadence_hours": 24,
        "stale_threshold_hours": 36,
        "cron_expression": "BOE_MODELOS_SYNC_INTERVAL=86400; timer *-*-* 06:00:00 Europe/Madrid",
        "notes": "BOE sourced modelo metadata. cron-boe-modelos-daily writes sync_log as worker-boe-modelos.",
    },
    # real schedule: persistent loop every 24h = 24 hours
    "worker-modelos": {
        "trigger": "cron_daily",
        "expected_cadence_hours": 24,
        "stale_threshold_hours": 36,
        "cron_expression": "AEAT_MODELS_SYNC_INTERVAL=86400",
        "notes": "AEAT modelos persistent worker.",
    },
    # real schedule: systemd daily 05:00 Europe/Madrid = 24 hours
    "cron-modelos-daily": {
        "trigger": "cron_daily",
        "expected_cadence_hours": 24,
        "stale_threshold_hours": 36,
        "cron_expression": "*-*-* 05:00:00 Europe/Madrid",
        "notes": "AEAT modelos scheduled cron.",
    },
    # real schedule: systemd daily 06:30 Europe/Madrid = 24 hours
    "cron-aeat-current-daily": {
        "trigger": "cron_daily",
        "expected_cadence_hours": 24,
        "stale_threshold_hours": 36,
        "cron_expression": "*-*-* 06:30:00 Europe/Madrid",
        "notes": "AEAT current designs and calendar scheduled cron.",
    },
    # real schedule: systemd daily 07:00 Europe/Madrid = 24 hours
    "cron-regulatory-daily": {
        "trigger": "cron_daily",
        "expected_cadence_hours": 24,
        "stale_threshold_hours": 36,
        "cron_expression": "*-*-* 07:00:00 Europe/Madrid",
        "notes": "Regulatory source revision watcher.",
    },
    # real schedule: persistent loop every 168h = 1 week
    "worker-dgt": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "SYNC_INTERVAL_SECONDS=604800",
        "notes": "DGT doctrina persistent worker.",
    },
    # real schedule: systemd weekly Monday 07:00 Europe/Madrid = 168 hours
    "cron-dgt-weekly": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Mon *-*-* 07:00:00 Europe/Madrid",
        "notes": "DGT doctrina scheduled cron.",
    },
    # real schedule: persistent loop every 168h = 1 week
    "worker-teac": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "SYNC_INTERVAL_SECONDS=604800",
        "notes": "TEAC persistent worker.",
    },
    # real schedule: systemd weekly Monday 08:00 Europe/Madrid = 168 hours
    "cron-teac-weekly": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Mon *-*-* 08:00:00 Europe/Madrid",
        "notes": "TEAC scheduled cron.",
    },
    # real schedule: persistent loop every 168h = 1 week
    "worker-bdns": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "SYNC_INTERVAL_SECONDS=604800",
        "notes": "BDNS persistent worker.",
    },
    # real schedule: systemd weekly Tuesday 09:00 Europe/Madrid = 168 hours
    "cron-bdns-weekly": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Tue *-*-* 09:00:00 Europe/Madrid",
        "notes": "BDNS scheduled cron.",
    },
    # real schedule: persistent loop every 168h = 1 week
    "worker-borme": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "SYNC_INTERVAL_SECONDS=604800",
        "notes": "BORME persistent worker.",
    },
    # real schedule: systemd weekly Tuesday 10:00 Europe/Madrid = 168 hours
    "cron-borme-weekly": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Tue *-*-* 10:00:00 Europe/Madrid",
        "notes": "BORME scheduled cron.",
    },
    # real schedule: persistent loop every 168h = 1 week
    "worker-bde": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "SYNC_INTERVAL_SECONDS=604800",
        "notes": "Banco de Espana persistent worker.",
    },
    # real schedule: systemd weekly Tuesday 13:00 Europe/Madrid = 168 hours
    "cron-bde-weekly": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Tue *-*-* 13:00:00 Europe/Madrid",
        "notes": "Banco de Espana scheduled cron.",
    },
    # real schedule: persistent loop every 168h = 1 week
    "worker-cendoj": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "SYNC_INTERVAL_SECONDS=604800",
        "notes": "CENDOJ persistent worker.",
    },
    # real schedule: systemd weekly Tuesday 14:00 Europe/Madrid = 168 hours
    "cron-cendoj-weekly": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Tue *-*-* 14:00:00 Europe/Madrid",
        "notes": "CENDOJ scheduled cron.",
    },
    # real schedule: persistent loop every 168h = 1 week
    "worker-aepd": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "SYNC_INTERVAL_SECONDS=604800",
        "notes": "AEPD persistent worker.",
    },
    # real schedule: systemd weekly Tuesday 15:00 Europe/Madrid = 168 hours
    "cron-aepd-weekly": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Tue *-*-* 15:00:00 Europe/Madrid",
        "notes": "AEPD scheduled cron.",
    },
    # real schedule: persistent loop every 168h = 1 week
    "worker-eurlex": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "SYNC_INTERVAL_SECONDS=604800",
        "notes": "EUR-Lex persistent worker.",
    },
    # real schedule: systemd weekly Tuesday 16:00 Europe/Madrid = 168 hours
    "cron-eurlex-weekly": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Tue *-*-* 16:00:00 Europe/Madrid",
        "notes": "EUR-Lex scheduled cron.",
    },
    # real schedule: persistent loop every 168h = 1 week
    "worker-cnmv": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "SYNC_INTERVAL_SECONDS=604800",
        "notes": "CNMV persistent worker.",
    },
    # real schedule: systemd weekly Wednesday 09:00 Europe/Madrid = 168 hours
    "cron-cnmv-weekly": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Wed *-*-* 09:00:00 Europe/Madrid",
        "notes": "CNMV scheduled cron.",
    },
    # real schedule: persistent loop every 168h = 1 week
    "worker-sepblac": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "SYNC_INTERVAL_SECONDS=604800",
        "notes": "SEPBLAC persistent worker.",
    },
    # real schedule: systemd weekly Wednesday 10:00 Europe/Madrid = 168 hours
    "cron-sepblac-weekly": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Wed *-*-* 10:00:00 Europe/Madrid",
        "notes": "SEPBLAC scheduled cron.",
    },
    # real schedule: systemd weekly Wednesday 11:00 Europe/Madrid = 168 hours
    "cron-psd2-weekly": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Wed *-*-* 11:00:00 Europe/Madrid",
        "notes": "PSD2/EBA scheduled cron.",
    },
    # real schedule: systemd weekly Wednesday 11:20 Europe/Madrid = 168 hours
    "official-regulatory-references": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Wed *-*-* 11:20:00 Europe/Madrid",
        "notes": "Official regulatory reference scheduled cron.",
    },
    # real schedule: persistent loop every 168h = 1 week
    "worker-cdi": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "CDI_SYNC_INTERVAL_SECONDS=604800",
        "notes": "International tax treaty persistent worker.",
    },
    # real schedule: systemd weekly = 168 hours
    "cron-cdi-weekly": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "weekly Europe/Madrid",
        "notes": "International tax treaty scheduled cron.",
    },
    # real schedule: systemd weekly Monday 03:15 Europe/Madrid = 168 hours
    "cron-ofac-sdn-weekly": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Mon *-*-* 03:15:00 Europe/Madrid",
        "notes": "OFAC SDN scheduled cron.",
    },
    # real schedule: systemd weekly Monday 03:35 Europe/Madrid = 168 hours
    "cron-mica-weekly": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Mon *-*-* 03:35:00 Europe/Madrid",
        "notes": "ESMA MiCA CASP scheduled cron.",
    },
    # real schedule: systemd monthly day 4 03:00 Europe/Madrid = 720 hours
    "worker-eurlex-market": {
        "trigger": "cron_monthly",
        "expected_cadence_hours": 720,
        "stale_threshold_hours": 1080,
        "cron_expression": "*-*-04 03:00:00 Europe/Madrid",
        "notes": "Dedicated EUR-Lex market acts refresh for MiFID II, MiFIR, MiCA and DLT Pilot.",
    },
    # real schedule: systemd weekly Monday 04:05 Europe/Madrid = 168 hours
    "worker-esma-mifir-reporting": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Mon *-*-* 04:05:00 Europe/Madrid",
        "notes": "ESMA MiFIR transaction reporting schemas, reporting documents and validation rules.",
    },
    # real schedule: systemd daily 04:20 Europe/Madrid = 24 hours
    "worker-esma-firds": {
        "trigger": "cron_daily",
        "expected_cadence_hours": 24,
        "stale_threshold_hours": 36,
        "cron_expression": "*-*-* 04:20:00 Europe/Madrid",
        "notes": "ESMA FIRDS DLTINS file metadata and bounded pilot sample refresh.",
    },
    # real schedule: systemd weekly Monday 04:35 Europe/Madrid = 168 hours
    "worker-esma-dlt": {
        "trigger": "cron_weekly",
        "expected_cadence_hours": 168,
        "stale_threshold_hours": 252,
        "cron_expression": "Mon *-*-* 04:35:00 Europe/Madrid",
        "notes": "ESMA DLT authorised market infrastructures official PDF refresh.",
    },
    # real schedule: systemd monthly day 2 02:00 Europe/Madrid = 720 hours
    "cron-giin-monthly": {
        "trigger": "cron_monthly",
        "expected_cadence_hours": 720,
        "stale_threshold_hours": 1080,
        "cron_expression": "*-*-02 02:00:00 Europe/Madrid",
        "notes": "IRS GIIN monthly sync.",
    },
    # real schedule: systemd monthly day 3 02:20 Europe/Madrid = 720 hours
    "cron-pgc-boe-monthly": {
        "trigger": "cron_monthly",
        "expected_cadence_hours": 720,
        "stale_threshold_hours": 1080,
        "cron_expression": "*-*-03 02:20:00 Europe/Madrid",
        "notes": "PGC BOE monthly sync.",
    },
}


WORKER_CADENCE_ALIASES = {
    "modelos": "worker-modelos",
    "worker-aeat-modelos": "worker-modelos",
    "worker-aeat-current-designs": "cron-aeat-current-daily",
    "cron-eurlex-market-monthly": "worker-eurlex-market",
    "cron-esma-mifir-reporting-weekly": "worker-esma-mifir-reporting",
    "cron-esma-firds-daily": "worker-esma-firds",
    "cron-esma-dlt-weekly": "worker-esma-dlt",
}


WORKER_CADENCE_EXCLUDED = {
    "cron-boe-modelos-daily": "scheduler service writes sync_log as worker-boe-modelos",
}
