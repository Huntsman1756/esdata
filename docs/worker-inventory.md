# Worker Inventory - A-12

Date: 2026-05-20
Branch: `fix/full-audit-stale-workers-20260520`
Baseline: v1.13.0 + A-01..A-11 audit fixes

## Scope

This inventory classifies the 68 DB worker modules listed in `docs/worker-db-retry-coverage.md`.
Those 68 files are the files in `apps/workers/*.py` that create a SQLAlchemy engine and therefore need the retry guard.

Out of scope:

- Helper files without `create_engine(...)`, such as `runtime.py`, `dead_letter.py`, `entrypoint.py`, `change_detection.py`, `boe_modelos.py`, `boe_pdf_parser.py`, `modelos_support.py`, `pgc_dataset.py`, `vocabulary.py`, and `vocabulary_validation.py`.
- Test fixtures and test modules.
- MCP transport behavior such as authenticated `GET /mcp` returning `400 Missing session ID`; that was closed in A-11 as expected stateful MCP behavior.

Evidence used:

- `docs/worker-db-retry-coverage.md`: 68 in-scope DB worker files, 0 missing retry guard.
- `infra/deploy/docker-compose.prod.yml`: 14 persistent worker files and 28 cron services.
- `infra/deploy/systemd/*.timer`: timers installed for all 28 cron services.
- VPS `/srv/esdata` on `root@212.227.227.64`: `systemctl list-timers` and `sync_log` snapshot taken during A-12.
- A-05/A-11 reports for Compose-service to `sync_log.worker` aliases.

## Summary

| Type | Count | Meaning |
|---|---:|---|
| `active-persistent` | 14 | Has a persistent Docker Compose worker service; most also have a cron run-once pair. |
| `active-cron` | 14 | No persistent service, but has a profiled cron service plus systemd timer. |
| `helper/module` | 31 | DB-capable module retained for manual/backlog/domain workflows; not a production Compose/systemd job today. |
| `dead/unused` | 9 | Superseded, legacy, or development-only DB loader; not production runtime. |
| **Total** | **68** | All in-scope retry-guarded DB worker files. |

No worker is left unclassified or without an explanatory comment.

Type labels are intentionally plain:

- `TYPE-active-persistent`
- `TYPE-active-cron`
- `TYPE-helper/module`
- `TYPE-dead/unused`

## Active Persistent Workers

All rows below have `retry-guard=yes`. Network is `esdata-internal`.

| File | Type | Compose service(s) | sync_log/status worker | Timer installed | Comment |
|---|---|---|---|---|---|
| `aeat_models.py` | `active-persistent` | `worker-modelos`, `worker-aeat`, `cron-modelos-daily` | `worker-modelos`, `cron-modelos-daily`, legacy `worker-aeat-modelos` | yes: `esdata-modelos-daily.timer` | Canonical AEAT model worker. `worker-aeat` is profiled/manual; persistent runtime is `worker-modelos`. |
| `aepd.py` | `active-persistent` | `worker-aepd`, `cron-aepd-weekly` | `worker-aepd`, `cron-aepd-weekly` | yes: `esdata-aepd-weekly.timer` | AEPD documents worker. |
| `bde.py` | `active-persistent` | `worker-bde`, `cron-bde-weekly` | `worker-bde`, `cron-bde-weekly` | yes: `esdata-bde-weekly.timer` | Banco de Espana worker. |
| `bdns.py` | `active-persistent` | `worker-bdns`, `cron-bdns-weekly` | `worker-bdns`, `cron-bdns-weekly` | yes: `esdata-bdns-weekly.timer` | BDNS worker. |
| `boe.py` | `active-persistent` | `worker-boe`, `cron-boe-daily` | `worker-boe`, `cron-boe-daily` | yes: `esdata-boe-daily.timer` | BOE consolidated legislation worker. |
| `boe_modelos_worker.py` | `active-persistent` | `worker-boe-modelos`, `cron-boe-modelos-daily` | `worker-boe-modelos` | yes: `esdata-boe-modelos-daily.timer` | Scheduler service writes as `worker-boe-modelos`; `cron-boe-modelos-daily` is excluded from status as a scheduler alias. |
| `borme.py` | `active-persistent` | `worker-borme`, `cron-borme-weekly` | `worker-borme`, `cron-borme-weekly` | yes: `esdata-borme-weekly.timer` | BORME worker. |
| `cdi.py` | `active-persistent` | `worker-cdi`, `cron-cdi-weekly` | `worker-cdi`, `cron-cdi-weekly` | yes: `esdata-cdi-weekly.timer` | Double-tax treaty worker. |
| `cendoj.py` | `active-persistent` | `worker-cendoj`, `cron-cendoj-weekly` | `worker-cendoj`, `cron-cendoj-weekly` | yes: `esdata-cendoj-weekly.timer` | CENDOJ jurisprudence worker. |
| `cnmv.py` | `active-persistent` | `worker-cnmv`, `cron-cnmv-weekly` | `worker-cnmv`, `cron-cnmv-weekly` | yes: `esdata-cnmv-weekly.timer` | CNMV corpus worker. |
| `dgt.py` | `active-persistent` | `worker-dgt`, `cron-dgt-weekly` | `worker-dgt`, `cron-dgt-weekly` | yes: `esdata-dgt-weekly.timer` | DGT doctrine worker. |
| `eurlex.py` | `active-persistent` | `worker-eurlex`, `cron-eurlex-weekly` | `worker-eurlex`, `cron-eurlex-weekly` | yes: `esdata-eurlex-weekly.timer` | EUR-Lex legislation worker. |
| `sepblac.py` | `active-persistent` | `worker-sepblac`, `cron-sepblac-weekly` | `worker-sepblac`, `cron-sepblac-weekly` | yes: `esdata-sepblac-weekly.timer` | SEPBLAC worker. |
| `teac.py` | `active-persistent` | `worker-teac`, `cron-teac-weekly` | `worker-teac`, `cron-teac-weekly` | yes: `esdata-teac-weekly.timer` | TEAC DYCTEA worker. |

## Active Cron-Only Workers

All rows below have `retry-guard=yes`. Network is `esdata-internal`.

| File | Type | Compose service(s) | sync_log/status worker | Timer installed | Comment |
|---|---|---|---|---|---|
| `aeat_current_designs.py` | `active-cron` | `cron-aeat-current-daily` | `worker-aeat-current-designs` -> status `cron-aeat-current-daily` | yes: `esdata-aeat-current-daily.timer` | A-05 alias: service writes internal worker name, A-11 maps it for status metrics. |
| `boe_diario.py` | `active-cron` | `cron-boe-diario-daily` | `cron-boe-diario-daily` | yes: `esdata-boe-diario-daily.timer` | BOE daily non-consolidated documents. |
| `eurlex_market.py` | `active-cron` | `cron-eurlex-market-monthly` via `worker_eurlex_market.py` wrapper | `worker-eurlex-market` | yes: `esdata-eurlex-market-monthly.timer` | A-05 alias: service writes `worker-eurlex-market`; wrapper file has no DB engine and is outside the 68 count. |
| `eu_sanctions.py` | `active-cron` | `cron-eu-sanctions-weekly` | `cron-eu-sanctions-weekly` | yes: `esdata-eu-sanctions-weekly.timer` | Writes fresh telemetry but upstream currently returns `HTTP 403`; not a stale-worker problem. |
| `giin.py` | `active-cron` | `cron-giin-monthly` | `cron-giin-monthly` | yes: `esdata-giin-monthly.timer` | IRS GIIN monthly sync. |
| `mica.py` | `active-cron` | `cron-mica-weekly` | `cron-mica-weekly` | yes: `esdata-mica-weekly.timer` | ESMA MiCA CASP register worker. |
| `ofac_sdn.py` | `active-cron` | `cron-ofac-sdn-weekly` | `cron-ofac-sdn-weekly` | yes: `esdata-ofac-sdn-weekly.timer` | OFAC SDN sanctions worker. |
| `official_regulatory_references.py` | `active-cron` | `official-regulatory-references` | `official-regulatory-references` | yes: `esdata-official-regulatory-references-weekly.timer` | Official regulatory reference loader; one of the original stale-alert targets. |
| `pgc_boe.py` | `active-cron` | `cron-pgc-boe-monthly` | `cron-pgc-boe-monthly` | yes: `esdata-pgc-boe-monthly.timer` | PGC BOE monthly worker; one of the original stale-alert targets. |
| `psd2_eba.py` | `active-cron` | `cron-psd2-weekly` | `cron-psd2-weekly` | yes: `esdata-psd2-weekly.timer` | PSD2/EBA worker; one of the original stale-alert targets. |
| `regulatory_watch.py` | `active-cron` | `cron-regulatory-daily` | `cron-regulatory-daily` | yes: `esdata-reg-watch-daily.timer` | Multi-source source-revision watcher. |
| `worker_esma_dlt.py` | `active-cron` | `cron-esma-dlt-weekly` | `worker-esma-dlt` | yes: `esdata-esma-dlt-weekly.timer` | A-05 alias: service writes internal worker name. |
| `worker_esma_firds.py` | `active-cron` | `cron-esma-firds-daily` | `worker-esma-firds` | yes: `esdata-esma-firds-daily.timer` | A-05 alias: service writes internal worker name. |
| `worker_esma_mifir_reporting.py` | `active-cron` | `cron-esma-mifir-reporting-weekly` | `worker-esma-mifir-reporting` | yes: `esdata-esma-mifir-reporting-weekly.timer` | A-05 alias: service writes internal worker name. |

## Helper Or Backlog Modules

All rows below have `retry-guard=yes`, but no production Compose service and no systemd timer today. Network is `NA`; timer is `no`.

| File | Type | Compose service(s) | sync_log/status worker | Timer installed | Comment |
|---|---|---|---|---|---|
| `aeat_irnr.py` | `helper/module` | none | none current | no | Manual/backlog IRNR loader; not a scheduled production job. |
| `aifmd_ucits.py` | `helper/module` | none | none current | no | Domain loader for AIFMD/UCITS data; not wired as runtime. |
| `consumer_credit_real.py` | `helper/module` | none | none current | no | Real-data successor path for consumer credit; not scheduled. |
| `corporate_sustainability.py` | `helper/module` | none | none current | no | CSRD/sustainability domain loader; not scheduled. |
| `crd_brrd_emir.py` | `helper/module` | none | none current | no | CRD/BRRD/EMIR domain loader; not scheduled. |
| `csdr.py` | `helper/module` | none | none current | no | CSDR domain loader; not scheduled. |
| `csr.py` | `helper/module` | none | none current | no | CSR/CSRD domain loader; not scheduled. |
| `dac8_real.py` | `helper/module` | none | none current | no | Real-data DAC8 path; not scheduled. |
| `dac_directives.py` | `helper/module` | none | none current | no | DAC directives domain loader; not scheduled. |
| `dgt_doctrina.py` | `helper/module` | none | none current | no | Alternate DGT doctrine queue/module; production service uses `dgt.py`. |
| `document_decomposition.py` | `helper/module` | none | none current | no | Enrichment/decomposition job; manual/backlog, not timer-driven. |
| `dora.py` | `helper/module` | none | none current | no | DORA domain loader; Sprint K data is already seeded/canonical elsewhere. |
| `entity_identity.py` | `helper/module` | none | none current | no | Entity identity enrichment module; not production-scheduled. |
| `fraud.py` | `helper/module` | none | none current | no | Fraud-domain loader; not production-scheduled. |
| `insurance.py` | `helper/module` | none | none current | no | Insurance/Solvency domain loader; not production-scheduled. |
| `jurisprudencia.py` | `helper/module` | none | none current | no | Jurisprudence module; production scheduled source is `cendoj.py`. |
| `legalize_es.py` | `helper/module` | none | none current | no | Markdown/legalize parser path; not a production service. |
| `mar_mifid.py` | `helper/module` | none | none current | no | MAR/MiFID domain loader; EUR-Lex production path is `eurlex.py`/market cron. |
| `mifid_mar_dora.py` | `helper/module` | none | none current | no | Combined EU-market domain loader; not scheduled. |
| `pbc.py` | `helper/module` | none | none current | no | PBC domain loader; not scheduled. |
| `pgc_real.py` | `helper/module` | none | none current | no | Real PGC data path; production monthly source is `pgc_boe.py`. |
| `pgc_xbrl_mapping.py` | `helper/module` | none | none current | no | XBRL mapping enrichment; not scheduled. |
| `priips_ownership.py` | `helper/module` | none | none current | no | PRIIPs/ownership domain loader; not scheduled. |
| `prospectos.py` | `helper/module` | none | none current | no | Prospectus domain loader; has retry guard but no current Compose/systemd service. |
| `rirnr.py` | `helper/module` | none | none current | no | RIRNR BOE regulation loader; not current production worker. |
| `screening_real.py` | `helper/module` | none | none current | no | Real screening path; production scheduled sanctions are OFAC/EU-specific workers. |
| `sfdr.py` | `helper/module` | none | none current | no | SFDR domain loader; not scheduled. |
| `solvency.py` | `helper/module` | none | none current | no | Solvency domain loader; not scheduled. |
| `sustainable_finance.py` | `helper/module` | none | none current | no | Sustainable-finance domain loader; not scheduled. |
| `xbrl.py` | `helper/module` | none | none current | no | XBRL ingestion module; not current production service. |
| `xbrl_taxonomy.py` | `helper/module` | none | none current | no | XBRL taxonomy loader; not scheduled. |

## Dead Or Unused Runtime Paths

All rows below have `retry-guard=yes`, but they are superseded, legacy, or development-only paths. They should not be promoted without a new story that proves official source, idempotency, telemetry, and API/MCP availability semantics.

| File | Type | Compose service(s) | sync_log/status worker | Timer installed | Comment |
|---|---|---|---|---|---|
| `consumer_credit.py` | `dead/unused` | none | none current | no | Legacy/seed consumer-credit path; `consumer_credit_real.py` is the real-data successor. |
| `dac8.py` | `dead/unused` | none | none current | no | Legacy/seed DAC8 path; `dac8_real.py` is the real-data successor. |
| `ley112009_socimi.py` | `dead/unused` | none | none current | no | One-off legacy legal loader; no Compose/systemd runtime. |
| `ley13_2023.py` | `dead/unused` | none | none current | no | One-off legacy legal loader; no Compose/systemd runtime. |
| `ley222014_lecr.py` | `dead/unused` | none | none current | no | One-off legacy legal loader; no Compose/systemd runtime. |
| `modelos.py` | `dead/unused` | none | none current | no | Legacy AEAT model path; canonical production worker is `aeat_models.py`. |
| `pgc.py` | `dead/unused` | none | none current | no | Legacy PGC seed/runtime path; production monthly BOE source is `pgc_boe.py`. |
| `psd2.py` | `dead/unused` | none | none current | no | Legacy PSD2 seed/path; production scheduled worker is `psd2_eba.py`. |
| `screening.py` | `dead/unused` | none | none current | no | Development/fictitious screening path; production sanctions sources are OFAC/EU workers. |

## Name Drift Rules

The inventory separates Compose service names from telemetry names. Current intentional mappings:

| Compose service | Real `sync_log.worker` / status label |
|---|---|
| `cron-aeat-current-daily` | `worker-aeat-current-designs` -> status alias `cron-aeat-current-daily` |
| `cron-boe-modelos-daily` | `worker-boe-modelos`; scheduler service is excluded from status |
| `cron-esma-dlt-weekly` | `worker-esma-dlt` |
| `cron-esma-firds-daily` | `worker-esma-firds` |
| `cron-esma-mifir-reporting-weekly` | `worker-esma-mifir-reporting` |
| `cron-eurlex-market-monthly` | `worker-eurlex-market` |

Alerting must continue to use `worker_stale_status`, not hardcoded Compose service names.

## Verification Commands

Local:

```powershell
python -m pytest scripts/tests/test_worker_db_retry_coverage.py apps/api/tests/test_worker_cadence.py -q
```

VPS evidence used:

```bash
systemctl list-timers --all --no-pager 'esdata*'
docker compose --env-file /etc/esdata/esdata.env \
  -f infra/deploy/docker-compose.prod.yml \
  exec -T postgres psql -U esdata -d esdata \
  -c "SELECT worker, COUNT(*), MAX(id), MAX(COALESCE(finished_at, started_at)) FROM sync_log GROUP BY worker ORDER BY worker;"
```
