# AEAT precision contract

This is the integration contract for AEAT campaign assertions in API, MCP, UI,
CLI clients and downstream automations.

Campaign data curation rules live in `docs/aeat/curation-rules.md`.
AI-agent curation limits live in `docs/aeat/ai-agents.md`.

## Campaign assertion gate

Only assert a fiscal campaign as current when all three conditions are true:

- `campana_safe_to_assert = true`
- `campana_afirmable != null`
- `campana_assertion_code = ASSERTABLE_DIRECT_OFFICIAL`

Every other state is non-assertable, even when the year looks plausible.

Non-assertable codes:

- `NOT_ASSERTABLE_INFERRED_INTERNAL`
- `NOT_ASSERTABLE_CONFLICT`
- `INSUFFICIENT_EVIDENCE`
- `STALE_SUSPECTED`

## Forbidden interpretation

Never use `campana_activa`, `campana_persistida` or `campana_candidata` to build
sentences such as "la campana activa es X", "campana vigente X" or equivalent
claims.

Those fields are context. They are not fiscal truth.

## Technical exercise coverage

`technical_exercise_coverage` is useful documentary context, not campaign
truth. It may describe official AEAT technical ranges such as "Ejercicios 2020
y siguientes" for a batch presentation or record design.

Every item must keep:

- `proves_campaign = false`
- `evidence_role = technical_exercise_coverage`

This field may support `stale_suspected` or conflict review when it contradicts
an old persisted campaign, but it must never feed:

- `campana_afirmable`
- `campana_safe_to_assert = true`
- `campana_assertion_code = ASSERTABLE_DIRECT_OFFICIAL`

## Required consumer behavior

When the gate is not satisfied, a client must abstain from asserting the
campaign and expose the structured warning when present:

- `campana_assertion_code`
- `campana_assertion_warning`

If a consumer asserts a campaign while `campana_safe_to_assert=false`, or while
`campana_assertion_code` is anything other than `ASSERTABLE_DIRECT_OFFICIAL`, it
violates the ESData fiscal truth contract.
