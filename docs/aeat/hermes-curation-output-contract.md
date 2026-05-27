# Hermes AEAT curation output contract

Hermes outputs are not evidence unless they conform to this contract. The
contract is intentionally stricter than a markdown report: it forces Hermes to
separate system telemetry from official documentary evidence.

Canonical schema:

```text
docs/aeat/hermes-curation-output.schema.json
```

Validation command:

```bash
python scripts/maintenance/validate_aeat_hermes_report.py <report.json>
```

## Layer Separation

Hermes must emit structured JSON with these layers:

- `mcp_observations`: facts observed from MCP/API. These are system telemetry,
  not documentary truth.
- `official_sources`: official AEAT/BOE/EUR-Lex/ESMA/CNMV sources with URL,
  localizable section and excerpt.
- `official_source_claims`: only claims that map 1:1 to one official source
  and one literal or structural locator.
- `derived_claims`: explicit inferences from other claims. They may help human
  review, but they never assert campaign.
- `system_observed_claims`: claims about what ESData/MCP currently reports.
  They never assert campaign.
- `rejected_claims`: plausible claims that must not be made.

## Hard Rules

1. MCP is not evidence. If a claim is only present in MCP, it is a
   `system_observed_claim`.
2. An `official_source_claim` must reference an `official_sources.source_id`.
3. Official source URLs must use an approved official domain.
4. Each official source must include a localizable `locator` and non-empty
   `excerpt`.
5. `official_source_claims` may not cite "cache", "metadata", "MCP says" or
   internal ESData wording as evidence.
6. Technical designs, XSD, WSDL, filenames and endpoints may only prove
   technical coverage when the official source says so. They do not prove
   active campaign, obligation, filing window or general applicability.
7. `derived_claims` and `system_observed_claims` must keep
   `may_assert_campaign=false`.
8. `human_review_required` must always be `true`.
9. `decision=ASSERTABLE` is valid only when the assertion gate is satisfied:
   `campana_safe_to_assert=true`, `campana_afirmable!=null` and
   `campana_assertion_code=ASSERTABLE_DIRECT_OFFICIAL`.

## Integrability

A conforming JSON report is still a review artifact, not a production write.
Promotion to `resolved_strong` remains a human decision governed by
`docs/aeat/curation-rules.md` and `docs/aeat/precision-contract.md`.
