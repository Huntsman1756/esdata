# Sprint N - MiCA emisor_token

## Scope

Sprint N adds the `emisor_token` profile for MiCA token issuers and maps base obligations for:

- ART issuers under MiCA Title III.
- EMT issuers under MiCA Title IV.

The sprint deliberately does not load new RTS/ITS. It reuses the canonical MiCA base norm `32023R1114` loaded in Sprint M.

## Gap: supervisor ART/EMT corpus

Estado: 0 documentos BdE/CNMV especificos de ART/EMT cargados en `documento_interpretativo`.

Motivo: no hay corpus supervisor ART/EMT cargado con guias, circulares o instrucciones tecnicas especificas para emisores ART/EMT. No se inventan documentos BdE/CNMV ni se usan fuentes LLM como fuente de verdad.

Impacto:

- `obtener_documentos_cnmv_perfil('emisor_token')` puede devolver 0 documentos especificos.
- Esto es un gap de corpus supervisor, no un fallo de las obligaciones base.
- Las obligaciones base de `emisor_token` se verifican contra MiCA `32023R1114`.

Pendiente Sprint O o posterior:

- Circular o guia CNMV sobre autorizacion ART cuando se publique/cargue.
- Guia BdE sobre EMT cuando se publique/cargue.
- Q&A ESMA MiCA ART/EMT si se incorpora a `documento_interpretativo`.

## Obligations seeded

ART:

- `art. 18` - autorizacion CNMV para emitir ART.
- `art. 19` - white paper ART, con contexto de publicacion de arts. 19-22.
- `art. 25` - obligaciones continuas del emisor ART.
- `art. 35` - reserva de activos, con contexto de custodia del art. 36.
- `art. 45` - restricciones para ART significativo, `completeness='parcial'`.

EMT:

- `art. 48` - requisitos y notificacion BdE para EMT, `completeness='parcial'`.
- `art. 51` - white paper EMT, `completeness='parcial'`.
- `art. 55` - reembolso EMT al valor nominal, `completeness='parcial'`.

No se crea ningun perfil separado `emisor_art` o `emisor_emt`.

## MCP behavior

The MCP routing policy now routes:

- CASP and crypto service-provider queries to `perfil_codigo='casp'`.
- ART/EMT issuer, white paper, ficha referenciada, ficha de dinero electronico and token issuer queries to `perfil_codigo='emisor_token'`.

The policy explicitly warns that the ART/EMT supervisor corpus can be empty and that the correct fallback is to answer from `obtener_obligaciones_perfil`, while naming the corpus gap.
