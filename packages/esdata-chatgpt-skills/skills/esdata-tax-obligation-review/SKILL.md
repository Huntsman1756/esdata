---
name: esdata-tax-obligation-review
description: Review Spanish tax filing, AEAT model, casilla, claves/subclaves, instructions, withholding, IRPF, IS, IVA, IRNR, FATCA Modelo 290, and tax obligation questions using ESData MCP evidence. Use when the user asks which Hacienda model applies, how to classify AEAT models/casillas, whether something is obligatory, how to fill a model field, or why ESData gave partial or conflicting tax answers.
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
6. When the question is about "que clave", "como rellenar" or "incluir/no incluir", inspect `claves`, `instrucciones`, and `reglas_inclusion` before answering.
7. Add a review gate before filing or relying on the answer.

## Hard Rules

- Do not say "debe presentar" unless ESData returns explicit evidence for that entity and fact pattern.
- For casillas, distinguish "casilla exists in Modelo X" from "casilla must be filled".
- For `completeness=parcial`, say "evidencia limitada" and refuse complete filing instructions.
- If `claves` or `instrucciones` are empty, say that ESData has field inventory only and cannot answer the procedural question.
- If `reglas_inclusion` are present, use them for include/exclude/conditional decisions and cite `fuente_normativa`.
- If ESData returns no relevant evidence, abstain instead of using tax memory.
- Do not use SearXNG, search results, or a skill checklist as authority.

## Current Tax Notes

- TRLIRNR is loaded and can be queried through `TRLIRNR` or `IRNR`; use it for IRNR references before falling back to generic search.
- Priority AEAT models may now expose instructions/keys: 187, 193, 198, 216, 290 and 296 can be `completa`; 200 and 303 may still have partial instructions.
- Modelo 290 FATCA has dedicated inclusion rules. Do not route FATCA passive entity questions to IRNR 216/296 unless ESData explicitly returns those models for the same FATCA claim.
- `casillas_total` confirms field inventory, not taxpayer applicability.

## Do Not Use When

- The user asks for general tax education without ESData evidence requirements.
- The user asks you to complete or submit a filing; this skill can only prepare a review draft.
- The answer would require private client records not provided in the conversation.
- ESData has no relevant source loaded and the user has not allowed external verification.

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
