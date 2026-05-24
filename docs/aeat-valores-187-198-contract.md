# AEAT valores 187/198 - contrato operativo

## Estado

Sprint T endurece la familia de valores `187/198` sin cambiar su cierre como
modelos AEAT estructurados.

| Modelo | Estado del modelo | Estado de obligacion perfil | Regla persistida | Limite |
| --- | --- | --- | --- | --- |
| `187` | `complete` como formulario/instrucciones/claves | `partial` si falta hash/captura en `obligacion_perfil` | `iic_transmisiones_reembolsos_187` | No prueba obligacion de perfil sin operacion de IIC, sujeto obligado y retencion/exencion |
| `198` | `complete` como formulario/instrucciones/claves | `partial` si falta hash/captura en `obligacion_perfil` | `activos_financieros_valores_mobiliarios_198` | No prueba obligacion de perfil sin operacion, intermediario/declarado y regla aplicable |

## Auditoria de produccion

Auditoria VPS previa al cambio:

- `187`: 50 casillas, 28 claves, 5 instrucciones, 0 reglas de inclusion.
- `198`: 72 casillas, 46 claves, 7 instrucciones, 0 reglas de inclusion.
- `187`: 3 filas `obligacion_perfil` con `safe_to_answer=true` pero sin `source_hash` o `capture_date`.
- `198`: 4 filas `obligacion_perfil` con `safe_to_answer=true` pero sin `source_hash` o `capture_date`.

La conclusion correcta es:

- El modelo puede seguir `complete` como contrato documental.
- La obligacion de perfil no puede ser segura sin hash/captura y relacion completa.

## Fuentes oficiales

- AEAT `GI07`: Modelo 187. Declaracion informativa de acciones y participaciones representativas del capital o patrimonio de instituciones de inversion colectiva.
- BOE `BOE-A-2014-9225`: Orden HAP/1608/2014, Modelo 187.
- AEAT `GI17`: Modelo 198. Declaracion anual de operaciones con activos financieros y otros valores mobiliarios.
- BOE `BOE-A-2004-20157`: Orden EHA/3895/2004, Modelo 198.
- Disenos oficiales AEAT:
  - `DR_Modelo_187_2022.pdf`
  - `DR_Modelo_198_2024.pdf`

Las reglas de Sprint T se insertan solo si `modelo_recurso` tiene
`sha256_contenido` y `last_seen_at`.

## Reglas operativas

### Modelo 187

`187` se puede usar como evidencia del alcance formal del modelo cuando el
supuesto trata acciones o participaciones de instituciones de inversion
colectiva y operaciones de transmision o reembolso.

No se debe presentar como obligacion segura por perfil si faltan:

- sujeto obligado,
- operacion concreta,
- renta o ganancia patrimonial,
- retencion, ingreso a cuenta, exencion o no sujecion,
- hash y fecha de captura de la fuente oficial.

### Modelo 198

`198` se puede usar como evidencia del alcance formal del modelo cuando el
supuesto trata operaciones con activos financieros y otros valores mobiliarios.

No se debe presentar como obligacion segura por perfil si faltan:

- operacion concreta,
- identificacion del declarante/intermediario o declarado,
- clase de activo financiero o valor mobiliario,
- regla aplicable,
- hash y fecha de captura de la fuente oficial.

## Decisiones

- No se crean obligaciones nuevas.
- No se cambia el estado `complete` del modelo como formulario.
- No se marca `safe_to_answer=true` en obligaciones legacy sin evidencia normalizada.
- No se usa una clave/casilla como sustituto de aplicabilidad por supuesto.
- `modelo_regla_inclusion` se usa como trazabilidad de alcance, no como autoridad juridica completa.

## Validacion esperada

- `/v1/modelos/aeat/187` conserva contrato de modelo completo.
- `/v1/modelos/aeat/198` conserva contrato de modelo completo.
- `obligation_context` para filas legacy sin hash/captura queda `safe_to_answer=false`.
- `modelo_regla_inclusion` contiene dos reglas por modelo con hash/captura.
- No aparece obligacion segura de perfil para `187/198` sin evidencia normalizada.
