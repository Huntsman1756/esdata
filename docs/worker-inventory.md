# Worker Inventory

Classification of all Python files in `apps/workers/`.

Evidence base:

- `apps/workers/*.py`: 82 files, excluding `__init__.py`.
- `infra/deploy/docker-compose.prod.yml`: 23 worker files wired through Compose services.
- `infra/deploy/systemd/*.timer`: profiled cron services are timer-driven through `esdata-job@<service>.service`.

## TYPE-A: Utility/Helper

These files are not standalone production jobs and do not need Compose services.

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

## TYPE-B: Domain Module

These modules are imported by other workers and are not standalone services.

| File | Imported By | Purpose |
|------|-------------|---------|
| `boe_modelos.py` | `boe_modelos_worker.py` | BOE XML parser for HAC orders |
| `boe_pdf_parser.py` | `boe_modelos_worker.py` | PDF download and parsing |
| `modelos_support.py` | `modelos.py`, `boe_modelos_worker.py` | Casilla/instruction upsert helpers |
| `pgc_dataset.py` | `pgc.py` | PGC seed data constants |

## TYPE-C: Standalone Workers

These files contain standalone worker code. A production-ready TYPE-C worker must have
official-source boundaries, run-once verification, retry/telemetry, Compose wiring,
systemd schedule where applicable, and MCP/API availability semantics.

### With Docker Service (23 files)

| File | Service(s) | Purpose |
|------|------------|---------|
| `aeat_current_designs.py` | `cron-aeat-current-daily` | AEAT current 1XX/2XX record designs and taxpayer calendar |
| `aeat_models.py` | `worker-aeat`, `worker-modelos`, `cron-modelos-daily` | AEAT portal model discovery |
| `aepd.py` | `worker-aepd`, `cron-aepd-weekly` | AEPD registry |
| `bde.py` | `worker-bde`, `cron-bde-weekly` | Banco de Espana registry |
| `bdns.py` | `worker-bdns`, `cron-bdns-weekly` | BDNS registry |
| `boe.py` | `worker-boe`, `cron-boe-daily` | BOE legislation sync |
| `boe_diario.py` | `cron-boe-diario-daily` | BOE diario non-consolidated XML/PDF documents |
| `boe_modelos_worker.py` | `worker-boe-modelos`, `cron-boe-modelos-daily` | BOE-to-models orchestrator |
| `borme.py` | `worker-borme`, `cron-borme-weekly` | BORME company extraction |
| `cdi.py` | `worker-cdi`, `cron-cdi-weekly` | Convenios de doble imposicion |
| `cendoj.py` | `worker-cendoj`, `cron-cendoj-weekly` | CENDOJ jurisprudence |
| `cnmv.py` | `worker-cnmv`, `cron-cnmv-weekly` | CNMV circulars |
| `dgt.py` | `worker-dgt`, `cron-dgt-weekly` | DGT doctrine scraping |
| `eurlex.py` | `worker-eurlex`, `cron-eurlex-weekly` | EUR-Lex EU legislation |
| `giin.py` | `cron-giin-monthly` | IRS FATCA FFI/GIIN official monthly CSV ZIP |
| `mica.py` | `cron-mica-weekly` | ESMA Interim MiCA Register CASP official CSV |
| `ofac_sdn.py` | `cron-ofac-sdn-weekly` | OFAC SDN official XML sanctions list |
| `official_regulatory_references.py` | `official-regulatory-references` | Compact official regulatory reference loader |
| `pgc_boe.py` | `cron-pgc-boe-monthly` | PGC BOE official-source ingestion |
| `psd2_eba.py` | `cron-psd2-weekly` | PSD2 EBA/BdE registry sync |
| `regulatory_watch.py` | `cron-regulatory-daily` | Multi-source regulatory monitoring |
| `sepblac.py` | `worker-sepblac`, `cron-sepblac-weekly` | SEPBLAC registry |
| `teac.py` | `worker-teac`, `cron-teac-weekly` | TEAC resolution ingestion |

### Existing Worker Modules Not Deployed In Production (37 files)

These files contain worker-style code, but they are not production jobs in the
current Compose/systemd wiring. They must stay documented as `not deployed` or
domain `partial/configured_but_unavailable` until each one has official-source
ingestion, run-once verification, cron/systemd wiring, rollback/retry evidence
and MCP/API availability semantics.

| File | Purpose | Priority |
|------|---------|----------|
| `aeat_irnr.py` | IRNR model and instruction scraping from AEAT | High |
| `aifmd_ucits.py` | AIFMD/UCITS funds from CNMV | Medium |
| `consumer_credit.py` | Consumer Credit Directive 2008/48/EC seed/legacy worker | Medium |
| `consumer_credit_real.py` | Consumer Credit real EUR-Lex data | Medium |
| `corporate_sustainability.py` | CSRD sustainability reports | Medium |
| `crd_brrd_emir.py` | CRD V/BRRD/EMIR regulations | Medium |
| `csdr.py` | CSDR regulation | Medium |
| `csr.py` | CSRD worker with EUR-Lex and company seed data | Medium |
| `dac8.py` | DAC8 reporting seed/legacy worker | High |
| `dac8_real.py` | DAC8 real data | High |
| `dac_directives.py` | DAC directives ingestion | High |
| `dgt_doctrina.py` | DGT doctrine queue | Medium |
| `document_decomposition.py` | Document decomposition and lineage enrichment job | Medium |
| `dora.py` | DORA regulation | Medium |
| `entity_identity.py` | Entity identity resolution | Low |
| `fraud.py` | Fraud risk assessment | Medium |
| `insurance.py` | Insurance regulation | Medium |
| `jurisprudencia.py` | Jurisprudence ingestion | Medium |
| `legalize_es.py` | Legalize ES markdown parser | Low |
| `mar_mifid.py` | MAR/MiFID data | Medium |
| `micro_obligations.py` | Micro-obligations seed loader | Low |
| `mifid_mar_dora.py` | MiFID/MAR/DORA combined | Medium |
| `modelos.py` | Legacy AEAT models sync path | High |
| `pbc.py` | PBC regulation | Medium |
| `pgc.py` | PGC account mapping seed path | Medium |
| `pgc_real.py` | Real PGC data path | Medium |
| `pgc_xbrl_mapping.py` | PGC-XBRL mapping | Low |
| `priips_ownership.py` | PRIIPs ownership | Medium |
| `prospectos.py` | Prospectus ingestion | Medium |
| `psd2.py` | PSD2 regulation seed/legacy worker | Medium |
| `rirnr.py` | RIRNR BOE consolidated regulation ingestion | High |
| `screening_real.py` | Multi-list screening worker with unofficial/fallback sources | Medium |
| `sfdr.py` | SFDR data | Medium |
| `solvency.py` | Solvency data | Medium |
| `sustainable_finance.py` | SFDR/sustainable finance worker with seed-backed product data | Medium |
| `xbrl.py` | XBRL from CNMV | Medium |
| `xbrl_taxonomy.py` | XBRL taxonomy seed loader | Low |

## TYPE-D: Deprecated Or Development-Only Loaders

These are simple one-shot scripts, seed loaders or superseded legal loaders. They are intentionally not production jobs.

| File | Purpose |
|------|---------|
| `ley62018.py` | Ley 62/2018 legacy loader |
| `ley272014.py` | Ley 27/2014 legacy loader |
| `ley222010.py` | Ley 22/2010 legacy loader |
| `ley12010.py` | Ley 12/2010 legacy loader |
| `ley112021.py` | Ley 11/2021 legacy loader |
| `ley222014_lecr.py` | Ley 22/2014 LEGR legacy loader |
| `ley13_2023.py` | Ley 13/2023 legacy loader |
| `ley112009_socimi.py` | Ley 11/2009 SOCIMI legacy loader |
| `rd2172008.py` | RD 217/2008 legacy loader |
| `nrv9.py` | NRV9 legacy loader |
| `trlmv.py` | TRLMV legacy loader |
| `screening.py` | Development-only fictitious screening data |

## Ralph Remediation Backlog

Undeployed TYPE-C modules are not counted as production workers. They are grouped
in `prd.json.workerRemediationStories` as target/backlog stories and should only
move into production after a dedicated Ralph iteration proves official sources,
idempotent writes, sync_log telemetry, retry/dead-letter behavior, systemd/Compose
wiring, and safe MCP/API availability semantics.
