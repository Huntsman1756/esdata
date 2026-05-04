# Diseno: MCP Fase 3.1 - Via canonica de seed AEAT

## Objetivo

Fijar una unica via canonica para poblar datos AEAT en el repo MCP y rebajar las rutas legacy para que no aparenten ser equivalentes ni autoritativas.

## Contexto

Hoy conviven varias rutas de seed AEAT con distinto nivel de calidad y distinta semantica:

- `scripts/seed-modelos.py` hace el bootstrap de `aeat_modelo` y carga relaciones `modelo_articulo` con fuente declarada.
- `scripts/seed-modelos-v2.py` carga datos por campana (`modelo_campana`, `modelo_casilla`, `modelo_clave`, `modelo_instruccion`, `modelo_normativa`, `modelo_campana_operativa`), pero depende de que `aeat_modelo` exista previamente.
- `scripts/data/seed_modelos.py`, `scripts/data/seed_aeat_models.py`, `scripts/data/seed_modelo_articulo.py` y `scripts/seed-fiscal-modelos.sql` siguen ofreciendo rutas paralelas manuales, curadas o historicas.
- `scripts/data/seed_all.py` todavia lista seeds AEAT legacy dentro de un runner bulk de desarrollo local.

Ese estado permite que un agente o una persona interpreten como productiva o autoritativa una ruta que no lo es.

## Decision de diseno

La via canonica AEAT para Fase 3.1 sera explicita y de dos pasos:

1. `python scripts/seed-modelos.py --db-url <DATABASE_URL>`
2. `python scripts/seed-modelos-v2.py --db-url <DATABASE_URL> --campana <YEAR>`

Razon:

- `scripts/seed-modelos.py` sigue siendo el bootstrap real de `aeat_modelo`.
- `scripts/seed-modelos-v2.py` no es autosuficiente hoy: si `aeat_modelo` no existe, los inserts por campana se degradan a `SKIP` y no pueblan la base esperada.
- Hacer `v2` autosuficiente seria un cambio mas grande y corresponde a otro slice si se decide mas adelante.

## Regla operativa resultante

- Solo los scripts root `scripts/seed-modelos.py` y `scripts/seed-modelos-v2.py` forman la ruta canonica AEAT.
- Los scripts bajo `scripts/data/` y el snapshot SQL permanecen ejecutables, pero deben quedar marcados como `LEGACY` o `NO AUTORITATIVO`.
- `scripts/data/seed_all.py` puede seguir existiendo para desarrollo local, pero debe advertir que no es la ruta productiva canonica para AEAT.

## Clasificacion de scripts

### Canonicos

- `scripts/seed-modelos.py`
  - Rol: bootstrap de `aeat_modelo` y relaciones `modelo_articulo` con fuente declarada.
  - Estado deseado tras 3.1: documentado como paso 1 canonico.

- `scripts/seed-modelos-v2.py`
  - Rol: enriquecimiento por campana y recursos asociados.
  - Estado deseado tras 3.1: documentado como paso 2 canonico.

### Legacy o no autoritativos

- `scripts/data/seed_modelos.py`
  - Motivo: seed manual curado paralelo, con cobertura y semantica distintas a la ruta root.

- `scripts/data/seed_aeat_models.py`
  - Motivo: extension declarada del seed legacy `seed_modelos.py`, no de la ruta canonica root.

- `scripts/data/seed_modelo_articulo.py`
  - Motivo: mapping legacy debil; hoy resuelve por `articulo.numero` sin exigir `(norma, numero)`.
  - Nota: se mantiene hasta Fase 3.2, pero ya no debe presentarse como ruta canonica.

- `scripts/seed-fiscal-modelos.sql`
  - Motivo: snapshot/manual SQL paralelo a la ruta Python canonica.

- `scripts/data/seed_all.py`
  - Motivo: runner bulk de desarrollo local; no debe venderse como flujo productivo AEAT.

## Implementacion minima aprobada

La implementacion de 3.1 debe ser deliberadamente pequena:

- anadir docstrings, encabezados o warnings visibles en los scripts afectados
- explicitar precondiciones y modo seguro en los scripts canonicos
- dejar una advertencia visible en `scripts/data/seed_all.py`
- actualizar documentacion activa del roadmap y memoria operativa
- anadir guardarrailes minimos que fijen la distincion canonico vs legacy

## Cambios fuera de alcance

3.1 no debe:

- volver `scripts/seed-modelos-v2.py` autosuficiente
- modificar schema, migraciones o runtime API
- endurecer todavia `modelo_articulo`
- introducir wrappers nuevos o fail-fast destructivo en scripts legacy
- eliminar archivos historicos o moverlos a `archive/`

## Archivos a tocar

- `scripts/seed-modelos.py`
- `scripts/seed-modelos-v2.py`
- `scripts/data/seed_modelos.py`
- `scripts/data/seed_aeat_models.py`
- `scripts/data/seed_modelo_articulo.py`
- `scripts/seed-fiscal-modelos.sql`
- `scripts/data/seed_all.py`
- `scripts/data/tests/test_seed_modelos.py` o test dedicado equivalente
- `scripts/tests/test_seed_aeat_models.py` o test dedicado equivalente
- `scripts/tests/test_seed_modelo_articulo.py` o test dedicado equivalente
- `docs/master-execution-roadmap.md`
- `docs/CHANGELOG.md`
- `docs/MEMO.md`
- `docs/operations/agent-notes.md`

## Estrategia de verificacion

La verificacion de 3.1 debe demostrar dos cosas:

1. la via canonica queda fijada por tests o guardarrailes de texto
2. los scripts canonicos siguen siendo seguros de inspeccionar o ejecutar en modo seguro

Verificacion minima prevista:

- `python -m pytest scripts/data/tests/test_seed_modelos.py -q`
- `python -m pytest scripts/tests/test_seed_aeat_models.py scripts/tests/test_seed_modelo_articulo.py -q`
- `python scripts/seed-modelos-v2.py --dry-run --campana 2025 --db-url postgresql://dummy:dummy@localhost:5432/dummy`

Nota: el ultimo comando solo es valido si el `--dry-run` evita escribir y la conexion se puede manejar de forma segura en el scope real del script. Si no es asi, se dejara constancia explicita y la evidencia se apoyara en tests.

## Riesgos conocidos que deben quedar documentados

- `scripts/seed-modelos-v2.py` depende de `aeat_modelo`; usarlo solo no equivale a un seed completo.
- `scripts/data/seed_modelo_articulo.py` sigue siendo una ruta legacy con linking debil y se corrige en 3.2.
- `scripts/data/seed_all.py` puede seguir ejecutando seeds AEAT legacy en entornos locales; por eso necesita warning explicito.

## Criterio de cierre de 3.1

Se podra cerrar 3.1 cuando:

- exista una unica ruta canonica AEAT claramente documentada
- las rutas legacy queden marcadas como `LEGACY` o `NO AUTORITATIVO`
- haya evidencia fresca de tests o `--dry-run` seguro
- el roadmap, changelog, memo y agent notes reflejen la decision sin contradicciones
