# AEAT Siguiente Modelo - Auditoria O-03

Estado: `candidate_executed`.

O-03 no implementa nueva cobertura productiva. Solo selecciona un candidato para el siguiente sprint a partir de evidencia ya cargada en produccion.

## Candidatos Auditados

| modelo | estado productivo | casillas | claves | instrucciones | recursos con hash | decision |
|--------|-------------------|----------|--------|---------------|-------------------|----------|
| `187` | `complete`, `curado` | `50` | `28` | `5` | si | candidato valido, pero mas estrecho y ligado a IIC |
| `193` | `complete`, `curado` | `71` | `38` | `5` | si | seleccionado |
| `198` | `complete`, `curado` | `72` | `46` | `7` | si | candidato valido, pero mas amplio y operativo |
| `200` | `partial`, `inferido` | `6807` | `0` | `5` | si | descartado para el siguiente sprint por amplitud y riesgo |
| `232` | sin `completeness_estado` | `223` | `0` | `0` | si | descartado hasta cerrar instrucciones/claves operativas |
| `303` | `partial`, `inferido` | `432` | `0` | `5` | si | descartado por amplitud IVA y estado parcial |

## Candidato Seleccionado

Siguiente sprint recomendado: **Modelo 193**.

Motivo:

- conecta naturalmente con rendimientos del capital mobiliario, dividendos e intereses en residentes;
- permite complementar el bloque IRNR `216/296` con la familia residente equivalente sin abrir Modelo 100;
- ya tiene casillas, claves, instrucciones y recursos oficiales con hash;
- tiene alcance menor y mas controlable que `200` o `303`;
- permite mantener la regla de producto: modelo completo no equivale a obligacion segura por perfil.

## PRD Operativo Siguiente

Objetivo inicial del sprint siguiente:

1. Auditar `193` en produccion por claves/subclaves relevantes.
2. Separar dividendos, intereses y otros rendimientos si las claves lo soportan.
3. Persistir reglas de inclusion/exclusion solo cuando la fuente oficial lo permita.
4. Conectar con perfil/supuesto residente sin convertirlo en obligacion universal.
5. Mantener `safe_to_answer=false` si falta pagador, tipo de renta, perceptor, exencion o regla de retencion.
6. Anadir tests de renta soportada, renta no soportada, falta de hash/captura y no contaminacion con `216/296`.

## Descartes Expresos

- No elegir `100`: alto valor, pero demasiado amplio para el siguiente corte.
- No elegir `200`: ya tiene gran volumen de casillas, pero sigue `partial`/`inferido` y abriria demasiados supuestos IS/IRNR.
- No elegir `232`: encaja con D-03, pero no tiene instrucciones/claves operativas suficientes en produccion.
- No elegir `303`: alto valor, pero el bloque IVA requiere un sprint propio por amplitud y por no mezclarlo con capital mobiliario.

## Ejecucion Posterior

El candidato `193` se ejecuta en el bloque `P-01`:

- documento de contrato: `docs/aeat-modelo-193-rentas-residentes-contract.md`;
- migracion: `20260524_0090_aeat_193_income_type_rules`;
- alcance: dividendos e intereses residentes;
- salida: reglas `CONDICIONAL`, no obligacion segura universal.
