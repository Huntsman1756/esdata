# Limites, alcance y estado actual

## Alcance actual

`esdata` esta orientado a datos y consulta fiscal-regulatoria con foco actual en `sociedad de valores` en Espana.

El producto no esta planteado como terminal de mercados, herramienta de trading ni sistema de ejecucion financiera.

## Estado funcional actual a alto nivel

Segun el roadmap activo del repo, el sistema ya tiene operativas capas de:

- retrieval y chunking
- corpus regulatorio prioritario
- perfil regulatorio y aplicabilidad inicial
- obligaciones operativas enriquecidas
- change impact
- workflow de compliance
- UI interna minima
- PGC
- ingestion `legalize-es`

Esto no significa que todos los dominios esten completos al mismo nivel de profundidad. Significa que existen slices funcionales ya implementados y consultables.

## Fuera de alcance inicial

- legal horizontal generalista
- litigacion civil o laboral amplia
- mezclar conocimiento privado del cliente con el corpus publico base sin una capa separada

## Limitaciones practicas importantes

- la cobertura real depende de las fuentes ya normalizadas y expuestas por API
- algunas capas estan orientadas a consulta y trazabilidad, no a automatizacion cerrada extremo a extremo
- el roadmap puede tener fases futuras planificadas que todavia no deben asumirse como disponibles para usuario final
- `MCP` y `API` no sustituyen validacion experta humana en escenarios legales o regulatorios sensibles
- la UI interna existe, pero el backend sigue siendo la capa canonica

En internacional y convenios DTA, la existencia de seeds o fixtures en el repo no garantiza por si sola que todos esos convenios esten cargados o validados en una instancia concreta. La cobertura operativa debe inferirse del contrato HTTP expuesto por la API y del dataset realmente sembrado en el entorno objetivo; por eso el manual documenta ejemplos verificados, no una matriz exhaustiva de paises.

En doctrina administrativa DGT/TEAC, el corpus y la busqueda existen como superficie parcial. La auditoria productiva `../doctrina-production-audit-20260521.md` confirma que hay documentos DGT/TEAC trazables, pero las lineas de criterio fiscales aun no estan curadas como producto completo. Una linea solo debe tratarse como utilizable si declara evidencia suficiente y `safe_to_answer=true`; si faltan fuente oficial, articulo, impuesto, modelo o fecha de captura trazable, la respuesta correcta es abstenerse o marcar evidencia limitada.

En CNMV, el corpus actual es parcial. La instancia productiva puede devolver decenas de circulares oficiales cargadas, pero eso no significa que incluya todo el universo CNMV: guias tecnicas, documentos a consulta, modelos normalizados, preguntas y respuestas y registros oficiales tienen familias propias. Use `GET /v1/cnmv/coverage` para distinguir lo cargado de lo conocido pero no disponible. Un no resultado en CNMV puede significar "no cargado", no "no existe".

## Regla sobre cobertura

No asumir que cualquier tema legal o financiero esta soportado por el producto solo porque exista infraestructura generica. La cobertura real depende de las fases implementadas y de la documentacion permanente del repo.

## Donde ver el estado vivo

Para saber:

- que fase esta activa
- que esta completado
- que sigue pendiente
- que decision estructural esta vigente

consultar siempre `../master-execution-roadmap.md`.

## Regla de mantenimiento

Cuando una tarea cambie el alcance util para el usuario, habilite una capacidad nueva, retire una anterior o introduzca una limitacion relevante, este capitulo debe actualizarse.

Referencias utiles:

- `../master-execution-roadmap.md`
- `../../README.md`
