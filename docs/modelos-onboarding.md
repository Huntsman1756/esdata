# Alta de nuevos modelos AEAT

## Objetivo

Definir el flujo recomendado para incorporar nuevos modelos AEAT sin aumentar deuda tecnica innecesaria.

## Qué necesita un modelo nuevo

Como minimo:

- fila en `aeat_modelo`
- `codigo`
- `nombre`
- `periodo`
- `impuesto`
- `url_info`

Opcionalmente desde el inicio:

- campaña activa inicial en `modelo_campana`
- `url_instrucciones`
- relaciones en `modelo_articulo`
- normativa en `modelo_normativa`

## Flujo recomendado de alta

1. crear o insertar el modelo en `aeat_modelo`
2. verificar que `url_info` responde y contiene referencias utiles a campañas o instrucciones
3. ejecutar `python apps/workers/modelos.py --run-once`
4. revisar si el worker detecta campañas y crea `modelo_campana`
5. validar si extrae correctamente:
   - `modelo_casilla`
   - `modelo_clave`
   - `modelo_instruccion`
6. completar manualmente `modelo_articulo` y `modelo_normativa` si no salen de forma automatica
7. validar la API:
   - `GET /v1/modelos`
   - `GET /v1/modelos/{codigo}`
   - `GET /v1/modelos/{codigo}/casillas`

## Regla de vigencia por defecto

La API debe devolver por defecto la campaña activa mas reciente del modelo.

Regla operativa actual:

- si el worker detecta varias campañas, conserva el historico
- deja `activo=true` solo en la campaña mas nueva
- las campañas antiguas siguen consultables con `?campana=`

## Criterios para decidir si un modelo encaja bien con el scraper actual

El modelo es buen candidato si:

- la sede AEAT publica HTML estable o al menos semiestructurado
- hay patrones recognoscibles de casillas o claves
- existe una campaña o ejercicio identificable en la página

El modelo requiere trabajo específico si:

- la información está solo en PDF o en un formato no parseable fácilmente
- usa nomenclaturas o estructuras distintas al patrón común
- el detalle crítico está en anexos o páginas secundarias no enlazadas limpiamente

## Estructura actual para escalar modelos

El worker de modelos queda repartido ahora así:

- `apps/workers/modelos.py`: orquestación del sync
- `apps/workers/modelos_support.py`: scraping, persistencia y utilidades del dominio de modelos

Esto permite añadir nuevas heurísticas y persistencia sin inflar el entrypoint principal.

## Modelos que ya dependen de IRNR

La cobertura actual del repo ya deja enlazados a `IRNR` estos modelos:

- `124`
- `216`
- `296`

Si se añaden nuevos modelos de no residentes, conviene reutilizar primero los articulos ya cubiertos del `RDL 5/2004` antes de inventar relaciones nuevas.

## Cuándo crear lógica específica por familia de modelos

Si varios modelos comparten el mismo patrón especial, conviene crear helpers específicos en `modelos_support.py`.

Ejemplos:

- modelos informativos con muchas claves y pocos importes
- modelos periódicos con casillas numéricas muy regulares
- modelos con campañas de tipo `T1-2025` o variantes no anuales

## Recomendación práctica

Antes de añadir muchos modelos de golpe, probar siempre el flujo con uno representativo de cada familia. Si aparecen diferencias fuertes de markup, separar la heurística antes de seguir escalando.
