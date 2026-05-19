# Sprint K - DORA RTS/ITS operativo

Fecha: 2026-05-19

## Resultado

Sprint K carga y operacionaliza los primeros RTS DORA confirmados en EUR-Lex y completa la cobertura de obligaciones DORA por perfil.

Normas DORA:

| CELEX | Estado | Uso |
|---|---|---|
| 32022R2554 | ya cargada | DORA base |
| 32024R1774 | cargada | RTS marco de gestion del riesgo TIC y marco simplificado |
| 32024R1773 | cargada | RTS acuerdos contractuales con terceros TIC |

La entrada debil `DORA_2022_2535` fue eliminada tras confirmar que no tenia referencias en `obligacion_perfil` ni `obligacion_fuente`.

## Obligaciones

Conteo final VPS:

| Perfil | DORA rows | Verified | Completeness |
|---|---:|---:|---|
| agencia_valores | 5 | 5 | completa |
| eaf | 4 | 4 | parcial |
| empresa_servicios_pago | 3 | 3 | completa/parcial |
| entidad_credito | 5 | 5 | completa/parcial |
| sgiic | 3 | 3 | completa |
| sociedad_valores | 3 | 3 | completa |

Cambios principales:

- `agencia_valores`: nuevas obligaciones DORA art. 5, art. 19 y art. 24.
- `eaf`: nuevas obligaciones DORA art. 5 y art. 19 con condicion microempresa DORA art. 2.3; todas `completeness=parcial`.
- Todos los perfiles: art. 28 registro de terceros TIC y art. 30 clausulas contractuales minimas.
- Se eliminaron rangos en obligaciones DORA: `arts. 5-16`, `arts. 17-23`, `arts. 26-27` pasan a anclas `art. 5`, `art. 19` y `art. 26`.

## Verificacion VPS

- `norma` con `32024R1774` y `32024R1773`: `2`.
- `DORA_2022_2535`: `0`.
- Rangos DORA restantes: `0`.
- `obligacion_perfil`: `168/168 verified`.
- `mcp_validation_suite.py --read-only --base-url http://api:8000`: `ok=true`.
- `mcp_deep_contract_audit.py --base-url http://api:8000`: `ok=true`.

## Decision de alcance

No se cargaron CELEX no confirmados como DORA. `32024R2555` y `32024R1782` existen en EUR-Lex pero no son DORA; `32024R2554`, `32024R2556` y `32024R2553` no resolvieron como documentos EUR-Lex validos durante la verificacion previa.
