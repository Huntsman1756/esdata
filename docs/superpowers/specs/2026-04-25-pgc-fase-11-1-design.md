# Fase 11.1 PGC Minimal Slice Design

## Objetivo

Definir el slice minimo ejecutable de `Fase 11.1` para incorporar la base del Plan General Contable (PGC) en `esdata` sin mezclar todavia versionado 2008/2021 ni vinculos fiscales/AEAT avanzados.

El resultado de este slice debe ser una base PGC consultable por API con datos semilla muy pequenos, tests verdes y trazabilidad suficiente para crecer en `11.2`, `11.3`, `11.4` y `11.5`.

## Estado real del repo

- Ya existe `alembic/versions/20260425_0010_pgc.py`.
- Esa migracion crea tablas base PGC, pero tambien adelanta seeds y vinculos que el roadmap actual reserva para `11.4` y `11.5`.
- El roadmap activo fija `11.1` como slice minimo: marco PGC + seed 2021 minimo + worker/router + tests.

## Decision principal

Se mantiene una estrategia estricta para `11.1` sobre la base ya iniciada en el repo:

- reutilizar `20260425_0010_pgc.py`
- recortar su comportamiento para que `11.1` no exponga funcionalidad de `11.4` ni `11.5`
- permitir que la migracion deje creadas tablas futuras, pero vacias y sin seeds funcionales
- mover la carga de datos del slice al worker
- reemplazar el seed amplio actual del worker por uno nuevo, limpio y trazable

No se crea una nueva migracion paralela para rehacer PGC desde cero.

## Alcance de 11.1

Incluido:

- tablas operativas de `pgc_marco` y `pgc_cuenta`
- tablas futuras permitidas pero sin uso funcional en `11.1`
- worker nuevo `apps/workers/pgc.py`
- seed 2021 amplio pero controlado, reemplazando el dataset actual del worker
- endpoint `GET /v1/pgc/cuentas`
- filtros basicos por `codigo`, `q` y `tipo`
- schemas Pydantic minimos para respuesta de lista
- tests unitarios de worker y router
- inclusion del router en `apps/api/main.py`

Excluido:

- versionado 2008 vs 2021
- endpoint de detalle enriquecido `/v1/pgc/cuentas/{codigo}`
- full-text avanzado de `GET /v1/pgc/buscar`
- poblar `pgc_cuenta_fiscal_ref`
- poblar `pgc_cuenta_modelo_aeat_ref`
- enriquecimiento con modelos AEAT o articulos fiscales
- estados financieros y normas de valoracion como parte funcional del slice

## Diseno tecnico

### Migracion

`alembic/versions/20260425_0010_pgc.py` se ajusta para que en `11.1`:

- cree `pgc_marco` y `pgc_cuenta` como tablas operativas del slice
- mantenga creadas `pgc_norma_valoracion`, `pgc_estado_financiero`, `pgc_cuenta_fiscal_ref` y `pgc_cuenta_modelo_aeat_ref` solo como estructura futura
- elimine todos los seeds adelantados de normas de valoracion, estados financieros, vinculos fiscales y vinculos AEAT
- no deje ningun comportamiento funcional que haga parecer disponibles `11.4` o `11.5`

La migracion queda centrada en esquema. La carga de datos de `11.1` vive en el worker.

### Worker

Se reemplaza `apps/workers/pgc.py` por un worker nuevo, limpio y alineado con `11.1`, con el mismo estilo pragmatico de workers existentes:

- CLI con `--db-url` y `--run-once`
- acceso DB via `create_engine`
- funcion `run_sync(...)`
- logging simple

El worker de `11.1` no necesita parser BOE completo. Puede trabajar con un seed estructurado propio y una referencia BOE estable para:

- insertar o actualizar `pgc_marco`
- insertar o actualizar un conjunto amplio pero controlado de cuentas PGC 2021

El worker debe:

- eliminar cualquier carga de vinculos fiscales o AEAT
- reemplazar el seed actual, que contiene ruido y errores de calidad, por uno nuevo y fiable
- mantener idempotencia por `codigo`

La meta de este worker es fijar el contrato de ingestion minima y util, no cerrar la cobertura completa del plan contable.

### API

Se anaden:

- `apps/api/routers/pgc.py`
- `apps/api/services/pgc.py`
- nuevos schemas en `apps/api/schemas.py`

El router seguira el patron actual:

- `APIRouter(prefix="/v1/pgc", tags=["pgc"])`
- `db_session()`
- queries SQL encapsuladas en `services/pgc.py`

Endpoint inicial:

- `GET /v1/pgc/cuentas`

Contrato inicial:

- `{"marco": {...}, "cuentas": [...]}`

Campos minimos esperados por cuenta:

- `codigo`
- `descripcion`
- `nivel`
- `padre_codigo`
- `tipo_cuenta`
- `grupo`
- `saldo_normal`
- `vigente`

Filtros minimos:

- `codigo`
- `q`
- `tipo`

Orden:

- estable por `codigo`

## Datos semilla recomendados

El seed no sera ultraminimo ni casi completo.

Marco:

- una referencia PGC 2021 clara y trazable al BOE

Cuentas:

- seed nuevo que reemplace por completo el dataset actual del worker
- alcance amplio pero controlado, suficiente para navegacion, filtros y validacion funcional
- incluir raices, nodos intermedios y cuentas conocidas de interes practico

Minimos que deben quedar incluidos:

- `1`, `2`, `4`, `6`, `7`
- `40`, `43`, `60`, `62`, `70`
- `47`
- `472`
- `477`

Esto permite validar:

- jerarquia simple y navegable
- consulta por codigo
- consulta textual
- disponibilidad de cuentas relevantes sin activar todavia vinculos oficiales

## Tests

### Worker

Archivo: `apps/workers/tests/test_pgc.py`

Cobertura minima:

- inserta marco PGC minimo una sola vez
- inserta el nuevo seed de cuentas una sola vez
- `run_sync(..., run_once=True)` completa sin errores en SQLite en memoria o fixture equivalente
- una segunda ejecucion no duplica filas

### Router

Archivo: `apps/api/tests/test_pgc.py`

Cobertura minima:

- `GET /v1/pgc/cuentas` responde `200`
- devuelve estructura `{"marco": {...}, "cuentas": [...]}`
- permite filtrar por `codigo`
- permite filtrar por `q`
- permite filtrar por `tipo`
- orden estable de resultados

## Riesgos y mitigaciones

### Riesgo 1

La migracion `0010` mezcla varias subfases.

Mitigacion:

- editarla explicitamente para reducir alcance funcional de `11.1`
- reflejar en docs que los vinculos fiscales/AEAT quedan pospuestos

### Riesgo 2

Arrastrar al seed nuevo errores del dataset amplio actual.

Mitigacion:

- reemplazar el dataset actual en vez de depurarlo parcialmente
- dejar un conjunto nuevo, limpio y verificable

### Riesgo 3

Hacer un seed demasiado grande y vaciar de contenido `11.2`.

Mitigacion:

- mantener un seed amplio pero controlado
- reservar plan 2021 completo y parser profundo para la siguiente subfase

## Criterio de aprobacion de 11.1

`11.1` se considera bien resuelta cuando:

1. existe un worker PGC minimo funcional
2. existe `GET /v1/pgc/cuentas` operativo
3. el seed 2021 es amplio pero controlado, estable y trazable
4. `0010_pgc.py` ya no adelanta comportamiento funcional de `11.4` y `11.5`
5. tests de worker y router estan en verde

## Archivos previstos

Modificar:

- `alembic/versions/20260425_0010_pgc.py`
- `apps/api/main.py`
- `apps/api/schemas.py`

Crear:

- `apps/workers/pgc.py`
- `apps/workers/tests/test_pgc.py`
- `apps/api/routers/pgc.py`
- `apps/api/services/pgc.py`
- `apps/api/tests/test_pgc.py`

## No objetivos de este slice

- no cerrar el modelo contable completo
- no modelar todavia reporting financiero estructurado
- no enlazar aun PGC con articulos fiscales reales ni campanas AEAT
- no introducir logica de negocio en frontend
