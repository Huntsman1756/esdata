# Diseno del buscador profesional de esdata

## Objetivo

La primera capa de producto de `esdata` debe hacer visible en menos de 10 segundos el valor ya construido en backend: busqueda fiscal util, doctrina DGT y TEAC enlazada con articulos, y contexto normativo consultable sin navegar varias fuentes oficiales.

La idea principal es que el usuario piense al entrar: `Aqui encuentro criterio fiscal rapido`.

## Alcance de este corte

Se construye un frontend pequeno en `apps/web` que consume la API publica existente.

Incluye:

- Home con buscador principal.
- Resultados para legislacion y doctrina.
- Detalle de doctrina con articulos vinculados.
- Despliegue como servicio separado dentro del mismo proyecto Railway.

No incluye en esta fase:

- Radar o alertas.
- Detalle de articulo con doctrina relacionada desde API nueva.
- Paginacion real en backend.
- Nuevos endpoints salvo que aparezca un bloqueo pequeno durante la implementacion.

## Arquitectura

Estructura propuesta:

```text
esdata/
|-- apps/
|   |-- api/
|   |-- workers/
|   `-- web/
```

Stack propuesto:

- Next.js 15 con App Router.
- TypeScript estricto.
- Tailwind CSS sin librerias UI adicionales.
- Fetch server-side hacia la API FastAPI.

Ruta de datos:

```text
Browser -> Next.js -> FastAPI -> PostgreSQL
```

El frontend no accede nunca a la base de datos directamente.

## Direccion visual

La interfaz debe sentirse editorial y profesional, no como dashboard generico.

Principios:

- Fondo calido claro tipo papel.
- Jerarquia tipografica sobria y legible.
- Mucho aire y lectura comoda.
- Color reservado para organismo, confianza y norma activa.
- Sin decoracion gratuita, sin tarjetas pesadas, sin estetica AI generica.

Paleta base:

- Fondo: `stone-50`.
- Texto principal: `stone-900`.
- DGT: azul.
- TEAC: violeta.
- Confianza 1.0: verde.
- Confianza menor a 1.0: ambar.

Tipografia:

- UI general y navegacion: sans.
- Texto legal largo: serif.
- Referencias normativas puntuales: mono solo cuando aporte claridad.

## Pantalla 1: Home

Ruta: `GET /`

Objetivo: llevar al usuario a una busqueda util lo antes posible.

Elementos:

- Marca `esdata`.
- Input principal grande con placeholder de busqueda fiscal.
- Tabs: `Legislacion`, `DGT`, `TEAC`.
- Lista de ejemplos clicables.
- Bloque de cobertura legislativa.
- Estado operativo y fecha de actualizacion.

Comportamiento:

- `Enter` redirige a `/buscar?q=...&tab=...`.
- Los ejemplos cargan una query real y, si aplica, parametros utiles como `norma=LIS`.
- El tab activo decide si la consulta va a legislacion o doctrina.

Fuentes de datos:

- `GET /v1/legislacion/cobertura`
- `GET /status`

La home no muestra total agregado de doctrina en esta fase porque el backend actual no expone ese dato de forma fiable.

## Pantalla 2: Resultados

Ruta: `GET /buscar?q=...`

Objetivo: presentar resultados utiles con el menor numero posible de decisiones de interfaz.

Variantes:

- `tab=legislacion`
- `tab=dgt`
- `tab=teac`

Elementos comunes:

- Buscador persistente en cabecera.
- Tabs de cambio rapido entre fuentes.
- Contador simple de resultados mostrados.
- Lista de resultados con fragmentos.
- Filtros solo de parametros que ya existen en API.

Resultados de legislacion:

- Codigo de norma.
- Numero de articulo si aplica.
- Fecha o vigencia visible.
- Titulo.
- Fragmento con `<mark>`.
- CTA a detalle del articulo.

Resultados de doctrina:

- Badge de organismo.
- Referencia.
- Fecha.
- Titulo.
- Fragmento.
- Articulos relacionados y confianza cuando existan.
- CTA a detalle del criterio.

Filtros fase 1:

- Legislacion: `norma`, `fuente`, `ambito`, `tipo`, `vigente_en`.
- Doctrina: `tipo`, `desde`.

No hay paginacion real en este corte. La UI debe decir claramente que muestra los primeros `N` resultados devueltos por la API.

Fuentes de datos:

- `GET /v1/buscar`
- `GET /v1/doctrina/buscar`

## Pantalla 3: Detalle de doctrina

Ruta: `GET /doctrina/{referencia}`

Objetivo: demostrar el valor diferencial del sistema enlazando texto doctrinal y articulos concretos.

Layout:

- Cabecera con vuelta a resultados.
- Identidad del criterio: referencia, organismo, tipo y fecha.
- Columna principal con el texto doctrinal.
- Columna lateral con articulos vinculados, confianza y metodo de enlace.

Representacion de confianza:

- `1.0`: check verde y mensaje `Enlace de confianza maxima`.
- `0.85 - 0.99`: estado ambar con mensaje `Enlace probable`.
- `< 0.85`: estado informativo con mensaje `Enlace por revisar`.

Fuente de datos:

- `GET /v1/doctrina/{referencia:path}`

## Contrato con la API real

El frontend de fase 1 se apoya en contratos ya existentes.

| Elemento UI | Endpoint |
| --- | --- |
| Busqueda legislacion | `GET /v1/buscar?q=...` |
| Busqueda doctrina | `GET /v1/doctrina/buscar?q=...` |
| Cobertura de normas | `GET /v1/legislacion/cobertura` |
| Estado operativo | `GET /status` |
| Detalle doctrina | `GET /v1/doctrina/{referencia}` |

Limitaciones conocidas del backend actual:

- No hay paginacion explicita.
- No hay total agregado de doctrina listo para home.
- El detalle de articulo no expone doctrina relacionada en esta fase.

El diseno evita depender de piezas que todavia no existen.

## Despliegue

- `apps/web` se desplegara como servicio separado dentro del mismo proyecto Railway.
- Variable esperada: `NEXT_PUBLIC_API_URL=https://esdata-production.up.railway.app`
- Revalidacion moderada en contenido no critico: `revalidate: 3600` donde tenga sentido.

## Fases

### Fase 1

- Home.
- Resultados de legislacion y doctrina.
- Detalle de doctrina.

### Fase 2

- Detalle de articulo mejorado.
- Navegacion cruzada mas rica entre articulo y doctrina.

### Fase 3

- Radar o capa de retencion sobre cambios recientes y criterio nuevo.

## Riesgos y decisiones

- Riesgo: intentar construir una UX mas ambiciosa que la API real.
  - Decision: limitar filtros y vistas a contratos ya existentes.
- Riesgo: front demasiado generico o tipo dashboard.
  - Decision: direccion editorial sobria y centrada en lectura.
- Riesgo: retrasar el front esperando mejoras operativas no bloqueantes.
  - Decision: el buscador profesional puede construirse encima del backend actual sin esperar nuevas features de API.

## Criterio de exito

Se considerara un buen primer corte si:

- un usuario puede ejecutar una busqueda fiscal real en segundos,
- distinguir entre legislacion, DGT y TEAC sin confusion,
- abrir un criterio doctrinal y entender rapidamente que articulos soportan el enlace,
- y percibir que `esdata` ya tiene un motor real detras, no una demo estatica.
