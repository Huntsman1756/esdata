# AEAT campaign curation - Modelo 126 - 2026-05-26

Estado: curacion documental read-only. No cambia datos productivos.

## Modelo

- Codigo: `126`
- Nombre AEAT: Modelo 126. Retenciones e ingresos a cuenta. Rendimientos del
  capital mobiliario obtenidos por la contraprestacion derivada de cuentas en
  toda clase de instituciones financieras.
- URL AEAT: <https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GH06.shtml>

## Estado observado en MCP/API

Superficies revisadas en VPS tras deploy:

- `/v1/modelos/126/fuentes-oficiales`
- `/v1/modelos/126/resumen-operativo`

Resultado antes de `AEAT-TECHNICAL-COVERAGE-INACTIVE-RESOURCES-01`:

```text
campana_activa=2013
campana_persistida=2013
campana_candidata=2013
campana_resolution_status=resolved_weak
campana_verification_level=inferred_internal
campana_safe_to_assert=false
campana_assertion_code=NOT_ASSERTABLE_INFERRED_INTERNAL
campana_evidence=[]
campana_conflict_years=[]
technical_exercise_coverage=[]
```

Lectura: MCP no afirma campana. Correcto. Pero en ese momento todavia no
conservaba la cobertura tecnica oficial `2020+` para el modelo 126, aunque la
fuente AEAT la publica.

## Fuentes oficiales revisadas

### Ficha AEAT GH06

URL: <https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GH06.shtml>

Evidencia:

- La ficha identifica el procedimiento del modelo 126.
- Incluye gestiones de presentacion, presentacion por lotes, consulta,
  domiciliaciones y documentacion complementaria.
- Enlaza a `Disenos de registro. Modelos 100 al 199`.
- En normativa enlaza a:
  - Orden HAP/2194/2013, de 22 de noviembre.
  - Orden EHA/3435/2007, de 23 de noviembre.
- La pagina consta actualizada el `13/febrero/2026`.

Conclusion:

- No contiene texto que vincule inequivocamente `modelo 126 + campana activa
  2013`.
- No contiene texto que permita afirmar una campana vigente concreta.
- La fecha de actualizacion de pagina no es campana.

### Disenos de registro AEAT modelos 100-199

URL: <https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro/modelos-100-199.html>

Evidencia:

- La pagina publica para `126`:

```text
126 - Orden EHA/3435/2007 (Ejercicios 2020 y siguientes) (111 KB - xlsx)
```

- La descripcion visible lo sitúa en IRPF, Impuesto sobre Sociedades e IRNR
  para retenciones e ingresos a cuenta sobre rendimientos del capital mobiliario
  o determinadas rentas.
- La pagina consta actualizada el `13/mayo/2026`.

Conclusion:

- Esto es evidencia oficial de cobertura tecnica de diseno de registro desde
  `2020` en adelante.
- No prueba campana activa.
- No permite `ASSERTABLE_DIRECT_OFFICIAL`.
- Si se usa en el sistema, debe entrar como `technical_exercise_coverage` con
  `proves_campaign=false`.

### BOE enlazado por AEAT

Fuentes enlazadas desde GH06:

- Orden HAP/2194/2013.
- Orden EHA/3435/2007.

Conclusion:

- La fecha BOE por si sola no prueba campana activa.
- La Orden EHA/3435/2007 aprueba, entre otros, el modelo 126, pero no prueba que
  `2013` sea campana activa vigente.
- No se usa BOE como trigger fuerte salvo texto que vincule modelo y
  ejercicio/campana/periodo de forma inequivoca.

## Dictamen

Resultado para campana afirmable: `UNKNOWN`.

No procede:

- `resolved_strong`
- `ASSERTABLE_DIRECT_OFFICIAL`
- `campana_afirmable=2013`

El estado actual `resolved_weak` evita afirmar, pero es semanticamente pobre
porque conserva `2013` como candidata interna sin reflejar la cobertura tecnica
oficial `2020+` publicada por AEAT.

## Recomendacion

Para el modelo 126:

1. Mantener `campana_safe_to_assert=false`.
2. Mantener `campana_afirmable=null`.
3. No promover a `resolved_strong`.
4. Anadir/derivar `technical_exercise_coverage`:

```json
{
  "from_year": 2020,
  "to_year": null,
  "label": "Ejercicios 2020 y siguientes",
  "scope": "technical_resource",
  "source_url": "https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro/modelos-100-199.html",
  "proves_campaign": false,
  "evidence_role": "technical_exercise_coverage"
}
```

5. Revaluar si el estado debe pasar de `resolved_weak` a:
   - `stale_suspected`, si el sistema usa cobertura tecnica reciente como senal
     de obsolescencia de `2013`;
   - o `conflict`, si los anos de cobertura tecnica se incorporan al detector de
     conflicto.

## Seguimiento tecnico

`AEAT-TECHNICAL-COVERAGE-INACTIVE-RESOURCES-01` corrige la causa tecnica sin
mutar datos: algunos XLSX oficiales de diseno de registro quedaban en
`modelo_recurso.activa=false` por la unicidad de recurso activo por tipo, pero
seguian teniendo metadatos oficiales utiles (`label` y `source_index`). El API
puede usarlos como evidencia no afirmativa para `technical_exercise_coverage`,
sin exponerlos como fuente activa ni permitir `campana_afirmable`.

Resultado esperado tras despliegue:

```text
campana_resolution_status=conflict
campana_safe_to_assert=false
campana_assertion_code=NOT_ASSERTABLE_CONFLICT
technical_exercise_coverage[0].from_year=2020
technical_exercise_coverage[0].proves_campaign=false
```

## No decisiones

- No se corrige base de datos.
- No se marca `2013` como falso por escritura automatica.
- No se selecciona `2020` como campana activa.
- No se usa nombre de fichero, XLSX ni fecha de pagina como evidencia fuerte de
  campana.
