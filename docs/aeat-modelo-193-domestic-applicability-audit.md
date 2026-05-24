# AEAT Modelo 193 - Auditoria De Aplicabilidad Domestica

Estado: `partial`.

Fecha de auditoria: 2026-05-24.

## Objetivo

Comprobar si el Modelo `193` puede pasar de evidencia de tipo de renta a obligacion domestica segura por supuesto.

El cierre solo seria aceptable si existieran, a la vez:

- fuente oficial trazable con URL, hash y fecha de captura,
- pagador u obligado identificado,
- perceptor identificado,
- tipo de renta confirmado,
- articulo fiscal aplicable,
- exencion o no sujecion tratada cuando aplique,
- relacion suficiente para responder sin inferencia.

## Resultado

No se cierra aplicabilidad domestica completa del Modelo `193`.

La produccion acredita el modelo, las claves de dividendos/intereses y ciertas naturalezas de exencion/no retencion. Eso mejora la trazabilidad, pero no demuestra por si solo que una sociedad de valores concreta deba presentar el modelo para cualquier supuesto domestico.

## Evidencia Encontrada

| pieza | estado | evidencia |
|-------|--------|-----------|
| Modelo 193 | `complete` como formulario/modelo | Procedimiento AEAT `GI12`, campana 2025, instrucciones y diseno oficial |
| Orden modelo | `traceable` | `BOE-A-2024-23244`, Orden HAC/1100/2024 |
| Claves dividendos | `traceable` | `PERCEPCION_A` + `NAT_A_02`, hash y `capture_date=2026-05-14` |
| Claves intereses | `traceable` | `PERCEPCION_B` + `NAT_BD_01`, hash y `capture_date=2026-05-14` |
| Exencion/no retencion | `partial_traceable` | Naturalezas `NAT_A_06`, `NAT_A_08`, `NAT_BD_07` existen con hash/captura |
| Articulo pagos a cuenta | `missing_for_model_contract` | No hay enlace persistido del Modelo 193 a `LIRPF art. 99/100/101` con hash/captura |
| RIRPF | `missing` | No hay norma `RIRPF` cargada ni enlace persistido a articulo reglamentario |
| Obligacion de perfil 193 | `downgraded` | Filas heredadas existian como `complete/safe`, pero sin `source_hash` |

## Decision

La migracion `20260524_0091_aeat_193_domestic_applicability_fail_closed` no siembra nuevas reglas de aplicabilidad.

Solo hace dos correcciones:

- corrige `aeat_modelo.periodo` del Modelo `193` a `anual`,
- degrada obligaciones de perfil `modelo_aeat='193'` sin `source_hash` o `capture_date` a `partial`, `verified=false` y `safe_to_answer=false`.

## Limites

- No se infiere obligacion por tener clientes residentes.
- No se usa la existencia de claves del diseno como prueba de obligacion efectiva.
- No se usa `LIRPF art. 101` como cierre suficiente si no hay hash/captura y supuesto completo.
- No se resuelve exencion/no sujecion por mera existencia de una naturaleza del registro.
- No se extrapola a modelos `123`, `124`, `216` o `296`.

## Siguiente Accion

Para intentar un cierre futuro hay que cargar o persistir una relacion completa con:

- articulo de pagos a cuenta aplicable,
- regla reglamentaria si procede,
- pagador/obligado,
- perceptor,
- tipo de renta,
- exencion/no sujecion,
- fuente oficial con hash y fecha de captura.

Hasta entonces, el Modelo `193` sigue siendo consultable como modelo y como evidencia de tipo de renta, pero no como obligacion domestica segura por supuesto.
