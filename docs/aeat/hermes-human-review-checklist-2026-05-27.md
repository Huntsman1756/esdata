# Hermes AEAT human review checklist - 2026-05-27

This checklist governs human review of Hermes AEAT JSON reports after they pass
schema validation and the evidence admission audit.

Passing `audit_aeat_hermes_integration.py` means the report is reviewable. It
does not mean the campaign is verified, assertable or writable to production.

Human review is not the default path for every model. First run batch
adjudication:

```bash
python scripts/maintenance/adjudicate_aeat_hermes_batch.py --verify-sources --latest-per-model --history-dir <metrics-dir> <reports-dir-or-json>
```

Use this checklist only for reports routed to `human_review_assertable_candidate`,
`needs_report_rewrite` or `reject_report`, and for sampled QA of automatically
accepted non-assertive evidence.

## Non-negotiable gate

Before accepting any report as documentary evidence:

- The JSON must pass `validate_aeat_hermes_report.py`.
- The JSON must pass `audit_aeat_hermes_integration.py`.
- Every retained `official_source_claim` must map to an official source URL,
  locator and excerpt.
- MCP/API observations may explain ESData state, but they cannot justify an
  official claim.
- Technical designs, XSD, WSDL, endpoints, filenames, cached resources and BOE
  publication dates cannot prove active campaign by themselves.
- `proves_campaign=true` is allowed only when the cited official text binds the
  model to an exercise, campaign or reporting period.
- No write to DB, no `resolved_strong`, and no
  `ASSERTABLE_DIRECT_OFFICIAL` promotion is allowed from this checklist alone.

## Review outputs

Each model review must end in exactly one of these outcomes:

- `accept_as_conflict_evidence`: claims are traceable and useful, but campaign
  remains non-assertable.
- `accept_as_stale_suspected_evidence`: evidence shows old persisted campaign
  is likely stale, but does not prove current campaign.
- `needs_report_rewrite`: useful direction, but claims need primary URL,
  locator or excerpt fixes before repository evidence.
- `reject_report`: hallucinated, untraceable or mixed-layer claims contaminate
  the report.

## Automatic rejection

Reject the report immediately if any of these conditions is true:

- A retained `official_source_claim` has no primary URL.
- A retained `official_source_claim` has no locator or only a vague locator
  such as "AEAT page" or "BOE".
- A retained `official_source_claim` has no excerpt.
- A retained `official_source_claim` mentions MCP/API/cache/internal metadata as
  the basis for an official claim.
- A retained `official_source_claim` cites a norm, order, regulation or URL
  that is not present in `official_sources`.
- A report states or implies active campaign while
  `campana_safe_to_assert=false`.
- A report sets or suggests `proves_campaign=true` from a filename, technical
  design year, XSD/WSDL, endpoint, BOE publication date, cached association or
  internal ESData field.
- A `derived_claim` or `system_observed_claim` has
  `may_assert_campaign=true`.
- The final outcome is `accept_as_stale_suspected_evidence` without naming the
  exact accepted claim that proves staleness.

When automatic rejection triggers, do not partially accept the report. Return
`reject_report` or `needs_report_rewrite`, depending on whether the problem is
contamination or missing traceability.

## Shared claim checklist

For each `official_source_claim`:

- [ ] Source URL is primary AEAT/BOE or other whitelisted official source.
- [ ] Locator points to a concrete section, table, row, heading or document
      part.
- [ ] Excerpt is present and supports the exact claim.
- [ ] Claim does not use `MCP`, `metadata`, `cacheado`, `modelo_recurso`,
      `campana_activa` or internal ESData state as evidence.
- [ ] Claim scope is correctly limited: campaign, technical coverage, legal
      basis, form existence, filing channel or design fields.
- [ ] `proves_campaign=false` unless the official text explicitly binds model
      and exercise/campaign/period.

For each `rejected_claim`:

- [ ] The rejected claim is plausible enough to document.
- [ ] The rejection reason is specific.
- [ ] The rejected claim cannot be reconstructed as an assertion elsewhere in
      the report.

For each `derived_claim`:

- [ ] It is clearly marked as inference.
- [ ] It depends only on accepted official claims or accepted system
      observations.
- [ ] It keeps `may_assert_campaign=false`.

## Model 210

Current audit result:

- JSON path on VPS:
  `/srv/esdata/hermes-curator/reports/aeat-campaign-curation-json/modelo-210-20260527-071917.json`
- `decision=CONFLICT`
- `campana_safe_to_assert=false`
- `campana_assertion_code=NOT_ASSERTABLE_CONFLICT`
- `official_claims=4`
- `official_claims_proving_campaign=0`
- `recommended_state=conflict`

Human review focus:

- [ ] Replace any wording equivalent to "official active cached resource" with
      the real official URL and locator.
- [ ] Verify whether `AEAT_GF00` proves only model/procedure existence, not
      active campaign.
- [ ] Verify whether `AEAT_CODPAISES` is only auxiliary technical support and
      cannot prove campaign.
- [ ] Verify whether `AEAT_DR210_2026` proves only technical design coverage
      for devengos from `01-01-2026`, not obligation, filing window or active
      campaign.
- [ ] Verify whether `BOE_NORM_2010_19707` is legal basis only and does not
      specify active campaign.
- [ ] Keep `proves_campaign=false` unless official text explicitly links model
      210 and campaign/exercise/period as current.

Expected outcome unless stronger evidence is found:

```text
accept_as_conflict_evidence
recommended_state=conflict
campana_safe_to_assert=false
```

## Model 128

Current audit result:

- JSON path on VPS:
  `/srv/esdata/hermes-curator/reports/aeat-campaign-curation-json/modelo-128-20260527-072022.json`
- `decision=CONFLICT`
- `campana_safe_to_assert=false`
- `campana_assertion_code=NOT_ASSERTABLE_CONFLICT`
- `official_claims=4`
- `official_claims_proving_campaign=0`
- `recommended_state=conflict`

Human review focus:

- [ ] Remove or reject any norm reference not present in the cited official
      sources, especially references equivalent to `RDL 20/2012` or
      `Orden HAC/2110/2003` if they are not directly cited in the report.
- [ ] Verify whether `AEAT_GH07` proves only model/procedure existence and
      periodicity, not active campaign.
- [ ] Verify whether `BOE_EHA_2007` is legal basis only and does not prove
      current campaign.
- [ ] Verify whether `AEAT_DR_128_2020` proves only technical coverage
      `Ejercicios 2020 y siguientes`, not active campaign.
- [ ] Verify whether design-field claims are structural only and should remain
      non-assertive.
- [ ] Keep `proves_campaign=false` unless official text explicitly links model
      128 and campaign/exercise/period as current.

Expected outcome unless stronger evidence is found:

```text
accept_as_conflict_evidence
recommended_state=conflict
campana_safe_to_assert=false
```

## Model 113

Current audit result:

- JSON path on VPS:
  `/srv/esdata/hermes-curator/reports/aeat-campaign-curation-json/modelo-113-20260527-080123.json`
- `decision=CONFLICT`
- `campana_safe_to_assert=false`
- `campana_assertion_code=NOT_ASSERTABLE_CONFLICT`
- `official_claims=4`
- `official_claims_proving_campaign=0`
- `recommended_state=conflict`

Human review focus:

- [ ] Ensure the rendered report body includes primary URLs explicitly, not
      only source IDs.
- [ ] Verify whether `AEAT_G614` proves only model/procedure existence for
      Modelo 113.
- [ ] Verify whether `AEAT_113_AYUDA` is only technical or presentation help
      and cannot prove active campaign.
- [ ] Verify whether `AEAT_DR113E16` proves only technical coverage for
      `ejercicios 2016 y siguientes`, not active campaign.
- [ ] Verify whether `AEAT_OV16_M113` proves only form/channel existence, not
      active campaign.
- [ ] Keep `proves_campaign=false` unless official text explicitly links model
      113 and campaign/exercise/period as current.

Expected outcome unless stronger evidence is found:

```text
accept_as_conflict_evidence
recommended_state=conflict
campana_safe_to_assert=false
```

## Acceptance record template

Use this block when a human finishes a model review:

```text
model_code:
reviewed_at:
reviewer:
json_report:
validation_result:
admission_result:
automatic_rejection_checked: true|false
automatic_rejection_reason: none|<reason>
accepted_official_claims:
  - claim_id_or_source_id:
    source_url:
    locator:
    excerpt:
    accepted_scope: campaign|technical_coverage|legal_basis|form_existence|filing_channel|design_fields
    proves_campaign: true|false
    acceptance_reason:
rejected_official_claims:
  - claim_id_or_source_id:
    rejection_reason:
    corrective_action: remove|rewrite_with_primary_source|move_to_derived_claim|move_to_system_observed_claim
accepted_derived_claims:
  - claim:
    input_claim_ids:
    acceptance_reason:
rejected_claims_reviewed:
  - claim:
    rejection_reason_is_sufficient: true|false
final_outcome:
recommended_state:
campana_safe_to_assert:
campana_assertion_code:
proves_campaign_claims_count:
requires_json_rewrite: true|false
notes:
```

Minimum acceptance requirements:

- `automatic_rejection_checked=true`.
- `automatic_rejection_reason=none`.
- `accepted_official_claims` lists every retained official claim.
- Every accepted official claim has `accepted_scope` and `acceptance_reason`.
- `proves_campaign_claims_count=0` unless the official excerpt explicitly
  binds model and exercise/campaign/period.
- If `final_outcome=accept_as_stale_suspected_evidence`, at least one accepted
  official claim must have `accepted_scope=technical_coverage` and explain why
  the persisted campaign is stale but not assertable.
- If any required field is missing, the only allowed outcome is
  `needs_report_rewrite`.
