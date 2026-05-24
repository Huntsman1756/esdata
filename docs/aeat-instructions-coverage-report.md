# AEAT Instructions, Keys & Validation Rules Coverage Report

Date: 2026-05-24

Scope: AEAT priority models enriched with official instructions, keys and inclusion rules. Counts for 216/296 reflect migration `20260524_0088_aeat_irnr_216_296_rules`; older production snapshots before that migration had `0` IRNR inclusion rules.

| codigo | claves | instrucciones | reglas_inclusion | completeness | verified | notes |
|---|---:|---:|---:|---|---|---|
| 187 | 28 | 5 | 0 | completa | true | Official IIC operation/value keys and instruction sections loaded. |
| 193 | 38 | 5 | 0 | completa | true | Official capital mobiliario keys and instruction sections loaded. |
| 198 | 46 | 7 | 0 | completa | true | Official activos financieros keys and instruction sections loaded. |
| 200 | 0 | 5 | 0 | parcial | false | High-value official IS instruction sections loaded; no deterministic clave set loaded in this sprint. |
| 216 | 5 | 6 | 3 | completa | true | Official IRNR retention keys, instruction sections and conditional inclusion/exclusion rules loaded. |
| 290 | 7 | 7 | 5 | completa | true | FATCA keys, instructions, trigger keywords and inclusion rules loaded from official BOE/AEAT sources. |
| 296 | 35 | 8 | 4 | completa | true | Official IRNR annual summary keys, instruction sections and conditional inclusion/exclusion rules loaded. |
| 303 | 0 | 5 | 0 | parcial | false | High-value official IVA instruction sections loaded; model remains partial by contract. |

## Validation Evidence

- Local full suite: `python -m pytest apps/ -q --basetemp .pytest-tmp` -> `3034 passed, 2 skipped, 34 warnings`.
- Production `mcp_validation_suite.py --read-only --base-url http://api:8000` -> `ok=True`, 38 checks.
- Production `mcp_deep_contract_audit.py --base-url http://api:8000` -> `ok=True`, 9 checks.
- Production `/status`: `api=ok`, `database=ok`; every worker in the `workers` object has `stale=false`.
- Production Alertmanager: `0` active alerts.

## Contract Notes

- `completa + verified=true` is only used where casillas, claves and instrucciones are present with source provenance.
- `216` and `296` are complete as AEAT model/form contracts, but model existence does not prove applicability for every IRNR scenario; `obligation_context.safe_to_answer` remains fail-closed for partial obligations or missing hash/capture.
- `200` and `303` intentionally remain `parcial + verified=false`; instructions were improved, but the sprint did not load complete deterministic key/rule coverage for those models.
- FATCA passive queries now route to Modelo 290 and are tested to avoid IRNR cross-domain contamination.
