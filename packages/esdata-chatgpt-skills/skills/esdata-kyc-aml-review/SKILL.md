---
name: esdata-kyc-aml-review
description: Triage KYC, AML, onboarding, sanctions, beneficial ownership, client classification, financial institution, MiFID, FATCA/CRS, and sociedad de valores compliance gaps using ESData MCP evidence. Use when the user wants a rules-grid style review with evidence, missing documents, escalation flags, and no invented regulatory obligations.
---

# ESData KYC AML Review

Use this skill for onboarding and AML/KYC triage. It adapts financial-services rules-grid patterns while keeping ESData as the evidence layer.

## Workflow

1. Identify client/entity, jurisdiction, product/service, risk factors, and onboarding stage.
2. Inventory supplied documents and missing facts.
3. Query ESData for regulatory references, sanctions/OFAC if loaded, FATCA/CRS, CNMV/MiFID, AEPD/privacy, and BOE/EUR-Lex context.
4. Build a rules grid:
   - requirement or risk area;
   - evidence received;
   - ESData source;
   - gap;
   - severity;
   - owner/reviewer.
5. Escalate any high-risk, incomplete, evidence-limited, or non-resident/US-person/CRS-reportable cases.

## Rules

- Do not approve onboarding.
- Do not clear sanctions or AML risk unless the relevant data source is loaded and verified.
- If ESData says a sanctions or KYC domain is `configured_but_unavailable`, state that screening is not covered by ESData.
- Treat BORME extraction as heuristic unless ESData marks it otherwise.
- Keep all conclusions as draft for compliance officer review.

## Output

```text
Cliente/perfil:
- tipo:
- residencia:
- producto:
- riesgo inicial:

Rules grid:
| area | evidencia recibida | evidencia ESData | gap | severidad | accion |

Decision draft:
- proceed / hold / escalate / insufficient evidence

Gate:
- Compliance officer must approve before onboarding or risk acceptance.
```
