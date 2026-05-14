---
name: esdata-sociedad-valores-review
description: Analyze Spanish sociedad de valores compliance questions with ESData MCP evidence, including AEAT models, resident/non-resident clients, capital mobiliario, IRNR, CNMV, MiFID II, FATCA/CRS, KYC/AML, BORME, and regulatory source traceability. Use when the user asks what applies to a sociedad de valores or wants a professional review without invented obligations.
---

# ESData Sociedad de Valores Review

Use this skill for Spanish investment firm / sociedad de valores questions. It combines legal cold-start, financial-services KYC gating, and ESData's hard truth contract.

## Cold Start

Ask only missing facts that change the answer:

- CNMV authorization type and services performed.
- Client residence: Spain, EU/EEE, third country, US person, CRS reportable jurisdiction.
- Product/instrument: listed securities, IIC, derivatives, deposits, crypto, fund shares.
- Transaction/income: dividends, interest, transmission, redemption, custody, advisory, execution.
- Role: payer, intermediary, account holder institution, reporting financial institution, tax withholder.
- Period and campaign year.

## Review Areas

1. AEAT models and casillas.
2. Withholding and information returns for residents/non-residents.
3. FATCA/CRS reporting signals.
4. CNMV/MiFID II regulatory obligations.
5. EUR-Lex/ESMA market regulation evidence: MiFID II, MiFIR, MiCA, DLT Pilot, ESMA transaction-reporting schemas.
6. KYC/AML evidence gaps.
7. BORME/company evidence, marked partial if heuristic.

## Answer Rules

- Separate ESData evidence from agent reasoning.
- Do not infer obligations from entity type alone.
- Classify models as `confirmado`, `candidato`, or `requiere verificacion`.
- If ESData says `evidence_limited`, keep the conclusion limited.
- For CNMV, check `/v1/cnmv/coverage` before treating a no-result as non-existence.
- For CNMV `vigente_modificado`, do not cite as consolidated current text unless ESData returns `es_consolidado=true`.
- For FATCA passive/active entity questions, use Modelo 290 `reglas_inclusion` before any generic tax-model classification.
- For ESMA reporting, use XSD/schema fields as authoritative only for loaded schema scope; FIRDS pilot data remains evidence-limited unless ESData says complete.
- Use a human review gate before client advice, filing, reporting, or regulatory submissions.

## Do Not Use When

- The user wants investment advice, portfolio recommendations, suitability conclusions, or order execution decisions.
- The question is about a non-Spanish financial entity and ESData has no loaded source for that jurisdiction.
- The user asks for a definitive obligation while material facts such as role, product, residence, or period are missing.
- The answer depends on live CNMV/AEAT filing portals rather than ESData's loaded evidence.

## Output

```text
Perfil analizado:
- entidad:
- clientes:
- productos/rentas:
- rol:

Evidencia ESData:
| area | item | clasificacion | condicion | fuente |

Razonamiento del agente:
- ...

No cubierto / contexto faltante:
- ...

Gate:
- Revision profesional requerida antes de presentar, reportar o comunicar conclusion regulatoria.
```
