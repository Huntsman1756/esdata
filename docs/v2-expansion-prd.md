# ESData v2 expansion PRD

Status: `DEFINED_NOT_STARTED`

This PRD defines the first v2 expansion after the useful v1 closeout. It does not change the v1 claim: ESData remains a fail-closed system for evidence-backed regulatory consultation, audit trails, and human review acceleration. v2 may add measurable operational coverage, but it must not turn inference into fiscal truth.

## Product claim

v2 expands official-evidence coverage for selected high-value fiscal models while preserving the v1 truth contract:

- no automatic fiscal decisioning
- no campaign promotion without direct official evidence
- no `resolved_strong` from LLM inference, internal state, file names, version labels, BOE dates, or technical endpoints alone
- no claim expansion beyond the scope of this PRD without a separate v2 PRD addendum

## Objectives

- Increase measurable `resolved_strong` coverage for the scoped P1 models to at least `40%`, only where direct official evidence exists.
- Move AEAT models `124`, `126`, and `128` from `CONFLICT` to `resolved_strong` only if fresh official evidence directly proves the campaign.
- Improve models `303` and `390` toward at least `50%` evidence-backed operational coverage for the scoped fields/flows.
- Audit model `289` as a documentary block and keep CRS/DAC2 as a separate block unless direct evidence supports combining them.
- Keep ambiguous `SKIPPED` legal-source status at `0%`.

## Non-goals

- Do not weaken the v1 closeout gate.
- Do not promote campaigns from Hermes output alone.
- Do not merge model `289` with full CRS/DAC2 coverage unless a later explicit scope change proves it.
- Do not expand UI/MCP claims from `consulta/auditoria fail-closed` to automatic fiscal decisioning.
- Do not add broad new source families outside the sprint scope.

## Anti-drift rules

- If evidence cannot be verified, the model stays fail-closed.
- `resolved_strong` requires direct, verifiable official evidence tied to the specific model and campaign/period claim.
- Evidence URLs must use HTTPS where supported, including `https://www.boe.es`.
- Evidence used for a promotion must include a fresh capture/hash less than `30` days old at the time of promotion.
- v1 gate regressions block v2 progress.

## Sprints

### Sprint 1: AEAT 124/126/128 campaign resolution

Scope:

- Re-audit models `124`, `126`, and `128`.
- Search only for direct official evidence capable of proving campaign/period.
- Keep each model in `CONFLICT` if evidence remains insufficient or contradictory.

Exit:

- Each model is either `resolved_strong` with direct official evidence or remains explicitly documented as `CONFLICT`.
- No product data is promoted unless the evidence passes the v1 truth contract.

### Sprint 2: AEAT 303/390 operational coverage

Scope:

- Improve evidence-backed operational coverage for models `303` and `390`.
- Prioritize official instructions, forms, designs, and traceable source artifacts.

Exit:

- At least `50%` scoped coverage for each model, or a documented fail-closed reason for shortfall.
- No derived operational claim lacks source URL, locator/excerpt where applicable, hash, and capture timestamp.

### Sprint 3: AEAT 289 documentary audit

Scope:

- Audit model `289` as its own documentary obligation block.
- Keep CRS/DAC2 as separate unless evidence proves direct merger is correct.

Exit:

- `289` has a documented evidence map and unresolved gaps.
- CRS/DAC2 separation is explicit in docs and data contracts.

## Gate

v2 work may proceed only if:

- v1 closeout gate has no regression for at least `2` Hermes cycles.
- `systemctl --failed` remains clean.
- Hermes summary has no hidden failures and no ambiguous `SKIPPED`.
- `/health`, authenticated `/status`, and `mcp_validation_suite` pass.
- Evidence artifacts for promoted claims have HTTPS source URLs, hashes, and capture timestamps less than `30` days old.

If a criterion cannot be verified, the gate fails.

## Metrics

| Metric | v1 closeout baseline | v2 target |
| --- | --- | --- |
| Scoped P1 `resolved_strong` coverage | `0%` for unresolved target set | `>= 40%` where evidence exists |
| 124/126/128 campaign state | `CONFLICT` / human review | `resolved_strong` only with direct official evidence |
| 303/390 scoped operational coverage | partial/unknown by scoped v2 standard | `>= 50%` or documented fail-closed shortfall |
| Ambiguous legal-source `SKIPPED` | blocked by v1 gate | `0%` |
| v1 gate regressions during v2 | `0` required | `0` |

## Main risk

The main risk is that models `124`, `126`, and `128` cannot progress because fresh official evidence does not exist or remains contradictory. The mitigation is to keep them in `CONFLICT`, document the evidence gap, and avoid forced promotion.

## Open only by explicit decision

This PRD defines v2 scope but does not start implementation by itself. Execution starts only when the roadmap opens a concrete v2 sprint with files, acceptance criteria, and verification commands.
