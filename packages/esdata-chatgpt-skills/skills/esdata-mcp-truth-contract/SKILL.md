---
name: esdata-mcp-truth-contract
description: Enforce ESData MCP truth contracts in legal, tax, regulatory, financial, KYC, FATCA/CRS, BOE, AEAT, CNMV, EUR-Lex, ESMA, AEPD, BORME, and compliance answers. Use when an agent must separate official ESData evidence from LLM reasoning, classify answers by verified/completeness, avoid invented obligations, and apply human review gates before filing, sending, or relying on a conclusion.
---

# ESData MCP Truth Contract

Use this skill whenever ESData MCP is the evidence source. The goal is to keep a hard boundary between official retrieved data and agent reasoning.

## Core Rule

Treat ESData as the evidence layer, not as a reasoning shortcut.

- Report what ESData returned: `verified`, `completeness`, `source_url`, `boe_reference`, `review_required`, `evidence_limited`, `configured_but_unavailable`.
- Label your own inference separately as agent reasoning.
- Never turn a prompt, checklist, web search, SearXNG result, or skill instruction into evidence.
- Never say "obligatorio", "debe presentar", "plazo definitivo", or "aplica" unless ESData returns explicit evidence for that claim.
- If evidence is partial, say so before the conclusion.

## Contract Mapping

| ESData contract | How to answer |
|---|---|
| `verified=true`, `completeness=completa` | Treat the returned record as authoritative for its loaded scope. |
| `verified=true`, `completeness=no-casillas-expected` | Treat absence of casillas as verified by design, not as missing data. |
| `verified=true`, `completeness=deprecated` | State that the model or record is deprecated or no longer current. |
| `verified=false`, `completeness=parcial` | Say "evidencia limitada"; do not present procedural or obligation claims as complete. |
| `configured_but_unavailable` | Domain is known but no usable data is loaded; abstain from substantive answer. |
| `workflow_empty` or `allowed_empty` | Explain that this is expected empty state, not evidence for the legal conclusion. |

## Workflow

1. Identify the user's exact claim request.
2. Query ESData or inspect the ESData response supplied by the user.
3. Extract only evidence-bearing fields and citations.
4. Classify every output item as `confirmado`, `candidato`, or `requiere verificacion`.
5. Ask for missing factual context if a legal/tax conclusion depends on it.
6. Add a human review gate before filing, submitting, sending, or relying on a conclusion.

## Output Template

```text
Fuente usada: ESData MCP.
Estado de evidencia: <verified/completeness/review_required>.

Dato ESData:
- <claim> -> <source_url or boe_reference> -> <contract state>

Clasificacion:
| item | clasificacion | condicion | evidencia |

Razonamiento del agente:
- <inference, clearly labeled>

Gate:
- No presentar/enviar/depender de esta conclusion sin revision profesional si review_required=true o evidence_limited.
```

Read `references/esdata-contract.md` when the answer spans multiple domains or partial data.
