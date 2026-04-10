# esdata.org — Mini PRD técnico v0.1

> Documento de referencia para la implementación de la v1. Cubre esquema de datos, endpoints MVP, arquitectura de workers y criterios de aceptación. Audiencia: desarrollador o equipo técnico que va a construir esto.

---

## Contexto y objetivo

El proyecto construye una API pública española de datos oficiales normalizados, empezando por legislación fiscal artículo por artículo con soporte a consulta automatizada (agentes de IA, LLMs vía MCP). El diferencial frente a soluciones existentes (apispain, legalize-es) es la combinación de:

- Legislación consolidada accesible a nivel de bloque/artículo con versiones por fecha
- Doctrina administrativa (DGT, TEAC) como capa de interpretación
- Cruce NIF → empresa → contratos → subvenciones en fase posterior
- Política explícita de confianza de respuesta para uso con LLMs

---

## Fase 1 — Alcance MVP

La v1 cubre tres módulos en orden de prioridad:

1. **Legislación fiscal**: LIVA, LIS, LIRPF, LGT artículo por artículo, buscable, versionado
2. **Doctrina DGT/TEAC**: consultas vinculantes y resoluciones indexadas, aunque sea parcialmente
3. **API pública + MCP**: exposición REST documentada + servidor MCP montado sobre el mismo backend

Los módulos de PLACE, BORME y BDNS se posponen a la v2 por complejidad de acceso a las fuentes.

---

## Esquema de base de datos

### Modelo de legislación con versionado por artículo

El diseño soporta la consulta `?vigente_en=YYYY-MM-DD` desde el inicio.

```sql
-- Norma (LIVA, LIS, LIRPF, LGT...)
CREATE TABLE norma (
    id              SERIAL PRIMARY KEY,
    boe_id          TEXT UNIQUE NOT NULL,         -- 'BOE-A-1992-28740'
    eli_uri         TEXT UNIQUE NOT NULL,          -- 'https://www.boe.es/eli/es/l/1992/12/28/37'
    codigo          TEXT UNIQUE NOT NULL,          -- 'LIVA', 'LIS', 'LIRPF', 'LGT'
    titulo          TEXT NOT NULL,
    vigente_desde   DATE NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Versión de norma (cada vez que el BOE publica una consolidación)
CREATE TABLE version_norma (
    id              SERIAL PRIMARY KEY,
    norma_id        INTEGER REFERENCES norma(id),
    boe_version_id  TEXT NOT NULL,                 -- identificador de la versión en BOE API
    fecha_version   DATE NOT NULL,
    es_vigente      BOOLEAN NOT NULL DEFAULT false,
    raw_xml         TEXT,                          -- backup del XML original
    fetched_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(norma_id, fecha_version)
);

-- Artículo
CREATE TABLE articulo (
    id              SERIAL PRIMARY KEY,
    norma_id        INTEGER REFERENCES norma(id),
    numero          TEXT NOT NULL,                 -- '91', '20.1', 'DA Primera'
    titulo          TEXT,
    tipo            TEXT NOT NULL,                 -- 'articulo', 'disposicion_adicional', 
                                                   --  'disposicion_transitoria', 'disposicion_final'
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(norma_id, numero)
);

-- Versión de artículo (el texto real, versionado)
CREATE TABLE version_articulo (
    id              SERIAL PRIMARY KEY,
    articulo_id     INTEGER REFERENCES articulo(id),
    version_norma_id INTEGER REFERENCES version_norma(id),
    texto           TEXT NOT NULL,
    vigente_desde   DATE NOT NULL,
    vigente_hasta   DATE,                          -- NULL = vigente hoy
    boe_bloque_id   TEXT,                         -- id_bloque en la API del BOE
    search_vector   TSVECTOR,                     -- generado por trigger
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Índice GIN para full-text en español
CREATE INDEX idx_version_articulo_fts 
    ON version_articulo USING GIN(search_vector);

-- Trigger para mantener search_vector actualizado
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('spanish', 
        COALESCE(NEW.texto, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_search_vector
BEFORE INSERT OR UPDATE ON version_articulo
FOR EACH ROW EXECUTE FUNCTION update_search_vector();

-- pg_trgm para fuzzy y autocompletado (sobre artículo, no versión)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_articulo_trgm 
    ON articulo USING GIN(titulo gin_trgm_ops);
```

### Tabla de relaciones y aliases curados

Este es el corazón del producto navegable. No se genera automáticamente: se construye y mantiene a mano o con un proceso de curaduría semi-automática.

```sql
-- Materias y alias temáticos
CREATE TABLE materia (
    id          SERIAL PRIMARY KEY,
    slug        TEXT UNIQUE NOT NULL,    -- 'tipo-reducido-iva', 'gastos-no-deducibles'
    etiqueta    TEXT NOT NULL,           -- 'Tipo reducido IVA'
    descripcion TEXT
);

-- Relación artículo ↔ materia (muchos a muchos)
CREATE TABLE articulo_materia (
    articulo_id INTEGER REFERENCES articulo(id),
    materia_id  INTEGER REFERENCES materia(id),
    relevancia  SMALLINT DEFAULT 1,     -- 1=secundario, 2=principal, 3=definitorio
    PRIMARY KEY (articulo_id, materia_id)
);

-- Relaciones jurídicas entre artículos
CREATE TABLE relacion_juridica (
    id              SERIAL PRIMARY KEY,
    articulo_origen_id  INTEGER REFERENCES articulo(id),
    articulo_destino_id INTEGER REFERENCES articulo(id),
    tipo            TEXT NOT NULL,      -- 'remite_a', 'modifica', 'excepciona', 'complementa'
    nota            TEXT
);
```

Ejemplos de datos curados en `articulo_materia`:

| articulo_id (ejemplo) | materia slug | relevancia |
|---|---|---|
| LIVA art. 91 | tipo-reducido-iva | 3 |
| LIVA art. 90 | tipo-general-iva | 3 |
| LGT art. 15 | obligados-tributarios | 3 |
| LIS art. 15 | gastos-no-deducibles | 3 |
| LIS art. 12 | correcciones-valor | 2 |

### Tabla de doctrina (DGT/TEAC)

```sql
CREATE TABLE doctrina (
    id              SERIAL PRIMARY KEY,
    tipo            TEXT NOT NULL,          -- 'consulta_vinculante', 'resolucion_teac'
    referencia      TEXT UNIQUE NOT NULL,   -- 'V2345-24', 'RG 1234/2023'
    fecha           DATE NOT NULL,
    texto           TEXT NOT NULL,
    url_fuente      TEXT,
    search_vector   TSVECTOR,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_doctrina_fts ON doctrina USING GIN(search_vector);

-- Relación doctrina ↔ artículo
CREATE TABLE doctrina_articulo (
    doctrina_id INTEGER REFERENCES doctrina(id),
    articulo_id INTEGER REFERENCES articulo(id),
    PRIMARY KEY (doctrina_id, articulo_id)
);
```

### Tabla de confianza de respuesta

La política de confianza no es solo para el LLM: se materializa como dato en la respuesta de la API.

```sql
-- Esta tabla no se consulta directamente: define los niveles
-- La capa de negocio los calcula y los devuelve en cada respuesta
-- Se documenta aquí como contrato explícito

-- nivel 1: ley citada (solo versión_articulo encontrada)
-- nivel 2: ley + doctrina DGT/TEAC (articulo + ≥1 doctrina_articulo)
-- nivel 3: ley + doctrina + aviso (conflicto entre doctrinas, 
--           artículo modificado recientemente, o consulta ambigua)
```

En la respuesta JSON, cada endpoint que devuelva contenido jurídico incluirá:

```json
{
  "confianza": {
    "nivel": 2,
    "fuentes": ["LIVA art. 91", "V1234-23 DGT"],
    "aviso": null
  }
}
```

---

## Endpoints MVP

Base URL: `https://api.esdata.org/v1`

### Legislación

```
GET /legislacion
    → lista de normas disponibles con metadatos

GET /legislacion/{codigo}
    → metadatos de una norma (LIVA, LIS, LIRPF, LGT)
    → incluye lista de versiones disponibles

GET /legislacion/{codigo}/articulos
    → lista de artículos de la norma
    → query params: ?tipo=articulo|disposicion_adicional|...

GET /legislacion/{codigo}/articulos/{numero}
    → texto del artículo en su versión vigente
    → query param: ?vigente_en=YYYY-MM-DD (por defecto: hoy)
    → incluye: texto, vigente_desde, vigente_hasta, materias, relaciones, confianza

GET /legislacion/{codigo}/articulos/{numero}/historial
    → todas las versiones del artículo ordenadas cronológicamente

GET /legislacion/buscar
    → query params: ?q=texto_libre&norma=LIVA,LIS&materia=tipo-reducido-iva&vigente_en=YYYY-MM-DD
    → full-text sobre tsvector + ranking por ts_rank
    → devuelve fragmentos con highlight del término buscado
    → incluye nivel de confianza por resultado
```

### Materias y aliases

```
GET /materias
    → lista de materias curadas con slug y etiqueta

GET /materias/{slug}
    → artículos asociados a esa materia, ordenados por relevancia
```

### Doctrina

```
GET /doctrina/buscar
    → query params: ?q=texto_libre&tipo=consulta_vinculante|resolucion_teac&desde=YYYY-MM-DD
    → full-text sobre doctrina

GET /doctrina/{referencia}
    → texto completo de una consulta o resolución
    → incluye artículos relacionados
```

### Estado del sistema

```
GET /status
    → estado de cada worker (último sync, próximo sync, errores recientes)

GET /health
    → healthcheck simple para monitorización
```

---

## Estructura de workers

Cada worker corre de forma independiente. Un fallo de uno no afecta a los demás.

### Worker BOE (legislación consolidada)

```
Frecuencia: diaria a las 06:00 (antes de la apertura del BOE)
Tecnología: Python + httpx + lxml

Proceso:
1. GET /datosabiertos/api/legislacion-consolidada
   → obtiene lista de normas con timestamp de última modificación
   
2. Para cada norma en scope (LIVA, LIS, LIRPF, LGT):
   a. Comparar timestamp con la última version_norma almacenada
   b. Si hay cambio → GET /id/{boe_id}/metadatos → upsert version_norma
   c. GET /id/{boe_id}/texto/indice → lista de bloques/artículos
   d. Por cada bloque nuevo o modificado:
      GET /id/{boe_id}/texto/bloque/{id_bloque}
      → parsear XML → upsert version_articulo
      → calcular vigente_hasta de versiones anteriores

3. Actualizar search_vector vía trigger (automático)
4. Registrar resultado en tabla sync_log
```

### Worker Doctrina DGT

```
Frecuencia: semanal (lunes 07:00)
Tecnología: Python + httpx/playwright (la fuente puede requerir scraping)

Fuente: https://petete.tributos.hacienda.gob.es/
        (buscador de consultas vinculantes de la DGT)

Proceso:
1. Consultar nuevas resoluciones desde la última fecha de sync
2. Extraer referencia, fecha, texto completo
3. Insertar en tabla doctrina
4. Paso de linkado semiautomático: buscar artículos mencionados
   en el texto (regex sobre patrones "artículo \d+ LIVA" etc.)
   → insertar en doctrina_articulo
5. Registrar en sync_log

Nota: validar estabilidad de la fuente antes de confiar
en este worker en producción.
```

### Worker Doctrina TEAC

```
Frecuencia: semanal (martes 07:00)
Fuente: https://www.hacienda.gob.es/
        (resoluciones del Tribunal Económico-Administrativo Central)

Proceso análogo al worker DGT.
```

### Tabla de control de workers

```sql
CREATE TABLE sync_log (
    id          SERIAL PRIMARY KEY,
    worker      TEXT NOT NULL,          -- 'boe_legislacion', 'doctrina_dgt', etc.
    started_at  TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status      TEXT NOT NULL,          -- 'running', 'ok', 'error'
    items_processed INTEGER,
    error_msg   TEXT,
    meta        JSONB                   -- contexto adicional (norma, fecha, etc.)
);
```

---

## Política de confianza — contrato explícito

| Nivel | Condición | Aviso en respuesta |
|---|---|---|
| 1 | Solo artículo encontrado, sin doctrina | `"Solo base legal, sin doctrina disponible"` |
| 2 | Artículo + ≥1 doctrina DGT o TEAC | null |
| 3 | Artículo modificado en los últimos 90 días | `"Artículo modificado recientemente, verificar vigencia"` |
| 3 | Doctrinas contradictorias entre sí | `"Existe doctrina contradictoria, consultar especialista"` |
| 3 | Query devuelve artículos de múltiples normas sin relación explícita | `"Respuesta basada en cruce no validado editorialmente"` |

Esta política se implementa en la capa de servicio (no en la BD) y se serializa siempre en la respuesta.

---

## Criterios de aceptación — v1

### Datos

- [ ] Las 4 normas fiscales prioritarias (LIVA, LIS, LIRPF, LGT) están indexadas en su versión consolidada vigente
- [ ] Cada artículo tiene al menos una `version_articulo` con `vigente_desde` correcta
- [ ] La query `?vigente_en=2020-01-01` sobre LIVA/91 devuelve la versión del texto que estaba vigente en esa fecha
- [ ] Existen materias curadas para los 20 conceptos fiscales más frecuentes (tipo general, tipo reducido, tipo superreducido, exenciones, deducciones IS, gastos no deducibles, amortizaciones, retenciones, IRPF rendimientos trabajo, etc.)
- [ ] Hay al menos 500 consultas vinculantes DGT indexadas con artículos relacionados

### API

- [ ] Todos los endpoints documentados en OpenAPI/Swagger responden correctamente
- [ ] La búsqueda full-text en español normaliza acentos (restauración ↔ restauracion, tipo ↔ tipos)
- [ ] El endpoint `/buscar` devuelve resultados en <200ms para queries simples sobre las 4 normas
- [ ] Cada respuesta incluye el objeto `confianza` con nivel, fuentes y aviso
- [ ] El servidor MCP está montado en `/mcp` y Claude puede conectarse y ejecutar búsquedas

### Calidad

- [ ] El worker BOE detecta cambios en una norma dentro de las 24h de publicación en el BOE
- [ ] `/status` refleja el estado real de cada worker (último sync, errores)
- [ ] Un artículo eliminado o renumerado no rompe las URLs existentes (gestión de redirects o tombstone)
- [ ] La API devuelve errores 404 con mensaje descriptivo, nunca 500 silenciosos

### Prueba de humo end-to-end

Las siguientes queries deben funcionar correctamente antes de considerar la v1 completa:

```
GET /v1/legislacion/LIVA/articulos/91?vigente_en=2020-01-01
→ texto del artículo 91 LIVA vigente el 1 de enero de 2020

GET /v1/legislacion/buscar?q=tipo+reducido&norma=LIVA
→ resultados relevantes con highlight, nivel de confianza ≥1

GET /v1/materias/gastos-no-deducibles
→ LIS art. 15 entre los primeros resultados, relevancia=3

GET /v1/doctrina/buscar?q=deducibilidad+multas&tipo=consulta_vinculante
→ al menos una consulta DGT relevante con artículo LIS relacionado
```

---

## Lo que queda fuera de la v1

- PLACE (contratación pública): ETL complejo, pendiente de validar acceso incremental
- BORME (empresas + NIF): cruza con PLACE, va después
- BDNS (subvenciones): acceso WSDL/XSD a validar antes de diseñar el worker
- Meteorología (AEMET): fácil técnicamente, pero no es el wedge fiscal
- Incendios: sin fuente estatal centralizada, requiere estrategia de agregación por CCAA
- pgvector / búsqueda semántica: se añade en v2, cuando hay suficiente doctrina para que los embeddings tengan sentido

---

*Versión: 0.1 — Abril 2026*
