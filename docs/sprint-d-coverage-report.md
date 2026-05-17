# Sprint D Coverage Report - ESMA/ESRB EU Regulations

Fecha: 2026-05-17.

Fuente de evidencia: SQL en VPS contra Postgres de produccion y endpoints API reconstruidos desde `feat/sprint-d-esma-esrb`.

## Resumen

| Indicador | Valor produccion |
|---|---:|
| Normas UE con `celex` y `tipo_norma` | 14 |
| ESMA guidelines (`guideline_esma`) | 4 |
| `obligacion_fuente` total | 131 |
| `sociedad_valores` obligaciones | 28 |
| `sociedad_valores` verified | 20 |
| `sociedad_valores` evidence_limited | 8 |

## Normas UE Cargadas

| norma | celex | tipo | vigente | obligaciones_referenciadas |
|---|---|---|---:|---:|
| 32009L0065 | 32009L0065 | directiva_ue | true | 0 |
| 32011L0061 | 32011L0061 | directiva_ue | true | 3 |
| 32012R0648 | 32012R0648 | reglamento_ue | true | 0 |
| 32013R0231 | 32013R0231 | reglamento_ue | true | 0 |
| 32013R0575 | 32013R0575 | reglamento_ue | true | 2 |
| 32014L0065 | 32014L0065 | directiva_ue | true | 0 |
| 32014R0600 | 32014R0600 | reglamento_ue | true | 2 |
| 32015R2365 | 32015R2365 | reglamento_ue | true | 1 |
| 32017R0565 | 32017R0565 | rts | true | 0 |
| 32017R0571 | 32017R0571 | rts | true | 0 |
| 32017R0590 | 32017R0590 | rts | true | 0 |
| 32019R0834 | 32019R0834 | reglamento_ue | true | 0 |
| 32019R0876 | 32019R0876 | reglamento_ue | true | 0 |
| 32022R2554 | 32022R2554 | reglamento_ue | true | 1 |

## Perfiles

| perfil | obligaciones | verified | evidence_limited |
|---|---:|---:|---:|
| agencia_valores | 26 | 18 | 8 |
| sgiic | 16 | 12 | 4 |
| sociedad_valores | 28 | 20 | 8 |

## Caveats

- SFTR se cargo con CELEX oficial `32015R2365`; el PRD tenia el typo `32019R2365`.
- ESMA product governance se cargo con referencia oficial actual `ESMA35-43-3448`, no la referencia antigua del PRD.
- ESMA liquidity stress testing se cargo con referencia oficial `ESMA34-39-897`.
- Las obligaciones prudenciales CRR de recursos propios referencian `32013R0575`, pero siguen `evidence_limited` hasta fijar articulo exacto.
- TEAC no genero enlaces a normas UE: busqueda estricta por MiFIR/EMIR/DORA/SFTR/CRR y numeros de reglamento devolvio 0 coincidencias reales.

## Verificacion

- Local: `python -m pytest apps/ -q --basetemp .pytest-tmp` => `3090 passed, 2 skipped`.
- VPS: `/status` => `api=ok`, `database=ok`.
- VPS: `/v1/norma/eu` => `10` filas en respuesta paginada del endpoint.
- VPS: `mcp_validation_suite.py --read-only --base-url http://api:8000` => `ok=true`.
- VPS: `mcp_deep_contract_audit.py --base-url http://api:8000` => `ok=true`.
- Alertmanager: `0` alertas activas via `alertmanager` container.
