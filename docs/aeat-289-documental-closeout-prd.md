# PRD: Cierre documental Modelo 289 y separacion CRS/DAC2

## Objetivo

Cerrar el `Modelo 289` como contrato documental solo si la evidencia lo
demuestra, sin convertirlo por arrastre en cobertura operativa completa
CRS/DAC2 ni en obligacion segura por perfil.

## Estado inicial

Estado actual: `implemented_partial`.

El modelo tiene base CRS solida, con fuentes oficiales y metadata auxiliar ya
normalizada en reglas e instrucciones, pero no esta cerrado como contrato
documental completo. La familia CRS/DAC2 operativa sigue separada y no debe
contaminar ni el estado del modelo ni `obligacion_perfil`.

Referencias activas:

- `docs/master-execution-roadmap.md`
- `docs/fiscal-regulatory-coverage-matrix.md`
- `docs/aeat-priority-model-closeout.md`
- `docs/aeat-289-metadata-evidence.md`
- `docs/aeat-289-sprint-1-checklist.md`
- `docs/aeat-289-documental-audit-2026-05-24.md`

## No objetivos

- No cerrar CRS/DAC2 como familia operativa.
- No marcar `obligation_context` como seguro sin evidencia propia por sujeto
  obligado y supuesto.
- No usar normativa general CRS para inferir aplicabilidad universal.
- No promover `verified=true` o `completeness=complete` si falta fuente, hash,
  captura o test.
- No tocar `obligacion_perfil` salvo auditoria especifica de sujeto obligado y
  supuesto.

## Perimetro documental

Sprint 1 debe congelar y auditar estas fuentes y piezas documentales:

1. Orden HAP/1695/2016.
2. Real Decreto 1021/2015.
3. AEAT GI42.
4. Manual CRS / servicio web de presentacion.
5. XSD, WSDL o diseno logico oficial aplicable.
6. Reglas de presentacion y tratamiento de aceptado, aceptado parcialmente,
   rechazado parcial y rechazado total.
7. Operaciones `OECD1`, `OECD2` y `OECD3`.
8. Reglas de jurisdiccion reportable.
9. Campos sensibles, incluidos `ResidenceCountryCode`, `AcctHolderType` y
   cuentas no documentadas.

## Tareas Sprint 1

1. Congelar perimetro documental y documentar explicitamente que queda fuera.
2. Auditar cada fuente oficial y registrar `source_url`, `source_hash` y
   `capture_date`.
3. Verificar que reglas, instrucciones y campos usados por API/MCP proceden de
   fuentes oficiales trazables.
4. Identificar cualquier fila auxiliar legacy que no pueda probarse literalmente
   desde fuente oficial y mantenerla fuera de `complete`.
5. Anadir o ampliar tests de contrato para `/v1/modelos/aeat/289` y la
   superficie MCP/catalogo equivalente.
6. Confirmar que `obligation_context` sigue fail-closed si falta evidencia
   propia por sujeto obligado y supuesto.
7. Ejecutar `docs/aeat-289-sprint-1-checklist.md`.
8. Actualizar matriz, closeout y manual solo con el estado realmente probado.

## Condiciones de hecho

`Modelo 289` solo puede marcarse `complete` como modelo documental si cumple las
ocho condiciones generales del repo:

1. Fuente oficial identificada.
2. Worker o seed reproducible.
3. Datos en produccion.
4. API o MCP expuesto.
5. Metadatos de evidencia: `verified`, `completeness`, `source_url`,
   `capture_date` o equivalente.
6. Tests de contrato.
7. Documentacion de cobertura.
8. Respuesta fail-closed cuando falte evidencia.

Si falla una condicion, el modelo queda `partial` con gap exacto documentado.

## Criterios de salida Sprint 1

- Si pasa las ocho condiciones de hecho, `Modelo 289` puede marcarse `complete`
  solo como modelo contractual/documental.
- Si no pasa, queda `partial` con gap exacto documentado.
- `complete` del `Modelo 289` no implica mejora ni degradacion automatica de
  CRS/DAC2 operativo.
- `CRS/DAC2 operativo` sigue `implemented_partial` hasta tener PRD y contrato de
  familia separados.
- No hay respuesta segura por perfil sin hash, captura, fuente y supuesto.

## Anti-derivas

- No confundir formulario documentado con procedimiento completo.
- No usar `complete` como objetivo politico; solo como resultado de checklist.
- No reutilizar hash/captura de una fuente general para probar una regla
  reformulada.
- No mezclar `289` con `290`/FATCA IRS salvo relacion explicita y documentada.
- No tocar `obligacion_perfil` salvo auditoria especifica de sujeto obligado y
  supuesto.

## Resultado esperado

La respuesta correcta a "esta cerrado el 289?" debe distinguir:

- `Modelo 289 documental`: cerrado solo si pasa el checklist completo.
- `CRS/DAC2 operativo`: familia separada, parcial hasta contrato propio.
- `obligacion_perfil`: fail-closed salvo evidencia propia por sujeto obligado y
  supuesto.

## Auditoria 2026-05-24

La primera ejecucion del checklist queda documentada en
`docs/aeat-289-documental-audit-2026-05-24.md` y mantiene el `Modelo 289` en
`partial`.

Resultado actualizado del Sprint 1 local:

- Revision local `20260524_0098_aeat_289_documental_source_refresh` creada para
  normalizar HAP/1695/2016, GI42 actual, manual CRS y XSD/WSDL como evidencia
  documental.
- Revision 0098 aplicada en VPS; DB confirma 5 recursos documentales activos,
  HAP normativa cargada, hash GI42 actual y correccion de campos XSD.
- Dos campos XSD persistidos quedan corregidos contra el ZIP oficial:
  `SendingCompanyIN` y `PaymentAmnt`.
- La suite live VPS no permite cierre: `mcp_validation_suite.py` desde `ops`
  devuelve `ok=false`; pasan checks documentales 289, pero fallan obligaciones
  de perfil no verificadas/sin hash.
- El resultado sigue siendo `partial`; cualquier promocion exige recuperar
  evidencia propia por sujeto obligado/supuesto o separar el cierre CRS/DAC2
  operativo.
