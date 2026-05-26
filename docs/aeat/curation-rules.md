# AEAT campaign curation rules

These rules govern manual and semi-automated curation of AEAT campaign states.
They do not authorize bulk promotion or inferred truth.

## Promotion rule

A model can be promoted to `resolved_strong` only when there is direct official
evidence for the campaign:

- explicit AEAT text linking the model to the exercise, campaign or reporting
  period; or
- an unequivocal official BOE/AEAT legal or technical text linking the model to
  the exercise, campaign or reporting period.

BOE publication date alone is not campaign evidence. File name, XSD/WSDL
version, endpoint, manual version, technical resource year or internal
`modelo_recurso` association are not strong evidence unless the official text
itself provides the model-to-exercise link.

## No bulk promotion

Never promote campaigns in bulk. Each model requires an individual curation
record with source URL, captured evidence, decision and residual uncertainty.

## Conflict handling

If documentary evidence conflicts, keep or move the model to `conflict` until
the conflict is resolved by stronger official evidence. Do not select the latest
year automatically.

## Insufficient evidence

If evidence is absent or does not explicitly bind model and exercise, keep or
move the model to `insufficient_evidence`.

## Stale suspicion

If a model has an old campaign and no fresh official evidence, prefer
`stale_suspected` over treating `resolved_weak` as current.

## Measurement

Progress is measured by models with:

- `campana_safe_to_assert = true`
- `campana_afirmable != null`
- `campana_assertion_code = ASSERTABLE_DIRECT_OFFICIAL`

Do not use total `resolved` count as a fiscal precision KPI.

## First review queue

Prioritize high-risk P1 models before broad coverage:

1. `124`, `126`, `128`
2. `113`, `122`, `145`, `226`
3. `210`
4. `111`, `115`, `117`, `237`
5. `211`, `213`
