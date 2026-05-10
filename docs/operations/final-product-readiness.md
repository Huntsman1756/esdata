# Final Product Readiness

Date: 2026-05-10

Scope: local product-readiness verification plus deployable VPS artifacts. This
document does not claim that the VPS is healthy until the same checks are run on
the server.

## Current Verdict

`CONDITIONAL PASS - VPS`

The local stack and deployment artifacts pass the final Ralph gate:

```bash
python scripts/ralph/final_product_gate.py --base-url http://localhost:8001 --api-key dev-key
```

Latest result:

- final gate: 6/6 passed
- local full gate: 5/5 passed
- table gate: 163 tables classified, 0 blockers, 0 unclassified
- cron/worker artifacts: 16/16 passed
- script registry: 207 scripts classified, 65 verified, 142 runtime-blocked by policy, 0 failures
- MCP/API accuracy: 10/10 passed
- maintenance-agent tests: 20/20 passed

## Data Position

The table registry is the controlling artifact:

- `scripts/ralph/table-remediation-registry.json`
- `docs/operations/table-source-action-plan.md`

Current classification:

- populated: 72
- workflow-empty: 53
- allowed-empty: 3
- configured-but-unavailable: 35
- blockers: 0
- derived blockers: 0
- unclassified: 0

Interpretation:

- Populated tables contain local data accepted by the registry.
- Workflow-empty tables are not filled with fake data. They require either a
  real user workflow, a configured official upstream source, or an official
  filing/register that is not currently available locally.
- Allowed-empty tables are system/meta tables that may be empty until the
  feature is actively used.
- Empty-table availability is exposed in API and HTTP MCP through
  `/v1/domain-availability`. Empty domain responses must use
  `workflow_empty`, `allowed_empty`, or `configured_but_unavailable` with
  `safe_to_answer=false` unless the table is populated with live rows.

No table should be filled with fixture/community/LLM data to satisfy row counts.

GIIN/FATCA update: `giin_registry` is populated locally and on the VPS from the
official IRS FATCA FFI monthly CSV ZIP, with `508593` distinct GIIN rows and no
seed fallback. The monthly cron service is `cron-giin-monthly`, scheduled by
`esdata-giin-monthly.timer`.

Screening update: `screening_entries` is populated locally and on the VPS from
the official OFAC SDN XML export, with `18947` distinct entries and no seed
fallback. EU, SEPBLAC, UN, and PEP filtered screening queries remain explicit
`configured_but_unavailable` surfaces until their official parsers are added.

## Workers And Cron

The local cron/worker run-once artifacts cover 18 services:

- BOE daily
- AEAT modelos daily
- AEAT current 1XX/2XX designs and taxpayer calendar daily
- BOE modelos daily
- regulatory daily
- GIIN/FATCA monthly
- OFAC SDN weekly
- PSD2 weekly
- AEPD, BDE, BDNS, BORME, CENDOJ, CNMV, DGT, EUR-Lex, SEPBLAC, TEAC weekly

All 16 artifacts are passing. Long-running official-source ingestions are not
rerun by the final gate; their prior run-once evidence is treated as the local
artifact of record unless worker code changes.

AEAT 1XX/2XX current coverage as of the local run:

- 86 active 1XX/2XX models
- 75 active models with official current design resources
- 28 active models with structured fields extracted from official XLS/XLSX or `.properties`
- 63 active models with at least one 2026 taxpayer-calendar deadline
- 11 active models without a current design resource on the official AEAT 1XX/2XX design pages: 121, 136, 140, 143, 146, 147, 150, 221, 228, 230, 247

PDF-only resources are retained with provenance but are not converted into
synthetic fields until a deterministic parser is validated.

## MCP/API Accuracy

The final local gate includes live checks against the API:

- health/status
- LIVA article 90 current 21 percent with BOE provenance
- historical LIVA article 90 boundary cases
- source freshness
- safe 404 behavior
- query audit traceability

Any silent stale answer, missing source URL, or wrong legal/tax fact in this
checked path fails the gate.

## Hermes And Alertmanager

Hermes remains read-only by default:

- `AUTO_RESTART_ENABLED=false`
- restarts require explicit `RESTART_ALLOWLIST`
- no write permission to fiscal/legal records

Alertmanager/Telegram is VPS-ready in artifact form:

- Telegram bot token is read from
  `/etc/alertmanager/secrets/telegram_bot_token` inside the container.
- `TELEGRAM_CHAT_ID` is configured in `/etc/esdata/esdata.env`.
- `prom/alertmanager:v0.28.1` config validation passes after render.

Manual Telegram delivery must still be verified on the VPS with the runbook in:

- `docs/operations/runbooks/grafana.md`

## VPS Gate

After deployment to `212.227.227.64`, do not mark production ready until these
server-side checks pass:

1. `docker compose ... config --quiet`
2. `docker compose ... ps`
3. `curl http://127.0.0.1:8000/health`
4. `curl -H "X-API-Key: $ESDATA_API_KEY" http://127.0.0.1:8000/status`
5. `systemctl list-timers --all 'esdata-*'`
6. `systemctl status esdata-hermes-monitor.service`
7. `systemctl status esdata-mcp-validation.timer`
8. Alertmanager manual Telegram test from the Grafana runbook
9. One manual cron run for the critical daily jobs after deploy
10. MCP/API accuracy gate against the VPS endpoint

## VPS Result - 2026-05-10

Deployment target: `212.227.227.64`.

Verified on the VPS:

- Docker Compose stack is up; API, web, Postgres, workers, Prometheus, Grafana
  and Hermes container are running.
- `/health` returns `{"status":"ok","database":"ok"}`.
- `/status` returns OK for the critical cron paths exercised after deploy:
  `cron-boe-daily`, `cron-modelos-daily`, `cron-aeat-current-daily`,
  `cron-boe-modelos-daily`, `cron-cdi-weekly`, `cron-eurlex-weekly`,
  `cron-dgt-weekly`, `cron-teac-weekly`, `cron-bdns-weekly`,
  `cron-borme-weekly`, `cron-cnmv-weekly`, `cron-sepblac-weekly`,
  `cron-cendoj-weekly`, `cron-bde-weekly`, `cron-aepd-weekly`,
  `cron-psd2-weekly`, and `cron-regulatory-daily`.
- Systemd timers are installed and active, including the new
  `esdata-aeat-current-daily.timer` and fixed `esdata-cdi-weekly.timer`.
- AEAT model data on VPS: 217 active models, 28,574 official design fields,
  9,623 model resources, and 215 taxpayer-calendar rows.
- BOE data on VPS: 5 BOE normas and 902 article rows after `cron-boe-daily`
  completed with 1,009 processed blocks/articulos across run segments.
- CDI data on VPS: 86 conventions from official Hacienda/AEAT sources.
- EUR-Lex data on VPS: 32 official ELI metadata rows. Deep article download is
  disabled by default (`EURLEX_FETCH_ARTICLES=false`) because the previous
  path held long DB transactions and blocked the worker.
- Focused local tests after fixes: 15/15 passed.

Important limitation:

- A full row-count audit still shows many empty public tables. Those are not
  filled with synthetic data. Empty domains include inactive workflow/event
  tables and domains whose official ingestion is not yet implemented or not
  configured on the VPS. The current state is therefore not `PRODUCTION READY`
  for every declared schema domain; it is production-usable only for the
  verified AEAT/BOE/CDI/interpretative-document surfaces above.
- Fresh local/VPS comparison shows deployment drift: local has `70` populated
  tables and `93` empty tables; the VPS has `39` populated tables and `124`
  empty tables. The active remediation plan is
  `docs/operations/table-source-action-plan.md`.

Update after P0 closure:

- Local/VPS empty-table drift for populated-local tables is closed:
  local `163` tables / `70` populated / `93` empty; VPS `163` tables /
  `70` populated / `93` empty; `vps_empty_local_populated=0`.
- `worker-dgt` health was corrected by touching heartbeat during long discovery
  loops; all `deploy-*` containers with healthchecks are healthy after recreate.
- Remaining empty tables are empty in both environments and must stay classified
  explicitly as workflow-empty, allowed-empty, or future official-source targets.

Operational notes:

- The systemd Hermes host service was disabled because the host Python
  environment lacked the SQLAlchemy psycopg dialect. The Docker Compose Hermes
  container remains running and is the active monitor.
- Alertmanager/Telegram is not marked verified unless real Telegram token and
  chat id are installed and a manual alert delivery test passes.
