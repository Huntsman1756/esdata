# Reference Map

Mapa operativo de referencias externas revisadas para acelerar la evolución de `esdata` sin convertir repos de terceros en fuente maestra.

## Regla general

- `esdata` usa como fuente maestra datos y texto provenientes de fuentes oficiales primarias.
- Los repos externos se usan para detectar huecos, estudiar arquitectura o inspirar UX.
- Ningún contenido externo entra en producción sin revalidación sobre AEAT, BOE, EUR-Lex u otra fuente pública primaria equivalente.

## Inventario

| Referencia | Uso permitido | Módulo destino | Prioridad | Riesgo |
| --- | --- | --- | --- | --- |
| `iMark21/aeat-mcp` | diseño de superficie MCP, framing de herramientas para agentes | `apps/api/mcp_server.py`, `apps/api/services/*` | alta | bajo |
| `OpenHacienda/puntoBOE` | ideas para validación local de formatos y artefactos AEAT/BOE | `apps/workers/modelos.py`, futura capa de validación | alta | bajo |
| `jatorre/hacienda-cli` | flujos operativos AEAT: login, descarga, validación XSD/XML, carga manual | `apps/workers/modelos_support.py`, futuros validadores | alta | medio |
| `paumrch/larenta` | taxonomía UX, exploración de deducciones, navegación por casos | `apps/web/*`, futuros endpoints de consulta IRPF | media | bajo |
| `joseconti/declaracion-renta-espana` | benchmark de cobertura IRPF, checklist de casos, detección de huecos | `docs/*`, backlog de cobertura | media | alto por GPL |
| `fawno/AEAT` | referencia puntual para interoperabilidad SOAP/WSDL AEAT | adaptadores periféricos si hacen falta | baja | medio |
| `mybooking-es/aeat-validador-nif` | referencia puntual para validación censal/NIF | futuro servicio de validación identificativa | baja | bajo |
| `GeiserX/DeclaRenta` | pendiente de revisión manual suficiente | no usar todavía | n/a | desconocido |

## Decisiones activas

- La primera integración práctica arranca en la capa MCP/API.
- La segunda integración práctica será la de artefactos y validación técnica AEAT.
- El benchmark GPL se mantiene fuera del corpus y fuera de la UI final.
