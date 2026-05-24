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
| Reglas inclusion/exclusion | `partial` tras `20260524_0088` | Reglas oficiales basicas de Orden EHA/3290/2008 para 216/296 |

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
- Excluir perceptores de rentas que la Orden excluye de la obligacion de declaracion negativa.
- Excluir como cierre ordinario de 296 cuando la propia Orden remite a declaracion anual especifica para IIC.

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
- Este bloque no sustituye la consulta del texto oficial ni la revision fiscal cuando falte base.

## Siguiente Accion

Para pasar de `implemented_partial` a una cobertura mas alta hace falta granularizar por tipo de renta y convenio, con fuente oficial y tests de abstencion por cada caso.
