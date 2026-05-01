# Source Compliance Register

Registro operativo de restricciones, condiciones de reutilizacion y limites tecnicos de las fuentes externas integradas en `esdata`.

## sede.agenciatributaria.gob.es (AEAT modelos)

| Campo | Valor |
| --- | --- |
| robots.txt | `https://www.sede.agenciatributaria.gob.es/robots.txt` |
| Licencia datos | Reutilizacion sujeta a condiciones AEAT |
| Rate limit implementado | `2 req/s` + backoff exponencial |
| Requiere JS | Si. `PlaywrightClient` se activa por fallback |
| Autenticacion | No requerida para modelos publicos |
| Limitaciones conocidas | DNS no resuelve desde IPs fuera de ES en el entorno de desarrollo actual |
| Ultima verificacion | `2026-05-01` |

## Criterio de Playwright

El worker intenta `httpx` primero. Si el listado devuelve `0` anchors de modelos, eleva `FallbackRequired` y activa `PlaywrightClient`.

Verificado el `2026-05-01`: `httpx` devuelve `0` anchors desde IP exterior y la fuente no pudo validarse live desde el entorno de desarrollo actual.

## Estado de validacion

`worker-aeat-modelos` no ha sido validado contra fuentes live.

DNS de `sede.agenciatributaria.gob.es` no resuelve desde el entorno de desarrollo actual. La validacion real requiere ejecucion desde una IP espanola o desde el VPS de produccion.

## Regla operativa

- No marcar el worker AEAT como completamente verificado hasta ejecutar un sync real desde red compatible.
- Cualquier cambio de portal, captcha, bloqueo geografico o renderizado JS debe reflejarse aqui antes de vender la integracion como estable.
