# AEAT AI agents

This document defines how agentic assistants such as Hermes may help with AEAT
campaign curation.

## Role

AI agents are documentary copilots. They may collect, compare and summarize
official evidence, but they are not fiscal decision makers.

## Allowed actions

Agents may:

- call read-only MCP/API tools;
- inspect `docs/aeat/precision-contract.md` and `docs/aeat/curation-rules.md`;
- review official-source payloads for one model at a time;
- generate draft reports under `reports/aeat-campaign-curation/<modelo>.md`;
- recommend one of `resolved_strong`, `resolved_weak`, `conflict`,
  `insufficient_evidence` or `stale_suspected` as a draft conclusion;
- write `UNKNOWN` when direct official evidence is absent or ambiguous.

## Structured output contract

Markdown-only Hermes reports are triage artifacts. They are not integrable
evidence.

Any agent output intended for review or repository integration must conform to:

```text
docs/aeat/hermes-curation-output.schema.json
```

and must pass:

```bash
python scripts/maintenance/validate_aeat_hermes_report.py <report.json>
```

Before any report is considered for repository evidence, run the admission
audit:

```bash
python scripts/maintenance/audit_aeat_hermes_integration.py <report.json>
```

`integrable=true` only means the report can enter human review as traceable
evidence. It does not allow the agent to promote a campaign or write
`resolved_strong`.

For batch operation, run automatic adjudication instead of reviewing every
model manually:

```bash
python scripts/maintenance/adjudicate_aeat_hermes_batch.py --verify-sources <reports-dir-or-json>
```

The adjudicator may auto-accept non-assertive conflict/stale/insufficient
evidence when it verifies official URLs, locators and excerpts. It must route
assertable candidates, missing traceability and rejected reports to human
review.

Human review of admitted AEAT reports should use the checklist in:

```text
docs/aeat/hermes-human-review-checklist-2026-05-27.md
```

The schema forces four separate layers:

- `official_source_claims`: claims traceable 1:1 to an official URL, locator
  and excerpt;
- `derived_claims`: explicit inference, never campaign assertion;
- `system_observed_claims`: MCP/API telemetry, never documentary evidence;
- `rejected_claims`: plausible claims that must not be made.

MCP output may route the investigation and describe ESData state. It must not
justify final documentary claims. If a claim exists only in MCP, it is not an
official-source claim.

## Forbidden actions

Agents must not:

- write to the database;
- run migrations;
- deploy to VPS or production;
- modify `modelo_campana`, `modelo_recurso` or assertion fields;
- decide `resolved_strong` or `ASSERTABLE_DIRECT_OFFICIAL`;
- promote campaigns in bulk;
- use BOE publication date, file name, XSD/WSDL version, endpoint, manual
  version or internal resource association as strong evidence by itself.
- produce integrable evidence as free-form markdown.

## Local Hermes pilot

The first Hermes experiment must run locally, not on the VPS.

Suggested profile:

```text
hermes-esdata-curator
```

Suggested local MCP target:

```text
http://host.docker.internal:8010/mcp
```

Expose only read-only model tools, for example:

```yaml
mcp_servers:
  esdata:
    url: "http://host.docker.internal:8010/mcp"
    headers:
      X-API-Key: "<local-api-key>"
    timeout: 180
    connect_timeout: 60
    tools:
      include:
        - list_modelos
        - get_modelo
        - get_modelo_fuentes_oficiales
        - get_modelo_artefactos
        - get_modelo_resumen_operativo
        - buscar_modelos_aeat_catalogo
      resources: false
      prompts: false
    sampling:
      enabled: false
```

## Pilot acceptance criteria

The first pilot should review `124` and `210`.

Each report must:

- cite the ESData fields used (`campana_safe_to_assert`,
  `campana_assertion_code`, `campana_afirmable`, `campana_resolution_status`);
- cite official-source URLs returned by ESData;
- distinguish official evidence from internal inference;
- return `UNKNOWN` when no direct official model-to-exercise evidence is found;
- avoid phrases such as "la campana activa es X" unless the assertion contract
  is satisfied and a human has accepted the curation.

Pilot markdown reports may be used only to decide whether the agent is worth
rerunning with the structured JSON contract. They must not be copied into
canonical curation docs without human rewrite and source verification.

No agent output is allowed to change production state. Human review remains the
only path to promotion.
