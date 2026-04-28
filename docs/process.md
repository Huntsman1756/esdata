# Process — Operaciones de trabajo

Este documento describe el flujo operativo del equipo. AGENTS.md solo contiene reglas de seguridad y restricciones globales. Para detalle operativo, leer aqui.

---

## Flujo minimo de trabajo

Secuencia obligatoria para cualquier tarea:

1. **Discovery read-only** — leer solo lo necesario.
2. **Plan corto** — para cambios medianos/grandes.
3. **Cambios minimos y reversibles** — un solo archivo o modulo a la vez.
4. **Validacion** — tests/lint/build disponibles.
5. **Reporte final** — evidencia y riesgos restantes.

### Jerarquia de lectura

Orden obligatorio:

1. `AGENTS.md`
2. `docs/master-execution-roadmap.md`
3. archivos afectados
4. docs tecnicas si aplica
5. historicos solo si hay bloqueo

Antes de empezar, reducir contexto a: fase actual, tarea, criterio de exito, archivos, restricciones.

---

## Reclamo de tarea

Antes de modificar cualquier archivo, anotar en `docs/master-execution-roadmap.md`:

- fase o slice activo
- tarea concreta
- archivos afectados
- estado `EN CURSO`
- inicio

**Regla de exclusividad:** Un archivo solo puede ser modificado por un agente a la vez. Lectura concurrente es segura. Si otro agente ya tiene la tarea `EN CURSO`, esperar.

---

## Ejecucion de tarea

### Antes de tocar archivos

1. leer `AGENTS.md`
2. leer `docs/master-execution-roadmap.md`
3. identificar fase actual, tarea y criterio de exito
4. comprobar si el archivo ya esta reclamado
5. reducir contexto a solo lo necesario

### Verificar antes del cambio

Antes de implementar, ejecutar al menos una prueba de evidencia:

- test puntual si existe
- comando de reproduccion del bug
- build/lint del modulo si el cambio es estructural
- comprobacion documental si el cambio es solo de docs

Nunca afirmar que algo esta roto o arreglado sin evidencia fresca.

### Ejecutar el cambio

- hacer el cambio minimo correcto
- no mezclar refactors no relacionados
- no mover archivos por estetica
- si el cambio toca comportamiento visible, actualizar el manual o justificar

### Verificar despues del cambio

- codigo Python: `pytest` del scope afectado y `ruff check` si aplica
- web: `npm test` y `npm build` del scope afectado si aplica
- scripts: test del script o `--help`/`--dry-run`/caso controlado
- docs: comprobar rutas, enlaces y consistencia con roadmap/manual

---

## Cierre de tarea

Actualizar `docs/master-execution-roadmap.md` con:

- estado final: `COMPLETADA` o `BLOQUEADA`
- evidencia concreta de verificacion
- archivos realmente tocados
- riesgos restantes
- siguiente paso exacto

Reportar al usuario:

- que se hizo
- que se verifico y con que evidencia
- que queda pendiente o bloqueado

Si no hubo verificacion, decirlo explicitamente.

---

## Commit y sincronizacion

### Reglas de commit

- Cada fix/cambio en un commit atomico y autocontenido.
- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`, `perf:`, `ci:`, `build:`.
- El mensaje describe el **que**, no el **como**: `fix(api): validate input before DB write`.
- Nunca commits vacios ni que mezclen cambios no relacionados.
- Si un fix requiere multiples archivos, todos van en un solo commit atomico.

### Sincronizacion multi-maquina

- Trabajar siempre desde `main` con `git pull --rebase` al empezar.
- Hacer `git push` despues de cada commit atomico.
- Si dos maquinas trabajan en paralelo, rebase antes de push: `git pull --rebase origin main`.
- Nunca `git push --force` sobre `main`.
- Resolter conflictos localmente y rebase antes de push.

### Verificacion antes de push

- `git status` limpio (solo cambios intencionales).
- Tests relevant pass si hay tests disponibles.
- Build/lint si el cambio es estructural.

---

## Actualizacion de CHANGELOG y MEMO

Cada commit atomico debe ir acompanado de dos actualizaciones documentales:

1. **`docs/CHANGELOG.md`** — entrada con fecha, rama, hash del commit, tipo conventional y mensaje.
2. **`docs/MEMO.md`** — tabla con commit, tipo, descripcion y archivos afectados.

El CHANGELOG y MEMO se actualizan ANTES de hacer `git commit`.

---

## Politicas de documentacion

### Evidencia en auditorias

- Cada hallazgo debe citar evidencia: `ruta/archivo:linea`.
- Si no hay evidencia: `NOT AVAILABLE IN REPO` o `UNKNOWN`.
- No suponer controles de seguridad no demostrados.

### Manual de usuario

- Fuente permanente: `docs/manual-usuario/`.
- Punto de entrada: `docs/manual-usuario/README.md`.
- Mantener por capitulos pequenos para reducir colisiones.
- Antes de editar un capitulo, reclamarlo en el roadmap.
- Tareas que cambien comportamiento visible deben actualizar el manual en la misma iteracion.
- Separar claramente: uso funcional, interfaces disponibles, operacion minima, limites.
- No duplicar estado operativo del roadmap dentro del manual.

### Cambios de alto impacto (requieren confirmacion explicita)

- Migraciones destructivas o cambios de esquema productivo.
- Cambios en autenticacion/autorizacion.
- Cambios en semantica de borrado de datos.
- Rotacion de credenciales productivas.
- Operaciones destructivas en git o borrados masivos.

---

## Integraciones LLM

- `MCP` como superficie principal para uso personal del owner con `OpenCode` y modelos LLM locales.
- `ChatGPT Business` como integracion separada via `OpenAPI/Actions`, no como cliente MCP principal.
- No mezclar ambas superficies en propuestas o docs.
- `MCP` puede vivir local o en VPS privado.
- `ChatGPT Business` requiere endpoint HTTPS accesible externamente y auth propia.
