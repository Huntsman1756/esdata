# ============================================
# DESPLIEGUE: Railway DEPRECATED
# ============================================
# Railway YA NO se usa como plataforma de despliegue para este proyecto.
# Despliegue de referencia: Docker Compose (infra/deploy/docker-compose.prod.yml)
#
# CUALQUIER referencia a Railway en este documento o en el repo es HISTORICA.
# No proponer cambios que asuman Railway, no modificar railway.toml,
# no usar comandos "railway", no mencionar Railway como plataforma valida.
#
# Si un markdown menciona Railway y no tiene etiqueta [HISTORICAL] o [DEPRECATED],
# corregirlo: marcar como historico o eliminar la referencia.
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

---

## Compliance check obligatorio (antes de generar codigo)

1. El frontend habla directo con DB?
2. Estoy escribiendo en DB input sin schema?
3. Estoy creando policy publica/anon?
4. Estoy exponiendo secretos en cliente?
5. Estoy procesando webhooks sin firma?

Si alguna respuesta es "si", detener y refactorizar.

---

## Mobile warning

- Nunca logica de negocio en app movil.
- Pricing, permisos, creditos y suscripciones deben vivir en backend controlado.

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

### Antes de empezar

1. **Leer los planes vigentes solo de forma selectiva**: `docs/next-session-handoff-2026-04-25.md`, `docs/professionalization-roadmap.md`, `docs/plan-fase2-chunking.md`, `docs/superpowers/plans/2026-04-12-buscador-profesional-phase-1.md`
2. **Extraer y conservar un resumen breve**: no arrastrar el contenido completo de esos documentos en iteraciones posteriores.
3. **Identificar la fase actual**: la primera fase sin marcar como completa en el handoff.
4. **Revisar solo la seccion del plan necesaria** para la tarea actual en `docs/superpowers/plans/` o `docs/superpowers/specs/`.
5. **Confirmar con el usuario** que la fase identificada es correcta antes de codificar.

### Durante la ejecución

6. **Trabajar fase a fase**: nunca saltar a la siguiente fase sin terminar la actual.
7. **Cambios minimos y reversibles**: cada commit debe ser un paso lógico dentro de la fase.
8. **No asumir contexto historico**: si un archivo menciona Railway sin [HISTORICAL]/[DEPRECATED], corregirlo.

### Al terminar una fase

9. **Actualizar el handoff**: editar `docs/next-session-handoff-2026-04-25.md`
   - Marcar la fase como `✅ COMPLETA` con el encabezado correspondiente
   - Listar items entregables con archivos afectados
   - Actualizar "Siguientes pasos recomendados" con la proxima fase
   - Actualizar "Estado actual" con scores/metrics si aplica
10. **Confirmar al usuario** que la fase esta completa y que el handoff fue actualizado.
11. **Preguntar si continuar** con la siguiente fase o cambiar de direccion.

### Estructura de actualizacion del handoff

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
