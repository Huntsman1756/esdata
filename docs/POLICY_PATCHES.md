# Policy Patches

## Reglas activas

- solo `.env.example` puede vivir en el repo como template de variables
- cualquier `.env` anidado o runtime es bloqueo automatico
- ninguna PR de retrieval/consulta/MCP pasa sin auditoria persistente
- ninguna PR de respuestas factuales pasa sin citas exactas o abstencion/revision
- ninguna PR puede describir `TARGET` o `PARTIAL` como si fuera `IMPLEMENTED`
- ningun cambio de esquema pasa sin migracion Alembic
- ningun texto generado por LLM entra como corpus autoritativo

## Enforcement en repo

- `.gitignore` bloquea `.env*` salvo `.env.example`
- CI ejecuta `scripts/maintenance/verify-doc-artifacts.py` tambien como gate de deriva entre `.env.example` y `docs/environment-variables.md`
- `PULL_REQUEST_TEMPLATE.md` obliga a declarar secretos, audit, parsing, grounding y veracidad documental

## Marcadores de estado documental

- `[IMPLEMENTED]` = activo en runtime y verificable
- `[PARTIAL]` = existe parcialmente o sin controles fuertes
- `[TARGET]` = roadmap o diseno objetivo
