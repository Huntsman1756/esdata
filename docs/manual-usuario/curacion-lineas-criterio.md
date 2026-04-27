# Curacion de lineas de criterio

## Resumen

Pipeline de curacion manual o semiasistida para vincular lineas de criterio con documentos interpretativos (doctrina, jurisprudencia, resoluciones). Permite sugerir documentos candidatos y asignarlos manualmente a cada linea.

## Arquitectura del pipeline

```
linea_criterio (con ambitos)
    ↓
  [suggest] → documento_interpretativo (con ambito)
    ↓
  scoring por relevancia
    ↓
  candidatos ordenados (top 10 por linea)
    ↓
  [assign] → linea_criterio_referencia
```

## Endpoint: Sugerir curacion

```
GET /v1/criterio/curacion/suggest
```

### Que hace

Recorre todas las lineas de criterio activas que tienen `ambitos` definidos y busca documentos interpretativos cuyo `ambito` coincida. Aplica scoring de relevancia.

### Respuesta

```json
{
  "sugerencias": [
    {
      "linea_id": 1,
      "linea_titulo": "IVA reducido en restauracion",
      "candidatos": [
        {
          "id": 42,
          "referencia": "STS-1234/2024",
          "tipo_documento": "sentencia",
          "organismo_emisor": "Tribunal Supremo",
          "ambito": "jurisprudencia_tributaria",
          "fecha": "2024-03-15",
          "titulo": "Sobre tipo reducido en hosteleria",
          "url_fuente": "https://...",
          "score": 3
        }
      ],
      "total_sugeridos": 1
    }
  ],
  "total_lineas": 1
}
```

### Algoritmo de scoring

Cada candidato recibe un score de 0 a 3:

| Criterio | Puntos |
|----------|--------|
| `ambito` coincide con un ambito conocido de la linea | +1 |
| `tipo_documento` es "sentencia" o "auto" | +1 |
| `organismo_emisor` contiene "Tribunal Supremo" o "Audiencia Nacional" | +1 |

### Limitaciones

- Solo devuelve candidatos con score >= 0 (todos los documentos con ambito coincidente)
- Maximo 10 candidatos por linea
- Ordenados por score descendente, luego por fecha descendente
- No analiza contenido del documento, solo metadatos
- No detecta contradicciones entre documentos

## Endpoint: Asignar documento a linea

```
POST /v1/criterio/curacion/assign
```

### Body

```json
{
  "linea_id": 1,
  "documento_referencia": "STS-1234/2024",
  "rol_en_linea": "soporte_complementario"
}
```

### Campos

| Campo | Obligatorio | Default | Valores permitidos |
|-------|-------------|---------|-------------------|
| `linea_id` | Si | — | ID de linea activa |
| `documento_referencia` | Si | — | Referencia unica del documento |
| `rol_en_linea` | No | `soporte_complementario` | `doctrina_principal`, `doctrina_complementaria`, `soporte`, `soporte_complementario`, `contradictorio`, `matiz`, `excepcion` |

### Respuesta

```json
{
  "assigned": true,
  "linea_id": 1,
  "documento_referencia": "STS-1234/2024",
  "referencia_existia": false
}
```

### Comportamiento

1. Si el documento existe en `documento_interpretativo`, copia `tipo_documento`, `organismo_emisor` a la referencia
2. Si no existe en `documento_interpretativo`, crea una referencia "desnuda" (solo referencia + rol)
3. Si la referencia ya existe para esa linea, devuelve `assigned: false` sin duplicar
4. El `orden` se calcula automaticamente como MAX(orden) + 1

## Script CLI: seed_linea_criterio.py

### Uso

```bash
# Solo ver sugerencias sin cambios
python scripts/seed_linea_criterio.py --db-url sqlite:///dev.db --dry-run

# Asignar documentos candidatos a lineas
python scripts/seed_linea_criterio.py --db-url sqlite:///dev.db --assign

# Filtrar por ambito especifico
python scripts/seed_linea_criterio.py --db-url sqlite:///dev.db --dry-run --ambito jurisprudencia_tributaria
```

### Flags

| Flag | Descripcion |
|------|-------------|
| `--db-url` | URL de la base de datos |
| `--dry-run` | Solo muestra que se asignaria sin escribir |
| `--assign` | Persiste los cambios en DB |
| `--ambito` | Filtra sugerencias por ambito |

## Ambitos conocidos

| Ambito | Descripcion |
|--------|-------------|
| `jurisprudencia_tributaria` | Doctrina sobre derecho tributario (IVA, IRPF, etc.) |
| `jurisprudencia_pbcft` | Prevencion de blanqueo de capitales y financiaciacion del terrorismo |
| `jurisprudencia_mercantil_regulatoria` | Derecho mercantil y regulacion de mercados financieros |

## Principios de curacion

1. **Nunca generar lineas sin soporte documental explicito** — cada linea debe estar respaldada por al menos un documento en `documento_interpretativo`
2. **Nunca presentar inferencias debiles como doctrina consolidada** — el score alto indica relevancia, no validez juridica
3. **Separar resumen curado, cita literal y referencia de fuente** — cada documento vinculado debe tener su rol definido
4. **Revision manual obligatoria** — las sugerencias automaticas son puntos de partida, no decisiones finales

## Flujos de uso

### Flujo basico

1. Llamar `GET /v1/criterio/curacion/suggest`
2. Revisar candidatos por linea
3. Para cada documento relevante, llamar `POST /v1/criterio/curacion/assign`
4. Verificar con `GET /v1/criterio/{id}` que la referencia aparecio

### Flujo con script

1. Ejecutar `seed_linea_criterio.py --dry-run`
2. Revisar la salida
3. Ejecutar `seed_linea_criterio.py --assign`
4. Verificar en DB

## Modelos de datos

### linea_criterio.ambitos

Array de strings que clasifica el ambito juridico de la linea. Se usa para matching con `documento_interpretativo.ambito`.

### documento_interpretativo.ambito

String unico que indica el ambito juridico del documento. Debe coincidir con un valor conocido para que el endpoint de sugerencias lo incluya.

### linea_criterio_referencia

Tabla intermedia que vincula lineas con documentos. Campos clave:

| Campo | Descripcion |
|-------|-------------|
| `linea_id` | FK a linea_criterio |
| `documento_referencia` | Referencia unica (o FK a documento_interpretativo.referencia) |
| `tipo_documento` | Copiado de documento_interpretativo si existe |
| `organismo_emisor` | Copiado de documento_interpretativo si existe |
| `rol_en_linea` | Papel del documento en la linea |
| `orden` | Orden dentro de la linea |

## Limitaciones actuales

- El matching por ambito es exacto (no parcial ni semantico)
- No hay deteccion automatica de contradicciones entre documentos
- No hay versionado de asignaciones (re-asignar no crea historico)
- El script solo procesa ambitos conocidos (3 valores)
- No hay UI para la curacion (solo API y CLI)
