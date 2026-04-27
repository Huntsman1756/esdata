# Bootstrap Hardening Checklist

## Secretos

- [ ] no existe ningun `.env` runtime dentro del repo
- [ ] secretos locales viven fuera del repo o en gestor de secretos local
- [ ] `.env.example` coincide con `docs/environment-variables.md`

## Auditoria

- [ ] endpoints de retrieval/consulta/MCP registran `request_id`, actor, query, chunks, modelo, config y revision
- [ ] existe evidencia verificable de persistencia durable

## Parsing seguro

- [ ] los workers documentales no parsean ficheros remotos sin allowlist y validacion de firma/MIME
- [ ] existe limite de tamano y ruta de cuarentena o sandbox

## Grounding

- [ ] las respuestas factuales usan citas exactas por claim o abstencion
- [ ] los chunks recuperados se tratan como input no confiable

## Documentacion

- [ ] `docs/architecture.md` marca cada capa como `[IMPLEMENTED]`, `[PARTIAL]` o `[TARGET]`
- [ ] ninguna doc activa exagera el estado real del sistema
