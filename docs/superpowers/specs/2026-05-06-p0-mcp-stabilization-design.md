# P0 MCP Stabilization Design

## Status

- Date: 2026-05-06
- Status: approved for planning
- Scope: P0 stabilization before broader frontend, developer-experience, or product expansion work
- Non-goal: production deploy without explicit confirmation and fresh verification

## Problem

The ESData MCP currently exposes compliance, tax, and regulatory data to workflows where wrong answers are liabilities. The audit found several stop-ship risks:

- current-law responses can be stale, demonstrated by `LIVA` article 91 returning obsolete rates for a current `vigente_en` date
- AEAT model responses can include raw HTML/navigation fragments while being marked `verified`
- not every MCP retrieval tool has durable audit coverage
- runtime API code can create schema objects outside Alembic, weakening RLS guarantees
- some hybrid/unified search paths have static SQL defects and source-isolation gaps
- production deployment config still contains deprecated Railway workflow paths and insufficient `/mcp` perimeter controls

P0 stabilization restores minimum safety for compliance-domain use. Broader enhancements wait until the verified surface is reliable.

## Goals

1. Prevent known-stale or contaminated data from being presented as verified.
2. Make every MCP tool invocation auditable, including errors and no-result states.
3. Restore Alembic-only schema ownership and enforce RLS on all public tables.
4. Fix retrieval defects that can silently return partial, cross-domain, or non-vigente results.
5. Add factual regression tests for current high-risk tax references and AEAT parser cleanliness.
6. Remove or disable active deprecated deployment paths and document `/mcp` perimeter protection requirements.

## Non-Goals

- Rebuild every source worker.
- Add new regulatory domains.
- Redesign the frontend beyond exposing trust/freshness/source warnings required by backend changes.
- SSH into the VPS, rotate secrets, alter firewall rules, or deploy to production without explicit user confirmation.
- Commit changes unless explicitly requested.

## Architecture

### Verified Response Gate

High-risk API/MCP responses must carry explicit trust state:

- `verified=true` only when the underlying parser or source pipeline passed cleanliness and source checks.
- `verified=false` or `completeness=partial` when data contains parser residue, missing official references, stale source snapshots, or failed freshness probes.
- Responses that cannot establish current-law correctness must surface an explicit warning instead of claiming completeness.

For P0, this gate applies first to legislation detail/search and AEAT model endpoints.

### Data Accuracy Guardrails

Add targeted factual probes for known high-liability references:

- `LIVA` article 90 current general rate.
- `LIVA` article 91 current reduced/super-reduced rate structure.
- AEAT model 303 name, official sources, casillas, claves, and instrucciones cleanliness for campaign 2025/active campaign.

These probes should run in tests against fixture/test data and as read-only production checks where possible.

### MCP Audit Boundary

Audit must happen at the MCP tool-call boundary, not only inside individual routers. Each HTTP MCP `tools/call` should record:

- request ID
- actor/session context when available
- tool name and normalized arguments
- status: success, validation_error, not_found, internal_error, partial
- retrieved source metadata when applicable
- response summary
- timestamp

Router-level audit can remain, but the MCP boundary is the enforcement point for MCP compliance.

### Schema Ownership And RLS

Runtime `CREATE TABLE IF NOT EXISTS` in API services must be removed or limited to SQLite tests. PostgreSQL schema must be Alembic-owned.

Add a post-head migration or verification migration that:

- enables RLS for every current public table
- grants only approved backend roles
- creates approved policies where missing
- fails or reports when public/anon/authenticated policies exist

Add a CI test that inspects migrations/source for forbidden runtime DDL in production API paths.

### Search And Retrieval

P0 fixes focus on correctness, not ranking sophistication:

- fix hybrid doctrine SQL construction
- fix unified 31.x alias/parameter defects
- pass requested source through 31.x search to avoid cross-domain contamination
- honor `vigente_en` in hybrid/vector legislation retrieval
- add exact-reference parsing for common legal references before fuzzy/full-text ranking
- avoid broad exception fallbacks that hide SQL or permission errors

### Worker And Cron Stabilization

P0 worker changes are narrow:

- make DGT queue claiming atomic or guarded by a worker-level lock
- add retry count and dead-letter semantics for persistent pending records
- add systemd timeout/failure handling for `esdata-job@.service`
- document overlap expectations for cron and persistent workers

### Infrastructure Controls

P0 infrastructure changes:

- disable or archive the deprecated Railway workflow so it cannot run on `main`
- keep real env files out of repo paths and do not read secrets during remediation
- add repo-side Caddy configuration hooks for `/mcp` restriction, defaulting to deny/allowlist behavior unless an explicit private-network deployment choice is documented before deploy
- harden `Dockerfile.ops` to match pinned/non-root baseline

### Frontend Surface

Frontend work is limited to trust communication:

- show source URL, freshness, and `verified/partial` state where backend provides it
- avoid making legal claims client-side
- keep all business logic backend-only

## Data Flow

1. Worker ingests official source and stores source metadata, hashes, freshness, and parsed records.
2. API retrieves records with exact filters first, then ranked search when exact match is unavailable.
3. API attaches trust state and source metadata.
4. MCP boundary logs the complete invocation and result/error state.
5. Frontend displays backend-provided trust/source state without deriving legal meaning locally.

## Error Handling

- Unexpected DB/search/parser errors must not be swallowed as empty or fallback results.
- Known partial states must return explicit `partial` status and warning fields.
- MCP errors must be audited with error status, not recorded as success.
- Stale data must be visible in responses and operational status.

## Testing Plan

P0 must add or update tests for:

- current `LIVA` article 91 and 90 factual probes
- AEAT model 303 parser cleanliness and `verified=false` on dirty content
- MCP audit row for every exposed HTTP MCP tool, including validation errors
- no runtime PostgreSQL DDL in API governance/audit services
- RLS verification over all current public tables in a test database or static migration check
- hybrid doctrine SQL path
- unified 31.x source isolation
- `vigente_en` honored in hybrid/vector legislation retrieval
- DGT queue overlap or atomic claim behavior
- systemd unit config contains timeout/failure handling
- Railway workflow cannot trigger on `main`

## Rollout Plan

1. Implement and verify locally in small slices.
2. Run focused API, worker, infra, and docs checks after each slice.
3. Run a consolidated smoke/regression suite.
4. Produce a deployment checklist with exact read-only prechecks and rollback notes.
5. Request explicit confirmation before touching production VPS or deploying.

## Acceptance Criteria

- Known stale `LIVA` article 91 current-date response is fixed or explicitly blocked as stale.
- Dirty AEAT model content is no longer marked verified.
- All HTTP MCP tools have audit coverage at the tool-call boundary.
- No production API path creates PostgreSQL tables at runtime.
- RLS coverage is enforced for all current public tables.
- Search fixes have tests that fail on the audited defects.
- Deprecated Railway workflow no longer deploys on push to `main`.
- `/mcp` production exposure has an implemented or explicitly documented private-access control.
- Verification evidence is recorded before any production deploy claim.

## Risks

- Existing worktree is heavily dirty; changes must avoid reverting unrelated user/agent work.
- Some fixes may depend on live DB data that is unavailable locally.
- Alembic/RLS changes are security-sensitive and require explicit confirmation before production application.
- Parser cleanup can reduce apparent coverage until data is re-ingested.

## Decisions For P0

- `/mcp` restriction will be implemented in repo-side deployment configuration hooks first. If production uses Tailscale/IP allowlist outside Caddy, the deployment checklist must record that exact control before deploy.
- Dirty AEAT records will be marked `verified=false` and `completeness=partial`; quarantine/re-ingestion can follow after the response contract is safe.
- DGT overlap safety will start with a whole-worker advisory lock to avoid schema-sensitive queue redesign in the first slice. Retry/dead-letter schema work can proceed only after the lock and current factual defects are handled.
