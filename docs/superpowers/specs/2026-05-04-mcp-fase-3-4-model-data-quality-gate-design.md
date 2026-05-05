# Diseno: MCP Fase 3.4 - Detector de contaminacion de datos de modelos

## Objetivo

Crear un quality gate pequeno y determinista que detecte contaminacion en los datos AEAT de `modelos` antes de merge/deploy.

El gate debe cubrir dos superficies distintas:

- contaminacion en archivos fuente de seed/script
- contaminacion ya persistida en DB

El objetivo no es validar toda la calidad del dominio fiscal. El objetivo de 3.4 es bloquear exactamente los casos que el plan MCP considera peligrosos para la cadena de confianza:

- hostnames no canonicos
- modelos/impuestos o claves sospechosas en mappings de articulos
- mappings sin fuente fuerte
- metadata curada presentada como si fuera oficial o suficientemente verificada

## Contexto

Tras 3.1, 3.2 y 3.3 el repo ya fija:

- una via canonica AEAT de dos pasos
- enlaces `modelo_articulo` fuertes solo con provenance explicita
- gating de `completeness`/`verified` en runtime para que modelos parciales no aparenten verificacion operativa

El hueco que queda es preventivo:

- hoy una contaminacion nueva puede entrar por seeds/scripts y no detectarse hasta runtime
- tambien puede existir drift en DB por inserciones manuales, rutas legacy o datos historicos incoherentes con el contrato actual

La Fase 3.4 introduce un detector explicito y reproducible en `scripts/maintenance/` para cortar ese drift antes de que vuelva a presentarse como superficie MCP fiable.

## Decision de diseno

Se adopta un unico script de mantenimiento con dos familias de chequeos:

1. chequeos estaticos sobre archivos fuente AEAT relevantes
2. chequeos DB-backed sobre tablas persistidas de `modelos`

La implementacion se concentra en:

- `scripts/maintenance/check_model_data_quality.py`
- `scripts/tests/test_check_model_data_quality.py`
- una integracion minima en `.github/workflows/ci.yml`

No se crea un framework generico de quality gates ni un sistema de reglas configurable. La fase pide un detector especifico para un conjunto pequeno de contaminaciones bien conocidas.

## Alcance exacto aprobado

### Static checks

El script inspecciona estos archivos fuente:

- `scripts/seed-modelos.py`
- `scripts/seed-modelos-v2.py`
- `scripts/data/seed_modelo_articulo.py`

Reglas estaticas obligatorias:

1. las URLs AEAT/BOE declaradas en esos archivos solo pueden usar hosts canonicos:
   - `sede.agenciatributaria.gob.es`
   - `www.boe.es`
2. no se aceptan URLs `http://`
3. cualquier mapping fuerte declarado en `scripts/data/seed_modelo_articulo.py` debe seguir teniendo `url_fuente` no vacia

Justificacion:

- el roadmap menciona hostnames no canonicos como contaminacion concreta
- 3.2 ya fijo que una fila fuerte sin `url_fuente` no debe presentarse en runtime como verdad operativa
- el check estatico detecta contaminacion antes incluso de sembrar la DB

### DB checks

El script inspecciona estas tablas si existe `DATABASE_URL`:

- `aeat_modelo`
- `modelo_campana`
- `modelo_normativa`
- `modelo_articulo`
- `modelo_campana_operativa`

Reglas DB obligatorias:

1. `aeat_modelo.url_info` solo puede usar host canonico AEAT cuando no sea null
2. `modelo_campana.url_instrucciones`, `url_normativa`, `url_formato` solo pueden usar hosts canonicos AEAT o BOE segun corresponda
3. `modelo_normativa.url_boe` solo puede usar `www.boe.es`
4. `modelo_articulo` debe marcar finding si una fila incumple cualquiera de estas condiciones de enlace fuerte esperado:
   - `url_fuente` nula o vacia
   - `metodo_enlace != 'manual_official'`
   - `confianza_enlace != 1.0`
5. `modelo_articulo.norma` debe marcar finding si contiene pseudo-claves sospechosas heredadas en lugar de una norma real, como:
   - `IRPF`, `IS`, `IVA`, `OP.347`, `FACTA`, `IVA.A`, `IRPF.T`, `DAC2`, `SII`, `BIEN.EX`, `PROV.NR`
6. `modelo_articulo.url_fuente` debe marcar finding si usa host no canonico
7. `modelo_campana_operativa` debe marcar finding cuando un registro se presenta como curado/manual curado pero queda en estado no curado o derivado de borrador, en particular:
   - `origen_metadato in {'seed_curado', 'manual_curado'}` con `estado_metadato in {'borrador', 'inferido'}`
   - `estado_metadato = 'curado'` junto con `origen_metadato = 'worker_derivado'`

Justificacion:

- 3.2 ya definio que el contrato fuerte visible en runtime es `manual_official + 1.0 + url_fuente`
- el plan 3.4 pide detectar modelos/impuestos sospechosos y mappings sin fuente
- el plan tambien pide detectar metadata curada presentada como oficial; en este repo eso se refleja en la pareja `origen_metadato` / `estado_metadato`

## Semantica de findings

Cada finding debe incluir como minimo:

- `check_id`
- `severity`
- `location`
- `message`

`location` sera:

- ruta de archivo + linea cuando el finding venga del analisis estatico
- tabla + clave suficientemente identificable cuando venga de DB

Severidades aprobadas para 3.4:

- `high`
- `medium`

No hace falta introducir mas granularidad en esta fase.

Clasificacion propuesta:

- `high`:
  - host no canonico
  - `http://`
  - mapping fuerte sin `url_fuente`
  - provenance fuerte rota en `modelo_articulo`
  - metadata curada incoherente con estado de borrador/inferido
- `medium`:
  - pseudo-clave sospechosa en `modelo_articulo.norma`

## Interfaz del script

CLI minima aprobada:

- `--json` para salida estructurada de CI
- `--db-url` opcional para sobreescribir `DATABASE_URL`
- `--static-only` para ejecutar solo chequeos estaticos
- `--db-only` para ejecutar solo chequeos DB

Comportamiento por defecto:

- si hay DB disponible, ejecutar static + DB
- si no hay DB disponible y no se pidio `--static-only`, salir con codigo `2`

Codigos de salida aprobados:

- `0`: sin findings
- `1`: findings detectados
- `2`: error de invocacion o falta DB para el modo solicitado

No se anade `--fix`; esta fase es de deteccion, no de autocorreccion.

## Estrategia tecnica

### Estructura interna del script

El script se divide en helpers pequenos y testeables:

- normalizacion de DB URL
- extraccion/validacion de hostnames
- chequeos estaticos por archivo
- chequeos DB por tabla o familia
- serializacion final de findings

Se prefiere `sqlalchemy` para los chequeos DB por coherencia con otros scripts de mantenimiento ya presentes en el repo.

### Regla de host canonico

La validacion de host debe ser deliberadamente conservadora:

- AEAT: solo `sede.agenciatributaria.gob.es`
- BOE: solo `www.boe.es`

No se aceptan subdominios alternativos ni hosts historicos por defecto. Si en el futuro aparece una excepcion valida, se abrira un slice separado con evidencia concreta.

### Regla de pseudo-claves sospechosas

Para minimizar inventos, el set inicial de claves sospechosas de `modelo_articulo.norma` se reutiliza del guardarrail ya fijado en `scripts/tests/test_seed_modelo_articulo.py`.

Esto evita duplicar una segunda definicion semantica distinta del mismo problema.

## Integracion CI aprobada

La integracion minima entra en un job Python ya bootstrappeado con Postgres y migraciones aplicadas.

Se anade un paso explicito tras `alembic upgrade heads` en `test-python`:

- ejecutar `python scripts/maintenance/check_model_data_quality.py`

Razon:

- 3.4 necesita DB real para la mitad de sus reglas
- no tiene sentido meterlo en `lint` o `security-audit`, que hoy no levantan la DB de test
- asi el gate se ejecuta sobre un schema/migraciones reales del CI existente, con coste operacional minimo

No se crea un job nuevo salvo que el rojo lo obligue.

## Estrategia de tests aprobada

La implementacion se hara con TDD.

### Tests del script

Se crea `scripts/tests/test_check_model_data_quality.py`.

Casos minimos a fijar primero en rojo:

1. detecta URL estatica con host no canonico
2. acepta URL estatica con host canonico
3. detecta fila `modelo_articulo` sin provenance fuerte
4. detecta pseudo-clave sospechosa en `modelo_articulo.norma`
5. detecta incoherencia curado/borrador en `modelo_campana_operativa`
6. `run()` devuelve `1` cuando hay findings
7. `run()` devuelve `0` cuando no hay findings

Los tests deben preferir fixtures pequenas sobre schema real completo cuando sea posible. Solo para chequeos DB se montara un SQLite temporal minimo con las tablas necesarias del caso.

### Verificacion funcional del script

Ademas de tests unitarios, la verificacion del slice debe incluir una ejecucion segura del script:

- `python scripts/maintenance/check_model_data_quality.py --static-only`

Y una verificacion de CI local equivalente via tests/lint del scope tocado.

## Archivos a tocar

Obligatorios:

- `scripts/maintenance/check_model_data_quality.py`
- `scripts/tests/test_check_model_data_quality.py`
- `.github/workflows/ci.yml`
- `docs/master-execution-roadmap.md`
- `docs/operations/agent-notes.md`

Opcionales solo si el rojo lo exige:

- `docs/CHANGELOG.md`
- `docs/MEMO.md`

## Fuera de alcance

3.4 no debe:

- reescribir seeds AEAT
- corregir datos automaticamente
- ampliar el runtime API
- cambiar el contrato JSON de `modelos`
- introducir migraciones nuevas
- validar cobertura funcional completa de todas las campañas AEAT
- convertirse en un framework generico de data quality para todo el repo

## Riesgos y decisiones explicitas

- un gate conservador puede detectar historicos viejos o fixtures no alineados; eso es aceptable si la finding es precisa y accionable
- el script debe evitar falsos positivos por `None`/campos vacios que no apliquen a una columna concreta; solo se valida host cuando exista URL
- si algun seed legacy sigue conteniendo hostnames no canonicos por diseño historico, 3.4 debe fallar igualmente: la fase existe precisamente para hacer visible esa contaminacion
- si el CI Postgres no contiene datos suficientes para disparar los checks DB, los tests dedicados del script siguen siendo la evidencia primaria del comportamiento

## Criterio de cierre

3.4 se podra cerrar cuando:

- exista `scripts/maintenance/check_model_data_quality.py` con static + DB checks
- haya tests dedicados en rojo->verde para los findings principales
- el CI ejecute el script en un job con DB bootstrappeada
- la verificacion fresca del slice quede verde
- el roadmap deje preparado el siguiente paso exacto hacia 4.x o el siguiente slice MCP decidido
