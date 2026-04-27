# Workflow operativo para agentes

## Objetivo

Definir una secuencia unica y repetible para trabajar en el repo con el minimo contexto, el menor riesgo de colision y evidencia real antes de declarar exito.

## Regla base

Un agente debe poder retomar el trabajo leyendo solo:

1. `AGENTS.md`
2. `docs/master-execution-roadmap.md`
3. el `AGENTS.md` del modulo afectado
4. los archivos del cambio

## Secuencia obligatoria por tarea

### 1. Inicio

1. leer `AGENTS.md`
2. leer `docs/master-execution-roadmap.md`
3. identificar fase actual, tarea actual y criterio de exito
4. reducir contexto a lo estrictamente necesario

### 2. Reclamo

Antes de editar:

- comprobar que nadie tiene el archivo reclamado
- anotar en el roadmap tarea, archivos, estado `EN CURSO` e inicio

Si no se puede reclamar de forma segura, no empezar.

### 3. Evidencia inicial

Ejecutar una prueba o check del scope afectado:

- test puntual
- reproduccion del bug
- `ruff check` del modulo
- `npm test` o `npm build` del modulo web
- comprobacion documental si el cambio es de docs

### 4. Cambio

- hacer el cambio minimo correcto
- no mezclar refactors no relacionados
- respetar el boundary entre runtime, tooling, docs activas e historicos
- si el cambio es visible para usuario, actualizar manual o justificar por que no aplica
- si el cambio descubre una trampa no obvia para agentes futuros, documentarla en `agent-notes.md` en la misma iteracion

### 5. Evidencia posterior

Volver a ejecutar el check mas cercano al cambio.

No declarar exito sin evidencia fresca.

### 6. Cierre

Actualizar el roadmap con:

- estado final
- evidencia concreta
- archivos realmente tocados
- riesgos restantes
- siguiente paso exacto

## Politica de verificacion

### Python

- `pytest <scope>`
- `ruff check <scope>` si aplica

### Web

- `npm --prefix apps/web run test`
- `npm --prefix apps/web run build`

### Scripts

- test dedicado, `--help`, `--dry-run` o caso controlado

### Docs

- comprobar rutas, enlaces y consistencia con roadmap/manual
- comprobar tambien que cualquier nueva referencia a `agent-notes.md` sea coherente con `operations/README.md` y `docs/README.md`

## Lo que no debe hacer un agente

- duplicar estado activo en varios markdowns
- abrir varios roadmaps como si todos mandaran
- usar docs historicas como fuente de verdad actual
- meter scripts manuales en `apps/api` o `apps/workers`
- afirmar que algo esta arreglado sin evidencia
