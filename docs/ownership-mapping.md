# Mapeo de Ownership — Modelos Internos vs Estándares Externos

Este documento mapea el modelo interno de ownership de `esdata` con los estándares
externos **OpenOwnership Data Standard (BODS)** y **followthemoney (FtM)**.

## Regla general

- El modelo interno es pequeno y pragmático: 3 tablas con trazabilidad temporal y por fuente.
- El mapping permite exportar/convertir datos a BODS o FtM sin forzar su adopción literal.
- Ningún dato externo entra en producción sin revalidación sobre fuentes oficiales primarias.

---

## Modelo interno

### Tabla: `ownership_share`

| Campo interno | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER | PK autoincremental |
| `empresa_id` | INTEGER | FK → `empresa.id` (empresa participada) |
| `titular_id` | INTEGER | FK a `empresa.id` si es corporativo |
| `titular_tipo` | TEXT | `'empresa'` o `'persona'` |
| `titular_nombre` | TEXT | Nombre del titular |
| `porcentaje` | NUMERIC(5,2) | % de participación (0-100) |
| `tipo_participacion` | TEXT | `'directa'` o `'indirecta'` |
| `vigencia_desde` | TEXT | Fecha de inicio (YYYY-MM-DD) |
| `vigencia_hasta` | TEXT | Fecha de fin (YYYY-MM-DD) |
| `fuente` | TEXT | Origen del dato (BORME, registro_mercantil, declaracion) |
| `fuente_ref` | TEXT | Referencia de la fuente original |
| `documento_id` | INTEGER | FK → `documento_interpretativo.id` |

### Tabla: `ownership_relation`

| Campo interno | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER | PK autoincremental |
| `empresa_origen_id` | INTEGER | FK → `empresa.id` |
| `empresa_destino_id` | INTEGER | FK → `empresa.id` |
| `tipo_relacion` | TEXT | control, absorbente, absorbida, filial, matriz, joint_venture, etc. |
| `porcentaje` | NUMERIC(5,2) | % si aplica |
| `vigencia_desde` | TEXT | Fecha de inicio |
| `vigencia_hasta` | TEXT | Fecha de fin |
| `fuente` | TEXT | Origen del dato |
| `fuente_ref` | TEXT | Referencia de la fuente |
| `nota` | TEXT | Nota adicional |

### Tabla: `ubo_record`

| Campo interno | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER | PK autoincremental |
| `empresa_id` | INTEGER | FK → `empresa.id` (empresa beneficiada) |
| `nombre_persona` | TEXT | Nombre del beneficiario |
| `nacionalidad` | TEXT | Código ISO |
| `fecha_nacimiento` | TEXT | YYYY-MM-DD |
| `pais_residencia` | TEXT | Código ISO |
| `tipo_ubo` | TEXT | titular_poder, titular_propiedad, control_por_otros_medios, etc. |
| `porcentaje_control` | NUMERIC(5,2) | % de control |
| `umbral_superado` | TEXT | Umbral regulatorio superado |
| `vigencia_desde` | TEXT | Fecha de inicio |
| `vigencia_hasta` | TEXT | Fecha de fin |
| `fuente` | TEXT | Origen |
| `fuente_ref` | TEXT | Referencia |

---

## Mapeo con OpenOwnership Data Standard (BODS v0.4)

BODS estructura los datos en **statements** que contienen declaraciones de propiedad
beneficiaria. Cada statement referencia entidades (personas, organizaciones) y
relaciones.

### BODS `Statement` → `ownership_share`

| Campo BODS | Campo interno | Regla de mapeo |
|---|---|---|
| `statementId` | `id` | Generar mapping interno → BODS statement ID |
| `statementDate` | `vigencia_desde` | Usar `vigencia_desde` como statement date si coincide |
| `subject.relationshipId` | `id` | El statement referencia la relación |
| `subject.id` | `empresa_id` | Entidad sobre la que se declara la propiedad |
| `interestedParty.id` | `titular_id` | ID del titular en sistema BODS |
| `interestedParty.name` | `titular_nombre` | Nombre completo del titular |
| `interestedParty.personalDetails.gender` | *(no mapeado)* | No disponible en modelo interno |
| `beneficialInterest.percentageEntitlement` | `porcentaje` | Mapeo directo |
| `beneficialInterest.controlMechanism` | `tipo_ubo` + `tipo_participacion` | Combinar para expresar mecanismo de control |
| *(implicit)* | `tipo_participacion` | BODS no distingue directa/indirecta explícitamente; se usa en nota |
| `interestedParty.identifiers[]` | `fuente_ref` | Identificadores oficiales del titular |
| `interestedParty.identifiers.jurisdiction` | *(no mapeado)* | No disponible en modelo interno |

### BODS `PersonRecord` → `ubo_record`

| Campo BODS | Campo interno | Regla de mapeo |
|---|---|---|
| `id` | `id` | Mapping 1:1 |
| `name` | `nombre_persona` | Mapeo directo |
| `personalDetails.dateOfBirth` | `fecha_nacimiento` | Mapeo directo |
| `personalDetails.nationalities[]` | `nacionalidad` | Array BODS → texto FtM (primer valor o combinado) |
| `addresses[]` | `pais_residencia` | Primer address → pais |
| `identifiers[]` | `fuente_ref` | Identificadores oficiales |
| `deathDate` | *(no mapeado)* | No disponible en modelo interno |

### BODS `OrganizationRecord` → `empresa` + `ownership_share`

| Campo BODS | Campo interno | Regla de mapeo |
|---|---|---|
| `id` | `empresa_id` | Mapping 1:1 |
| `name` | `empresa.nombre` | Mapeo directo |
| `identifiers[]` | `empresa.nif` + `fuente_ref` | Identificadores oficiales |
| `registrationDate` | `vigencia_desde` (en share) | Fecha de registro de la empresa |
| `dissolutionDate` | `vigencia_hasta` (en share) | Fecha de disolución |

### BODS `RelationshipRecord` → `ownership_relation`

| Campo BODS | Campo interno | Regla de mapeo |
|---|---|---|
| `id` | `id` | Mapping 1:1 |
| `subject.id` | `empresa_origen_id` | Entidad que ejerce el control |
| `object.id` | `empresa_destino_id` | Entidad controlada |
| `type` | `tipo_relacion` | Mapeo directo (ver tabla de equivalencias abajo) |
| `startDate` | `vigencia_desde` | Mapeo directo |
| `endDate` | `vigencia_hasta` | Mapeo directo |

### Equivalencias `BODS relationship type` → `tipo_relacion`

| BODS type | Valor interno | Notas |
|---|---|---|
| `parent-child` | `filial` / `matriz` | Relación padre-hijo simple |
| `merger-absorption` | `absorbente` / `absorbida` | Fusión por absorción |
| `merger-new-formation` | `equivalencia` | Fusión por constitución |
| `split-off` | `escindente` / `escindida` | Escisión |
| `ownership` | `participacion_mayoritaria` | Participación >50% |
| `significant-influence-or-control` | `control` | Control significativo |
| `right-to-manage-directors` | `administrador` | Derecho a nombrar administradores |
| `voting-rights` | `participacion_significativa` | Derechos de voto |
| `right-to-exercise-control` | `control_por_otros_medios` | Control por otros medios |
| `construction` | `joint_venture` | Construcción de relación conjunta |

---

## Mapeo con followthemoney (FtM)

FtM usa un modelo basado en **Types** y **Properties** con valores temporales
(`startDate`, `endDate`).

### FtM `Ownership` edge → `ownership_share`

| Propiedad FtM | Campo interno | Regla de mapeo |
|---|---|---|
| `Ownership` (edge type) | *(tipo implícito)* | El edge Ownership conecta `owner` → `owned` |
| `owner` | `titular_id` + `titular_tipo` | Entidad que posee |
| `owned` | `empresa_id` | Entidad poseída |
| `ownershipPercentage` | `porcentaje` | Mapeo directo (0-100) |
| `ownershipType` | `tipo_participacion` | `'direct'` / `'indirect'` |
| `startDate` | `vigencia_desde` | Mapeo directo |
| `endDate` | `vigencia_hasta` | Mapeo directo |

### FtM `Person` → `ubo_record`

| Propiedad FtM | Campo interno | Regla de mapeo |
|---|---|---|
| `Person` (type) | *(tipo implícito)* | |
| `name` | `nombre_persona` | Mapeo directo |
| `birthDate` | `fecha_nacimiento` | Mapeo directo |
| `nationality` | `nacionalidad` | Código ISO país |
| `country` | `pais_residencia` | Código ISO de residencia |
| `identificationNumber` | `fuente_ref` | Identificador oficial |

### FtM `Organization` → `empresa`

| Propiedad FtM | Campo interno | Regla de mapeo |
|---|---|---|
| `Organization` (type) | *(tipo implícito)* | |
| `name` | `empresa.nombre` | Mapeo directo |
| `country` | *(no mapeado)* | No disponible en modelo interno |
| `registrationNumber` | `empresa.nif` | NIF/CIF como registrationNumber |
| `incorporationDate` | `vigencia_desde` (en share) | Fecha de incorporación |
| `dissolutionDate` | `vigencia_hasta` (en share) | Fecha de disolución |

### FtM `Person` → `ownership_share` (titular persona)

Cuando `titular_tipo = 'persona'`, el titular se modela como `Person` en FtM:

| Propiedad FtM | Campo interno | Regla de mapeo |
|---|---|---|
| `Person` (type) | *(tipo implícito)* | |
| `name` | `titular_nombre` | Mapeo directo |
| `ownership.owner` | `id` (Person) | El Person es el owner en el edge Ownership |
| `ownership.owned` | `empresa_id` | La empresa poseída |
| `ownership.percentage` | `porcentaje` | Mapeo directo |

---

## Transformaciones clave

### De interno a BODS

```
ownership_share → BODS Statement
  ├─ subject → empresa (OrganizationRecord)
  ├─ interestedParty → titular (PersonRecord u OrganizationRecord)
  ├─ beneficialInterest.percentageEntitlement → porcentaje
  ├─ beneficialInterest.controlMechanism → tipo_ubo (desde ubo_record si aplica)
  └─ statementDate → vigencia_desde

ubo_record → BODS Statement
  ├─ subject → empresa (OrganizationRecord)
  ├─ interestedParty → persona (PersonRecord)
  ├─ beneficialInterest.controlMechanism → tipo_ubo
  └─ beneficialInterest.percentageEntitlement → porcentaje_control
```

### De interno a FtM

```
ownership_share → FtM
  ├─ Crear/lookup Person u Organization para titular
  ├─ Crear/lookup Organization para empresa_id
  ├─ Edge Ownership: owner → owned
  ├─ ownershipPercentage → porcentaje
  ├─ ownershipType → tipo_participacion
  └─ startDate/endDate → vigencia

ubo_record → FtM
  ├─ Crear/lookup Person para nombre_persona
  ├─ Edge Ownership: Person → empresa
  ├─ ownershipPercentage → porcentaje_control
  └─ birthDate → fecha_nacimiento
```

### De BODS/FtM a interno

```
BODS statement → ownership_share
  ├─ interestedParty.name → titular_nombre
  ├─ interestedParty.id → titular_id (lookup por nombre + identifier)
  ├─ percentageEntitlement → porcentaje
  ├─ controlMechanism → tipo_ubo
  └─ statementDate → vigencia_desde

FtM Ownership edge → ownership_share
  ├─ owner.name → titular_nombre
  ├─ owner.birthDate → buscar en ubo_record
  ├─ ownershipPercentage → porcentaje
  └─ owner/owned dates → vigencia
```

---

## Notas de implementación

### Generación de IDs externos

- **BODS statementId**: `bods-{empresa_id}-{titular_id}-{vigencia_desde}`
- **FtM entity IDs**: `entity-{tipo}-{empresa_id}` o `entity-{tipo}-{nombre_slug}`

### Resolución de entidades

Al importar desde BODS/FtM:
1. Buscar por `nif`/`registrationNumber` primero (matching determinista)
2. Si no hay match, buscar por `name` + `country` (matching heurístico)
3. Si no hay match, crear nueva entidad con flag `imported=true`

### Campos no mapeados

Los siguientes campos de BODS/FtM no tienen equivalente en el modelo interno:

- BODS: `gender`, `deathDate`, `identifiers.jurisdiction`, `contactDetails`
- FtM: `address.street`, `role`, `sector`, `status`

Se pueden añadir en el campo `nota` si es necesario preservar la información.

### Trazabilidad

Cada registro interno mantiene `fuente` y `fuente_ref` que permiten:
- Saber si un dato vino de BORME, FtM importado, BODS importado, o declaración directa
- Rastrear el documento original (`documento_id`)
- Reconstruir la cadena de procedencia para auditoría
