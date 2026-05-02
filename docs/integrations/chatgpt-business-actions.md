# ChatGPT Business + Actions

## Objetivo

Documentar la integracion recomendada de `esdata` con `ChatGPT Business`.

La superficie recomendada para este caso no es MCP, sino `Actions` basadas en OpenAPI.

## Regla principal

Para `ChatGPT Business`:

- usar `OpenAPI + Actions`
- no depender del endpoint MCP como camino principal

Motivo:

- `ChatGPT Business` corre en la nube de OpenAI
- necesita alcanzar un endpoint HTTPS accesible externamente
- un endpoint solo local, solo VPN o solo Tailscale no suele ser suficiente para una integracion directa desde OpenAI

## Arquitectura recomendada

- `api.tudominio.com` expone la API REST
- `ChatGPT Business` consume una spec OpenAPI reducida
- `/mcp` puede seguir existiendo para otros clientes, pero no es el contrato principal para ChatGPT

## Requisitos de conectividad

La API debe ser:

- accesible por HTTPS
- estable y con certificado valido
- autenticada
- observable por IT o por el owner

No vale como integracion directa para ChatGPT Business:

- `localhost`
- IP privada sin salida publica
- endpoint visible solo por VPN de usuario final

## Autenticacion recomendada

### Opcion minima

- API key o bearer token dedicado para `Actions`

### Recomendaciones

- no reutilizar la misma key del MCP personal
- rotar secretos si el uso se comparte
- dejar la key fuera del prompt y fuera de ficheros versionados

## Spec recomendada

No exponer toda la API si no es necesario. Mantener una spec reducida y enfocada al caso de uso.

Superficie minima recomendada:

- `buscar_legislacion`
- `get_articulo`
- `buscar_doctrina`
- `get_doctrina`
- `list_modelos`
- `get_modelo`

Superficie opcional adicional si aporta valor real:

- `get_modelo_fuentes_oficiales`
- `get_modelo_resumen_operativo`

## Flujo de integracion

### 1. Desplegar API accesible por HTTPS

Debe existir un endpoint publico controlado, por ejemplo:

- `https://api.example.com/openapi.json`
- o una spec reducida tipo `docs/openapi-gpt.json` publicada por URL o subida por fichero

### 2. Elegir spec

Opciones ya presentes en el repo:

- spec reducida servida por la API en `/gpt-actions/modelos/openapi.json`
- `docs/openapi-gpt.json`
- `docs/openapi-gpt-3.0.json`

Contrato recomendado para Custom GPT / Business Actions:

- base URL HTTPS publica del backend
- spec `OpenAPI 3.1` desde `/gpt-actions/modelos/openapi.json` o `docs/openapi-gpt.json`
- auth por API key dedicada, enviada como cabecera `X-API-Key`

Recomendacion:

- usar spec reducida para Actions

Ejemplo verificado en VPS Arsys:

- spec URL: `https://api.desuscribir.es/gpt-actions/modelos/openapi.json`
- privacy URL: `https://api.desuscribir.es/privacy`
- auth en builder: cabecera `X-API-Key` con valor `ESDATA_API_KEY`
- no usar `/mcp` para ChatGPT

### 3. Crear el GPT o configurar el workspace

En el builder de `ChatGPT Business`:

- crear Custom GPT o configuracion equivalente
- anadir `Actions`
- importar la OpenAPI por URL o por archivo
- configurar el esquema de autenticacion requerido

### 4. Validar rutas clave

Comprobar al menos:

- una busqueda legislativa
- un detalle de articulo
- una busqueda doctrinal
- un detalle de modelo AEAT

## Separacion de superficies

### MCP personal

- pensado para `OpenCode`
- pensado para LLM local
- puede vivir local o en VPS privado

### Actions para empresa

- pensado para `ChatGPT Business`
- pensado para acceso HTTPS externo controlado
- administrado despues por IT si el uso escala

## Riesgos y consideraciones

- si la API no es accesible desde OpenAI, `Actions` no funcionara
- si publicas demasiados endpoints, la experiencia del GPT sera peor y mas dificil de gobernar
- si reutilizas secretos entre MCP y Actions, mezclas dominios de riesgo innecesariamente

## Checklist previo a IT

1. la API responde por HTTPS
2. la spec OpenAPI que se va a usar esta cerrada y probada
3. el metodo de auth esta decidido
4. hay un endpoint de health y una forma de ver logs
5. el caso de uso del GPT esta acotado

## Referencias

- `docs/openapi-gpt.json`
- `docs/openapi-gpt-3.0.json`
- `docs/deployment/HANDOFF-IT.md`
- `docs/integrations/opencode-local-and-vps.md`
