# PRD: Cobertura operativa CRS/DAC2

## Objetivo

Crear una familia operativa CRS/DAC2 independiente del cierre documental del
`Modelo 289`, con contrato de cobertura, evidencia y abstencion segura cuando
falte base suficiente.

## Estado inicial

Estado actual: `implemented_partial`.

El repo ya contiene piezas relacionadas con CRS/FATCA y el `Modelo 289`, pero
esas piezas no equivalen a un procedimiento CRS/DAC2 completo por sujeto
obligado, tipo de cuenta, jurisdiccion, titular, plazo y regla de diligencia
debida.

## No objetivos

- No usar el estado documental del `Modelo 289` como prueba de cobertura
  operativa CRS/DAC2.
- No calcular aplicabilidad definitiva si falta sujeto obligado, jurisdiccion,
  tipo de cuenta, fuente o regla de diligencia debida.
- No mezclar CRS/DAC2 con FATCA IRS o `Modelo 290` salvo relacion explicita y
  documentada.
- No devolver respuestas seguras a partir de fuentes generales sin evidencia por
  supuesto.

## Contrato minimo

La familia CRS/DAC2 debe modelar, como minimo:

| Dimension | Requisito |
| --- | --- |
| Sujeto obligado | Tipo de institucion financiera o entidad reportante |
| Cuenta | Tipo de cuenta financiera y estado de documentacion |
| Jurisdiccion | Jurisdiccion reportable y residencia fiscal |
| Persona | Titular, entidad, controlling person o equivalente |
| Operacion | Alta, correccion, anulacion u operacion CRS aplicable |
| Plazo | Periodo y ventana de presentacion |
| Evidencia | `source_url`, `source_hash`, `capture_date`, `verified`, `completeness` |
| Seguridad | `safe_to_answer`, `review_required`, `evidence_notice` |

## Tareas Sprint 2

1. Definir matriz CRS/DAC2 independiente del `Modelo 289`.
2. Auditar fuentes oficiales CRS/DAC2 aplicables y separar AEAT, BOE, UE/OCDE e
   IRS/FATCA cuando proceda.
3. Definir primer lote acotado de cobertura, por ejemplo institucion financiera
   reportante espanola, cuenta reportable CRS y presentacion mediante `289`.
4. Disenar endpoint o tool de `coverage`, no calculo definitivo.
5. Anadir tests fail-closed para falta de jurisdiccion, fuente, hash/captura,
   sujeto obligado o regla de diligencia debida.
6. Documentar gaps por dimension y siguiente accion.
7. Actualizar matriz fiscal-regulatoria y manual si cambia comportamiento
   visible.

## Reglas fail-closed

La respuesta debe abstenerse o marcar `safe_to_answer=false` cuando:

- falta sujeto obligado,
- falta jurisdiccion o residencia fiscal,
- falta tipo de cuenta o estado de documentacion,
- falta fuente oficial trazable,
- falta `source_hash` o `capture_date`,
- la regla procede de inferencia o resumen legacy,
- la consulta requiere FATCA IRS o `Modelo 290` y no hay relacion explicita.

## Criterios de salida Sprint 2

- CRS/DAC2 queda como familia propia, separada del `Modelo 289`.
- El sistema puede explicar cobertura y gaps sin inventar aplicabilidad.
- Ningun dato del `Modelo 289` convierte automaticamente una obligacion
  CRS/DAC2 en segura.
- Existe una superficie de `coverage` con estado, evidencia y gaps.
- Los tests fallan si una respuesta factual no incluye evidencia suficiente.

## Resultado esperado

La respuesta correcta a "esta cerrado CRS/DAC2?" debe ser:

> CRS/DAC2 existe como superficie parcial y familia independiente. El `Modelo
> 289` puede estar mejor documentado, pero no prueba por si solo aplicabilidad
> operativa completa ni obligacion segura por perfil.
