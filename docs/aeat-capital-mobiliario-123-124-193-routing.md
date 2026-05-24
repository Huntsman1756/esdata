# AEAT Capital Mobiliario 123/124/193 - Routing Semantico

## Estado

`123`, `124` y `193` forman una familia operativa de capital mobiliario, pero no tienen el mismo alcance.

| Modelo | Estado operativo | Uso en `/v1/modelos/por-supuesto` | Limite |
| --- | --- | --- | --- |
| `123` | `partial` | Candidato para retenciones de capital mobiliario residentes | No acredita obligacion concreta sin pagador, perceptor, renta y articulo |
| `124` | `partial` | Candidato solo si el supuesto identifica activos financieros y transmision, amortizacion, reembolso, canje o conversion | No debe salir por capital mobiliario residente generico |
| `193` | Modelo saneado; obligacion domestica sigue `partial` | Candidato informativo anual; puede aportar evidencia de claves si hay hash/captura | No acredita obligacion por perfil sin articulo y sujeto trazados |

## Fuentes De Alcance

- Modelo `123`: ficha AEAT `GH04`, retenciones e ingresos a cuenta sobre determinados rendimientos del capital mobiliario o determinadas rentas.
- Modelo `124`: ficha AEAT `GH05`, rentas y rendimientos del capital mobiliario derivados de transmision, amortizacion, reembolso, canje o conversion de activos representativos de la captacion y utilizacion de capitales ajenos.
- Modelo `193`: ficha AEAT `GI12`, resumen anual de retenciones e ingresos a cuenta sobre determinados rendimientos del capital mobiliario y determinadas rentas.

## Decision De Routing

El Modelo `124` no se ofrece como candidato cuando la consulta solo declara:

- `clientes_residentes=true`,
- `tipo_renta=capital_mobiliario`,
- sin `tipo_operacion` especifico.

En ese caso se devuelve como excluido con motivo `activos_financieros_no_confirmados_para_124`.

`124` vuelve a aparecer como candidato si el supuesto contiene una operacion propia del modelo, por ejemplo:

- transmision de activos financieros,
- amortizacion de activos financieros,
- reembolso de activos financieros,
- canje de activos financieros,
- conversion de activos financieros.

La clasificacion sigue siendo `candidato`, no `confirmado`.

## Reglas Persistidas

La migracion `20260524_0092_aeat_capital_mobiliario_123_124_rules` persiste reglas de alcance, no reglas de obligacion completa:

| Modelo | Regla | Decision | Fuente |
| --- | --- | --- | --- |
| `123` | `capital_mobiliario_general_123` | `CONDICIONAL` | Ficha AEAT `GH04` cacheada con hash/captura |
| `123` | `aplicabilidad_no_confirmada_123` | `EVIDENCE_LIMITED` | Ficha AEAT `GH04` cacheada con hash/captura |
| `124` | `activos_financieros_124` | `CONDICIONAL` | Ficha AEAT `GH05` cacheada con hash/captura |
| `124` | `activos_financieros_no_generico_124` | `EXCLUIR` | Ficha AEAT `GH05` cacheada con hash/captura |

Tambien se corrige el metadato de `124` a `IRPF/IS/IRNR`, porque la ficha AEAT lo presenta como retenciones e ingresos a cuenta de esos impuestos; no se mantiene como modelo puramente IRNR.

Estas reglas no cargan `modelo_clave` ni `modelo_instruccion`: no se han localizado claves/instrucciones deterministas equivalentes a las de `193`.

## Reglas

- No convertir `124` en obligacion segura por analogia con `123` o `193`.
- No usar la existencia de casillas oficiales como prueba de aplicabilidad.
- No marcar `safe_to_answer=true` por presencia de modelo en el catalogo.
- Mantener `review_required=true` hasta tener regla oficial de pagador, perceptor, renta, articulo y fuente con hash/captura.

## Gaps

- `123` y `124` no tienen aun claves, instrucciones y reglas de inclusion equivalentes al trabajo hecho en `193`.
- `124` necesita curacion especifica por activos financieros antes de cualquier intento de cierre.
- La familia debe seguir documentada como `implemented_partial`.
