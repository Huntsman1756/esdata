# AEAT IRNR Retenciones 216/296

Estado: `implemented_partial`.

Este bloque conecta la linea doctrinal D-01 (`TRLIRNR art. 31`) con los modelos AEAT `216` y `296`, sin convertir la existencia del modelo en aplicabilidad completa para cualquier supuesto.

## Estado Real

| pieza | estado | evidencia |
|-------|--------|-----------|
| Modelo 216 | `complete` como formulario/modelo operativo | Casillas, claves e instrucciones oficiales cargadas con URL, hash y captura |
| Modelo 296 | `complete` como formulario/modelo operativo | Casillas, claves e instrucciones oficiales cargadas con URL, hash y captura |
| D-01 | `complete` | DGT `V0166-25`, `TRLIRNR art. 31`, modelos `216/296`, hash y captura |
| Aplicabilidad por supuesto | `partial` | Depende de tipo de renta, residencia, convenio, excepciones y obligacion concreta de retener |
| Reglas inclusion/exclusion | `partial` tras `20260524_0089` | Reglas oficiales basicas de Orden EHA/3290/2008 para 216/296 y claves de renta 296 para dividendos/intereses |

## Fuentes Oficiales

- BOE: Orden EHA/3290/2008, de 6 de noviembre, modelos 216 y 296: <https://www.boe.es/buscar/act.php?id=BOE-A-2008-18497>
- AEAT Modelo 216, procedimiento GF05: <https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GF05.shtml>
- AEAT Modelo 296, resumen anual IRNR: <https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelo-296-declaracion-informativa-resumen-anual_.html>
- D-01 doctrina principal: DGT `V0166-25`, conectada a `TRLIRNR art. 31`.

## Reglas Operativas

### Modelo 216

- Incluir de forma condicional cuando exista obligacion de retener o ingresar a cuenta por rentas IRNR obtenidas sin mediacion de establecimiento permanente.
- Incluir de forma condicional cuando proceda declaracion negativa por supuestos de `TRLIRNR art. 31.4`.
- Excluir como cierre de 216 cuando el supuesto corresponda a transmisiones/reembolsos de IIC o premios de determinadas loterias y apuestas si la fuente oficial remite a declaraciones especificas.

### Modelo 296

- Incluir de forma condicional como resumen anual de retenciones e ingresos a cuenta IRNR.
- Incluir de forma condicional para entidades que paguen por cuenta ajena rentas sujetas a retencion o ingreso a cuenta, o que sean depositarias/gestoras del cobro de rentas de valores.
- Identificar de forma condicional la clave de renta `1` para dividendos y otras rentas derivadas de participacion en fondos propios, solo como evidencia de tipo de renta en el resumen anual.
- Identificar de forma condicional la clave de renta `2` para intereses y otras rentas derivadas de la cesion a terceros de capitales propios, solo como evidencia de tipo de renta en el resumen anual.
- Excluir perceptores de rentas que la Orden excluye de la obligacion de declaracion negativa.
- Excluir como cierre ordinario de 296 cuando la propia Orden remite a declaracion anual especifica para IIC.

## Auditoria O-01: Dividendos E Intereses

Produccion contiene claves oficiales cargadas para `296`:

| renta | modelo | clave | estado | evidencia |
|-------|--------|-------|--------|-----------|
| dividendos | `296` | `CLAVE_RENTA 1` | `partial_traceable` | URL oficial, `source_hash` y `capture_date=2026-05-14` |
| intereses | `296` | `CLAVE_RENTA 2` | `partial_traceable` | URL oficial, `source_hash` y `capture_date=2026-05-14` |

La migracion `20260524_0089_aeat_irnr_income_type_rules` persiste estas dos reglas como `CONDICIONAL` en `modelo_regla_inclusion`. No se crea una regla equivalente de tipo de renta para `216`, porque el modelo `216` opera como autoliquidacion periodica agregada y no hay clave de renta cargada equivalente que separe dividendos/intereses con el mismo nivel de evidencia.

El clasificador `/v1/modelos/por-supuesto` puede anadir evidencia de `modelo_clave` para `296` cuando `tipo_renta=dividendos` o `tipo_renta=intereses`, pero sigue devolviendo `status=evidence_limited`, `verified=false` y `review_required=true`. La clave de renta acredita el tipo de renta en el resumen anual; no acredita por si sola convenio, protocolo, residencia efectiva, exencion ni retencion final.

## Fail-Closed

`safe_to_answer=true` en `obligation_context` requiere simultaneamente:

- `verified=true`,
- `completeness='completa'`,
- `source_url`,
- `source_hash`,
- `capture_date`,
- y que la obligacion almacenada no este marcada como insegura.

Por tanto, una obligacion de perfil `partial`, aunque tenga articulo `TRLIRNR art. 31`, debe exponerse con `safe_to_answer=false` y `review_required=true`.

## Limites

- Este bloque no calcula retencion aplicable.
- Este bloque no resuelve convenio, protocolo, exencion o tipo de renta final.
- Este bloque no convierte 216/296 en obligatorios por perfil sin supuesto concreto.
- Este bloque no extrapola las claves `296` de dividendos/intereses al modelo `216` ni a canones, servicios profesionales o ganancias patrimoniales.
- Este bloque no sustituye la consulta del texto oficial ni la revision fiscal cuando falte base.

## Siguiente Accion

Para pasar de `implemented_partial` a una cobertura mas alta hace falta granularizar por tipo de renta y convenio, con fuente oficial y tests de abstencion por cada caso.
