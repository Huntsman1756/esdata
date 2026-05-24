# AEAT 289 Metadata Evidence

## Estado

`Modelo 289` mantiene contrato parcial. Este bloque normaliza evidencia auxiliar
ya existente en `modelo_regla_inclusion` y `modelo_instruccion`; no promueve
obligaciones de perfil ni convierte el procedimiento CRS/DAC2 en respuesta
segura universal.

## Alcance

- Tabla `modelo_regla_inclusion`: filas del `289` con fuente BOE del Real
  Decreto 1021/2015.
- Tabla `modelo_instruccion`: instrucciones del `289` con fuente BOE, ficha AEAT
  GI42 y PDF AEAT de presentacion CRS.
- Sin cambios en `obligacion_perfil`.
- Sin cambios en `modelo_clave`.
- Sin cambios en `safe_to_answer`, `verified` o `completeness` de obligaciones.

## Evidencia normalizada

| Fuente | URL | SHA-256 | Capture date |
| --- | --- | --- | --- |
| BOE RD 1021/2015 | `https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399` | `423708790f64e673977e020d223ee8af89e99bea7970d793c998264e0fbc7b75` | `2026-05-24` |
| AEAT GI42 | `https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI42.shtml` | `c73351f50935086f4fbeda39d5123563587a6964e2aaa8d254a4ba7b38b4b9a1` | `2026-05-24` |
| AEAT CRS PDF | `https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI42/Ayuda/CRS_Presentac_289_SWeb_2.6.pdf` | `ce76a21a629125961efe6a1ed9800262f4d253ab55c72a7f04e358936a448be3` | `2026-05-24` |

## Resultado esperado

- Las reglas auxiliares `289` con URL oficial dejan de estar sin hash.
- Las instrucciones auxiliares `289` con URL oficial dejan de estar sin hash.
- `Modelo 289` puede exponer mejor trazabilidad documental, pero sigue siendo
  `partial`/`evidence_limited` donde falten supuesto, sujeto obligado,
  articulo operativo o contrato de obligacion completo.
- `obligacion_perfil` para `289` debe seguir fail-closed salvo evidencia
  especifica futura.

## Siguiente accion

No recuperar seguridad de `289` por perfil desde esta normalizacion. Si se quiere
cerrar aplicabilidad CRS/DAC2, abrir un bloque separado que audite sujeto
obligado, cuenta reportable, plazo, exclusiones y relacion normativa completa.
