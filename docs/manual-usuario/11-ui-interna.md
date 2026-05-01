# UI interna

## Objetivo

La UI interna sirve para consulta humana rapida y para algunos paneles operativos. No sustituye al backend como fuente canonica.

## Rutas visibles actuales

- `/` — consulta principal
- `/buscar` — resultados por tabs
- `/articulo/[norma]/[numero]` — detalle de articulo
- `/doctrina/[...referencia]` — detalle de doctrina
- `/modelo/[codigo]` — detalle de modelo AEAT
- `/admin/cambios` — panel de cambios regulatorios `[IMPLEMENTED]`
- `/admin/workflow` — panel de workflow de compliance `[IMPLEMENTED]`

## Home de consulta

La home visible actual del App Router es el buscador principal de `apps/web/app/page.tsx`.

`ConsultaClient` sigue existiendo como componente de consulta avanzada y debe tratarse como superficie interna reutilizable, no como fuente unica de verdad sobre la home.

La experiencia principal permite una consulta guiada con campos como:

- texto libre `q`
- `sujeto`
- `pais`

El objetivo es devolver modelos AEAT y resultados complementarios de forma legible.

## Pantalla de busqueda

`/buscar` organiza resultados en tres vistas:

- legislacion
- DGT
- TEAC

Soporta parametros de busqueda y filtros por query string como:

- `q`
- `tab`
- `norma`
- `fuente`
- `ambito`
- `tipo`
- `vigente_en`
- `desde`

## Detalle de articulo

La pantalla de articulo muestra:

- identidad del articulo
- texto vigente
- historial de versiones
- navegacion por fecha de vigencia
- modelos relacionados en sidebar

## Detalle de doctrina

La pantalla de doctrina muestra:

- referencia y organismo emisor
- texto doctrinal
- articulos vinculados con nivel de confianza
- modelos AEAT relacionados derivados de esos articulos

## Detalle de modelo AEAT

La pantalla de modelo muestra:

- identidad y metadatos del modelo
- selector de campana
- instrucciones
- casillas
- claves
- articulos relacionados
- normativa

## Admin de cambios

La pantalla `/admin/cambios` consume `GET /v1/cambios` a traves del proxy server-side `GET /api/cambios`.

Permite filtrar por:

- fuente
- estado
- prioridad
- obligacion afectada

Muestra impacto, accion recomendada, fecha y obligaciones afectadas.

## Admin de workflow

La pantalla `/admin/workflow` consume `GET /v1/compliance/workflow` a traves del proxy server-side `GET /api/workflow`.

Muestra:

- identificador del caso
- estado
- cambio y obligacion asociados
- owner
- fecha objetivo
- checklist
- acciones recomendadas
- notas y resultado de revision

## Regla de interpretacion

Si hay duda entre lo que muestra la UI y lo que devuelve la API, la superficie canonica sigue siendo la `API`.

La UI es una capa de presentacion y consulta.
