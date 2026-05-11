# Worker Inventory

Classification of all Python files in `apps/workers/`.

## TYPE-A: Utility/Helper (not standalone, no service needed)

| File | Purpose |
|------|---------|
| `runtime.py` | Core runtime: logging, DB connection, heartbeat, failure handling |
| `dead_letter.py` | Dead-letter queue for failed sync entities |
| `change_detection.py` | Content change detection, revision tracking |
| `embeddings.py` | Embedding generation/management |
| `entrypoint.py` | Docker worker entrypoint; executes `WORKER_CMD` |
| `vocabulary.py` | Vocabulary definitions and lookup |
| `vocabulary_validation.py` | Document payload sanitization |
| `scripts/hermes_monitor.py` | Canonical read-only service monitor copied into the worker image as `/app/hermes_monitor.py` for the `hermes` service |

## TYPE-B: Domain Module (imported by others, no service needed)

| File | Imported By | Purpose |
|------|-------------|---------|
| `boe_modelos.py` | `boe_modelos_worker.py` | BOE XML parser for HAC orders |
| `boe_pdf_parser.py` | `boe_modelos_worker.py` | PDF download and parsing |
| `document_decomposition.py` | manual/API enrichment flows | Document decomposition helper |
| `modelos_support.py` | `modelos.py`, `boe_modelos_worker.py` | Casilla/instruction upsert helpers |
| `official_regulatory_references.py` | Ralph/local reference sync | Official compact regulatory reference loader |
| `pgc_dataset.py` | `pgc.py` | PGC seed data constants |

## TYPE-C: Standalone Workers (should have docker-compose service)

### With Docker Service (19 files)

| File | Service(s) | Purpose |
|------|------------|---------|
| `boe.py` | `worker-boe`, `cron-boe-daily` | BOE legislacion sync |
| `aeat_models.py` | `worker-modelos`, `cron-modelos-daily` | AEAT portal model discovery |
| `aeat_current_designs.py` | `cron-aeat-current-daily` | AEAT current 1XX/2XX record designs and 2026 taxpayer calendar |
| `boe_modelos_worker.py` | `worker-boe-modelos`, `cron-boe-modelos-daily` | BOE->models orchestrator |
| `dgt.py` | `worker-dgt`, `cron-dgt-weekly` | DGT doctrine scraping |
| `teac.py` | `worker-teac`, `cron-teac-weekly` | TEAC resolution ingestion |
| `bdns.py` | `worker-bdns`, `cron-bdns-weekly` | BDNS registry |
| `borme.py` | `worker-borme`, `cron-borme-weekly` | BORME company extraction |
| `cnmv.py` | `worker-cnmv`, `cron-cnmv-weekly` | CNMV circulars |
| `sepblac.py` | `worker-sepblac`, `cron-sepblac-weekly` | SEPBLAC registry |
| `cendoj.py` | `worker-cendoj`, `cron-cendoj-weekly` | CENDOJ jurisprudence |
| `eurlex.py` | `worker-eurlex`, `cron-eurlex-weekly` | EUR-Lex EU legislation |
| `bde.py` | `worker-bde`, `cron-bde-weekly` | BDE registry |
| `cdi.py` | `worker-cdi` | CDI (convenios doble imposicion) |
| `aepd.py` | `worker-aepd`, `cron-aepd-weekly` | AEPD registry |
| `regulatory_watch.py` | `cron-regulatory-daily` | Multi-source regulatory monitoring |
| `giin.py` | `cron-giin-monthly` | IRS FATCA FFI/GIIN official monthly CSV ZIP |
| `ofac_sdn.py` | `cron-ofac-sdn-weekly` | OFAC SDN official XML sanctions list |
| `mica.py` | `cron-mica-weekly` | ESMA Interim MiCA Register CASP official CSV |

### Existing Worker Modules Not Deployed In Production (38 files)

These files contain worker-style code, but they are not production jobs in the
current Compose/systemd wiring. They must stay documented as `not deployed` or
domain `partial/configured_but_unavailable` until each one has official-source
ingestion, run-once verification, cron/systemd wiring, rollback/retry evidence
and MCP/API availability semantics.

| File | Purpose | Priority |
|------|---------|----------|
| `aeat_irnr.py` | IRNR model from AEAT | High |
| `aifmd_ucits.py` | AIFMD/UCITS funds from CNMV | Medium |
| `consumer_credit.py` | Consumer Credit Directive 2008/48/EC | Medium |
| `consumer_credit_real.py` | Consumer Credit real EUR-Lex data | Medium |
| `corporate_sustainability.py` | CSRD sustainability reports | Medium |
| `crd_brrd_emir.py` | CRD V/BRRD/EMIR regulations | Medium |
| `csr.py` | CSRD worker with EUR-Lex + company seed data | Medium |
| `csdr.py` | CSDR regulation | Medium |
| `dac8.py` | DAC8 directive | High |
| `dac8_real.py` | DAC8 real data | High |
| `dac_directives.py` | DAC directives ingestion | High |
| `dgt_doctrina.py` | DGT doctrine queue | Medium |
| `dora.py` | DORA regulation | Medium |
| `entity_identity.py` | Entity identity resolution | Low |
| `fraud.py` | Fraud risk assessment | Medium |
| `insurance.py` | Insurance regulation | Medium |
| `jurisprudencia.py` | Jurisprudence ingestion | Medium |
| `legalize_es.py` | Legalize ES markdown parser | Low |
| `mar_mifid.py` | MAR/MiFID data | Medium |
| `micro_obligations.py` | Micro-obligations seed loader | Low |
| `mifid_mar_dora.py` | MiFID/MAR/DORA combined | Medium |
| `modelos.py` | AEAT models sync | High |
| `pgc.py` | PGC account mapping | Medium |
| `pgc_boe.py` | PGC BOE official source ingestion | Medium |
| `pgc_real.py` | Real PGC data | Medium |
| `pgc_xbrl_mapping.py` | PGC-XBRL mapping | Low |
| `priips_ownership.py` | PRIIPs ownership | Medium |
| `prospectos.py` | Prospectus ingestion | Medium |
| `psd2.py` | PSD2 regulation | Medium |
| `psd2_eba.py` | PSD2 EBA/BdE registry sync | Medium |
| `pbc.py` | PBC regulation | Medium |
| `rirnr.py` | RIRNR BOE consolidated regulation ingestion | High |
| `screening_real.py` | Multi-list screening worker with unofficial/fallback sources | Medium |
| `sfdr.py` | SFDR data | Medium |
| `solvency.py` | Solvency data | Medium |
| `sustainable_finance.py` | SFDR/sustainable finance worker with seed-backed product data | Medium |
| `xbrl.py` | XBRL from CNMV | Medium |
| `xbrl_taxonomy.py` | XBRL taxonomy | Low |

## TYPE-D: Simple Scripts / Data Loaders (deprecated/dead code)

One-shot data loaders with `--run-once` but no `run_sync()`, no heartbeat, no DLQ.

| File | Purpose |
|------|---------|
| `ley62018.py` | Ley 62/2018 |
| `ley272014.py` | Ley 27/2014 |
| `ley222010.py` | Ley 22/2010 |
| `ley12010.py` | Ley 12/2010 |
| `ley112021.py` | Ley 11/2021 |
| `ley222014_lecr.py` | Ley 22/2014 LEGR |
| `ley13_2023.py` | Ley 13/2023 |
| `ley112009_socimi.py` | Ley 11/2009 SOCIMI |
| `rd2172008.py` | RD 217/2008 |
| `nrv9.py` | NRV9 |
| `trlmv.py` | TRLMV |
| `screening.py` | Development-only fictitious screening data |
