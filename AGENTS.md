# ============================================
# DESPLIEGUE ACTIVO: Docker Compose
# ============================================
# El despliegue de referencia de este proyecto es Docker Compose.
#
# No mantener workflows, config ni comandos activos de plataformas antiguas.
# Si una referencia antigua aparece en el repo, debe vivir en `docs/archive/`
# y quedar marcada como [HISTORICAL] o [DEPRECATED].
# ============================================

<!-- karpathy-guidelines:begin -->
## Karpathy workflow
- Use the local `karpathy-guidelines` skill at `G:\_Proyectos\.agents\skills\_local\karpathy-guidelines\SKILL.md` for non-trivial implementation, debugging, refactors, and reviews.
- Think before coding: state assumptions, surface ambiguity, and prefer the simpler approach when it is enough.
- Keep changes surgical: avoid unrelated refactors and only remove code made unused by your change.
- Work against explicit checks: reproduce with tests or verification steps first, then confirm the result.
<!-- karpathy-guidelines:end -->
# AGENTS - Seguridad S-TIER para Codex/OpenAI

Estandar global para `C:\Users\rome_\_Proyectos`.
Compatible con Codex/OpenAI y alineado con la base existente de `CLAUDE.md`.

---

## Alcance y prioridad

- Aplica a todos los proyectos dentro de `_Proyectos/`.
- `AGENTS.md` o `CLAUDE.md` local puede extender estas reglas.
- Si hay conflicto, prevalece la regla mas estricta de seguridad.

---

## Mision

Prevenir vulnerabilidades de "vibe coding" con arquitectura backend-first y zero-trust.

---

## Mapa modular del repo

- `apps/api/` — backend FastAPI, contratos, middleware y superficies MCP/API. Ver `apps/api/AGENTS.md`
- `apps/web/` — UI interna Next.js. Ver `apps/web/AGENTS.md`
- `apps/workers/` — ingestion y normalizacion por fuente. Ver `apps/workers/AGENTS.md`
- `scripts/` — tooling, ops, evaluacion, mantenimiento y seeds. Ver `scripts/AGENTS.md`
- `docs/` — documentacion viva y archivo historico. Ver `docs/AGENTS.md`
- `infra/` — despliegue y configuracion operativa. Ver `infra/AGENTS.md`

## Flujos cross-domain

- `apps/web` consume `apps/api`; no contiene logica de negocio ni acceso DB.
- `apps/workers` pueblan y enriquecen datos consumidos por `apps/api`.
- `scripts/` ejecuta tareas operativas o de mantenimiento fuera del runtime.
- `docs/master-execution-roadmap.md` es la unica fuente activa de estado.

---

## Constraints no negociables (S-TIER)

1. Arquitectura backend-only:
- Nunca logica de negocio ni acceso DB directo en frontend.
- Frontend solo llama APIs/Server Actions/Functions backend.

2. RLS Zero Policy (Supabase/Postgres):
- RLS obligatorio en todas las tablas de datos.
- Sin policies para `public` o `anon`.
- Acceso real de datos solo con `service_role` en servidor.

3. Mass assignment:
- Toda mutacion valida esquema antes de escribir (allowlist explicita).
- Prohibido pasar `req.body` directo a `.update()` o `.create()`.

4. Storage:
- Buckets privados por defecto.
- Nombres de archivo con UUID.
- Acceso via signed URL temporal.

5. Pagos y webhooks:
- Verificacion criptografica de firma obligatoria.
- Idempotencia por `event.id` obligatoria.

6. Variables de entorno:
- Nunca secretos hardcodeados ni en frontend.
- Nunca secretos con `NEXT_PUBLIC_*`.
- Validacion de env al arranque (schema).

7. RPC lockdown:
- Tras `CREATE FUNCTION`, revocar execute a `public` y `anon`.
- Conceder solo a `service_role` cuando aplique.

8. Input validation + rate limiting:
- Validacion de input en toda mutacion.
- Rate limiting obligatorio en auth, mutaciones, webhooks, uploads y endpoints de AI.

9. Docker security (si aplica):
- Ejecutar como non-root.
- Sin secretos en capas de imagen.
- Imagen base fijada (no `latest`).

10. AI data leakage:
- Minimizacion de datos al llamar modelos.
- No enviar PII sin necesidad y sin base legal.
- Proteger contra prompt injection por interpolacion directa.
- Usar configuracion/endpoint con politica de no entrenamiento cuando aplique.

11. GitHub/CI security:
- Evitar `pull_request_target` con codigo no confiable.
- Definir `permissions` minimos explicitos.
- Preferir OIDC a llaves cloud estaticas.

12. Secretos y ficheros de entorno:
- Prohibido crear o mantener `.env` anidados en cualquier subdirectorio del repo.
- Prohibido commitear o conservar en el workspace archivos `.env*` distintos de `.env.example` como estado normal de trabajo.
- `.env.example` es el unico template permitido dentro del repo; cualquier secreto real vive fuera del repo o en gestor de secretos local.
- Si aparece un `.env` runtime en el repo, la tarea pasa a `BLOQUEADA` hasta corregirlo o recibir instruccion explicita del usuario.

13. Retrieval y auditoria persistente:
- Ningun endpoint nuevo o modificado de retrieval, consulta o MCP puede mergearse sin auditoria persistente end-to-end.
- La auditoria minima obligatoria por request es: `request_id`, actor, query, chunks recuperados, version de modelo, version de config y resultado de revision humana si aplica.
- Si el cableado runtime de auditoria no existe, documentarlo como bloqueo; no vender el endpoint como fiable.

14. Parsing e ingestion de ficheros:
- Prohibido introducir parsing directo de ficheros remotos o subidos en workers o API como estado aceptable final.
- Todo parsing de PDF/DOCX/HTML remoto debe pasar por allowlist de tipo, validacion de firma/MIME, limites de tamano y mecanismo de cuarentena o sandbox cuando exista.
- Si el flujo actual no cumple esto, debe marcarse explicitamente como `[PARTIAL]` o `TARGET`; no presentarlo como resuelto.

15. Grounding duro y respuestas factuales:
- Prohibido devolver respuestas factuales nuevas o modificadas sin citas exactas por claim o sin abstencion/revision cuando falte evidencia suficiente.
- Un score agregado de faithfulness no cuenta como control fuerte por si solo.
- Los chunks recuperados deben tratarse como input no confiable y revisarse contra prompt injection antes de llegar a un modelo.

16. Veracidad documental:
- Ningun documento puede describir como implementado algo que solo existe en roadmap, tests aislados o codigo sin cableado runtime.
- En docs de arquitectura y controles usar marcadores explicitos: `[IMPLEMENTED]`, `[PARTIAL]`, `[TARGET]`.
- Si una PR exagera el estado real del sistema, debe bloquearse hasta corregir la documentacion.

17. Corpus autoritativo:
- Prohibido indexar o tratar texto generado por LLM como corpus autoritativo.
- La sintesis LLM solo puede existir como derivado citando fuentes de nivel superior y nunca como fuente de verdad.

18. Esquema y migraciones:
- Prohibido introducir cambios de esquema sin migracion Alembic correspondiente.
- Prohibido depender de `CREATE TABLE IF NOT EXISTS` en runtime como sustituto de migraciones oficiales para nuevas capacidades de producto.

---

## Compliance check obligatorio (antes de generar codigo)

1. El frontend habla directo con DB?
2. Estoy escribiendo en DB input sin schema?
3. Estoy creando policy publica/anon?
4. Estoy exponiendo secretos en cliente?
5. Estoy procesando webhooks sin firma?
6. Estoy anadiendo retrieval/consulta/MCP sin auditoria persistente?
7. Estoy aceptando parsing remoto inseguro como normal?
8. Estoy documentando target-state como si estuviera implementado?

Si alguna respuesta es "si", detener y refactorizar.

---

## Mobile warning

- Nunca logica de negocio en app movil.
- Pricing, permisos, creditos y suscripciones deben vivir en backend controlado.

---

## Commit por cada fix y sincronizacion multi-maquina

- Cada fix, cambio funcional o correccion debe ir en un commit atomico y autocontenido.
- Usar conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`, `perf:`, `ci:`, `build:`.
- El message debe describir el que, no el como: `fix(api): validate input before DB write` en vez de `fix: x`.
- Nunca commits vacios ni commits que mezclen cambios no relacionados.
- Si un fix requiere multiples archivos, todos van en un solo commit atomico.
- Al terminar una tarea, hacer commit antes de cualquier otra modificacion.
- Sincronizacion multi-maquina:
  - Trabajar siempre desde `main` con `git pull --rebase` al empezar.
  - Hacer `git push` despues de cada commit atomico para mantener el remote actualizado.
  - Si dos maquinas trabajan en paralelo, rebase antes de push: `git pull --rebase origin main`.
  - Nunca hacer `git push --force` sobre `main`.
  - Si hay conflictos, resolverlos localmente y rebase antes de push.
- Verificacion antes de push:
  - `git status` limpio (solo cambios intencionales).
  - Tests relevant pass si hay tests disponibles.
  - Build/lint si el cambio es estructural.
  - Solo push tras verificar.

### Actualizacion obligatoria de CHANGELOG y MEMO por commit

Cada commit atomico debe ir acompanado de dos actualizaciones documentales:

1. **`docs/CHANGELOG.md`** — entrada con fecha, rama, hash del commit, tipo conventional y mensaje:
   ```
   ## 2026-04-27
   ### main
   - **abc1234** `fix(api)` — validate input before DB write
   ```
2. **`docs/MEMO.md`** — tabla con commit, tipo, descripcion y archivos afectados:
   ```
   | abc1234 | fix(api) | validate input before DB write | apps/api/routers/consulta.py, apps/api/services/search.py |
   ```
3. El CHANGELOG y MEMO se actualizan ANTES de hacer `git commit`.
4. Si el commit toca archivos en multiples areas (api + workers + docs), se anotan todos en la misma entrada.
5. El CHANGELOG se mantiene ordenado por fecha (descendente) y rama.
6. El MEMO se mantiene ordenado por rama, con el resumen de la rama activa siempre arriba.
7. Si `docs/CHANGELOG.md` o `docs/MEMO.md` no existen, crearlos.

---

## Integraciones LLM (persistente)

- Tratar `MCP` como superficie principal para uso personal del owner con `OpenCode` y modelos LLM locales.
- Tratar `ChatGPT Business` como integracion separada via `OpenAPI/Actions`, no como cliente MCP principal.
- No mezclar ambas superficies en propuestas o docs: documentar por separado `MCP personal` y `Actions corporativas`.
- Para trabajo futuro sobre despliegue o integraciones:
  - `MCP` puede vivir local o en VPS privado.
  - `ChatGPT Business` requiere endpoint HTTPS accesible externamente y auth propia.
- Si hay duda sobre consumo futuro, preservar ambas superficies: `MCP` para flujo personal y `OpenAPI` reducida para empresa.

---

## Protocolo de trabajo seguro

1. Discovery read-only.
2. Plan corto para cambios medianos/grandes.
3. Cambios minimos y reversibles.
4. Validacion con tests/lint/build disponibles.
5. Reporte final con evidencia y riesgos restantes.

## Protocolo operativo por tarea

Todo agente debe seguir esta secuencia exacta al empezar y cerrar una tarea:

### 1. Antes de tocar archivos

1. leer `AGENTS.md`
2. leer `docs/master-execution-roadmap.md`
3. identificar fase actual, tarea actual y criterio de exito
4. comprobar si el archivo ya esta reclamado por otro agente
5. reducir contexto a solo lo necesario

### 2. Reclamar la tarea

Antes de editar, anotar en `docs/master-execution-roadmap.md`:

- fase o slice activo
- tarea concreta
- archivos afectados
- estado `EN CURSO`
- inicio

Si no se puede reclamar de forma segura, no empezar.

### 3. Verificar antes del cambio

Antes de implementar, ejecutar o definir al menos una prueba de evidencia:

- test puntual si existe
- comando de reproduccion del bug
- build/lint del modulo si el cambio es estructural
- comprobacion documental si el cambio es solo de docs

Nunca afirmar que algo esta roto o arreglado sin evidencia fresca.

### 4. Ejecutar el cambio

- hacer el cambio minimo correcto
- no mezclar refactors no relacionados
- no mover archivos por estetica si no mejora estructura real o coste de contexto
- si el cambio toca comportamiento visible, actualizar el manual o justificar por que no aplica

### 5. Verificar despues del cambio

Ejecutar las verificaciones minimas del modulo afectado. Como regla:

- codigo Python: `pytest` del scope afectado y `ruff check` si aplica
- web: `npm test` y `npm build` del scope afectado si aplica
- scripts: test del script o `--help`/`--dry-run`/caso controlado
- docs: comprobar rutas, enlaces y consistencia con roadmap/manual

### 6. Cerrar la tarea

Actualizar `docs/master-execution-roadmap.md` con:

- estado final: `COMPLETADA` o `BLOQUEADA`
- evidencia concreta de verificacion
- archivos realmente tocados
- riesgos restantes
- siguiente paso exacto

### 7. Reportar al usuario

El reporte final debe incluir:

- que se hizo
- que se verifico y con que evidencia
- que queda pendiente o bloqueado

Si no hubo verificacion, debe decirse explicitamente.

---

## Politica de evidencia en auditorias

- Cada hallazgo debe citar evidencia: `ruta/archivo:linea`.
- Si no hay evidencia: `NOT AVAILABLE IN REPO` o `UNKNOWN`.
- No suponer controles de seguridad no demostrados.

---

## Cambios de alto impacto (requieren confirmacion explicita)

- Migraciones destructivas o cambios de esquema productivo.
- Cambios en autenticacion/autorizacion.
- Cambios en semantica de borrado de datos.
- Rotacion de credenciales productivas.
- Operaciones destructivas en git o borrados masivos.

---

## Coordinacion multi-agente (reclamo de tarea)

Cuando varios agentes pueden trabajar simultaneamente en el mismo repo, el riesgo principal es la colision de escrituras en los mismos archivos.

### Regla de reclamo obligatorio

Antes de modificar cualquier archivo, el agente debe:

1. Anotar en `docs/master-execution-roadmap.md` (seccion "Fase activa" o resumen vivo) que esta trabajando en esa tarea especifica.
2. Incluir: tarea, archivos afectados, estado "EN CURSO".
3. Si otro agente detecta que la tarea ya esta marcada como "EN CURSO" por otro agente, no iniciar trabajo en esos archivos.
4. Esperar a que se marque como completada o cancelada antes de intervenir.

### Regla de no colision

- Un archivo solo puede ser modificado por un agente a la vez.
- Si dos agentes necesitan el mismo archivo, uno espera y el otro continua.
- El agente que termina debe actualizar el estado en el roadmap maestro.

### Regla de lectura concurrente

- Lectura concurrente de archivos es segura.
- Solo las escrituras requieren reclamo y exclusividad.

### Regla de reporte al usuario

- Si un agente no puede reclamar una tarea porque ya esta en curso, debe reportarlo al usuario y sugerir otra tarea o esperar.
- No silenciar el conflicto ni empezar trabajo duplicado.

### Regla para documentacion funcional y manual de usuario vivo

- Existe una fuente permanente y acumulativa para el manual de usuario: `docs/manual-usuario/`.
- Punto de entrada obligatorio del manual: `docs/manual-usuario/README.md`.
- El manual debe mantenerse por capitulos pequenos para reducir colisiones entre agentes. No concentrar todo en un unico markdown largo.
- Antes de editar cualquier capitulo del manual, el agente debe reclamar ese archivo exacto en `docs/master-execution-roadmap.md` igual que cualquier otro archivo de codigo o doc.
- Si otro agente ya tiene un capitulo del manual en `EN CURSO`, no editar ese mismo archivo. Esperar o trabajar en otro capitulo no reclamado.
- Toda tarea que cambie comportamiento visible, forma de uso, setup, limitaciones, endpoints, MCP, flujos operativos o capacidades del producto debe actualizar en la misma iteracion el capitulo correspondiente del manual.
- Si el cambio no requiere actualizar el manual, el agente debe decirlo explicitamente en el reporte final con una razon concreta.
- Si no existe un capitulo adecuado, crear uno nuevo dentro de `docs/manual-usuario/`, anadirlo al indice `docs/manual-usuario/README.md` y mantener nombres estables y descriptivos.
- El manual debe separar claramente:
  - uso funcional para usuario
  - interfaces disponibles (`API`, `MCP`, UI interna, CLI si aplica)
  - operacion tecnica minima
  - limites, alcance actual y exclusiones
- No duplicar estado operativo del roadmap dentro del manual. El roadmap sigue siendo la fuente activa de fase/estado; el manual explica capacidades, uso y limites para humanos.
- Al cerrar una tarea, el agente debe indicar que archivos del manual actualizo.

### Ejemplo de reclamo en el roadmap maestro

En la seccion "Fase activa" o "Resumen vivo" del roadmap maestro:

```
## Fase activa
- Fase activa: Fase 6 — Change impact
- Estado: EN CURSO por agente-X
- Tarea actual: anadir filtro por obligacion_afectada
- Archivos afectados:
  - apps/api/routers/cambios.py
  - apps/api/tests/test_change_impact.py
- Inicio: 2026-04-25T10:00
- Estado del agente: modificando archivos
```

Cuando termine:

```
- Estado del agente: COMPLETADA
- Cambios: filtro anadido, tests verdes
- Siguiente paso: [proxima tarea]
```

---

## Context budget y control de tokens (obligatorio)

Objetivo: evitar `ContextWindowExceededError`, reducir coste y mantener respuestas utiles.

### Reglas duras

1. Nunca enviar contexto completo "por si acaso".
- Incluir solo archivos, fragmentos y mensajes estrictamente relevantes para la tarea actual.
- Prohibido pegar logs completos, handoffs completos, planes completos o archivos enteros si basta un extracto.

2. Presupuesto de contexto por defecto
- Trabajar con un limite operativo del 70-80% de la ventana real del modelo.
- Dejar siempre margen para la respuesta.
- Si no se conoce la ventana exacta, asumir que es menor de lo anunciado y ser conservador.

3. Limite de salida
- No pedir salidas largas por defecto.
- Usar salida corta/media salvo que el usuario pida explicitamente un documento largo.
- Si la entrada es grande, reducir automaticamente la salida solicitada.

4. Jerarquia de inclusion de contexto
- Nivel 1: tarea actual y archivos directamente afectados.
- Nivel 2: restricciones locales del proyecto.
- Nivel 3: resumen del contexto historico.
- Nivel 4: contexto historico literal solo si es imprescindible.

5. Compresion obligatoria
- Cuando una conversacion o tarea crezca, sustituir historial antiguo por un resumen estructurado.
- El resumen debe conservar: objetivo, decisiones tomadas, restricciones, archivos afectados, riesgos abiertos y siguientes pasos.
- No reenviar mensajes antiguos completos tras haberlos resumido, salvo necesidad real.

6. Recuperacion por fragmentos
- Para documentos largos, usar busqueda por relevancia y extraer chunks concretos.
- Nunca pasar un documento completo si la consulta afecta solo a una seccion.

7. Fallo controlado
- Si aun asi no cabe el contexto, detenerse y responder:
  - que sobra contexto,
  - que se necesita recorte o resumen,
  - y que se priorizara lo mas relevante.
- No reintentar ciegamente con la misma carga.

8. Prioridad operativa en caso de exceso de contexto
- Mantener siempre: seguridad, tarea actual, archivos afectados y restricciones locales.
- Comprimir o eliminar primero: historial conversacional, planes largos, handoffs, logs extensos y referencias duplicadas.
- Nunca sacrificar reglas criticas de seguridad para hacer hueco a contexto historico o documental.

### Politica de inclusion minima

Antes de generar codigo o responder, comprobar:
1. Este fragmento es necesario para resolver la tarea actual?
2. Puedo sustituir este bloque por un resumen de 3-10 lineas?
3. Puedo citar ruta y seccion en vez de pegar contenido completo?
4. Puedo recuperar solo los trozos relevantes en lugar del archivo entero?

Si la respuesta a 2, 3 o 4 es "si", no incluir el bloque completo.

### Formato de resumen acumulado recomendado

Mantener un resumen vivo del proyecto con este esquema:

- Objetivo actual
- Estado actual
- Decisiones tomadas
- Restricciones no negociables
- Archivos relevantes
- Riesgos o dudas abiertas
- Siguiente paso exacto

### Regla especial para planes y handoffs

- No inyectar planes, roadmaps o handoffs completos en cada peticion.
- Extraer solo:
  - fase actual,
  - tarea actual,
  - criterio de exito,
  - archivos implicados.
- El resto debe resumirse en 5-15 lineas maximo.

### Regla especial para logs y errores

- Incluir solo:
  - mensaje de error,
  - stack trace minimo relevante,
  - comando ejecutado,
  - contexto inmediato.
- Nunca adjuntar miles de lineas de log salvo peticion expresa.

### Regla especial para AGENTS/CLAUDE/SYSTEM prompts

- Estas reglas deben ser compactas y no duplicarse entre archivos.
- Si una regla ya existe en `CLAUDE.md` o en un `AGENTS.md` local, referenciarla y no repetirla entera.
- Evitar listas enormes de instrucciones permanentes que no afecten a la tarea actual.

---

## Referencias obligatorias

- `CLAUDE.md`
- `SECURITY_BASELINE.md`
- `chekmyinternet/AGENTS.md`
- `chekmyinternet/PROMPT_CLAUDE_CODE_AUDIT_V3.md`

Regla:
- Estas referencias deben consultarse por ruta y de forma selectiva.
- No copiar ni inyectar su contenido completo en el contexto salvo necesidad directa.
- Si basta una cita de ruta, seccion o resumen, usar eso.

---

## Protocolo de trabajo por fases

## Modelo de trabajo permanente del repo

Este repositorio debe poder ser trabajado por cualquier LLM o agente sin depender de memoria conversacional larga ni de grandes ventanas de contexto.

La regla principal es simple:

- una sola fuente activa de estado y ejecucion
- una sola fase activa cada vez
- un solo siguiente paso exacto
- contexto minimo suficiente, no contexto maximo

### Fuente activa unica

- Documento maestro activo: `docs/master-execution-roadmap.md`
- Los demas roadmaps, handoffs y planes pasan a ser `REFERENCE` o `HISTORICAL`
- Ningun documento historico puede competir con el documento maestro como fuente de estado actual

### Jerarquia obligatoria de lectura

Orden obligatorio:

1. `AGENTS.md`
2. `docs/master-execution-roadmap.md`
3. archivos de codigo directamente afectados
4. una documentacion tecnica adicional solo si la fase actual lo requiere
5. documentos historicos solo si hay bloqueo real y el documento maestro lo indica

### Politica de contexto minima

- no cargar documentos completos por defecto
- no cargar mas de una fase completa a la vez
- no cargar mas de un documento historico por iteracion
- no arrastrar handoffs completos entre sesiones
- siempre resumir antes de expandir

Antes de empezar cualquier tarea, reducir el contexto a:

- fase actual
- tarea actual
- criterio de exito
- archivos afectados
- restricciones no negociables

### Slice minimo obligatorio

Secuencia obligatoria:

1. identificar fase y siguiente paso exacto
2. reclamar la tarea y archivos
3. anadir o ejecutar verificacion inicial
4. hacer el cambio minimo
5. volver a verificar
6. actualizar el estado vivo
7. dejar escrito el siguiente paso exacto

### Regla de no duplicacion operativa

Queda prohibido mantener el mismo estado operativo en varios documentos activos.

Contenido que solo puede vivir en un sitio activo:

- fase actual
- siguiente paso exacto
- estado ejecutivo
- objetivo actual
- criterio de exito de la fase

### Regla documental permanente

- `AGENTS.md` define disciplina, seguridad y restricciones
- `docs/master-execution-roadmap.md` define estado y ejecucion activos
- docs tecnicos (`architecture`, `database`, `operations`, `deployment`) se leen solo cuando la tarea lo requiere
- handoffs antiguos y planes cerrados no se leen por defecto

### Antipatrones prohibidos

- empezar leyendo varios roadmaps a la vez
- usar el handoff mas reciente como sustituto del roadmap maestro
- cargar contexto completo "por si acaso"
- abrir varias fases en paralelo sin control
- afirmar exito sin verificacion fresca
- crear nuevos planes activos sin integrarlos en el documento maestro

### Antes de empezar

1. **Leer siempre primero**: `docs/master-execution-roadmap.md`
2. **Extraer y conservar un resumen breve**: no arrastrar el contenido completo de documentos en iteraciones posteriores.
3. **Identificar la fase actual**: la primera fase no completada o la fase marcada como activa en el documento maestro.
4. **Revisar solo la seccion necesaria** del plan o spec de detalle si el documento maestro lo exige para la tarea actual.
5. **Reclamar la tarea y los archivos** antes de editar.
6. **Definir como se verificara** la tarea antes de implementar.
7. **Confirmar con el usuario** la fase solo cuando el cambio implique nueva fase, migraciones sensibles o redireccion importante.

### Durante la ejecución

8. **Trabajar fase a fase**: nunca saltar a la siguiente fase sin terminar la actual.
9. **Cambios minimos y reversibles**: cada commit debe ser un paso lógico dentro de la fase.
10. **Verificar despues de cada slice** antes de declarar avance real.
11. **No asumir contexto historico**: si un archivo menciona una plataforma antigua sin [HISTORICAL]/[DEPRECATED], corregirlo.

### Al terminar una fase

12. **Actualizar el documento maestro**: editar `docs/master-execution-roadmap.md`
   - Marcar la fase o subfase como completa cuando aplique
   - Actualizar `Resumen vivo`
   - Actualizar `Fase activa` y `Siguiente paso exacto`
   - Reflejar scores/metrics si aplica
13. **Confirmar al usuario** que la fase esta completa y que el documento maestro fue actualizado.
14. **Preguntar si continuar** con la siguiente fase o cambiar de direccion.

### Estructura de actualizacion del documento maestro

```
## Fase X — [nombre] ✅ COMPLETA

### X.1 [subitem] ✅
- Root cause / decision: ...
- Fix / cambio: ...
- Archivo: `ruta/archivo`

### X.2 [subitem] ✅
- ...

## Siguientes pasos recomendados
1. [proxima tarea]
2. [proxima tarea]

## Criterios de exito Fase X
1. ✅ [criterio 1]
2. ✅ [criterio 2]
```
