# Sprint J CRS/Modelo 289 Report

Fecha: 2026-05-18

Rama: `feat/sprint-j-crs-289`

## Resultado

Sprint J completa la brecha CRS/Modelo 289 detectada en produccion. El modelo ya existia y las obligaciones de perfil estaban verificadas, pero faltaban instrucciones, reglas, keywords y estructura CRS suficiente para responder consultas operativas.

## Identificadores

| elemento | valor |
|----------|-------|
| aeat_modelo.codigo | 289 |
| aeat_modelo.id | 95 |
| modelo_campana.id | 95 |
| campana | 2025 |

## Conteos finales VPS

| area | conteo |
|------|--------|
| normativa | 4 |
| instrucciones | 5 |
| reglas_inclusion | 6 |
| trigger_keywords | 12 |
| casillas | 161 |
| obligaciones perfil verificadas | 4 |

## Normativa cargada

- Orden HAC/1150/2024, ya existente.
- RD 1021/2015, CRS cuentas financieras.
- Ley 58/2003 General Tributaria, Disposicion adicional 22.
- Directiva 2014/107/UE DAC2, CELEX `32014L0107`.

## Instrucciones cargadas

- Determinacion de Institucion Financiera Obligada.
- Cuenta financiera reportable.
- Plazo de presentacion anual, enero a mayo.
- Declaracion negativa `NilReport` con `CRS704`.
- Correcciones y cancelaciones con `CRS701`, `CRS702` y `CRS703`.

## Reglas cargadas

Inclusiones:

- Entidad de custodia.
- Entidad de deposito.
- Entidad de inversion.

Exclusiones:

- Entidad gubernamental, organizacion internacional o banco central.
- Entidad no financiera activa.
- Cuenta preexistente de entidad bajo umbral de minimis de 250.000 USD.

## Contrato API/MCP

- `buscar_modelos_aeat_catalogo` ahora expone `reglas_inclusion_count`.
- El catalogo AEAT sigue sin devolver `obligation_context`; la obligatoriedad por perfil permanece en `obtener_obligaciones_perfil`.
- `mcp_validation_suite.py` valida los conteos CRS/289, `NilReport`, exclusiones y obligaciones de perfil.
- `mcp_deep_contract_audit.py` valida el contrato de catalogo para `codigo=289`.

## Verificacion

- Local: `pytest apps/ -q --basetemp .pytest-tmp` => `3124 passed`.
- VPS: `mcp_validation_suite.py --read-only --base-url http://api:8000` => `ok=true`.
- VPS: `mcp_deep_contract_audit.py --base-url http://api:8000` => `ok=true`.
- VPS `/status`: `api=ok`, `database=ok`.
- Alertmanager: 0 alertas activas.

## Notas de entorno

Las suites MCP se ejecutaron en VPS contra corpus completo, despues de aplicar seeds J-01 a J-06 y reconstruir `api`/`ops`. La DB local no se usa como fuente de verdad para cierre de sprint de corpus.
