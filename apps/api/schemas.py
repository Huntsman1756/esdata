"""Pydantic response models for the esdata API.

Focused on the endpoints exposed to Custom GPT Actions.
"""

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class ConfianzaInfo(BaseModel):
    nivel: int = Field(description="Nivel de confianza (0-2)")
    fuentes: list[str] = Field(description="Fuentes que respaldan la respuesta")
    aviso: str | None = Field(default=None, description="Advertencia si la confianza es baja")


# ---------------------------------------------------------------------------
# Legislacion
# ---------------------------------------------------------------------------

class Norma(BaseModel):
    codigo: str = Field(description="Código de la norma (ej: LIVA, LIRPF)")
    titulo: str = Field(description="Título completo de la norma")
    jurisdiccion: str = Field(description="Jurisdicción (es, autonomico, etc.)")
    tipo_fuente: str = Field(description="Tipo de fuente (boe, autonomica, etc.)")
    tipo_documento: str = Field(description="Tipo de documento (ley, real_decreto_legislativo, etc.)")
    ambito: str = Field(description="Ámbito temático (tributario, etc.)")
    estado_cobertura: str = Field(description="Estado de cobertura (ingestada, parcial, etc.)")


class ArticuloListItem(BaseModel):
    numero: str = Field(description="Número del artículo")
    titulo: str | None = Field(default=None, description="Título del artículo")
    tipo: str = Field(description="Tipo (articulo, disposicion, etc.)")


class ArticuloDetail(BaseModel):
    norma: str = Field(description="Código de la norma")
    numero: str = Field(description="Número del artículo")
    texto: str = Field(description="Texto vigente del artículo")
    vigente_desde: str | None = Field(default=None, description="Fecha de inicio de vigencia (YYYY-MM-DD)")
    vigente_hasta: str | None = Field(default=None, description="Fecha de fin de vigencia (YYYY-MM-DD)")
    fuente_norma: str | None = Field(default=None, description="Identificador BOE/ELI de la norma")
    confianza: ConfianzaInfo = Field(description="Información de confianza del dato")


class SearchResult(BaseModel):
    tipo: str = Field(description="Tipo de resultado (articulo, norma, etc.)")
    norma: str = Field(description="Código de la norma")
    numero: str = Field(description="Número del artículo")
    texto: str = Field(description="Texto del artículo")
    fragmento: str = Field(description="Fragmento destacado con el término buscado")
    vigente_desde: str | None = Field(default=None, description="Fecha de inicio de vigencia")
    vigente_hasta: str | None = Field(default=None, description="Fecha de fin de vigencia")
    rank: float | None = Field(default=None, description="Puntuación de relevancia (ts_rank)")
    fuente_norma: str | None = Field(default=None, description="Identificador BOE/ELI de la norma")
    source_url: str | None = Field(default=None, description="URL directa al documento fuente")
    motivo_ranking: str | None = Field(default=None, description="Explicación del ranking obtenido")
    confianza: ConfianzaInfo = Field(description="Información de confianza del dato")


# ---------------------------------------------------------------------------
# Doctrina
# ---------------------------------------------------------------------------

class ArticuloRelacionado(BaseModel):
    norma: str = Field(description="Código de la norma vinculada")
    numero: str = Field(description="Número del artículo vinculado")
    metodo_enlace: str = Field(description="Método de enlace (manual, auto_link, etc.)")
    confianza_enlace: float = Field(description="Confianza del enlace (0-1)")


class DoctrinaDetail(BaseModel):
    referencia: str = Field(description="Referencia del documento (ej: V0000-26, 00/1234/2024)")
    tipo_documento: str = Field(description="Tipo (consulta_vinculante, resolucion_teac, etc.)")
    organismo_emisor: str = Field(description="Organismo emisor (DGT, TEAC, etc.)")
    texto: str = Field(description="Texto completo del documento")
    articulos_relacionados: list[ArticuloRelacionado] = Field(
        default_factory=list, description="Artículos de ley vinculados"
    )
    confianza: ConfianzaInfo = Field(description="Información de confianza del dato")


class DoctrinaSearchResult(BaseModel):
    referencia: str = Field(description="Referencia del documento")
    tipo_documento: str = Field(description="Tipo de documento")
    organismo_emisor: str = Field(description="Organismo emisor")
    fecha: str | None = Field(default=None, description="Fecha del documento (YYYY-MM-DD)")
    titulo: str | None = Field(default=None, description="Título del documento")
    nivel_enlace: float = Field(description="Máxima confianza de enlace (0-1)")
    norma: str | None = Field(default=None, description="Código de norma vinculada")
    numero: str | None = Field(default=None, description="Número de artículo vinculado")
    fragmento: str = Field(description="Fragmento del texto con el término buscado")
    source_url: str | None = Field(default=None, description="URL directa al documento doctrinal")


# ---------------------------------------------------------------------------
# Modelos AEAT
# ---------------------------------------------------------------------------

class ModeloSummary(BaseModel):
    codigo: str = Field(description="Código del modelo (ej: 100, 303)")
    nombre: str = Field(description="Nombre completo del modelo")
    periodo: str | None = Field(default=None, description="Periodo de presentación (anual, trimestral, etc.)")
    impuesto: str = Field(description="Impuesto asociado (IRPF, IVA, etc.)")
    articulos_count: int = Field(description="Número de artículos de ley vinculados")
    casillas_count: int = Field(description="Número de casillas en la campaña activa")


class ModeloArticulo(BaseModel):
    norma: str = Field(description="Código de la norma")
    numero: str = Field(description="Número del artículo")
    titulo: str | None = Field(default=None, description="Título del artículo")
    casilla: str | None = Field(default=None, description="Casilla asociada")
    nota: str | None = Field(default=None, description="Nota explicativa")
    fuente: str = Field(description="Fuente del enlace")
    url_fuente: str | None = Field(default=None, description="URL de la fuente")


class DoctrinaViaArticulo(BaseModel):
    norma: str = Field(description="Código de la norma")
    numero: str = Field(description="Número del artículo")


class DoctrinaRelacionada(BaseModel):
    referencia: str = Field(description="Referencia del documento doctrinal")
    organismo_emisor: str = Field(description="Organismo emisor")
    fecha: str | None = Field(default=None, description="Fecha del documento")
    via_articulos: list[DoctrinaViaArticulo] = Field(
        default_factory=list, description="Artículos por los que se relaciona"
    )


class ModeloCasilla(BaseModel):
    codigo: str = Field(description="Código de la casilla")
    etiqueta: str = Field(description="Etiqueta descriptiva")
    descripcion: str | None = Field(default=None, description="Descripción breve")
    tipo_casilla: str | None = Field(default=None, description="Tipo (importe, checkbox, texto, etc.)")
    pagina: int | None = Field(default=None, description="Página del PDF donde aparece")
    orden: int | None = Field(default=None, description="Orden de aparición")


class ModeloClave(BaseModel):
    codigo: str = Field(description="Código de la clave")
    etiqueta: str = Field(description="Etiqueta descriptiva")
    descripcion: str | None = Field(default=None, description="Descripción de la clave")
    tipo_clave: str | None = Field(default=None, description="Tipo (rendimiento, regimen, etc.)")


class ModeloInstruccion(BaseModel):
    seccion: str = Field(description="Sección (caracteristicas, quien-debe, como-rellenar, plazo)")
    titulo: str = Field(description="Título de la sección")
    contenido: str = Field(description="Contenido paso a paso")
    orden: int = Field(description="Orden de presentación")


class ModeloNormativa(BaseModel):
    boe_id: str | None = Field(default=None, description="Identificador BOE")
    titulo: str = Field(description="Título de la norma")
    fecha: str | None = Field(default=None, description="Fecha de publicación (YYYY-MM-DD)")
    url_boe: str | None = Field(default=None, description="URL al BOE")
    resumen: str | None = Field(default=None, description="Breve descripción")


class ModeloCampana(BaseModel):
    campana: str = Field(description="Año/campaña (2025, 2024, etc.)")
    activo: bool = Field(description="Si es la campaña activa")


class ModeloFuenteOficial(BaseModel):
    tipo: str = Field(description="Tipo de fuente oficial o cuasi oficial")
    titulo: str = Field(description="Título legible de la fuente")
    url: str = Field(description="URL pública de la fuente")
    organismo: str = Field(description="Organismo emisor o titular de la fuente")
    campana: str | None = Field(default=None, description="Campaña asociada si aplica")
    boe_id: str | None = Field(default=None, description="Identificador BOE si aplica")
    fecha: str | None = Field(default=None, description="Fecha de publicación si aplica")
    oficial: bool = Field(description="Si la fuente es oficial primaria")
    nota: str | None = Field(default=None, description="Contexto corto para el uso de la fuente")


class ModeloFuentesOficialesResponse(BaseModel):
    codigo: str = Field(description="Código del modelo")
    campana_activa: str | None = Field(default=None, description="Campaña activa resuelta")
    criterio_uso: str = Field(description="Criterio de uso de estas fuentes en esdata")
    fuentes_oficiales: list[ModeloFuenteOficial] = Field(
        default_factory=list,
        description="Fuentes oficiales y de trazabilidad recomendadas para trabajar el modelo",
    )


class ModeloArtefacto(BaseModel):
    tipo: str = Field(description="Tipo de artefacto técnico del modelo")
    titulo: str = Field(description="Título legible del artefacto")
    url: str = Field(description="URL pública del artefacto")
    campana: str | None = Field(default=None, description="Campaña asociada")
    boe_id: str | None = Field(default=None, description="Identificador BOE si aplica")
    fecha: str | None = Field(default=None, description="Fecha asociada si aplica")
    formato: str | None = Field(default=None, description="Formato esperado del artefacto")
    oficial: bool = Field(description="Si el artefacto procede de fuente oficial primaria")
    nota: str | None = Field(default=None, description="Descripción corta de uso")


class ModeloArtefactosResponse(BaseModel):
    codigo: str = Field(description="Código del modelo")
    campana_activa: str | None = Field(default=None, description="Campaña activa resuelta")
    criterio_validacion: str = Field(description="Criterio de uso de estos artefactos para validación")
    artefactos: list[ModeloArtefacto] = Field(
        default_factory=list,
        description="Artefactos técnicos disponibles para trabajar o validar el modelo",
    )


class ModeloResumenOperativoResponse(BaseModel):
    codigo: str = Field(description="Código del modelo")
    nombre: str = Field(description="Nombre completo del modelo")
    impuesto: str = Field(description="Impuesto asociado")
    periodo: str | None = Field(default=None, description="Periodicidad o periodo del modelo")
    campana_activa: str | None = Field(default=None, description="Campaña activa resuelta")
    quien_debe_presentarlo: str | None = Field(
        default=None,
        description="Resumen operativo de sujetos obligados según instrucciones",
    )
    plazo_presentacion: str | None = Field(
        default=None,
        description="Resumen operativo del plazo de presentación según instrucciones",
    )
    fuentes_recomendadas: list[ModeloFuenteOficial] = Field(
        default_factory=list,
        description="Fuentes oficiales recomendadas para validar el resumen operativo",
    )


class ModeloCampanaOperativaResponse(BaseModel):
    codigo: str = Field(description="Código del modelo")
    nombre: str = Field(description="Nombre completo del modelo")
    campana: str | None = Field(default=None, description="Campaña resuelta")
    impuesto: str = Field(description="Impuesto asociado")
    periodo: str | None = Field(default=None, description="Periodo o frecuencia declarada")
    frecuencia_presentacion: str | None = Field(
        default=None,
        description="Frecuencia normalizada estimada: mensual, trimestral, anual o variable",
    )
    ventana_presentacion: str | None = Field(
        default=None,
        description="Ventana normalizada de presentación cuando se puede inferir",
    )
    canal_presentacion: str | None = Field(
        default=None,
        description="Canal normalizado de presentación: electronica, presencial o mixta",
    )
    categoria_obligado: str | None = Field(
        default=None,
        description="Categoría normalizada del sujeto obligado cuando se puede inferir",
    )
    norma_base: str | None = Field(
        default=None,
        description="Referencia corta a la norma o artículo base de la operativa del modelo",
    )
    origen_metadato: str | None = Field(
        default=None,
        description="Procedencia del metadato operativo: seed_curado, manual_curado o worker_derivado",
    )
    estado_metadato: str | None = Field(
        default=None,
        description="Estado de revisión del metadato operativo: curado o borrador",
    )
    obligados_resumen: str | None = Field(
        default=None,
        description="Resumen corto de quién debe presentar el modelo en la campaña",
    )
    plazo_resumen: str | None = Field(
        default=None,
        description="Resumen corto del plazo de presentación",
    )
    presentacion_resumen: str | None = Field(
        default=None,
        description="Resumen corto de la forma de presentación",
    )
    fuentes_recomendadas: list[ModeloFuenteOficial] = Field(
        default_factory=list,
        description="Fuentes recomendadas para confirmar la operativa de campaña",
    )


class ModelosCampanasOperativasResponse(BaseModel):
    modelos: list[ModeloCampanaOperativaResponse] = Field(
        default_factory=list,
        description="Resumen operativo de campaña para varios modelos",
    )


class ModeloDetail(BaseModel):
    codigo: str = Field(description="Código del modelo")
    nombre: str = Field(description="Nombre completo")
    periodo: str | None = Field(default=None, description="Periodo")
    impuesto: str = Field(description="Impuesto asociado")
    url_info: str | None = Field(default=None, description="URL a la sede AEAT")
    campana_activa: str | None = Field(default=None, description="Campaña activa (año)")
    campanas: list[ModeloCampana] = Field(default_factory=list, description="Campañas disponibles")
    articulos: list[ModeloArticulo] = Field(default_factory=list, description="Artículos de ley vinculados")
    casillas: list[ModeloCasilla] = Field(default_factory=list, description="Casillas de la campaña activa")
    claves: list[ModeloClave] = Field(default_factory=list, description="Claves de la campaña activa")
    instrucciones: list[ModeloInstruccion] = Field(default_factory=list, description="Instrucciones")
    normativa: list[ModeloNormativa] = Field(default_factory=list, description="Normativa BOE")
    doctrina_relacionada: list[DoctrinaRelacionada] = Field(
        default_factory=list, description="Doctrina relacionada vía artículos"
    )


# ---------------------------------------------------------------------------
# Envelopes (list/search responses)
# ---------------------------------------------------------------------------

class NormasListResponse(BaseModel):
    normas: list[Norma]


class ArticulosListResponse(BaseModel):
    norma: str = Field(description="Código de la norma")
    articulos: list[ArticuloListItem]


class LegislacionSearchResponse(BaseModel):
    q: str = Field(description="Término de búsqueda")
    resultados: list[SearchResult]


class HybridSearchResult(BaseModel):
    doc_id: int = Field(description="ID del documento")
    tipo: str = Field(description="Tipo de resultado (articulo, norma, etc.)")
    norma: str = Field(description="Código de la norma")
    numero: str = Field(description="Número del artículo")
    texto: str = Field(description="Texto del resultado")
    fragmento: str | None = Field(default=None, description="Fragmento destacado")
    vigente_desde: str = Field(description="Fecha de inicio de vigencia")
    vigente_hasta: str | None = Field(default=None, description="Fecha de fin de vigencia")
    rank: float | None = Field(default=None, description="Puntuación de relevancia")
    chunk_texto: str | None = Field(default=None, description="Texto del chunk")
    chunk_id: int | None = Field(default=None, description="ID del chunk")
    fuente_norma: str | None = Field(default=None, description="Identificador BOE/ELI")
    source_url: str | None = Field(default=None, description="URL directa al documento fuente")
    source: str = Field(description="Fuente: fulltext, vector, or hybrid")
    rrf_score: float | None = Field(default=None, description="Score RRF")
    rrf_sources: list[str] | None = Field(default=None, description="Fuentes combinadas")


class HybridSearchResponse(BaseModel):
    q: str = Field(description="Término de búsqueda")
    resultados: list[HybridSearchResult]
    search_mode: str = Field(description="Modo de búsqueda: hybrid, fulltext, vector")
    weights: dict = Field(description="Pesos usados para fulltext y vector")


class DoctrinaSearchResponse(BaseModel):
    q: str = Field(description="Término de búsqueda")
    resultados: list[DoctrinaSearchResult]


class ResultadoEvidencia(BaseModel):
    source_url: str | None = Field(default=None, description="URL directa a la fuente principal")
    fuente_norma: str | None = Field(default=None, description="Identificador BOE/ELI de la norma cuando aplique")
    fragmento_exacto: str | None = Field(default=None, description="Fragmento exacto usado para anclar el resultado")
    motivo_ranking: str | None = Field(default=None, description="Motivo corto del orden o relevancia del resultado")
    chunk_id: int | None = Field(default=None, description="ID del chunk si aplica")
    chunk_type: str | None = Field(default=None, description="Tipo de chunk: natural, size_bound, overlap")
    orden_fragmento: int | None = Field(default=None, description="Orden del fragmento dentro del documento")


class ConsultaResultado(BaseModel):
    model_config = ConfigDict(extra='allow')

    tipo: str = Field(description="Tipo de resultado agregado")
    codigo: str | None = Field(default=None, description="Código del modelo u obligación si aplica")
    nombre: str | None = Field(default=None, description="Nombre legible del resultado")
    periodo: str | None = Field(default=None, description="Periodicidad o periodo si aplica")
    impuesto: str | None = Field(default=None, description="Impuesto asociado si aplica")
    referencia: str | None = Field(default=None, description="Referencia doctrinal o documental si aplica")
    tipo_doc: str | None = Field(default=None, description="Tipo documental abreviado si aplica")
    organismo: str | None = Field(default=None, description="Organismo emisor si aplica")
    titulo: str | None = Field(default=None, description="Título del documento si aplica")
    fecha: str | None = Field(default=None, description="Fecha del documento si aplica")
    norma: str | None = Field(default=None, description="Código de la norma si aplica")
    articulo: str | None = Field(default=None, description="Número de artículo si aplica")
    texto: str | None = Field(default=None, description="Texto relevante del resultado")
    fragmento: str | None = Field(default=None, description="Resumen anclado mostrado al consumidor")
    vigente_desde: str | None = Field(default=None, description="Fecha de inicio de vigencia si aplica")
    vigente_hasta: str | None = Field(default=None, description="Fecha de fin de vigencia si aplica")
    rank: float | None = Field(default=None, description="Score de ranking si aplica")
    fuente: str | None = Field(default=None, description="Fuente principal en obligaciones")
    tipo_obligacion: str | None = Field(default=None, description="Tipo funcional de obligación")
    sujeto: str | None = Field(default=None, description="Sujeto obligado o categoría equivalente")
    periodicidad: str | None = Field(default=None, description="Periodicidad declarada")
    modelos: str | None = Field(default=None, description="Modelo o reporte asociado en obligaciones")
    ambito: str | None = Field(default=None, description="Ámbito del resultado si aplica")
    vigencia: str | None = Field(default=None, description="Estado de vigencia si aplica")
    source_url: str | None = Field(default=None, description="URL directa a la fuente mostrada por compatibilidad")
    fuente_norma: str | None = Field(default=None, description="Identificador BOE/ELI por compatibilidad")
    motivo_ranking: str | None = Field(default=None, description="Motivo corto del ranking por compatibilidad")
    evidencia: ResultadoEvidencia | None = Field(default=None, description="Bloque estable de evidencia y anclaje")


class ConsultaModelo(BaseModel):
    codigo: str = Field(description="Código del modelo")
    nombre: str = Field(description="Nombre completo del modelo")
    periodo: str | None = Field(default=None, description="Periodo o frecuencia")
    impuesto: str | None = Field(default=None, description="Impuesto asociado")
    url_info: str | None = Field(default=None, description="URL de la sede AEAT")
    campana: str | None = Field(default=None, description="Campaña resuelta")
    categoria_obligado: str | None = Field(default=None, description="Categoría normalizada del obligado")
    frecuencia: str | None = Field(default=None, description="Frecuencia normalizada de presentación")
    ventana: str | None = Field(default=None, description="Ventana de presentación")
    canal: str | None = Field(default=None, description="Canal de presentación")
    obligados_resumen: str | None = Field(default=None, description="Resumen corto de obligados")
    plazo_resumen: str | None = Field(default=None, description="Resumen corto de plazo")
    norma_base: str | None = Field(default=None, description="Norma base abreviada")
    instrucciones: list[ModeloInstruccion] = Field(default_factory=list, description="Instrucciones del modelo")


class Relevancia(BaseModel):
    nivel: str = Field(description="Nivel de relevancia: alta, media, baja")
    score: float = Field(description="Puntuación de relevancia (0-1)")
    coincidencia: str = Field(description="Descripción de la coincidencia encontrada")
    terminos_encontrados: list[str] = Field(default_factory=list, description="Términos de la query encontrados en el resultado")
    terminos_faltantes: list[str] = Field(default_factory=list, description="Términos de la query no encontrados")


class ConsultaConfianza(BaseModel):
    nivel: int = Field(description="Nivel de confianza (0-2)")
    nivel_texto: str = Field(description="Texto del nivel: alta, media, baja")
    fuentes: list[str] = Field(description="Fuentes que respaldan la respuesta")
    aviso: str | None = Field(default=None, description="Advertencia si la confianza es baja")
    modelos_cubiertos: list[str] = Field(default_factory=list, description="Modelos AEAT identificados")
    resultados_clasificados: dict[str, int] = Field(default_factory=dict, description="Conteo por tipo: modelo, normativa, doctrina, obligacion")


class ConsultaFiscalResponse(BaseModel):
    consulta: str = Field(description="Consulta resuelta o resumen de parámetros")
    modelos: list[ConsultaModelo] = Field(default_factory=list, description="Modelos resueltos para la consulta")
    resultados: list[ConsultaResultado] = Field(default_factory=list, description="Resultados agregados con evidencia y relevancia")
    total_resultados: int = Field(description="Número total de resultados agregados")
    relevancia: Relevancia | None = Field(default=None, description="Información de relevancia de la respuesta")
    confianza: ConsultaConfianza | None = Field(default=None, description="Información de confianza de la respuesta")


# ---------------------------------------------------------------------------
# BDNS
# ---------------------------------------------------------------------------

class BDNSSummary(BaseModel):
    referencia: str = Field(description="Referencia interna del documento BDNS")
    fecha: str | None = Field(default=None, description="Fecha del documento (YYYY-MM-DD)")
    titulo: str | None = Field(default=None, description="Título de la convocatoria")
    fragmento: str = Field(description="Fragmento resumido del documento")
    url_fuente: str | None = Field(default=None, description="URL pública del documento BDNS")


class BDNSDetail(BaseModel):
    referencia: str = Field(description="Referencia interna del documento BDNS")
    fecha: str | None = Field(default=None, description="Fecha del documento (YYYY-MM-DD)")
    titulo: str | None = Field(default=None, description="Título de la convocatoria")
    texto: str = Field(description="Texto completo extraído del documento")
    url_fuente: str | None = Field(default=None, description="URL pública del documento BDNS")


class BDNSListResponse(BaseModel):
    convocatorias: list[BDNSSummary]


class BORMESummary(BaseModel):
    referencia: str = Field(description="Referencia interna del documento BORME")
    fecha: str | None = Field(default=None, description="Fecha del documento (YYYY-MM-DD)")
    titulo: str | None = Field(default=None, description="Título o encabezado principal")
    tipo_documento: str = Field(description="Tipo de acto societario detectado")
    fragmento: str = Field(description="Fragmento resumido del documento")
    url_fuente: str | None = Field(default=None, description="URL pública del documento BORME")


class BORMEEmpresaRelacionada(BaseModel):
    id: int = Field(description="Identificador interno de la empresa")
    nombre: str = Field(description="Denominación social relacionada")
    rol: str = Field(description="Rol detectado de la empresa en el acto")
    confianza_extraccion: float = Field(description="Confianza de la extracción (0-1)")


class BORMEDetail(BaseModel):
    referencia: str = Field(description="Referencia interna del documento BORME")
    fecha: str | None = Field(default=None, description="Fecha del documento (YYYY-MM-DD)")
    titulo: str | None = Field(default=None, description="Título o encabezado principal")
    tipo_documento: str = Field(description="Tipo de acto societario detectado")
    texto: str = Field(description="Texto completo extraído del documento")
    url_fuente: str | None = Field(default=None, description="URL pública del documento BORME")
    empresas_relacionadas: list[BORMEEmpresaRelacionada] = Field(default_factory=list, description="Empresas relacionadas con el acto")


class BORMEListResponse(BaseModel):
    actos: list[BORMESummary]


class CNMVSummary(BaseModel):
    referencia: str = Field(description="Referencia interna del documento CNMV")
    fecha: str | None = Field(default=None, description="Fecha del documento (YYYY-MM-DD)")
    titulo: str | None = Field(default=None, description="Título principal del documento CNMV")
    tipo_documento: str = Field(description="Tipo de documento CNMV")
    ambito: str = Field(description="Ámbito regulatorio del documento")
    fragmento: str = Field(description="Fragmento resumido del documento")
    url_fuente: str | None = Field(default=None, description="URL pública del documento CNMV")


class CNMVDetail(BaseModel):
    referencia: str = Field(description="Referencia interna del documento CNMV")
    fecha: str | None = Field(default=None, description="Fecha del documento (YYYY-MM-DD)")
    titulo: str | None = Field(default=None, description="Título principal del documento CNMV")
    tipo_documento: str = Field(description="Tipo de documento CNMV")
    ambito: str = Field(description="Ámbito regulatorio del documento")
    texto: str = Field(description="Texto completo extraído del documento")
    url_fuente: str | None = Field(default=None, description="URL pública del documento CNMV")


class CNMVListResponse(BaseModel):
    documentos: list[CNMVSummary]


class SEPBLACSummary(BaseModel):
    referencia: str = Field(description="Referencia interna del documento SEPBLAC")
    fecha: str | None = Field(default=None, description="Fecha del documento (YYYY-MM-DD)")
    titulo: str | None = Field(default=None, description="Título principal del documento SEPBLAC")
    tipo_documento: str = Field(description="Tipo de documento SEPBLAC")
    ambito: str = Field(description="Ámbito operativo o regulatorio del documento")
    fragmento: str = Field(description="Fragmento resumido del documento")
    url_fuente: str | None = Field(default=None, description="URL pública del documento SEPBLAC")


class SEPBLACDetail(BaseModel):
    referencia: str = Field(description="Referencia interna del documento SEPBLAC")
    fecha: str | None = Field(default=None, description="Fecha del documento (YYYY-MM-DD)")
    titulo: str | None = Field(default=None, description="Título principal del documento SEPBLAC")
    tipo_documento: str = Field(description="Tipo de documento SEPBLAC")
    ambito: str = Field(description="Ámbito operativo o regulatorio del documento")
    texto: str = Field(description="Texto completo extraído del documento")
    url_fuente: str | None = Field(default=None, description="URL pública del documento SEPBLAC")


class SEPBLACListResponse(BaseModel):
    documentos: list[SEPBLACSummary]


class EmpresaSummary(BaseModel):
    id: int = Field(description="Identificador interno de empresa")
    nombre: str = Field(description="Denominación social detectada")
    nif: str | None = Field(default=None, description="NIF si existe")
    domicilio: str | None = Field(default=None, description="Domicilio detectado")
    fuente_inicial: str = Field(description="Fuente por la que se creó la empresa")
    documentos_count: int = Field(description="Número de documentos vinculados")


class EmpresaDocumento(BaseModel):
    referencia: str = Field(description="Referencia del documento relacionado")
    organismo_emisor: str = Field(description="Organismo emisor del documento")
    tipo_fuente: str = Field(description="Fuente documental")
    tipo_documento: str = Field(description="Tipo de documento o acto")
    fecha: str | None = Field(default=None, description="Fecha del documento")
    rol: str = Field(description="Rol de la empresa en el documento")
    confianza_extraccion: float = Field(description="Confianza de la extracción (0-1)")


class EmpresaDetail(BaseModel):
    id: int = Field(description="Identificador interno de empresa")
    nombre: str = Field(description="Denominación social detectada")
    nif: str | None = Field(default=None, description="NIF si existe")
    domicilio: str | None = Field(default=None, description="Domicilio detectado")
    fuente_inicial: str = Field(description="Fuente por la que se creó la empresa")
    documentos: list[EmpresaDocumento] = Field(default_factory=list, description="Documentos públicos relacionados")


class EmpresasListResponse(BaseModel):
    empresas: list[EmpresaSummary]


class ObligacionDocumento(BaseModel):
    referencia: str = Field(description="Referencia del documento fuente")
    organismo_emisor: str = Field(description="Organismo emisor del documento")
    tipo_fuente: str = Field(description="Fuente documental o normativa")
    tipo_documento: str = Field(description="Tipo de documento fuente")
    tipo_relacion: str = Field(description="Tipo de relación con la obligación")


class ObligacionSummary(BaseModel):
    codigo: str = Field(description="Código único de la obligación regulatoria")
    nombre: str = Field(description="Nombre corto de la obligación")
    fuente: str = Field(description="Fuente principal de la obligación")
    organismo_emisor: str = Field(description="Organismo emisor principal")
    tipo_obligacion: str = Field(description="Tipo funcional de obligación")
    sujeto_obligado: str = Field(description="Sujeto obligado principal")
    periodicidad: str | None = Field(default=None, description="Periodicidad declarada")
    reporte_modelo: str | None = Field(default=None, description="Modelo o reporte asociado")
    ambito: str = Field(description="Ámbito de cumplimiento")
    estado_vigencia: str = Field(description="Estado de vigencia")
    plazo_dias: int | None = Field(default=None, description="Días naturales para presentar")
    frecuencia_presentacion: str | None = Field(default=None, description="Frecuencia: mensual, trimestral, anual, eventual")
    ventana_presentacion: str | None = Field(default=None, description="Ventana normalizada de presentación")
    trigger_presentacion: str | None = Field(default=None, description="Evento que inicia el plazo")
    sancion_min: float | None = Field(default=None, description="Multa mínima en euros")
    sancion_max: float | None = Field(default=None, description="Multa máxima en euros")
    prescripcion_anos: int | None = Field(default=None, description="Años de prescripción")


class ObligacionDetail(BaseModel):
    codigo: str = Field(description="Código único de la obligación regulatoria")
    nombre: str = Field(description="Nombre corto de la obligación")
    fuente: str = Field(description="Fuente principal de la obligación")
    organismo_emisor: str = Field(description="Organismo emisor principal")
    tipo_obligacion: str = Field(description="Tipo funcional de obligación")
    sujeto_obligado: str = Field(description="Sujeto obligado principal")
    periodicidad: str | None = Field(default=None, description="Periodicidad declarada")
    reporte_modelo: str | None = Field(default=None, description="Modelo o reporte asociado")
    ambito: str = Field(description="Ámbito de cumplimiento")
    estado_vigencia: str = Field(description="Estado de vigencia")
    documento_origen_tipo: str = Field(description="Tipo del documento origen")
    documento_origen_ref: str = Field(description="Referencia del documento origen")
    seccion_origen: str | None = Field(default=None, description="Sección origen si aplica")
    anexo_origen: str | None = Field(default=None, description="Anexo origen si aplica")
    nota: str | None = Field(default=None, description="Nota operativa adicional")
    documentos: list[ObligacionDocumento] = Field(default_factory=list, description="Documentos relacionados")
    plazo_dias: int | None = Field(default=None, description="Días naturales para presentar")
    frecuencia_presentacion: str | None = Field(default=None, description="Frecuencia: mensual, trimestral, anual, eventual")
    ventana_presentacion: str | None = Field(default=None, description="Ventana normalizada de presentación")
    trigger_presentacion: str | None = Field(default=None, description="Evento que inicia el plazo")
    canal_presentacion: str | None = Field(default=None, description="Canal: electronica, presencial")
    obligados_resumen: str | None = Field(default=None, description="Resumen de quiénes están obligados")
    sancion_min: float | None = Field(default=None, description="Multa mínima en euros")
    sancion_max: float | None = Field(default=None, description="Multa máxima en euros")
    recargo_voluntario: str | None = Field(default=None, description="Recargo voluntario (ej: 5%)")
    recargo_involuntario: str | None = Field(default=None, description="Recargo involuntario (ej: 5-20%)")
    interes_demora: str | None = Field(default=None, description="Interés de demora (ej: TIE + 4%)")
    prescripcion_anos: int | None = Field(default=None, description="Años de prescripción")
    deposito_previo: str | None = Field(default=None, description="Requisito de depósito previo (ej: 50%)")
    fuentes_operativas: dict | None = Field(default=None, description="Fuentes operativas estructuradas")
    ultima_actualizacion: str | None = Field(default=None, description="Última actualización de datos operativos")
    origen_metadato: str | None = Field(default=None, description="Origen: seed_curado, worker_derivado")
    estado_metadato: str | None = Field(default=None, description="Estado: curado, borrador")
    evidencia_requerida: list[str] = Field(default_factory=list, description="Evidencias mínimas sugeridas para soportar el cumplimiento")
    owner_rol_sugerido: str | None = Field(default=None, description="Rol sugerido como owner de la obligación")
    criticidad: str | None = Field(default=None, description="Criticidad operativa sugerida")
    control_interno_sugerido: str | None = Field(default=None, description="Control interno sugerido para cubrir la obligación")
    procedimiento_relacionado: str | None = Field(default=None, description="Procedimiento interno sugerido relacionado con la obligación")


class ChunkSeccion(BaseModel):
    id: int = Field(description="ID de la sección")
    tipo_seccion: str = Field(description="Tipo de sección")
    numero: str | None = Field(default=None, description="Número de sección")
    titulo: str | None = Field(default=None, description="Título de la sección")
    nivel: int = Field(description="Nivel jerárquico")


class ChunkResponse(BaseModel):
    id: int = Field(description="ID del chunk")
    documento_origen_tipo: str = Field(description="Tipo de documento origen")
    documento_origen_id: int = Field(description="ID del documento origen")
    chunk_index: int = Field(description="Índice del chunk")
    chunk_type: str = Field(description="Tipo de chunk")
    titulo: str | None = Field(default=None, description="Título del chunk")
    texto: str = Field(description="Texto del chunk")
    char_start: int | None = Field(default=None, description="Posición inicial")
    char_end: int | None = Field(default=None, description="Posición final")
    token_count: int | None = Field(default=None, description="Número de tokens")
    seccion: ChunkSeccion | None = Field(default=None, description="Sección padre")


class ChunkDetailResponse(BaseModel):
    chunk: ChunkResponse


class ObligacionesListResponse(BaseModel):
    obligaciones: list[ObligacionSummary]


class ObligacionesAplicablesResponse(BaseModel):
    perfil: dict = Field(description="Perfil regulatorio usado para la evaluación de aplicabilidad")
    obligaciones: list[ObligacionSummary] = Field(default_factory=list, description="Obligaciones aplicables al perfil")


class ModelosListResponse(BaseModel):
    modelos: list[ModeloSummary]
