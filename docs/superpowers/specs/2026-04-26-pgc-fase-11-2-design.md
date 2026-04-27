# PGC Fase 11.2 Design

## Objetivo

Extender el slice PGC tras `11.1` para cubrir tres capacidades nuevas sin abrir todavia `11.3-11.5` completas:

- ampliar el plan 2021 hacia una cobertura real y trazable del cuadro de cuentas
- enriquecer la consulta estructurada de cuentas y anadir una superficie de busqueda libre
- activar un primer slice de `pgc_norma_valoracion` enlazado a cuentas cuando aplique

El resultado buscado es una `11.2` util y navegable, pero aun contenida: sin logica fiscal, sin referencias AEAT y sin semantica contable avanzada.

## Decision principal

Se adopta una estrategia integrada para `11.2`:

- ampliar `apps/workers/pgc.py` con un dataset estructurado y trazable en repo
- mantener `GET /v1/pgc/cuentas` como endpoint estructurado principal, con filtros ampliados
- anadir `GET /v1/pgc/buscar` para texto libre
- activar `GET /v1/pgc/normas-valoracion` con un slice minimo de normas enlazadas a cuentas cuando haya correspondencia clara

No se incorpora aun parser BOE operativo como dependencia del runtime. Si se usa ayuda de parser/normalizador, sera solo como soporte de construccion o validacion del dataset, no como contrato de ejecucion del sistema.

## Alcance

- ampliar `PGC_ACCOUNTS` o moverlo a un dataset dedicado mantenido en repo
- cubrir clases y grupos completos, y cuentas/subcuentas donde la fuente estructurada sea fiable
- ampliar `list_pgc_cuentas(...)` con filtros estructurados adicionales
- crear superficie `buscar` para texto libre
- poblar `pgc_norma_valoracion` con un bloque inicial de normas enlazadas a cuentas cuando aplique
- ampliar tests del worker y de la API para el nuevo slice
- actualizar roadmap maestro para reflejar cierre de `11.2` cuando se implemente

## Fuera de alcance

- parser BOE obligatorio en runtime
- logica de asientos, `debe_haber`, `tipo_operacion` u otra semantica contable avanzada
- activacion funcional completa de `pgc_estado_financiero`
- referencias fiscales (`11.4`)
- referencias AEAT (`11.5`)
- logica fiscal o calculos tributarios

## Arquitectura

### Worker

`apps/workers/pgc.py` se extiende para dejar de ser solo un seed minimo de `11.1`.

Responsabilidades en `11.2`:

- cargar `pgc_marco` vigente
- cargar un dataset ampliado de cuentas 2021
- cargar un dataset minimo de `pgc_norma_valoracion`
- mantener idempotencia en reejecucion

Se permite extraer los datasets a un modulo dedicado si mejora legibilidad, por ejemplo:

- `apps/workers/pgc_dataset.py`

Esa extraccion es aceptable solo si ayuda a que `pgc.py` no se convierta en un archivo inmanejable. El criterio principal es mantener limites claros entre:

- codigo de carga/upsert
- datos estructurados del plan
- datos estructurados de normas

### Datos de cuentas

La fuente operativa de `11.2` sera un dataset estructurado en repo y trazable a BOE.

Cada cuenta seguira el modelo actual:

- `codigo`
- `descripcion`
- `nivel`
- `padre_codigo`
- `grupo`
- `clase`
- `saldo_normal`
- `tipo_cuenta`
- `nota`

Reglas de modelado:

- clases y grupos deben quedar completos
- cuentas/subcuentas se cargan cuando la estructura sea fiable
- si una zona del plan no es fiable todavia, se prioriza consistencia estructural sobre volumen
- `padre_codigo` debe permitir navegar el arbol sin inferencias especiales

### Datos de normas de valoracion

`11.2` activa un primer slice funcional de `pgc_norma_valoracion`.

Campos funcionales del slice:

- `norma_ref`
- `articulo`
- `descripcion`
- `cuenta_id` cuando exista enlace claro

Reglas:

- una norma puede existir sin cuenta asociada
- el enlace a cuenta solo se crea cuando la correspondencia sea clara
- no se activa en `11.2` semantica adicional como `debe_haber`

### API

#### `GET /v1/pgc/cuentas`

Sigue siendo la superficie estructurada principal.

Contrato:

- `{"marco": {...}, "cuentas": [...]}`

Filtros previstos:

- `codigo`
- `q`
- `tipo`
- `nivel`
- `clase`
- `grupo`
- `padre_codigo`

Orden:

- estable por `codigo`

#### `GET /v1/pgc/buscar`

Nueva superficie de texto libre.

Contrato inicial recomendado:

- `{"marco": {...}, "resultados": [...]}`

Busqueda sobre:

- `codigo`
- `descripcion`
- `nota` cuando exista

Orden:

- coincidencia simple primero
- `codigo` como desempate estable

No se introduce todavia full-text real ni indices especiales como requisito del slice.

#### `GET /v1/pgc/normas-valoracion`

Nueva superficie minima para el slice de normas.

Contrato inicial recomendado:

- `{"marco": {...}, "normas": [...]}`

Filtros minimos:

- `norma_ref`
- `cuenta_codigo`

## Archivos implicados

- `apps/workers/pgc.py`
- `apps/workers/pgc_dataset.py` o equivalente, si se decide extraer datos
- `apps/api/pgc_data.py`
- `apps/api/routers/pgc.py`
- `apps/api/schemas.py`
- `apps/api/tests/conftest.py`
- `apps/api/tests/test_pgc.py`
- `docs/master-execution-roadmap.md`

## Tests

### Worker

Cobertura minima:

- carga marco una sola vez
- carga dataset ampliado de cuentas sin duplicar
- carga normas minimas sin duplicar
- reejecucion idempotente

### API cuentas

Cobertura minima:

- `GET /v1/pgc/cuentas` responde `200`
- devuelve `marco + cuentas`
- filtra por `codigo`
- filtra por `tipo`
- filtra por `nivel`
- filtra por `clase`
- filtra por `grupo`
- filtra por `padre_codigo`
- mantiene orden estable

### API busqueda

Cobertura minima:

- `GET /v1/pgc/buscar` responde `200`
- encuentra por texto en descripcion
- encuentra por codigo parcial
- orden estable y predecible

### API normas

Cobertura minima:

- `GET /v1/pgc/normas-valoracion` responde `200`
- filtra por `norma_ref`
- filtra por `cuenta_codigo`
- soporta normas enlazadas y normas sin cuenta

## Riesgos

### Riesgo 1

La pretension de cobertura real completa puede disparar el tamano del slice.

Mitigacion:

- priorizar estructura fiable y trazable
- permitir dataset amplio pero no necesariamente exhaustivo al 100% literal si eso rompe calidad

### Riesgo 2

`/buscar` puede duplicar la utilidad de `/cuentas?q=`.

Mitigacion:

- dejar `/cuentas` como consulta estructurada
- dejar `/buscar` como superficie de texto libre y ranking simple

### Riesgo 3

Las normas enlazadas a cuentas pueden inducir asociaciones debiles.

Mitigacion:

- enlazar solo cuando la correspondencia sea clara
- permitir normas sin cuenta asociada

## Criterio de exito

1. el plan 2021 queda ampliado de forma trazable y util sobre la base de `11.1`
2. `GET /v1/pgc/cuentas` soporta filtros estructurados ampliados
3. `GET /v1/pgc/buscar` queda operativo para texto libre
4. `GET /v1/pgc/normas-valoracion` queda operativo con slice minimo enlazado a cuentas cuando aplique
5. tests del slice `11.2` estan en verde
6. roadmap actualizado deja `11.3-11.5` pendientes
