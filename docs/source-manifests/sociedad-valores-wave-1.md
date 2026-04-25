# Sociedad de valores - Wave 1 source manifest

## Objetivo

Cerrar la primera ola de fuentes necesarias para que `esdata` deje de ser solo un motor fiscal trazable y empiece a ser util para una `sociedad de valores` en Espana.

## Regla de uso

- Priorizar siempre fuentes oficiales primarias.
- No ampliar una fuente a gran escala sin antes fijar referencia canonica, `source_url`, tipo documental y estado de vigencia.
- No pasar a workflow interno hasta que este manifest tenga al menos cobertura util en `CNMV`, `SEPBLAC`, `EUR-Lex` y `CENDOJ`.

## Wave 1

| Fuente | Referencia canonica / slice | Tipo | Prioridad | Estado actual repo | Estado objetivo |
|---|---|---|---|---|---|
| CNMV | Circulares ESI, reporting reservado, reporting financiero, guias operativas | documento_regulatorio | P1 | slice inicial | corpus curado |
| SEPBLAC | Ley 10/2010, RD 304/2014, Modelo 19, manual PBC/FT, secciones operativas | norma + formulario + manual | P1 | slice inicial | corpus curado |
| EUR-Lex | MiFID II, MiFIR, MAR, PRIIPs, DORA | norma_ue | P1 | parcial | curado |
| CENDOJ | TS, AN, TSJ filtrado en tributario, contencioso-administrativo, mercantil-regulatorio, PBC/FT | jurisprudencia | P1 | basico | filtrado-curado |
| Banco de Espana | circulares y guias sobre supervision, reporting y sistemas de pago | documento_regulatorio | P2 | basico | curado |
| AEPD | guias y resoluciones sobre onboarding, AML/KYC, conservacion y acceso a datos | guidance | P2 | basico | curado |

## Campos minimos por documento

- `referencia`
- `url_fuente`
- `tipo_fuente`
- `tipo_documento`
- `organismo_emisor`
- `ambito`
- `fecha`
- `estado_vigencia` cuando aplique

## Criterio de salida de Wave 1

La Wave 1 se considera suficientemente cerrada para pasar al motor de aplicabilidad cuando:

1. `CNMV` y `SEPBLAC` tienen mas que documentos semilla y ya cubren obligaciones base de una ESI.
2. `EUR-Lex` incluye al menos `MiFID II`, `MiFIR`, `MAR`, `PRIIPs` y `DORA` con referencias canonicas estables.
3. `CENDOJ` devuelve un corpus filtrado y util, no una capa judicial generica.
4. cada fuente tiene worker, router, smoke check y metadata suficiente para explicabilidad.

## Siguiente paso recomendado

1. endurecer `CNMV`, `SEPBLAC`, `CENDOJ`, `EUR-Lex`
2. despues introducir `perfil_entidad_regulada`
3. solo entonces construir `obligaciones_aplicables`
