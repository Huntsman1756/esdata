# Sprint L - CNMV calidad y aplicabilidad

Fecha: 2026-05-19
Rama: `feat/sprint-l-cnmv-calidad`

## Resultado

Sprint L completa el trabajo de calidad sobre el corpus CNMV ya cargado. No se crean registros oficiales de entidades ni tablas nuevas de registros; esa familia queda documentada como `configured_but_unavailable` y candidata a Sprint M.

Conteos verificados en VPS:

| Area | Resultado |
|---|---:|
| Filas CNMV en `documento_interpretativo` | 141 |
| Filas CNMV con `sujeto_obligado` | 141 |
| CNMV docs aplicables a `sociedad_valores` | 141 |
| CNMV docs aplicables a `sgiic` | 104 |
| Obligaciones CNMV en `obligacion_perfil` | 6 |
| Links `modelo_normalizado_esi` | 8 |
| MCP tools HTTP | 77 |

## Cambios

- Se anade `documento_interpretativo.sujeto_obligado text[]` mediante migracion Alembic y seed idempotente.
- Se mapean los 141 documentos CNMV a perfiles aplicables, con espejo en `metadata->'sujeto_obligado'`.
- Se cargan obligaciones verificadas para `CNMV_CIRC_1_2013` y `CNMV_CIRC_1_2010` en `sociedad_valores`, `agencia_valores` y `sgiic`.
- Se enlazan los 8 `modelo_esi_cnmv` como `cnmv_obligation_link.tipo_obligacion='modelo_normalizado_esi'`.
- Se anade `GET /v1/cnmv/perfil/{perfil_codigo}` para recuperar documentos supervisores CNMV por perfil.
- Se expone el nuevo tool MCP `obtener_documentos_cnmv_perfil` y se actualiza `docs/openapi-gpt.json`.
- Se amplian `mcp_validation_suite.py` y `mcp_deep_contract_audit.py` con checks CNMV.

## Decision Modelo ESI

Los documentos `modelo_esi_cnmv` no se cargan en `modelo_casilla` ni `modelo_instruccion` en Sprint L. Esas tablas cuelgan de `modelo_campana -> aeat_modelo`; reutilizarlas para CNMV mezclaria formularios AEAT con modelos supervisores CNMV. La decision correcta en este sprint es mantenerlos como documentos CNMV enlazados por `cnmv_obligation_link`.

## Verificacion

- Local focal: `pytest apps/api/tests/test_cnmv_router.py apps/api/tests/test_cnmv_perfil.py -q` -> `10 passed`.
- Local MCP focal: `pytest apps/api/tests/test_mcp_cnmv_tool.py -v` -> `4 passed`.
- Local completo: `pytest apps/ -q --basetemp .pytest-tmp` -> `3131 passed, 2 skipped`.
- VPS: `mcp_validation_suite.py --read-only --base-url http://api:8000` -> `ok=true`.
- VPS: `mcp_deep_contract_audit.py --base-url http://api:8000` -> `ok=true`.
- VPS: `/status` -> `api=ok`, `database=ok`; Alertmanager sin alertas activas.

## Fuera de alcance

- `cnmv_registro_entidad` no se crea.
- Registros oficiales CNMV siguen como `configured_but_unavailable`.
- No se hace scraping/carga de entidades registradas CNMV.
