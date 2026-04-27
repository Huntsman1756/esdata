# AGENTS - apps/web

## Alcance

Estas reglas aplican a `apps/web/`.

## Objetivo del modulo

- `apps/web/` contiene la UI interna y superficies web del producto.
- La UI consume backend; no implementa logica de negocio ni acceso directo a DB.

## Estructura esperada

- `app/` — rutas App Router
- `components/` — componentes visuales
- `lib/` — cliente API, tipos y helpers de presentacion
- `public/` — assets estaticos

## Reglas duras

- No introducir secretos cliente-side ni `NEXT_PUBLIC_*` sensibles.
- No acceder a DB ni mover logica de negocio al frontend.
- Mantener `.next/`, `node_modules/` y artefactos locales fuera del control efectivo del repo.
- Si una necesidad es operativa o de integracion, documentarla en `docs/`, no en el codigo UI.

## Verificacion minima

- `npm --prefix apps/web run test`
- `npm --prefix apps/web run build`

## Documentacion relacionada

- `docs/manual-usuario/11-ui-interna.md`
- `docs/manual-usuario/03-superficies-disponibles.md`
