# AEAT 200/202/303 - saneamiento fail-closed

## Estado

Sprint U sanea obligaciones legacy de `200/202/303` sin intentar cerrar los
modelos como `complete`.

| Modelo | Estado del modelo | Cambio Sprint U | Limite |
| --- | --- | --- | --- |
| `200` | `partial` | Obligaciones legacy sin hash/captura pasan a `partial`, `verified=false`, `safe_to_answer=false` | No se cierra IS anual por casillas/instrucciones |
| `202` | `partial` | Obligaciones legacy sin hash/captura pasan a `partial`, `verified=false`, `safe_to_answer=false` | No se cierra pago fraccionado sin reglas y fuente normalizada por perfil |
| `303` | `partial` | Obligaciones legacy sin hash/captura pasan a `partial`, `verified=false`, `safe_to_answer=false` | No se cierra IVA periodico sin reglas de aplicabilidad |

## Auditoria previa

Produccion antes del cambio:

- `200`: 6807 casillas, 5 instrucciones, 0 reglas; 6 obligaciones de perfil con `safe_to_answer=true` sin `source_hash`.
- `202`: 118 casillas, 0 instrucciones, 0 reglas; 6 obligaciones de perfil con `safe_to_answer=true` sin `source_hash`.
- `303`: 432 casillas, 5 instrucciones, 0 reglas; 5 obligaciones de perfil con `safe_to_answer=true` sin `source_hash`.

La API ya degradaba `obligation_context` al construir la respuesta. Sprint U
alinea la base de datos para que el estado persistido no contradiga el contrato
fail-closed.

## Reglas

- No promover `200`, `202` ni `303` a `complete`.
- No crear obligaciones nuevas.
- No tocar `349` ni `390`.
- No usar casillas, instrucciones o fichas de modelo como prueba de obligacion
  segura por perfil.
- `safe_to_answer=true` en `obligacion_perfil` requiere fuente normalizada con
  `source_hash` y `capture_date`.

## Validacion esperada

- DB: `unsafe_200_202_303 = 0`.
- API: `obligation_context` no contiene contextos seguros sin hash/captura.
- `/v1/modelos/aeat/200`, `/202` y `/303` siguen `partial`.
- `349` y `390` quedan fuera del cambio.
