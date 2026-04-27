# AGENTS - infra

## Alcance

Estas reglas aplican a `infra/`.

## Objetivo del modulo

- `infra/` contiene despliegue, bootstrap SQL y configuracion operativa reproducible.

## Reglas duras

- El despliegue de referencia es Docker Compose.
- No proponer Railway como plataforma activa.
- No hardcodear secretos ni credenciales en archivos de infra.
- Cambios sensibles de despliegue o SQL inicial deben verificarse antes de darse por buenos.

## Verificacion minima

- revisar rutas reales usadas por `docker-compose` y runbooks
- comprobar consistencia con `docs/deployment/*`
