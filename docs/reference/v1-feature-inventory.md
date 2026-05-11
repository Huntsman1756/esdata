# ESData v1.0 Feature Inventory

Status: `ACTIVE_DRAFT`

Last audit: 2026-05-11 Europe/Madrid

This document is the v1.0 feature truth table. It is intentionally conservative:
features are only marked implemented when code, wiring, and evidence agree.
If a feature exists in files but is not mounted, not deployed, or not validated,
it is marked as partial, hidden/internal, unmounted, or documented-only.

## Evidence Baseline

- Runtime FastAPI OpenAPI import: 379 paths, 410 operations.
- Static router scan: 443 endpoints across 84 router modules.
- Subagent API/MCP scan: 409 mounted router endpoints, 34 router endpoints defined but unmounted, 417 total runtime app routes including FastAPI/docs/internal routes.
- HTTP MCP catalog: 36 operation IDs.
- Stdio MCP advertised catalog: 9 tools.
- Stdio MCP dispatch implementation: 51 callable branches, including 42 hidden/unadvertised branches.
- GPT Actions contract: 13 paths with `ApiKeyAuth` via `X-API-Key`.
- Ralph table registry: 163 tables total, 73 populated, 53 `workflow_empty`, 3 `allowed_empty`, 34 `configured_but_unavailable`, 0 blockers, 0 unclassified.
- Compose production services: 47 services.
- Systemd timers: 21 timers.
- Web app: 7 pages and 3 server proxy routes.

Primary evidence files:

- `apps/api/main.py`
- `apps/api/mcp_catalog.py`
- `apps/api/mcp_stdio.py`
- `docs/openapi-gpt.json`
- `infra/deploy/docker-compose.prod.yml`
- `infra/deploy/systemd/`
- `scripts/ralph/table-remediation-registry.json`
- `scripts/maintenance/mcp_validation_suite.py`
- `docs/master-execution-roadmap.md`

## Status Vocabulary

- `implemented`: mounted or deployed, has schema/data path, and has evidence.
- `partial`: real implementation exists but coverage, freshness, upstream reliability, or deployment is incomplete.
- `hidden/internal`: implemented for operators or internal agents, not a public product surface.
- `unmounted`: endpoint code exists but is not included in the running FastAPI app.
- `not deployed`: worker/script exists but is not wired in production Compose/systemd.
- `documented-only`: documentation claims a feature that runtime/deploy evidence does not support.
- `allowed_empty`: table can be empty by design.
- `workflow_empty`: table is populated only by runtime/user workflow.
- `configured_but_unavailable`: table exists for a real domain but no configured official ingestion currently populates it.
- `broken/unverified`: behavior could not be proved or evidence indicates a fault.

## v1.0 Verdict

`CONDITIONAL V1.0 CANDIDATE`

The core MCP/API product is real: official-source retrieval, AEAT models, BOE legislation,
doctrine, domain availability, freshness, query audit, deployed workers, validation gates,
Docker deployment, and GPT Actions are all present.

The whole repository is not a clean v1.0 claim yet. The main blockers to an honest v1.0
feature list are:

1. Several router modules define endpoints that are not mounted at runtime.
2. Stdio MCP has hidden callable branches that are not advertised in `tools/list`.
3. Several worker modules exist but are not wired in production Compose/systemd.
4. `docs/database.md` is stale and conflicts with the active table registry and `source_revision` policy.
5. Some roadmap sections overclaim cron/worker coverage for modules not present in production wiring.
6. DGT, EUR-Lex, PSD2/EBA, BOE modelos/casillas and some broad regulatory domains remain partial by evidence.

## Public And Integration Surfaces

### REST API

Status: `implemented` for mounted runtime operations, `unmounted` for router-only endpoints.

Runtime evidence:

- 379 OpenAPI paths.
- 410 OpenAPI operations.
- 84 router modules with static endpoint definitions.
- 34 static router endpoints are defined but unmounted.

Major mounted API domains:

| Domain | Runtime operation count | Status | Notes |
|---|---:|---|---|
| Search and legislation | 9 | implemented | `/v1/buscar`, `/v1/legislacion/*`, hybrid search, article history. |
| Fiscal aggregate query | 1 | implemented/partial | `/v1/consulta` with confidence, citations, review flags and fail-closed behavior. |
| AEAT models | 15 | implemented/partial | Model list/detail/campaigns/casillas/claves/instructions/normativa/artifacts/fuentes and `por-supuesto`. |
| Doctrine and DGT doctrine | 5 | implemented/partial | General doctrine plus DGT rendimiento endpoints. DGT upstream is source-fragile. |
| CNMV/BDE/AEPD/CENDOJ/EUR-Lex documents | 13 | implemented/partial | Document list/detail, CNMV versions/relations/obligations. EUR-Lex depth partial. |
| Obligations, compliance, playbooks and changes | 16 | implemented/partial | Operational compliance and regulatory change workflows. |
| Domain availability and source freshness | 5 | implemented | Explicit `workflow_empty`, `allowed_empty`, `configured_but_unavailable` semantics. |
| Data governance and audit | 8 | hidden/internal implemented | Query audit, AI audit, lineage, quality, catalog, observability. |
| Banking | 7 | implemented | IBAN, ISO20022, N43 and SEPA helpers. |
| Screening | 3 | implemented/partial | Screening checks, entries and matches. |
| PGC/accounting | 6 | implemented/partial | PGC accounts, valuation rules and links. |
| XBRL | 5 | partial | Taxonomy present; filings/facts configured unavailable. |
| MIFID | 16 | partial | Operational tables/endpoints exist; many workflow-driven. |
| MiCA | 14 | partial | CASP implemented; asset/wallet/token domains unavailable/workflow-empty. |
| PBC/AML | 8 | implemented/partial | PBC entities/internal controls/subjects. |
| PSD2/SEPA | 12 | partial | PSD2 fallback via BdE verified seed; SEPA rule data present. |
| DORA | 10 | partial | Framework data present; incident/provider/register workflows are mostly workflow-empty. |
| SFDR/CSRD | 18 | partial | Selected reference tables populated; fund/entity/report workflows partial. |
| AIFMD/UCITS | 10 | partial | Schemas and endpoints exist; fund/report tables configured unavailable. |
| CRD/BRRD/EMIR | 20 | partial | Schemas/endpoints exist; many configured unavailable. |
| Editorial, criteria, risk/control | 26 | hidden/internal partial | Internal curation, playbooks, risk-control matrix, micro-obligations. |
| AI governance | 19 | hidden/internal partial | Model registry/config/history, audit log, human review, safety/risk where mounted. |

### Unmounted API Endpoints

Status: `unmounted` or `documented-only` if manuals claim them as available.

Router modules with endpoints that exist in code but are not included in `apps/api/main.py`:

- `ai_risk`: 3 endpoints.
- `ai_safety`: 4 endpoints.
- `bdns`: 2 endpoints.
- `borme`: 2 endpoints.
- `calendario_fiscal`: 3 endpoints.
- `chunks`: 1 endpoint.
- `connectivity`: 4 endpoints.
- `fairness`: 1 endpoint.
- `gdpr`: 7 endpoints.
- `irs`: 2 endpoints.
- `sepblac`: 2 endpoints.
- `xai`: 3 endpoints.

Documentation state:

- Active manual pages now mark `/v1/bdns`, `/v1/borme`, `/v1/sepblac`,
  `/v1/chunks`, `/v1/connectivity`, AI risk/fairness, GDPR and XAI as
  unmounted/backlog rather than available v1.0 runtime endpoints.
- Human review is documented under the mounted `/v1/ai/human-review/...`
  prefix.

### HTTP MCP

Status: `implemented`, curated surface.

HTTP MCP exposes 36 operation IDs from `HTTP_MCP_OPERATIONS`:

- Legislation: `list_legislacion`, `get_norma`, `list_articulos`, `get_articulo`, `get_articulo_historial`, `buscar`, `buscar_legislacion`.
- Materias: `list_materias`, `get_materia`.
- Doctrine: `buscar_doctrina`, `get_doctrina`.
- AEAT models: `list_modelos`, `list_modelos_campanas_operativas`, `get_modelo`, `get_modelo_articulos`, `get_modelo_casillas`, `get_modelo_claves`, `get_modelo_instrucciones`, `get_modelo_normativa`, `get_modelo_artefactos`, `get_modelo_campana_operativa`, `get_modelo_resumen_operativo`, `get_modelo_fuentes_oficiales`, `list_modelos_por_supuesto`.
- Domain availability: `list_domain_availability`, `get_domain_availability`.
- DTA/retentions: `listar_convenios_dta_internacional`, `detalle_convenio_dta_internacional`, `listar_reglas_retencion_internacional`, `calcular_retencion`.
- Bridged operational tools: `consulta_fiscal`, `listar_obligaciones_operativas`, `listar_deadlines`, `listar_obligaciones_aplicables`, `get_obligacion`, `listar_workflow_compliance`.

Important limitation:

- `scripts/maintenance/mcp_validation_suite.py` now validates both REST backing
  contracts and the real `/mcp` transport handshake + `tools/list` for the
  required v1.0 MCP tools.

### Stdio MCP

Advertised status: `implemented`.

Advertised tools:

- `consulta_fiscal`
- `listar_obligaciones_operativas`
- `listar_deadlines`
- `listar_obligaciones_aplicables`
- `get_obligacion_completa`
- `agente_consulta`
- `list_modelos_por_supuesto`
- `agente_monitoreo_status`
- `agente_compliance_resumen`

Hidden status: rejected fail-closed.

`mcp_stdio.py` still contains legacy dispatch branches for additional SFDR,
CSRD, AIFMD/UCITS, CRD/BRRD/EMIR and DTA/retention operations, but dispatch now
rejects any tool not present in `get_stdio_tool_definitions()` with JSON-RPC
`-32601`. Those legacy branches are not public v1.0 MCP tools until catalog,
tests and documentation are aligned.

### GPT Actions

Status: `implemented`, curated surface.

The active GPT Actions contract is `docs/openapi-gpt.json` and the served URL
`/gpt-actions/modelos/openapi.json`.

It exposes 13 paths:

- `/status`
- `/v1/consulta`
- `/v1/domain-availability`
- `/v1/domain-availability/{table}`
- `/v1/sources/freshness`
- `/v1/legislacion/buscar`
- `/v1/legislacion/{codigo}`
- `/v1/legislacion/{codigo}/articulos/{numero}`
- `/v1/doctrina/buscar`
- `/v1/doctrina/{referencia}`
- `/v1/modelos`
- `/v1/modelos/{codigo}`
- `/v1/modelos/por-supuesto`

Auth: `ApiKeyAuth`, header `X-API-Key`.

Older Action specs:

- `docs/openapi-gpt-clipboard.json`: stale/minimal, 7 paths and no security scheme.
- `docs/openapi-gpt-minimal-modelos.json`: minimal model-only spec, 2 paths.

### Web UI

Status: `implemented` as internal/minimal UI.

Pages:

- `/`
- `/buscar`
- `/articulo/{norma}/{numero}`
- `/doctrina/{referencia...}`
- `/modelo/{codigo}`
- `/admin/cambios`
- `/admin/workflow`

Server proxy routes:

- `GET /api/consulta`
- `GET /api/cambios`
- `GET /api/workflow`

Boundary: web uses backend API proxy helpers; it is not the canonical compliance
source. Backend/API/MCP remain the source of truth.

## Data Feature Inventory

### Table Registry Summary

| Classification | Count | Release meaning |
|---|---:|---|
| `populated` | 73 | Has data in the Ralph registry evidence. |
| `workflow_empty` | 53 | Empty by runtime workflow until user/system actions produce rows. |
| `allowed_empty` | 3 | Empty by design, not a product failure. |
| `configured_but_unavailable` | 34 | Schema exists but no configured official ingestion currently populates it. |
| `blocker` | 0 | No table blockers in registry. |
| `unclassified` | 0 | No unclassified tables in registry. |

### Data Domains

| Domain | Status | Key tables |
|---|---|---|
| BOE consolidated legislation | implemented | `norma`, `articulo`, `version_articulo`, `materia`, `articulo_materia`, `documento_articulo`, `documento_fragmento`. |
| AEAT models/campaigns/casillas | implemented/partial | `aeat_modelo`, `modelo_campana`, `modelo_campana_operativa`, `modelo_casilla`, `modelo_clave`, `modelo_instruccion`, `modelo_normativa`, `modelo_formato`, `modelo_recurso`, `modelo_articulo`, `modelo_fiscal_calendar`. |
| Official doctrine/circulars/jurisprudence | implemented/partial | `documento_interpretativo`, `documento_seccion`, `documento_fragmento`, `documento_version`, `documento_cnmv_version`, `documento_empresa`, `documento_articulo`, `empresa`. |
| DGT queue | implemented | `dgt_queue`, `source_revision`, `documento_interpretativo`. |
| Freshness/change detection | partial/internal | `source_revision`, `source_freshness_snapshot`, `data_freshness_alerts`. |
| Operational sync/audit trail | hidden/internal implemented | `sync_log`, `sync_dead_letter`, `query_audit_log`, `data_lineage`. |
| PGC/accounting | implemented/partial | `pgc_marco`, `pgc_cuenta`, `pgc_norma_valoracion`, `pgc_estado_financiero`, `pgc_cuenta_fiscal_ref`, `pgc_cuenta_modelo_aeat_ref`, `pgc_xbrl_mapping`. |
| Screening/sanctions | implemented/partial | `screening_lists`, `screening_entries`, `screening_matches`, `giin_registry`. |
| MiCA/crypto | partial | `casp`, `crypto_asset`, `crypto_transaction`, `tokenized_asset`, `wallet_custodian`. |
| IRS/IRNR/CDI/international tax | implemented/partial | `irs_*`, `irnr_*`, `giin_registry`, `obligacion_internacional`, `dac_*`. |
| EU financial regulation | partial | DORA, MiFID/MAR, PRIIPs/LIVMC, SFDR, CSRD, AIFMD/UCITS, CRD/BRRD/EMIR, PSD2/SEPA, consumer credit, IDD/Solvency tables. |
| Ownership/UBO/entity identity | partial | `ownership_share`, `ownership_relation`, `ubo_record`, `beneficial_owner_record`, `entity_identifiers`, `entity_aliases`, `empresa`. |
| Editorial/internal criteria/workflows | hidden/internal partial | `nota_editorial_interna`, `posicion_interpretativa`, `linea_criterio`, `workflow_cases`, `playbook_operativo`, `playbook_step`. |
| Risk/control/micro-obligations | hidden/internal partial | `riesgo_regulatorio`, `control_interno`, `riesgo_control_link`, `prueba_control`, `micro_obligacion`, `obligacion_micro_obligacion`. |
| XBRL/ESEF | partial | `xbrl_taxonomy`, `xbrl_company`, `xbrl_filing`, `xbrl_fact`, `pgc_xbrl_mapping`. |
| AI/evaluation | hidden/internal | `ai_audit_log`, `ai_config_version`, `ai_model_registry`, `eval_run`, `eval_query`, `human_review`, `embedding_version`. |

Schema ownership status:

- `source_freshness_snapshot` and `data_freshness_alerts` are referenced by
  later governance/RLS code and are now explicitly owned by Alembic revision
  `20260511_0068_freshness_tables_schema.py`. Runtime/init compatibility code
  may still tolerate pre-existing deployments.

Documentation warning:

- `docs/database.md` has been updated with the v1.0 registry summary and the
  rule that `source_revision` is canonical for regulatory revisions.

## Deployed Worker And Job Inventory

### Implemented Or Partial Deployed Workers

| Worker/job | Trigger | Status | Notes |
|---|---|---|---|
| `worker-boe` / `cron-boe-daily` | continuous + daily | implemented | BOE consolidated legislation into `norma`, `articulo`, `version_articulo`. |
| `worker-boe-modelos` / `cron-boe-modelos-daily` | continuous + daily | partial | BOE modelos/casillas; some BOE ID mappings missing by artifact. |
| `worker-dgt` / `cron-dgt-weekly` | continuous + weekly | partial | Petete/DGT is source-fragile; transient 502/503/504/session failures now log `partial` instead of poisoning DLQ as unrecoverable errors. |
| `worker-teac` / `cron-teac-weekly` | continuous + weekly | implemented | TEAC doctrine. |
| `worker-modelos` / `cron-modelos-daily` | continuous + daily | partial | AEAT models; official fetch failures degrade to partial. |
| `cron-aeat-current-daily` | daily | implemented | AEAT current designs/calendar; artifact: 74 design links, 2527 fields, 248 calendar entries. |
| `worker-bdns` / `cron-bdns-weekly` | continuous + weekly | implemented | BDNS documents. |
| `worker-borme` / `cron-borme-weekly` | continuous + weekly | implemented | BORME documents/companies. |
| `worker-cnmv` / `cron-cnmv-weekly` | continuous + weekly | implemented/partial | CNMV circulars and related links; broad completeness partial. |
| `worker-sepblac` / `cron-sepblac-weekly` | continuous + weekly | implemented | SEPBLAC documents. |
| `worker-cendoj` / `cron-cendoj-weekly` | continuous + weekly | implemented/partial | CENDOJ source-sensitive ingestion. |
| `worker-eurlex` / `cron-eurlex-weekly` | continuous + weekly | partial | EUR-Lex/SPARQL; deep article fetch disabled by default and residual CELEX skips exist. |
| `worker-bde` / `cron-bde-weekly` | continuous + weekly | implemented | Banco de Espana documents. |
| `worker-cdi` / `cron-cdi-weekly` | continuous + weekly | implemented | CDI/DTA conventions into IRS DTA convention tables. |
| `worker-aepd` / `cron-aepd-weekly` | continuous + weekly | implemented | AEPD documents. |
| `cron-regulatory-daily` | daily | implemented | Watches BOE, AEAT, EUR-Lex, AEPD, BDE, DGT into `source_revision`. |
| `cron-psd2-weekly` | weekly | partial | EBA primary unavailable in artifact; uses BdE-verified fallback. |
| `cron-giin-monthly` | monthly | implemented | IRS FATCA GIIN. |
| `cron-ofac-sdn-weekly` | weekly | implemented/partial | OFAC SDN only, official XML source. |
| `cron-mica-weekly` | weekly | implemented/partial | ESMA CASP; crypto/token/wallet domains remain unavailable/workflow-empty. |

### Worker Modules Not Wired In Production Compose/Systemd

Status: `not deployed` unless invoked manually by seeds/tests.

Examples include:

- `aeat_irnr.py`
- `aifmd_ucits.py`
- `consumer_credit.py`
- `consumer_credit_real.py`
- `corporate_sustainability.py`
- `crd_brrd_emir.py`
- `csdr.py`
- `dac8.py`
- `dac8_real.py`
- `dac_directives.py`
- `dgt_doctrina.py`
- `dora.py`
- `entity_identity.py`
- `fraud.py`
- `insurance.py`
- `jurisprudencia.py`
- `legalize_es.py`
- `ley*.py`
- `mar_mifid.py`
- `mifid_mar_dora.py`
- `official_regulatory_references.py`
- `pbc.py`
- `pgc*.py`
- `priips_ownership.py`
- `prospectos.py`
- `rirnr.py`
- `screening.py`
- `screening_real.py`
- `sfdr.py`
- `solvency.py`
- `sustainable_finance.py`
- `trlmv.py`
- `xbrl.py`
- `xbrl_taxonomy.py`

Documentation drift:

- Older roadmap sections claim all these workers are integrated into Compose
  cron profiles. Current production Compose/systemd evidence does not support
  that claim.

## Operations, Security And Observability

Implemented:

- Docker Compose deployment for API, web, PostgreSQL/pgvector, Caddy, workers, cron services, Hermes, backup, ops, Prometheus, Alertmanager, Grafana and node exporter.
- Caddy binds 80/443; API and web bind to localhost by default behind Caddy.
- API and web containers are read-only with `/tmp` tmpfs and `no-new-privileges`.
- Cron containers inherit read-only hardening and are run via flocked systemd services.
- REST API uses `ESDATA_API_KEY`; MCP uses `MCP_API_KEY`.
- Rate limiting exists for `/health`, `/v1`, `/mcp`, with Redis optional and in-memory fallback.
- Query audit log exists and is append-only by migration.
- Hourly MCP validation timer exists.
- Prometheus/Alertmanager/Grafana are configured under production profile.
- Alertmanager Telegram can be enabled via `TELEGRAM_CHAT_ID` plus token secret; otherwise it starts in noop mode.

Partial/needs cleanup:

- Hermes has one canonical implementation: `scripts/hermes_monitor.py`.
  `apps/workers/Dockerfile.worker` copies it into `/app/hermes_monitor.py` so
  Docker Compose and host/systemd use the same read-only monitor behavior.
- Alertmanager config can validate while Telegram delivery still needs an actual
  manual alert proof.
- `scripts/maintenance/show_dead_letter_queue.py` now uses PostgreSQL boolean
  filters (`resolved IS FALSE/TRUE`) and has a SQLite regression test. It still
  needs production execution as part of deploy verification.
- Public `/metrics` is intended to be blocked externally by Caddy but remains
  an internal API route for Prometheus scraping.

## v1.0 Blockers And Cleanup List

Critical for honest v1.0 claims:

1. Decide whether unmounted routers are in v1.0. If yes, mount/test/document them.
   If no, keep them marked as backlog/unavailable in manuals.
2. Normalize worker documentation: only deployed Compose/systemd jobs should be
   claimed as production jobs.
3. Decide whether unmounted worker modules are v1.0 deployed jobs or backlog,
   then align worker inventory docs with Compose/systemd.

Resolved in this remediation batch:

1. Stdio MCP dispatch is fail-closed for unadvertised tools.
2. `docs/database.md` has been aligned to the table registry summary and
   `source_revision` canonical rule.
3. DGT transient upstream failures are documented and logged as `partial`.
4. `source_freshness_snapshot` and `data_freshness_alerts` have Alembic
   ownership in revision `20260511_0068_freshness_tables_schema.py`.
5. The hourly MCP validation suite now includes real `/mcp` transport
   handshake and `tools/list`.
6. Hermes Docker and host/systemd now use the same canonical monitor script.

Important but not blocking if documented:

1. Keep GPT Actions as a curated 13-path surface, not full API.
2. Keep full REST API broader than MCP and Actions by design.
3. Mark many regulatory operational domains as schema/API-ready but workflow-empty
   until real events or official ingestion populate them.
4. Keep web UI as internal/minimal, not the canonical compliance surface.

## Release Claim Guidance

Allowed v1.0 claim:

> ESData v1.0 provides a grounded Spanish fiscal-regulatory MCP/API core with
> official-source retrieval, AEAT model support, domain availability, source
> freshness, audit logging, deployed ingestion workers, validation gates and a
> curated GPT Actions surface.

Not allowed without further work:

> Every router, every worker module and every documented endpoint in the repo is
> deployed and production-ready.

Not allowed:

> All regulatory tables are populated.

Correct wording:

> All tables are classified. Populated domains are served with provenance; empty
> domains are explicitly exposed as `workflow_empty`, `allowed_empty`, or
> `configured_but_unavailable`.
