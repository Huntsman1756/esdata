# Fase 16.1 XBRL Fixture-First Design

## Objetivo

Implementar el primer slice real de la Fase 16 con un pipeline pequeno, verificable y desacoplado: leer un fixture XBRL local, extraer un subconjunto minimo de facts normalizados, persistirlos en base de datos y exponerlos via API para consulta por entidad y concepto.

Este slice no intenta resolver aun iXBRL completo, taxonomias extensas, ingestion remota ni validacion avanzada con Arelle. El objetivo es fijar el contrato minimo `raw fixture -> parsed facts -> db -> api` con cobertura de tests.

## Alcance aprobado

Incluido en este slice:

- un worker o modulo de carga para leer fixtures XBRL locales desde el repo
- soporte inicial para un fixture XBRL pequeno y determinista
- persistencia minima para filings y facts
- extraccion de campos basicos de facts:
  - `concept`
  - `value`
  - `unit`
  - `context_ref`
  - `period_start`
  - `period_end`
  - `entity_identifier`
- endpoint minimo de lectura:
  - `GET /v1/xbrl/facts?entity_id=...&concept=...`
- tests de parser, persistencia y endpoint

Fuera de alcance en este slice:

- iXBRL completo
- ingestion remota o crawlers ESEF/ESMA
- taxonomias completas
- validacion avanzada XBRL con Arelle
- enlace automatico fuerte con PGC
- surface `GET /v1/xbrl/filings/{filing_id}`

## Enfoque recomendado

Se adopta un enfoque `fixture-first` porque minimiza riesgo y fija primero la forma de los datos. El parser no necesita ser generalista desde el inicio; debe ser suficientemente correcto para un subconjunto pequeno y controlado de XBRL, con output estable y pruebas reproducibles.

El sistema debe persistir facts ya normalizados en lugar de exponer XML bruto. Esto mantiene el patron de arquitectura del repo: workers o modulos de ingesta convierten la fuente original en estructuras internas consultables por API.

## Arquitectura del slice

Patron:

`fixture XBRL local -> parser minimo -> tablas xbrl_filing/xbrl_fact -> consulta API`

Componentes:

1. **Migracion Alembic minima**
- crear `xbrl_filing`
- crear `xbrl_fact`
- indices minimos para `entity_identifier`, `concept`, `period_end` y `filing_id`

2. **Fixtures locales**
- guardar 1 fixture XBRL pequeno en el repo para tests y seed inicial
- el fixture debe contener al menos:
  - un identificador de entidad
  - un contexto temporal
  - una unidad monetaria
  - varios facts con conceptos distintos

3. **Parser minimo**
- leer XML XBRL con libreria estandar o parser XML pequeno ya disponible en Python
- extraer contextos, unidades y facts esenciales
- resolver para cada fact:
  - `concept`
  - `value`
  - `unit`
  - `context_ref`
  - `period_start` / `period_end`
  - `entity_identifier`
- ignorar en este slice dimensiones complejas, footnotes y taxonomia avanzada

4. **Ingestion / loader**
- un modulo de worker o loader cargara el fixture y hara upsert de filing + facts
- el modelo debe ser idempotente por `source_path` o `external_id` de filing y por combinacion estable de fact dentro del filing

5. **Consulta API**
- `GET /v1/xbrl/facts`
- filtros minimos:
  - `entity_id`
  - `concept`
  - `period_end` opcional si el coste marginal es pequeno
- respuesta JSON con `filing` resumido y lista de facts

## Modelo de datos minimo

### xbrl_filing

Campos minimos:

- `id`
- `source_name`
- `source_path`
- `entity_identifier`
- `period_start`
- `period_end`
- `filing_type`
- `created_at`

Reglas:

- `source_path` o equivalente debe permitir idempotencia en fixtures locales
- `entity_identifier` se guarda tal como venga del contexto del filing, sin reconciliar aun contra entidades internas

### xbrl_fact

Campos minimos:

- `id`
- `filing_id`
- `concept`
- `value_raw`
- `value_numeric` nullable
- `unit`
- `context_ref`
- `period_start`
- `period_end`
- `entity_identifier`
- `decimals` nullable
- `created_at`

Reglas:

- `value_numeric` solo se rellena cuando el valor sea parseable numericamante
- `value_raw` siempre conserva el valor textual original
- `entity_identifier` se duplica en facts para simplificar consulta en este MVP

## Contrato funcional

### Ingestion

Entrada:

- ruta local a fixture XBRL controlado por el proyecto

Salida:

- un filing persistido
- facts persistidos y reutilizables

### Consulta

Endpoint inicial:

- `GET /v1/xbrl/facts?entity_id=<id>&concept=<concept>`

Respuesta:

- metadatos de filtro aplicados
- lista de facts ordenados por `period_end` descendente y `concept`
- datos suficientes para depurar el pipeline sin exponer XML bruto

## Errores y limites

- si el fixture no puede parsearse, la ingesta debe fallar con error explicable
- si faltan contextos o unidades, el parser debe degradar de forma controlada: conservar el fact si se puede y dejar campos `NULL` donde falte dato no esencial
- no se intentara validar conformidad XBRL completa
- no se aceptan uploads arbitrarios del usuario en este slice

## Testing

El slice debe seguir TDD y cubrir:

1. **Parser unitario**
- extrae identificador de entidad, periodos y facts de un fixture pequeno
- conserva `value_raw`
- rellena `value_numeric` cuando aplica

2. **Persistencia**
- inserta filing y facts
- reejecutar la carga no duplica registros

3. **API**
- `GET /v1/xbrl/facts` devuelve 200
- filtra por `entity_id`
- filtra por `concept`
- devuelve lista ordenada y estructura estable

4. **Integracion minima**
- fixture local -> parser -> DB -> API

## Trade-offs aceptados

- se prioriza simplicidad sobre cobertura amplia de XBRL
- se duplica `entity_identifier` en facts para simplificar consulta MVP
- no se introduce Arelle en este slice para evitar sobrecarga temprana
- `GET /v1/xbrl/filings/{filing_id}` se difiere a un slice posterior

## Riesgos abiertos

- algunos XBRL reales usan estructuras mas complejas que el fixture MVP
- el parser pequeno puede necesitar refactor cuando entre iXBRL o taxonomia mas rica
- elegir un fixture demasiado simple puede esconder problemas reales; debe tener al menos contexto, unidad y varios conceptos

## Criterio de exito del slice

1. un fixture XBRL local puede cargarse y persistir facts clave
2. los facts son consultables por `entity_id` y `concept` via API
3. la implementacion queda desacoplada del bloque PGC
4. tests verdes del bloque XBRL

## Archivos previsibles

Nuevos o modificados previsibles en implementacion:

- `alembic/versions/..._xbrl.py`
- `apps/workers/xbrl.py`
- `apps/api/routers/xbrl.py`
- `apps/api/schemas.py`
- `apps/api/main.py`
- `apps/api/tests/test_xbrl.py`
- `apps/api/tests/conftest.py`
- `fixtures/` o ruta equivalente para XBRL de prueba
- `docs/manual-usuario/09-referencia-de-endpoints.md` si se expone el endpoint en esta iteracion

## Decision final

Se aprueba implementar Fase 16.1 con un enfoque `fixture-first`, parser minimo, persistencia de filing/facts y endpoint de consulta de facts. iXBRL, Arelle, taxonomias amplias y ESEF remoto quedan explicitamente fuera de este primer corte.
