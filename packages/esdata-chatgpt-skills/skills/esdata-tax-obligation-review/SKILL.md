---
name: esdata-tax-obligation-review
description: Review Spanish tax filing, AEAT model, casilla, withholding, IRPF, IS, IVA, IRNR, and tax obligation questions using ESData MCP evidence. Use when the user asks which Hacienda model applies, how to classify AEAT models/casillas, whether something is obligatory, or why ESData gave partial or conflicting tax answers.
---

# ESData Tax Obligation Review

Use ESData as the only evidence source unless the user explicitly allows external sources. This skill adapts the legal human-review and cold-start patterns to Spanish tax workflows.

## Workflow

1. Restate the requested obligation or inventory.
2. Gather minimum context before concluding: taxpayer/entity type, residence, transaction, income type, period, role as payer/withholder/intermediary, and whether the user asks for applicability or just model/casilla inventory.
3. Query ESData with narrow structured prompts or endpoints.
4. Classify each returned model/casilla:
   - `confirmado`: directly returned for the requested inventory or verified source.
   - `candidato`: relevant to the fact pattern but not explicit enough for obligation.
   - `requiere verificacion`: partial, weak, deprecated, missing condition, or incomplete evidence.
5. Explain conditions without converting them into obligations.
6. Add a review gate before filing or relying on the answer.

## Hard Rules

- Do not say "debe presentar" unless ESData returns explicit evidence for that entity and fact pattern.
- For casillas, distinguish "casilla exists in Modelo X" from "casilla must be filled".
- For `completeness=parcial`, say "evidencia limitada" and refuse complete filing instructions.
- If ESData returns no relevant evidence, abstain instead of using tax memory.
- Do not use SearXNG, search results, or a skill checklist as authority.

## Output Shape

```text
Fuente: ESData MCP.
Contexto usado: <facts supplied>.
Contexto faltante: <facts needed, if any>.

| modelo/casilla | clasificacion | condicion de aplicacion | evidencia ESData |

Conclusion:
- Dato confirmado: ...
- Razonamiento del agente: ...
- Gate: revisar antes de presentar o confiar fiscalmente.
```

Read `references/tax-review-patterns.md` for common AEAT evidence traps.
