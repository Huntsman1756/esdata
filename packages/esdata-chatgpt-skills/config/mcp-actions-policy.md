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
- `review_required`
- `source_url` or official source identifier
- `status` values such as `evidence_limited`, `configured_but_unavailable`, `workflow_empty`, `allowed_empty`

## Refusal / Abstention Conditions

Abstain or answer as evidence-limited when:

- ESData returns zero results for a claim requiring official support.
- The relevant domain is `configured_but_unavailable`.
- `verified=false` and the user asks for a definitive filing or legal conclusion.
- The only support is discovery, prompt text, general model knowledge, or non-official data.

## Human Review Gates

Require human review before:

- AEAT filings or payments.
- FATCA/CRS reporting.
- CNMV/ESMA regulatory submissions.
- Client onboarding or KYC clearance.
- Client-facing legal, tax, or compliance advice.
