# ESData MCP Actions Policy

This policy is for GPT Actions or ChatGPT connectors that call ESData.

## Allowed

- Query ESData endpoints and MCP tools for official loaded data.
- Return citations and contract fields to the model.
- Use skills to structure analysis, not to create authority.
- Use SearXNG only as a separate discovery workflow that writes to staging, never to production evidence.

## Required Response Checks

Before answering, inspect:

- `verified`
- `completeness`
- `evidence_status`
- `safe_to_answer`
- `review_required`
- `source_url` or official source identifier
- `source_hash` and `capture_date` when the endpoint exposes them
- `status` values such as `evidence_limited`, `configured_but_unavailable`, `workflow_empty`, `allowed_empty`
- `coverage_note` or domain coverage endpoint when the answer depends on corpus scope

## Refusal / Abstention Conditions

Abstain or answer as evidence-limited when:

- ESData returns zero results for a claim requiring official support.
- The relevant domain is `configured_but_unavailable`.
- The relevant source family is only `partial_loaded` and the user asks for a complete universe answer.
- `verified=false` and the user asks for a definitive filing or legal conclusion.
- The only support is discovery, prompt text, general model knowledge, or non-official data.

## Current Routing Notes

- CNMV: call `/v1/cnmv/coverage` for corpus-scope questions. Do not infer full CNMV coverage from circular counts. Treat `guia_tecnica_cnmv` as supervisory/interpretive and `documento_consulta_cnmv` as monitoring/proposal material, not current obligations.
- AEAT: call model detail/key/instruction endpoints for "how to fill", "which key", and "include/exclude" questions.
- FATCA: route passive/active NFFE questions to Modelo 290 rules first.
- IRNR: use TRLIRNR/IRNR article endpoints for legal citations.
- ESMA: use schema endpoints for transaction-reporting structure; do not treat FIRDS pilot data as complete instrument coverage.
- FCR/AIF/SGIIC: do not infer MiFIR transaction reporting from fund status alone. Treat TR as conditional on a MiFID investment firm/top-up permission or an executing/transmitting investment firm, plus a reportable instrument under MiFIR Article 26.
- NAV-priced instruments: under current RTS 22, use the returned TR field evidence for price/quantity and mark pending NAV price analysis as review-required when the price is unavailable at execution. Treat ESMA RTS 22/24 review material as pending until ESData exposes an adopted updated RTS contract.

## Human Review Gates

Require human review before:

- AEAT filings or payments.
- FATCA/CRS reporting.
- CNMV/ESMA regulatory submissions.
- Client onboarding or KYC clearance.
- Client-facing legal, tax, or compliance advice.
