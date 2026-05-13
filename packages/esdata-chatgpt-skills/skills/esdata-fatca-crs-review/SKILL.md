---
name: esdata-fatca-crs-review
description: Review FATCA, CRS, DAC2, Modelo 289, Modelo 290, reportable accounts, US persons, non-resident clients, and financial institution reporting questions using only ESData MCP evidence. Use when a user asks how to present FATCA/CRS, which clients are affected, or whether ESData evidence is partial.
---

# ESData FATCA CRS Review

Use this skill for FATCA/CRS questions. It must be conservative because ESData may have official references while still lacking complete procedural instructions.

## Workflow

1. Identify whether the user asks about FATCA, CRS/DAC2, or both.
2. Collect facts: reporting financial institution, account type, account holder residence, US indicia, controlling persons, period, and whether the query is about model inventory or filing procedure.
3. Query ESData for Modelos 289/290 and international obligations.
4. If ESData returns `verified=false` or `completeness=parcial`, answer as evidence-limited.
5. Do not describe full filing mechanics unless ESData returns official procedural evidence.

## Client Impact Classification

Use these labels:

- `confirmado`: ESData explicitly identifies the affected client/account class.
- `candidato`: ESData identifies a related reporting regime/model but not the specific client condition.
- `requiere verificacion`: missing account classification, residence, indicia, controlling person, or procedure evidence.

## Red Lines

- Do not explain IRS Form 8938, W-8/W-9 mechanics, XML filing, nil returns, thresholds, or due diligence steps unless ESData evidence supports them.
- Do not convert Modelo 289/290 existence into a filing obligation.
- Do not use general web search as evidence.

## Output

```text
Regimen: FATCA / CRS / ambos.
Estado ESData: <verified/completeness/review_required>.

| regimen | modelo/referencia | clientes afectados segun evidencia | clasificacion | fuente |

Respuesta:
- Confirmado por ESData: ...
- Razonamiento del agente: ...
- Evidencia limitada / faltante: ...
- Gate: revisar antes de reportar o comunicar a clientes.
```
