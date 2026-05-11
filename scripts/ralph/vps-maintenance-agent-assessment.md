# Ralph VPS Maintenance Agent Assessment

Date: 2026-05-10
Scope: local evidence only. VPS `212.227.227.64` has not been accessed in this phase.

## Current Local Gate

Status: PASS

Evidence:

- `python scripts\ralph\local_full_gate.py --base-url http://localhost:8001 --api-key dev-key`
- Result: `5` checks, `5` passed, `0` failed.
- Artifacts:
  - `scripts/ralph/local-full-gate-results.json`
  - `scripts/ralph/table-remediation-registry.json`
  - `scripts/ralph/script-verification-registry.json`
  - `scripts/ralph/mcp-api-local-results.json`
  - `scripts/ralph/worker-run-once-results-*.json`

## MCP Benchmark Notes

External MCP references reviewed:

- Official MCP docs: MCP servers expose resources, tools, and prompts; STDIO servers must not write operational logs to stdout because that corrupts JSON-RPC.
- OpenAI Apps SDK MCP docs: MCP server metadata and tool/component descriptions should be explicit for client use.
- AEAT MCP reference: official-source-only model with exact source fields.
- BOE MCP reference: BOE consolidated legislation, daily BOE/BORME, and structured MCP server layout.
- data.gouv.fr MCP reference: official public MCP endpoint, read-only tools, and hosted streamable HTTP endpoint.

Local alignment:

- The local API/MCP gate verifies health, status, LIVA art. 90 current and historical answers, source freshness, safe 404 behavior, and query audit traceability.
- Current local evidence confirms LIVA art. 90 current 21% with BOE provenance and historical 15/18/21 transitions.
- Query audit is present for `get_articulo` with `verified=true` and retrieved chunks.
- The local gate does not yet exhaustively validate every MCP tool against a broad golden legal test suite; it validates the highest-risk LIVA art. 90 path and infrastructure contract.

## Hermes Existing Script

File: `scripts/hermes_monitor.py`

Current capability:

- Polls `/health`.
- Polls `/status`.
- Detects stale/error/partial workers.
- Checks `sync_dead_letter`.
- Can attempt Docker restarts only when `AUTO_RESTART_ENABLED=true` and worker is in `RESTART_ALLOWLIST`.

Local evidence:

- Command: `python scripts\hermes_monitor.py --api-url http://localhost:8001 --no-restart`
- API health: OK.
- `/status`: OK, 29 workers read.
- DLQ: local Docker DB contains 2 rows via `docker compose exec postgres`, but Hermes host-side DB lookup failed because host `localhost:5432` is an external PostgreSQL process in this Windows environment, not the Docker DB.
- Hermes reported 11 stale workers. In the local dev stack only `worker-boe` is actually running continuously; cron artifacts are verified separately. Therefore local Hermes stale output is useful as a signal, but not a production verdict.

Decision:

- Useful: YES, but only as a constrained operational monitor.
- Deploy now on VPS: CONDITIONAL.
- Required before deployment:
  - Run inside the Compose network or with a verified production `DATABASE_URL`.
  - Keep `AUTO_RESTART_ENABLED=false` initially.
  - Use a narrow `RESTART_ALLOWLIST` only after observing false positives.
  - Send logs to journald/file with UTF-8-safe configuration.
  - Treat `partial` for known parser skips differently from hard `error` if `sync_log.error_msg` is a structured summary.

Safe permissions:

- Read `/health`, `/status`, `/v1/sources/freshness`, and DLQ.
- Read journald/docker logs.
- Optional restart-only permission for explicitly allowlisted stateless worker containers.

Unsafe permissions:

- Direct writes to compliance data.
- Automatic mutation of `norma`, `articulo`, `version_articulo`, source revisions, tax rates, legal interpretations, or AEAT/BOE records.
- Broad Docker restart permission without allowlist.

## Tester-Healer Agent

Decision: YES, deploy as read-only validator first.

Scope:

- Run `scripts/maintenance/mcp_validation_suite.py --read-only`.
- Run `scripts/ralph/verify_mcp_api_local.py` equivalent against production base URL with production API key.
- Check source freshness and query audit traceability.
- Store reports and alert on failure.

Safe remediation:

- None for legal data.
- Optional infrastructure-level restart only if paired with Hermes allowlist and after repeated health failures.

Unsafe remediation:

- Re-ingesting or rewriting regulatory records without human approval.
- Changing legal interpretations automatically.

## Regulatory Awareness Agent

Decision: YES, but read-only digest mode only.

Scope:

- Watch official sources: BOE, AEAT, EUR-Lex, AEPD, DGT, Banco de España, CNMV, SEPBLAC.
- Produce daily digest of source changes and likely affected tables/tools.
- Draft tasks for human review.

Safe permissions:

- Read official publication channels.
- Read local source revision metadata.
- Write digest/audit reports.

Unsafe permissions:

- Silent DB updates to legal/tax records.
- Silent cache invalidation that changes answers without validation.
- Any autonomous legal interpretation.

## Recommended VPS Loops

Hourly:

- Hermes health/status/DLQ check.
- MCP validation smoke: health, status, LIVA art. 90, source freshness, query audit.

Daily:

- Regulatory awareness digest for BOE/AEAT/EUR-Lex and source revision deltas.
- Cron execution verification: expected jobs ran, exit codes, processed rows, errors.

Weekly:

- Full Ralph gate equivalent using production-safe read-only checks.
- Dependency/security scan and backup restore drill evidence.

## Verdict

Local system status before VPS deployment: CONDITIONAL PASS.

Reason:

- Local jobs, cron artifacts, table classification, scripts, API/MCP accuracy, and Docker services pass the local Ralph gate.
- Hermes-style monitoring is useful but not yet production-hardened enough to be granted autonomous write/restart permissions broadly.
- The remaining step is VPS-specific validation after access is available; local evidence must not be represented as VPS production evidence.
