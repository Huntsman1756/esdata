# AGENTS - docs

## Alcance

Estas reglas aplican a todo `docs/`.

## Jerarquia documental

- `master-execution-roadmap.md` es la unica fuente activa de estado y siguiente paso.
- `manual-usuario/` es la unica fuente funcional viva para usuarios humanos.
- `archive/` contiene historicos, snapshots y planes cerrados.
- Ningun documento en `archive/` manda sobre el roadmap o el manual.

## Donde va cada cosa

- `manual-usuario/`: uso funcional, interfaces, limites y operacion minima
- `operations/`: runbooks y operacion repetible
- `operations/agent-notes.md`: memoria operativa acumulativa para traps, invariantes no obvios y hallazgos tecnicos reutilizables por agentes futuros
- `deployment/`: instalacion, despliegue y rollback
- `architecture/` o docs tecnicos raiz: boundaries, estructura y decisiones tecnicas estables
- `reference/` o referencias tecnicas raiz: material estable reutilizable
- `adr/`: decisiones estructurales permanentes
- `archive/`: historicos y contexto no activo

## Reglas de mantenimiento

- No duplicar estado activo entre varios markdowns.
- Si un documento deja de ser fuente actual, moverlo a `archive/`.
- Marcar historicos con `[HISTORICAL]`, `[DEPRECATED]` o `[SUPERSEDED]`.
- Mantener enlaces estables desde `docs/README.md` y `manual-usuario/README.md`.
- Si un cambio altera comportamiento visible, revisar el capitulo correspondiente del manual en la misma iteracion.
- Si un cambio descubre una restriccion no obvia o una trampa recurrente para agentes, registrarla en `operations/agent-notes.md` en la misma iteracion.

## Verificacion

- Comprobar enlaces y rutas editadas.
- Confirmar que `docs/README.md` y `master-execution-roadmap.md` no se contradicen.
- No introducir referencias activas a Railway salvo claramente historicas.
