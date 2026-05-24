# AEAT Modelo 193 - Dividendos E Intereses Residentes

Estado: `implemented_partial`.

Este bloque granulariza el Modelo `193` para rendimientos del capital mobiliario de residentes, empezando por dividendos e intereses. No convierte el modelo en obligacion segura por perfil ni calcula retenciones.

## Estado Real

| pieza | estado | evidencia |
|-------|--------|-----------|
| Modelo 193 | `complete` como formulario/modelo operativo | Casillas, claves, instrucciones y recursos oficiales cargados con hash |
| Dividendos residentes | `partial_traceable` | `PERCEPCION_A` + `NAT_A_02`, con URL, `source_hash` y `capture_date=2026-05-14` |
| Intereses residentes | `partial_traceable` | `PERCEPCION_B` + `NAT_BD_01`, con URL, `source_hash` y `capture_date=2026-05-14` |
| Aplicabilidad por supuesto | `partial` | Depende de pagador, perceptor, tipo de renta, exencion/no sujecion y obligacion concreta de retener |

## Fuentes

- Modelo 193 AEAT, procedimiento GI12.
- Diseno de registro oficial `DR_Modelo_193_2025.pdf`.
- Normativa asociada cargada en produccion con recurso oficial y hash.

## Reglas Persistidas

La migracion `20260524_0090_aeat_193_income_type_rules` persiste dos reglas `CONDICIONAL` en `modelo_regla_inclusion`:

| supuesto | lectura |
|----------|---------|
| `tipo_renta_dividendos_residentes_193` | Requiere doble anclaje `PERCEPCION_A` y `NAT_A_02`. |
| `tipo_renta_intereses_residentes_193` | Requiere doble anclaje `PERCEPCION_B` y `NAT_BD_01`. |

El doble anclaje evita cerrar por una unica etiqueta generica de capital mobiliario.

## API

`GET /v1/modelos/por-supuesto` proyecta evidencia de `modelo_clave` para `193` cuando:

- `tipo_entidad=sociedad_valores`,
- `clientes_residentes=true`,
- `tipo_renta=dividendos` o `tipo_renta=intereses`,
- existen las dos claves oficiales esperadas,
- ambas tienen `source_hash` y `capture_date`.

La respuesta sigue:

- `status=evidence_limited`,
- `verified=false`,
- `review_required=true`.

## Limites

- No se calcula retencion aplicable.
- No se determina si el pagador tiene obligacion efectiva.
- No se resuelve exencion, no sujecion, perceptor ni regla especial.
- No se extrapola `193` a no residentes ni a `216/296`.
- No se extrapola una naturaleza de dividendos/intereses a canones, servicios profesionales, ganancias patrimoniales u otras rentas.

## Siguiente Accion

La auditoria posterior de aplicabilidad domestica queda documentada en `docs/aeat-modelo-193-domestic-applicability-audit.md`.

Resultado: no hay base suficiente para cerrar obligacion domestica segura del Modelo `193`. Las obligaciones heredadas de perfil sin `source_hash` o `capture_date` deben quedar `partial`, `verified=false` y `safe_to_answer=false` hasta que exista relacion completa de pagador, perceptor, articulo, tipo de renta y exencion/no sujecion.
