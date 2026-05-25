# AEAT precision policy

## Campaign assertion rule

ESData must not present a fiscal campaign as active unless the response carries
all three signals:

- `campana_safe_to_assert = true`
- `campana_afirmable` is not `null`
- `campana_assertion_code = ASSERTABLE_DIRECT_OFFICIAL`

Any other combination is non-assertable. Consumers must either abstain from
stating a campaign or show the structured warning returned by the API.

## Structured warning codes

The campaign assertion contract exposes:

- `campana_assertion_code`
- `campana_assertion_warning`

Allowed codes:

- `ASSERTABLE_DIRECT_OFFICIAL`: official direct evidence supports the asserted campaign.
- `NOT_ASSERTABLE_INFERRED_INTERNAL`: campaign is internally inferred or persisted only.
- `NOT_ASSERTABLE_CONFLICT`: documentary years conflict; no campaign can be selected.
- `INSUFFICIENT_EVIDENCE`: there is not enough official evidence to determine a campaign.
- `STALE_SUSPECTED`: campaign may be stale and requires fresh official-source review.

## Non-negotiable integration rule

`campana_activa`, `campana_persistida` and `campana_candidata` are context, not
truth. A client that ignores `campana_safe_to_assert=false` or a
`NOT_ASSERTABLE_*` code is violating the ESData fiscal truth contract.

The canonical integration contract lives in `docs/aeat/precision-contract.md`.
