# AEAT precision contract

This is the integration contract for AEAT campaign assertions in API, MCP, UI,
CLI clients and downstream automations.

Campaign data curation rules live in `docs/aeat/curation-rules.md`.
AI-agent curation limits live in `docs/aeat/ai-agents.md`.
Hermes structured output rules live in
`docs/aeat/hermes-curation-output-contract.md`.

## Campaign assertion gate

Only assert a fiscal campaign as current when all three conditions are true:

- `campana_safe_to_assert = true`
- `campana_afirmable != null`
- `campana_assertion_code = ASSERTABLE_DIRECT_OFFICIAL`

Every other state is non-assertable, even when the year looks plausible.

`campana_safe_to_assert` is derived from `campana_evidence`, which separates
three independent lanes:

- `campana_evidence.legal`: BOE/legal approval evidence. It can become
  `resolved_strong_legal` only with normalized official BOE evidence.
- `campana_evidence.operational`: AEAT Sede operational evidence. It can become
  `resolved_strong_operational` only with direct official AEAT evidence.
- `campana_evidence.design`: technical design coverage. It may become
  `technical_design_current`, but it never makes `campana_safe_to_assert=true`.

`campana_assertion_basis` lists the lanes that support the response. A basis of
`technical_design` alone means design context only, not an active fiscal
campaign.

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

When the only fresh evidence is technical coverage, clients should say
"diseño técnico vigente/cubierto" rather than "campaña activa".

## Required consumer behavior

When the gate is not satisfied, a client must abstain from asserting the
campaign and expose the structured warning when present:

- `campana_assertion_code`
- `campana_assertion_warning`

If a consumer asserts a campaign while `campana_safe_to_assert=false`, or while
`campana_assertion_code` is anything other than `ASSERTABLE_DIRECT_OFFICIAL`, it
violates the ESData fiscal truth contract.
