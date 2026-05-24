# AEAT 289 Metadata Evidence

## Estado

`Modelo 289` mantiene contrato parcial. Este bloque normaliza evidencia auxiliar
ya existente en `modelo_regla_inclusion` y `modelo_instruccion` y, en 0098,
registra recursos documentales frescos del cierre Sprint 1. No promueve
obligaciones de perfil ni convierte el procedimiento CRS/DAC2 en respuesta
segura universal.

## Alcance

- Tabla `modelo_regla_inclusion`: filas del `289` con fuente BOE del Real
  Decreto 1021/2015.
- Tabla `modelo_instruccion`: instrucciones del `289` con fuente BOE, ficha AEAT
  GI42 y PDF AEAT de presentacion CRS.
- Tabla `modelo_normativa`: Orden HAP/1695/2016 como fuente normativa directa
  del modelo documental.
- Tabla `modelo_recurso`: recursos documentales oficiales con hash fresco:
  RD 1021/2015, HAP/1695/2016, GI42, manual CRS y ZIP XSD/WSDL.
- Tabla `modelo_casilla`: correccion de dos campos XSD contra el ZIP oficial
  (`SendingCompanyIN` y `PaymentAmnt`).
- Sin cambios en `obligacion_perfil`.
- Sin cambios en `modelo_clave`.
- Sin cambios en `safe_to_answer`, `verified` o `completeness` de obligaciones.

## Evidencia normalizada

| Fuente | URL | SHA-256 | Capture date |
| --- | --- | --- | --- |
| BOE RD 1021/2015 | `https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399` | `423708790f64e673977e020d223ee8af89e99bea7970d793c998264e0fbc7b75` | `2026-05-24` |
| BOE Orden HAP/1695/2016 | `https://www.boe.es/buscar/doc.php?id=BOE-A-2016-9834` | `502a67740152eb23bdf66a59c1a2a69d0a34d8e4054b26191bb7dcfef7d05794` | `2026-05-24` |
| AEAT GI42 | `https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI42.shtml` | `1c00efed01d8d917591907c134abdc8dde84d87e51a6b69ca5a6acf830a26e1c` | `2026-05-24` |
| AEAT CRS PDF | `https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI42/Ayuda/CRS_Presentac_289_SWeb_2.6.pdf` | `ce76a21a629125961efe6a1ed9800262f4d253ab55c72a7f04e358936a448be3` | `2026-05-24` |
| AEAT XSD/WSDL ZIP | `https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI42/Ayuda/XSD_WSDL/289_XSD_2.0_WSDL_2.0.1.zip` | `6948eec877d04ca637b099f59fa944996aa878c8d68181dfffde87fd056a048d` | `2026-05-24` |

## Resultado esperado

- Las reglas auxiliares `289` con URL oficial dejan de estar sin hash.
- Las instrucciones auxiliares `289` con URL oficial dejan de estar sin hash.
- Los recursos documentales del 289 quedan disponibles como evidencia
  reproducible tras aplicar 0098.
- Las casillas XSD persistidas evitan dos nombres no presentes en el schema
  oficial: `SendingEntityIN` y `AmntEndsmnt`.
- `Modelo 289` puede exponer mejor trazabilidad documental, pero sigue siendo
  `partial`/`evidence_limited` donde falten supuesto, sujeto obligado,
  articulo operativo o contrato de obligacion completo.
- `obligacion_perfil` para `289` debe seguir fail-closed salvo evidencia
  especifica futura.

## Siguiente accion

No recuperar seguridad de `289` por perfil desde esta normalizacion. Si se quiere
cerrar aplicabilidad CRS/DAC2, abrir un bloque separado que audite sujeto
obligado, cuenta reportable, plazo, exclusiones y relacion normativa completa.

## PRD derivados

- `docs/aeat-289-documental-closeout-prd.md`: cierre condicionado del contrato
  documental del `Modelo 289`.
- `docs/aeat-289-sprint-1-checklist.md`: checks ejecutables para decidir si el
  cierre documental pasa las condiciones de hecho.
- `docs/crs-dac2-coverage-prd.md`: familia operativa CRS/DAC2 separada del
  estado documental del modelo.
