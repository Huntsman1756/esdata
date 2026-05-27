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

Evidence admission command:

```bash
python scripts/maintenance/audit_aeat_hermes_integration.py <report.json>
```

Batch adjudication command:

```bash
python scripts/maintenance/adjudicate_aeat_hermes_batch.py --verify-sources --latest-per-model --history-dir <metrics-dir> <reports-dir-or-json>
```

Trend summary command:

```bash
python scripts/maintenance/summarize_aeat_adjudication_history.py <metrics-dir>
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
6. `official_sources.excerpt` may not contain internal system terms such as
   "cache", "metadata", "MCP", "ESData", `modelo_recurso`,
   `campana_activa` or `campana_persistida`.
7. `official_sources` should contain only sources referenced by at least one
   `official_source_claim`, unless the report has no official claims.
8. Technical designs, XSD, WSDL, filenames and endpoints may only prove
   technical coverage when the official source says so. They do not prove
   active campaign, obligation, filing window or general applicability.
9. Transactional AEAT form URLs such as `www1.agenciatributaria.gob.es/wlpl/OV16-*`
   are not valid official evidence sources for this contract.
10. `derived_claims` and `system_observed_claims` must keep
   `may_assert_campaign=false`.
11. `human_review_required` must always be `true`.
12. `decision=ASSERTABLE` is valid only when the assertion gate is satisfied:
   `campana_safe_to_assert=true`, `campana_afirmable!=null` and
   `campana_assertion_code=ASSERTABLE_DIRECT_OFFICIAL`.

## Integrability

A conforming JSON report is still a review artifact, not a production write.
Promotion to `resolved_strong` remains a human decision governed by
`docs/aeat/curation-rules.md` and `docs/aeat/precision-contract.md`.

`integrable=true` in `audit_aeat_hermes_integration.py` means only that the
report contains traceable official-source claims that a human can review. It
does not authorize writes to production, assertion fields, or campaign
promotion.

Minimum admission rules:

1. Schema validity is required but is not sufficient.
2. At least one `official_source_claim` is required.
3. `ASSERTABLE` reports are not admissible unless the direct official assertion
   gate is satisfied.
4. `resolved_strong` is only a recommendation when the direct official gate is
   satisfied and at least one official claim has `proves_campaign=true`.
5. `CONFLICT`, `STALE_SUSPECTED`, `INSUFFICIENT_EVIDENCE` and `UNKNOWN` remain
   non-assertable even when their reports are integrable for human review.

## Batch Adjudication

Human review is not required model-by-model for non-assertive evidence. The
batch adjudicator may automatically route validated reports when it can verify
source traceability mechanically.

`adjudicate_aeat_hermes_batch.py --verify-sources`:

- validates the Hermes JSON contract;
- runs the evidence admission audit;
- fetches official source URLs;
- verifies that each source excerpt appears in the fetched official content;
- can suggest a replacement excerpt from the official content when Hermes used
  a non-literal title or paraphrase;
- only blocks source verification failures for sources referenced by
  `official_source_claims`;
- treats binary official files (`.pdf`, `.xls`, `.xlsx`, `.zip`) as reachable
  sources only, not literal-text proof;
- rejects vague locators and mixed MCP/API/cache evidence;
- never writes production data;
- never promotes `resolved_strong`.

Allowed automatic outcomes:

- `auto_accept_conflict_evidence`: conflict evidence is traceable and remains
  non-assertive.
- `auto_accept_stale_suspected_evidence`: stale evidence is traceable and
  remains non-assertive.
- `auto_accept_nonassertable_evidence`: evidence is traceable but does not
  assert campaign.

Human review remains mandatory only for:

- `human_review_assertable_candidate`;
- `needs_report_rewrite`;
- `reject_report`.

The batch output includes `metrics` so the system can be monitored without
reading every report:

- `auto_accepted_total`;
- `human_review_required_total`;
- `rewrite_or_reject_total`;
- `assertable_candidates_total`;
- `repaired_excerpts_total`;
- `unused_source_warnings_total`;
- `blocking_errors_total`.

It also includes `run_metadata` with:

- execution timestamp;
- adjudicator version;
- current Git head when available;
- selected report count;
- schema version and SHA-256;
- prompt SHA-256;
- adjudicator SHA-256;
- persisted history path when `--history-dir` is used.

Primary dashboard:

- `repaired_excerpt_ratio`;
- `rewrite_ratio`;
- `blocking_error_ratio`;
- `unused_source_warning_ratio`;
- `assertable_candidate_ratio`.

Trend alerts:

- `blocking_error_ratio > 0`: critical alert. The batch produced blocking
  errors and must not be treated as healthy.
- `rewrite_ratio > 0.10`: warning. Prompt, extractor or source traceability may
  be degrading.
- `repaired_excerpt_ratio > 1.0`: warning. Hermes still depends heavily on
  automatic excerpt repair.
- `unused_source_warning_ratio > 0.20`: warning. Source selection may be noisy
  or too broad.
- `assertable_candidate_ratio > 0`: warning. Assertable candidates are not bad
  by themselves, but they require human review before any promotion.

Drilldown is exposed under `metrics.drilldown` and should only be used when
aggregate ratios degrade.

`auto_accept_*` means admission to a draft/review bucket. It is not canonical
evidence, not a database write and not campaign resolution.
