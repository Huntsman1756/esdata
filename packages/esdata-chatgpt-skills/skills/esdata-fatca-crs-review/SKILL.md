---
name: esdata-fatca-crs-review
description: Review FATCA, CRS, DAC2, Modelo 289, Modelo 290, reportable accounts, US persons, passive/active NFFE, controlling persons, non-resident clients, and financial institution reporting questions using only ESData MCP evidence. Use when a user asks how to present FATCA/CRS, which clients are affected, or whether ESData evidence is partial.
---

# ESData FATCA CRS Review

Use this skill for FATCA/CRS questions. It must be conservative: ESData can now expose Modelo 290 instructions, keys and inclusion rules, but only returned ESData fields are evidence.

## Workflow

1. Identify whether the user asks about FATCA, CRS/DAC2, or both.
2. Collect facts: reporting financial institution, account type, account holder residence, US indicia, controlling persons, period, and whether the query is about model inventory or filing procedure.
3. Query ESData for Modelos 289/290, `claves`, `instrucciones`, `reglas_inclusion`, and international obligations.
4. For FATCA/passive NFFE, route first to Modelo 290. Do not let generic IRNR matches override FATCA evidence.
5. If ESData returns `verified=false`, `completeness=parcial`, or `safe_to_answer=false`, answer as evidence-limited.
6. Do not describe full filing mechanics unless ESData returns official procedural evidence.

## Client Impact Classification

Use these labels:

- `confirmado`: ESData explicitly identifies the affected client/account class.
- `candidato`: ESData identifies a related reporting regime/model but not the specific client condition.
- `requiere verificacion`: missing account classification, residence, indicia, controlling person, or procedure evidence.

## Modelo 290 Handling

- Use `reglas_inclusion` for include/exclude/conditional decisions.
- If a rule mentions passive NFFE, controlling persons, substantial owner, US person, or active NFFE, quote the returned rule and `fuente_normativa`.
- Do not add a percentage threshold, XML rule, nil-return rule, or due-diligence step unless ESData returns it.
- If ESData has a rule but material facts are missing, classify as `requiere verificacion`, not `confirmado`.

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
