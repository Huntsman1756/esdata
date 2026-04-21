# License And Sourcing Policy

Política de trabajo para incorporar referencias externas al producto `esdata`.

## 1. Fuente maestra

Se consideran fuentes maestras:

- AEAT y su sede electrónica
- BOE
- EUR-Lex
- otros portales públicos oficiales expresamente incorporados al corpus

Todo dato normativo, doctrinal o técnico publicado por `esdata` debe poder trazarse hasta una fuente maestra.

## 2. Repositorios externos

Los repositorios externos se clasifican así:

- `architecture_reference`: sirve para aprender estructura, flujos o interfaces
- `ux_reference`: sirve para inspiración de navegación, filtros y presentación
- `coverage_benchmark`: sirve para detectar huecos funcionales
- `integration_reference`: sirve para entender protocolos o formatos concretos

Ninguna de estas clases convierte al repositorio en fuente maestra.

## 3. Política de licencia

- Repos MIT o equivalentes permisivos pueden servir como referencia de implementación, siempre con revisión manual y adaptación al código de `esdata`.
- Repos GPL o copyleft fuerte no deben utilizarse como base directa de código, contenido, corpus ni estructura derivada de producto salvo decisión explícita de relicenciamiento.
- El caso `joseconti/declaracion-renta-espana` queda marcado como `coverage_benchmark_only`.

## 4. Política de contenido

- No copiar texto fiscal o explicativo de terceros al corpus de `esdata`.
- No copiar listados de deducciones, reglas o explicaciones desde repos externos sin rehacer la pieza a partir de fuente oficial.
- Sí se permite usar repos externos para construir checklists internos de verificación de cobertura.

## 5. Aplicación práctica

Antes de incorporar una referencia externa a código o producto:

1. clasificar el repo por tipo de uso
2. validar su licencia
3. identificar la fuente maestra equivalente
4. documentar el uso previsto en `docs/reference-map.md`
5. implementar solo la parte respaldada por fuentes maestras
