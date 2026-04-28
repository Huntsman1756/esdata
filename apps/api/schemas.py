"""Pydantic response models for the esdata API.

Focused on the endpoints exposed to Custom GPT Actions.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    boe_id: str | None = Field(default=None, description="ID de referencia en BOE/CELEX")
    eli_uri: str | None = Field(default=None, description="URI ELI de la norma")
    jurisdiccion: str = Field(description="Jurisdicción (es, autonomico, etc.)")
    tipo_fuente: str = Field(description="Tipo de fuente (boe, autonomica, etc.)")
    tipo_documento: str = Field(description="Tipo de documento (ley, real_decreto_legislativo, etc.)")
    ambito: str = Field(description="Ámbito temático (tributario, etc.)")
    estado_cobertura: str = Field(description="Estado de cobertura (ingestada, parcial, etc.)")
    regulacion_relacionada: str | None = Field(default=None, description="Regulación relacionada (ej: dac_directives)")


class ArticuloListItem(BaseModel):
    numero: str = Field(description="Número del artículo")
    titulo: str | None = Field(default=None, description="Título del artículo")
    tipo: str = Field(description="Tipo (articulo, disposicion, etc.)")


class ArticuloHistoryItem(BaseModel):
    numero: str = Field(description="Número del artículo")
    titulo: str | None = Field(default=None, description="Título del artículo")
    tipo: str = Field(description="Tipo (articulo, disposicion, etc.)")
    texto: str | None = Field(default=None, description="Texto de la versión")
    vigente_desde: str | None = Field(default=None, description="Fecha de inicio de vigencia (YYYY-MM-DD)")
    vigente_hasta: str | None = Field(default=None, description="Fecha de fin de vigencia (YYYY-MM-DD)")


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
    total: int = Field(default=0, description="Número total de normas devueltas")


class ArticulosListResponse(BaseModel):
    norma: str = Field(description="Código de la norma")
    articulos: list[ArticuloListItem]
    total: int = Field(default=0, description="Número total de artículos devueltos")


class ArticulosHistoryResponse(BaseModel):
    norma: str = Field(description="Código de la norma")
    articulos: list[ArticuloHistoryItem]


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
    source_hash: str | None = Field(default=None, description="Hash estable del contenido fuente/anclaje usado como evidencia")
    fragmento_exacto: str | None = Field(default=None, description="Fragmento exacto usado para anclar el resultado")
    motivo_ranking: str | None = Field(default=None, description="Motivo corto del orden o relevancia del resultado")
    chunk_id: int | None = Field(default=None, description="ID del chunk si aplica")
    chunk_type: str | None = Field(default=None, description="Tipo de chunk: natural, size_bound, overlap")
    orden_fragmento: int | None = Field(default=None, description="Orden del fragmento dentro del documento")


class ConsultaResultado(BaseModel):
    model_config = ConfigDict(extra="allow")

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
    source_hash: str | None = Field(default=None, description="Hash estable del anclaje/fuente por compatibilidad")
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
    faithfulness_score: float = Field(description="Score de grounding/faithfulness de la respuesta (0-1)")
    faithfulness_label: str = Field(description="Etiqueta cualitativa del faithfulness: alta, media, baja")
    review_required: bool = Field(description="Si la respuesta requiere revision humana por baja faithfulness")


class ChunkCitation(BaseModel):
    chunk_id: str = Field(description="Identificador del chunk o anclaje citado")
    source_document: str = Field(description="Documento o fuente principal del chunk citado")
    article_number: str | None = Field(default=None, description="Numero de articulo cuando aplica")
    rerank_score: float = Field(description="Score bruto devuelto por el reranker para este chunk")
    excerpt: str = Field(description="Extracto corto del chunk para verificacion humana")
    grounded: bool = Field(default=False, description="Si el chunk supera el umbral de grounding minimo")
    chunk_clean: bool = Field(default=True, description="Si el chunk no contiene patrones de inyeccion sospechosos")


class ClaimCitation(BaseModel):
    claim: dict = Field(description="Identificador del claim (resultado)")
    citations: list[ChunkCitation] = Field(description="Chunks que respaldan este claim")
    grounded: bool = Field(default=False, description="Si el claim cuenta con al menos una citation grounded")


class ConsultaFiscalResponse(BaseModel):
    consulta: str = Field(description="Consulta resuelta o resumen de parámetros")
    modelos: list[ConsultaModelo] = Field(default_factory=list, description="Modelos resueltos para la consulta")
    resultados: list[ConsultaResultado] = Field(default_factory=list, description="Resultados agregados con evidencia y relevancia")
    total_resultados: int = Field(description="Número total de resultados agregados")
    relevancia: Relevancia | None = Field(default=None, description="Información de relevancia de la respuesta")
    confianza: ConsultaConfianza | None = Field(default=None, description="Información de confianza de la respuesta")
    cited_chunks: list[ChunkCitation] = Field(default_factory=list, description="Chunks o anclajes priorizados para justificar la respuesta")
    claim_citations: list[ClaimCitation] = Field(default_factory=list, description="Mapeo claim-to-chunk para grounding por afirmacion")


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
    estado_vigencia: str | None = Field(default=None, description="Estado de vigencia del documento")


class CNMVDetail(BaseModel):
    referencia: str = Field(description="Referencia interna del documento CNMV")
    fecha: str | None = Field(default=None, description="Fecha del documento (YYYY-MM-DD)")
    titulo: str | None = Field(default=None, description="Título principal del documento CNMV")
    tipo_documento: str = Field(description="Tipo de documento CNMV")
    ambito: str = Field(description="Ámbito regulatorio del documento")
    texto: str = Field(description="Texto completo extraído del documento")
    url_fuente: str | None = Field(default=None, description="URL pública del documento CNMV")
    estado_vigencia: str | None = Field(default=None, description="Estado de vigencia del documento")
    numero_circular: str | None = Field(default=None, description="Número de circular (ej: 9/2008)")
    fecha_publicacion: str | None = Field(default=None, description="Fecha de publicación en BOE")
    referencia_boe: str | None = Field(default=None, description="Referencia BOE (ej: BOE-A-2009-133)")


class CNMVListResponse(BaseModel):
    documentos: list[CNMVSummary]
    skip: int = Field(default=0, description="Offset usado en la paginación")
    limit: int = Field(default=20, description="Límite de resultados solicitado")
    total: int = Field(default=0, description="Número total de resultados devueltos")


class CNMVVersionItem(BaseModel):
    version_numero: int = Field(description="Número de versión")
    estado_version: str = Field(description="Estado: vigente, modificado, derogado, sustituido")
    fecha_version: str | None = Field(default=None, description="Fecha de la versión (YYYY-MM-DD)")
    resumen_cambios: str | None = Field(default=None, description="Resumen de cambios")
    fuente_version: str | None = Field(default=None, description="URL o fuente de la versión")
    creado_en: str | None = Field(default=None, description="Timestamp de creación")


class CNMVVersionResponse(BaseModel):
    referencia: str = Field(description="Referencia del documento CNMV")
    versiones: list[CNMVVersionItem] = Field(description="Historial de versiones")
    total: int = Field(description="Número total de versiones")


class CNMVRegulationLinkItem(BaseModel):
    regulacion_codigo: str = Field(description="Código de regulación EU/ES (ej: eurl:2014:65)")
    tipo_relacion: str = Field(description="Tipo: implementa, complementa, deriva_de")
    articulo_afectado: str | None = Field(default=None, description="Artículo o sección afectada")
    creado_en: str | None = Field(default=None, description="Timestamp de creación")


class CNMVRegulationLinkResponse(BaseModel):
    referencia: str = Field(description="Referencia del documento CNMV")
    regulaciones: list[CNMVRegulationLinkItem] = Field(description="Regulaciones relacionadas")
    total: int = Field(description="Número total de regulaciones relacionadas")


class CNMVObligationLinkItem(BaseModel):
    tipo_obligacion: str = Field(description="Tipo de obligación: presentacion_modelo, remision_informacion, control_interno, comunicacion_indicio, reporting_prudencial")
    nota: str | None = Field(default=None, description="Nota descriptiva sobre la obligación")


class CNMVObligationLinkResponse(BaseModel):
    referencia: str = Field(description="Referencia del documento CNMV")
    obligaciones: list[CNMVObligationLinkItem] = Field(description="Obligaciones relacionadas")
    total: int = Field(description="Número total de obligaciones relacionadas")


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


class ConnectivityArticuloRef(BaseModel):
    norma: str = Field(description="Codigo de la norma del articulo raiz")
    numero: str = Field(description="Numero del articulo raiz")
    titulo: str | None = Field(default=None, description="Titulo del articulo raiz")


class ConnectivityModeloItem(BaseModel):
    codigo: str = Field(description="Codigo del modelo conectado")
    nombre: str = Field(description="Nombre del modelo conectado")
    impuesto: str = Field(description="Impuesto principal del modelo")
    fuente: str | None = Field(default=None, description="Fuente del enlace articulo-modelo")


class ConnectivityDoctrinaItem(BaseModel):
    referencia: str = Field(description="Referencia del documento doctrinal conectado")
    organismo_emisor: str = Field(description="Organismo emisor del documento")
    tipo_documento: str = Field(description="Tipo de documento doctrinal")
    confianza_enlace: float = Field(description="Confianza del enlace con el articulo")


class ConnectivityObligacionItem(BaseModel):
    codigo: str = Field(description="Codigo de la obligacion conectada")
    nombre: str = Field(description="Nombre de la obligacion conectada")
    fuente: str = Field(description="Fuente principal de la obligacion")
    tipo_relacion: str = Field(description="Tipo de relacion documento-obligacion que materializa la conexion")


class ConnectivityTotales(BaseModel):
    modelos: int = Field(description="Numero de modelos conectados")
    doctrina: int = Field(description="Numero de documentos doctrinales conectados")
    obligaciones: int = Field(description="Numero de obligaciones conectadas")


class ConnectivityArticuloResponse(BaseModel):
    articulo: ConnectivityArticuloRef = Field(description="Articulo raiz usado para derivar la conectividad")
    modelos: list[ConnectivityModeloItem] = Field(default_factory=list, description="Modelos conectados por el articulo")
    doctrina: list[ConnectivityDoctrinaItem] = Field(default_factory=list, description="Doctrina conectada por el articulo")
    obligaciones: list[ConnectivityObligacionItem] = Field(default_factory=list, description="Obligaciones conectadas via documentos doctrinales enlazados al articulo")
    totales: ConnectivityTotales = Field(description="Totales agregados por tipo de conexion")


class ConnectivityDocumentoRef(BaseModel):
    referencia: str = Field(description="Referencia del documento raiz")
    organismo_emisor: str = Field(description="Organismo emisor del documento")
    tipo_documento: str = Field(description="Tipo del documento raiz")


class ConnectivityDocumentoResponse(BaseModel):
    documento: ConnectivityDocumentoRef = Field(description="Documento raiz usado para derivar la conectividad")
    articulos: list[ArticuloRelacionado] = Field(default_factory=list, description="Articulos enlazados al documento")
    obligaciones: list[ConnectivityObligacionItem] = Field(default_factory=list, description="Obligaciones conectadas al documento")
    totales: dict[str, int] = Field(description="Totales agregados por tipo de conexion")


class ConnectivityObligacionRef(BaseModel):
    codigo: str = Field(description="Codigo de la obligacion raiz")
    nombre: str = Field(description="Nombre de la obligacion raiz")
    fuente: str = Field(description="Fuente principal de la obligacion")


class ConnectivityDocumentoItem(BaseModel):
    referencia: str = Field(description="Referencia del documento conectado")
    organismo_emisor: str = Field(description="Organismo emisor del documento")
    tipo_documento: str = Field(description="Tipo de documento conectado")
    tipo_relacion: str = Field(description="Tipo de relacion con la obligacion")


class ConnectivityObligacionResponse(BaseModel):
    obligacion: ConnectivityObligacionRef = Field(description="Obligacion raiz usada para derivar la conectividad")
    documentos: list[ConnectivityDocumentoItem] = Field(default_factory=list, description="Documentos conectados a la obligacion")
    articulos: list[ArticuloRelacionado] = Field(default_factory=list, description="Articulos conectados via documentos de la obligacion")
    totales: dict[str, int] = Field(description="Totales agregados por tipo de conexion")
    seccion: ChunkSeccion | None = Field(default=None, description="Sección padre")


class ConnectivityGraphNode(BaseModel):
    type: str = Field(description="Tipo de nodo en el grafo (articulo, documento, obligacion, etc.)")
    id: str = Field(description="Identificador unico del nodo")
    label: str = Field(description="Etiqueta legible del nodo")
    properties: dict = Field(description="Propiedades del nodo")


class ConnectivityGraphEdge(BaseModel):
    type: str = Field(description="Tipo de relacion (references, cites, relates_to, etc.)")
    source: str = Field(description="Nodo origen en formato tipo/id")
    target: str = Field(description="Nodo destino en formato tipo/id")
    properties: dict = Field(description="Propiedades de la relacion")


class ConnectivityGraphResponse(BaseModel):
    root: ConnectivityGraphNode = Field(description="Nodo raiz de la traversal")
    nodes: list[ConnectivityGraphNode] = Field(default_factory=list, description="Nodos descubiertos en la traversal")
    edges: list[ConnectivityGraphEdge] = Field(default_factory=list, description="Relaciones descubiertas")
    depth: int = Field(description="Profundidad alcanzada en la traversal")
    max_depth: int = Field(description="Profundidad maxima solicitada")
    stats: dict[str, int] = Field(description="Estadisticas: total_nodes, total_edges")


class ChunkDetailResponse(BaseModel):
    chunk: ChunkResponse


class ObligacionesListResponse(BaseModel):
    obligaciones: list[ObligacionSummary]


class ObligacionesAplicablesResponse(BaseModel):
    perfil: dict = Field(description="Perfil regulatorio usado para la evaluación de aplicabilidad")
    obligaciones: list[ObligacionSummary] = Field(default_factory=list, description="Obligaciones aplicables al perfil")


class ModelosListResponse(BaseModel):
    modelos: list[ModeloSummary]


class PgcMarcoActual(BaseModel):
    codigo: str = Field(description="Codigo del marco PGC vigente")
    titulo: str = Field(description="Titulo completo del marco PGC")
    tipo: str = Field(description="Tipo de documento del marco PGC")
    anio: int | None = Field(default=None, description="Ano de referencia del marco PGC")
    texto: str | None = Field(default=None, description="Descripcion resumida del marco PGC")
    url_boe: str | None = Field(default=None, description="URL de referencia oficial del BOE")
    vigente: bool = Field(description="Indica si el marco PGC esta vigente")


class PgcCuentaListItem(BaseModel):
    codigo: str = Field(description="Codigo de la cuenta PGC")
    descripcion: str = Field(description="Descripcion legible de la cuenta PGC")
    nivel: int = Field(description="Nivel jerarquico de la cuenta PGC")
    padre_codigo: str | None = Field(default=None, description="Codigo de la cuenta padre cuando aplica")
    grupo: str | None = Field(default=None, description="Grupo contable al que pertenece la cuenta")
    clase: str | None = Field(default=None, description="Clase contable de la cuenta")
    saldo_normal: str | None = Field(default=None, description="Saldo normal esperado de la cuenta")
    tipo_cuenta: str | None = Field(default=None, description="Tipo de cuenta dentro del catalogo PGC")
    vigente: bool = Field(description="Indica si la cuenta esta vigente")
    nota: str | None = Field(default=None, description="Nota adicional asociada a la cuenta")


class PgcCuentasResponse(BaseModel):
    marco: PgcMarcoActual | None = Field(default=None, description="Marco PGC vigente usado para listar cuentas")
    cuentas: list[PgcCuentaListItem] = Field(default_factory=list, description="Cuentas PGC devueltas por la consulta")


class PgcBuscarResponse(BaseModel):
    marco: PgcMarcoActual | None = Field(default=None, description="Marco PGC vigente usado en la busqueda")
    resultados: list[PgcCuentaListItem] = Field(default_factory=list, description="Cuentas PGC que coinciden con la busqueda libre")


class PgcNormaValoracionItem(BaseModel):
    norma_ref: str = Field(description="Referencia corta de la norma de valoracion")
    articulo: str | None = Field(default=None, description="Articulo o apartado de la norma cuando aplica")
    descripcion: str = Field(description="Descripcion resumida de la norma de valoracion")
    cuenta_codigo: str | None = Field(default=None, description="Codigo de cuenta PGC enlazado a la norma")
    cuenta_descripcion: str | None = Field(default=None, description="Descripcion de la cuenta PGC enlazada")


class PgcNormasValoracionResponse(BaseModel):
    marco: PgcMarcoActual | None = Field(default=None, description="Marco PGC vigente usado para listar normas")
    normas: list[PgcNormaValoracionItem] = Field(default_factory=list, description="Normas de valoracion PGC disponibles en el slice actual")


class PgcEstadoFinancieroItem(BaseModel):
    id: str = Field(description="ID del registro")
    estado: str = Field(description="Tipo de estado financiero (balance, pyg)")
    tipo_presentacion: str | None = Field(default=None, description="Tipo de presentacion dentro del estado")
    orden: int = Field(description="Orden de presentacion")
    periodo: str = Field(description="Periodo de presentacion")
    importe_base: float | None = Field(default=None, description="Importe base del periodo actual")
    importe_anterior: float | None = Field(default=None, description="Importe del periodo anterior")
    nota_pieds: str | None = Field(default=None, description="Nota a los pies relacionada")
    cuenta_codigo: str | None = Field(default=None, description="Codigo de cuenta PGC vinculada")
    cuenta_descripcion: str | None = Field(default=None, description="Descripcion de cuenta PGC vinculada")


class PgcEstadosFinancierosResponse(BaseModel):
    marco: PgcMarcoActual | None = Field(default=None, description="Marco PGC vigente usado para listar estados")
    estados: list[PgcEstadoFinancieroItem] = Field(default_factory=list, description="Estados financieros PGC disponibles")


class PgcReferenciaFiscalItem(BaseModel):
    modelo: str = Field(description="Modelo fiscal (IRPF, IVA, IS...)")
    casilla: str | None = Field(default=None, description="Casilla del modelo fiscal")
    ejercicio: str | None = Field(default=None, description="Periodo del ejercicio (anual, trimestral...)")
    nota: str | None = Field(default=None, description="Descripcion de la referencia fiscal")
    cuenta_codigo: str | None = Field(default=None, description="Codigo de cuenta PGC vinculada")
    cuenta_descripcion: str | None = Field(default=None, description="Descripcion de cuenta PGC vinculada")


class PgcReferenciasFiscalesResponse(BaseModel):
    marco: PgcMarcoActual | None = Field(default=None, description="Marco PGC vigente usado para listar referencias fiscales")
    referencias: list[PgcReferenciaFiscalItem] = Field(default_factory=list, description="Referencias fiscales PGC disponibles")


class PgcAeatReferenceItem(BaseModel):
    modelo_id: int = Field(description="ID del modelo AEAT (100=IRPF, 303=IVA, 200=IS...)")
    campana: str | None = Field(default=None, description="Campana o ejercicio fiscal")
    nota: str | None = Field(default=None, description="Descripcion de la referencia AEAT")
    cuenta_codigo: str | None = Field(default=None, description="Codigo de cuenta PGC vinculada")
    cuenta_descripcion: str | None = Field(default=None, description="Descripcion de cuenta PGC vinculada")


class PgcAeatReferencesResponse(BaseModel):
    marco: PgcMarcoActual | None = Field(default=None, description="Marco PGC vigente usado para listar referencias AEAT")
    referencias: list[PgcAeatReferenceItem] = Field(default_factory=list, description="Referencias AEAT PGC disponibles")


# ---------------------------------------------------------------------------
# XBRL
# ---------------------------------------------------------------------------

class XbrlFact(BaseModel):
    filing_id: int = Field(description="Identificador interno del filing XBRL origen")
    concept: str = Field(description="Concepto XBRL normalizado")
    value_raw: str = Field(description="Valor original del fact")
    value_numeric: float | None = Field(default=None, description="Valor numerico si es parseable")
    unit: str | None = Field(default=None, description="Unidad del fact")
    context_ref: str | None = Field(default=None, description="Contexto del fact")
    period_start: str | None = Field(default=None, description="Fecha inicial del periodo")
    period_end: str | None = Field(default=None, description="Fecha final del periodo")
    entity_identifier: str = Field(description="Identificador externo XBRL de la entidad")
    decimals: str | None = Field(default=None, description="Precision declarada en el fact")


class XbrlFactsResponse(BaseModel):
    entity_id: str | None = Field(default=None, description="Filtro aplicado sobre el identificador externo XBRL de la entidad")
    concept: str | None = Field(default=None, description="Filtro de concepto aplicado")
    facts: list[XbrlFact] = Field(default_factory=list, description="Facts XBRL recuperados")


class XbrlFilingDetail(BaseModel):
    id: int = Field(description="Identificador interno del filing")
    source_name: str = Field(description="Nombre de la fuente del filing")
    source_path: str = Field(description="Ruta o identificador de la fuente")
    entity_identifier: str = Field(description="Identificador externo XBRL de la entidad")
    period_start: str | None = Field(default=None, description="Fecha inicial del periodo (YYYY-MM-DD)")
    period_end: str | None = Field(default=None, description="Fecha final del periodo (YYYY-MM-DD)")
    filing_type: str = Field(description="Tipo de filing XBRL")
    created_at: str | None = Field(default=None, description="Fecha de creacion en el sistema")


class XbrlFilingDetailResponse(BaseModel):
    filing: XbrlFilingDetail = Field(description="Metadata del filing XBRL")
    facts: list[XbrlFact] = Field(default_factory=list, description="Facts XBRL asociados al filing")


class XbrlFilingDetail(BaseModel):
    id: int = Field(description="Identificador interno del filing")
    source_name: str = Field(description="Nombre del archivo fuente")
    source_path: str = Field(description="Ruta del archivo fuente")
    entity_identifier: str = Field(description="Identificador externo XBRL de la entidad")
    period_start: str | None = Field(default=None, description="Fecha inicial del periodo")
    period_end: str | None = Field(default=None, description="Fecha final del periodo")
    filing_type: str = Field(description="Tipo de filing XBRL")
    created_at: str | None = Field(default=None, description="Fecha de creacion en DB")


class XbrlFilingDetailResponse(BaseModel):
    filing: XbrlFilingDetail = Field(description="Metadata del filing XBRL")
    facts: list[XbrlFact] = Field(default_factory=list, description="Facts XBRL del filing")


class XbrlTaxonomyEntry(BaseModel):
    concept_qname: str = Field(description="Nombre cualificado del concepto XBRL")
    namespace: str = Field(description="Namespace de la taxonomia")
    label: str = Field(description="Etiqueta legible del concepto")
    label_language: str = Field(description="Idioma de la etiqueta (en, es, etc.)")
    label_role: str = Field(description="Rol de la etiqueta (label, presentation, definition)")
    standard: str | None = Field(default=None, description="Norma IFRS/IAS/ESEF asociada")
    data_type: str = Field(description="Tipo de dato XBRL")
    period_type: str = Field(description="Tipo de periodo (duration, instant)")
    is_monetary: bool = Field(description="Si el concepto es monetario")
    is_negative_allowed: bool = Field(description="Si permite valores negativos")


class XbrlTaxonomyResponse(BaseModel):
    standard: str | None = Field(default=None, description="Filtro de norma aplicado")
    language: str | None = Field(default=None, description="Filtro de idioma aplicado")
    concept: str | None = Field(default=None, description="Filtro de concepto aplicado")
    entries: list[XbrlTaxonomyEntry] = Field(default_factory=list, description="Conceptos de taxonomia XBRL")


class PgcXbrlMappingItem(BaseModel):
    xbrl_concept_qname: str = Field(description="Concepto XBRL IFRS/ESEF enlazado")
    pgc_account_codigo: str = Field(description="Codigo de cuenta PGC enlazada")
    pgc_account_descripcion: str | None = Field(default=None, description="Descripcion de la cuenta PGC")
    confidence: str = Field(description="Nivel de confianza (high, medium, low)")
    mapping_type: str = Field(description="Tipo de mapeo (direct, similar, derived, expert)")
    note: str | None = Field(default=None, description="Nota explicativa del mapeo")


class PgcXbrlMappingsResponse(BaseModel):
    xbrl_concept: str | None = Field(default=None, description="Filtro de concepto XBRL aplicado")
    pgc_account: str | None = Field(default=None, description="Filtro de cuenta PGC aplicado")
    confidence: str | None = Field(default=None, description="Filtro de confianza aplicado")
    mappings: list[PgcXbrlMappingItem] = Field(default_factory=list, description="Mapeos XBRL -> PGC encontrados")


class XbrlFactWithPgc(BaseModel):
    """XBRL fact enriquecido con mapeo PGC cuando existe."""
    filing_id: int = Field(description="Identificador interno del filing XBRL origen")
    concept: str = Field(description="Concepto XBRL normalizado")
    value_raw: str = Field(description="Valor original del fact")
    value_numeric: float | None = Field(default=None, description="Valor numerico si es parseable")
    unit: str | None = Field(default=None, description="Unidad del fact")
    context_ref: str | None = Field(default=None, description="Contexto del fact")
    period_start: str | None = Field(default=None, description="Fecha inicial del periodo")
    period_end: str | None = Field(default=None, description="Fecha final del periodo")
    entity_identifier: str = Field(description="Identificador externo XBRL de la entidad")
    decimals: str | None = Field(default=None, description="Precision declarada en el fact")
    pgc_account_codigo: str | None = Field(default=None, description="Cuenta PGC mapeada si existe")
    pgc_account_descripcion: str | None = Field(default=None, description="Descripcion de la cuenta PGC mapeada")
    mapping_confidence: str | None = Field(default=None, description="Confianza del mapeo XBRL->PGC")
    mapping_type: str | None = Field(default=None, description="Tipo de mapeo (direct, similar, derived, expert)")
    mapping_note: str | None = Field(default=None, description="Nota del mapeo XBRL->PGC")


class XbrlFactsWithPgcResponse(BaseModel):
    entity_id: str | None = Field(default=None, description="Filtro aplicado sobre el identificador externo XBRL de la entidad")
    concept: str | None = Field(default=None, description="Filtro de concepto aplicado")
    pgc_account: str | None = Field(default=None, description="Filtro de cuenta PGC aplicado")
    confidence: str | None = Field(default=None, description="Filtro de confianza aplicado")
    facts: list[XbrlFactWithPgc] = Field(default_factory=list, description="Facts XBRL con mapeo PGC")


# ---------------------------------------------------------------------------
# Identidad de entidad y LEI / vLEI
# ---------------------------------------------------------------------------

class EntityAlias(BaseModel):
    alias: str = Field(description="Alias o variante del nombre de la entidad")
    alias_normalizado: str = Field(description="Alias normalizado para matching")
    fuente: str = Field(description="Fuente del alias (GLEIF, BORME, CNMV, manual)")
    confianza: float = Field(description="Confianza del alias (0-1)")


class EntityIdentifier(BaseModel):
    id: int = Field(description="Identificador interno de la entidad")
    lei: str | None = Field(default=None, description="Global Legal Entity Identifier (20 caracteres)")
    nombre_legal: str | None = Field(default=None, description="Nombre legal registrado")
    pais: str | None = Field(default=None, description="Código ISO 3166-1 alpha-2 del país de registro")
    estado: str = Field(description="Estado del LEI: active, inactive, merged, replaced, expired, unit_deleted")
    vigencia_desde: str | None = Field(default=None, description="Fecha de inicio de vigencia (YYYY-MM-DD)")
    vigencia_hasta: str | None = Field(default=None, description="Fecha de fin de vigencia (YYYY-MM-DD)")
    vlei_status: str | None = Field(default=None, description="Estado de la credencial vLEI (placeholder para futuro)")
    vlei_cred_url: str | None = Field(default=None, description="URL de la credencial vLEI verificable (placeholder para futuro)")
    fuente_ref: str | None = Field(default=None, description="Referencia de la fuente original de datos")
    aliases: list[EntityAlias] = Field(default_factory=list, description="Aliases y variantes normalizadas")


class EntityLeiResponse(BaseModel):
    entidad: EntityIdentifier


class EntitySearchResult(BaseModel):
    id: int = Field(description="Identificador interno de la entidad")
    nombre: str = Field(description="Denominación social detectada")
    lei: str | None = Field(default=None, description="LEI si existe")
    nombre_legal: str | None = Field(default=None, description="Nombre legal registrado")
    pais: str | None = Field(default=None, description="Código ISO 3166-1 alpha-2 del país de registro")
    estado: str = Field(description="Estado del LEI")
    confianza: float = Field(description="Confianza de la coincidencia (0-1)")
    motivo: str | None = Field(default=None, description="Motivo de la coincidencia: lei_match, nombre_exacto, alias, fuzzy")


class EntitySearchResponse(BaseModel):
    q: str = Field(description="Término de búsqueda")
    resultados: list[EntitySearchResult]


# ---------------------------------------------------------------------------
# Screening, sanciones y PEPs
# ---------------------------------------------------------------------------

class ScreeningList(BaseModel):
    id: int = Field(description="Identificador interno de la lista")
    codigo: str = Field(description="Código de la lista (OFAC_SDN, EU_SANCTIONS, UN_SANCTIONS, SEPBLAC)")
    nombre: str = Field(description="Nombre completo de la lista")
    tipo: str = Field(description="Tipo de lista: sanctions, pep, watchlist")
    organismo: str = Field(description="Organismo que publica la lista")
    pais: str | None = Field(default=None, description="Código ISO 3166-1 alpha-2 del país/ámbito")
    url_fuente: str | None = Field(default=None, description="URL de la fuente oficial")
    descripcion: str | None = Field(default=None, description="Descripción de la lista")
    actualizada: str | None = Field(default=None, description="Fecha de última actualización (YYYY-MM-DD)")
    activo: bool = Field(description="Estado activo de la lista")


class ScreeningEntry(BaseModel):
    id: int = Field(description="Identificador interno")
    entidad_id: str = Field(description="ID de la entidad en la lista original")
    nombre: str = Field(description="Nombre de la entidad o persona")
    tipo_entidad: str = Field(description="Tipo: person, entity, vessel, aircraft")
    pais: str | None = Field(default=None, description="Código ISO 3166-1 alpha-2")
    nif: str | None = Field(default=None, description="NIF/identificador fiscal")
    fecha_nacimiento: str | None = Field(default=None, description="Fecha de nacimiento (personas)")
    aliases: list[str] = Field(default_factory=list, description="Aliases o nombres alternativos")
    categorias: list[str] = Field(default_factory=list, description="Categorías de sanción o PEP")
    descripcion: str | None = Field(default=None, description="Descripción o razón de la sanción")
    fecha_sancion: str | None = Field(default=None, description="Fecha de imposición de la sanción")
    fecha_baja: str | None = Field(default=None, description="Fecha de baja de la lista")
    activo: bool = Field(default=True, description="Estado activo en la lista")
    lista: ScreeningList = Field(description="Lista a la que pertenece esta entrada")


class ScreeningMatch(BaseModel):
    id: int | None = Field(default=None, description="Identificador interno del match")
    empresa_id: int | None = Field(default=None, description="ID de la empresa evaluada")
    entry: ScreeningEntry = Field(description="Entrada de screening que coincide")
    confianza: float = Field(description="Confianza del match (0-1)")
    motivo: str = Field(description="Motivo del match: nombre_exacto, nombre_similar, nif_exacto, alias")
    match_campo: str = Field(description="Campo que generó el match: nombre, nif, alias")
    match_texto: str | None = Field(default=None, description="Texto comparado")
    revisado: bool = Field(description="Si el match ha sido revisado manualmente")
    revisor: str | None = Field(default=None, description="Usuario que revisó el match")
    revisado_at: str | None = Field(default=None, description="Fecha de revisión (YYYY-MM-DDTHH:MM:SS)")
    notas: str | None = Field(default=None, description="Notas de la revisión")


class ScreeningCheckRequest(BaseModel):
    empresa_id: int | None = Field(default=None, description="ID de empresa en esdata")
    nombre: str = Field(default="", description="Nombre de entidad/persona a evaluar")
    nif: str | None = Field(default=None, description="NIF/identificador fiscal")
    tipo_entidad: str | None = Field(default=None, description="Tipo: person, entity, vessel, aircraft")
    listas: list[str] | None = Field(default=None, description="Filtrar por códigos de lista (OFAC_SDN, EU_SANCTIONS, etc.)")

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("nombre cannot be empty")
        return v


class ScreeningCheckResponse(BaseModel):
    empresa_id: int | None = Field(default=None)
    nombre_evaluado: str = Field(description="Nombre evaluado")
    nif_evaluado: str | None = Field(default=None)
    matches: list[ScreeningMatch] = Field(default_factory=list, description="Matches encontrados")
    sin_coincidencias: bool = Field(description="True si no hay matches con confianza > 0")


class ScreeningEntriesResponse(BaseModel):
    total: int = Field(description="Total de entradas que coinciden con los filtros")
    limit: int = Field(description="Limite de resultados aplicado")
    entries: list[ScreeningEntry] = Field(default_factory=list, description="Lista de entradas de screening")


class ScreeningMatchesResponse(BaseModel):
    empresa_id: int = Field(description="ID de la empresa")
    nombre: str = Field(description="Nombre de la empresa")
    matches: list[ScreeningMatch] = Field(default_factory=list, description="Matches previos")


# ---------------------------------------------------------------------------
# Ownership y estructura societaria
# ---------------------------------------------------------------------------

class OwnershipShare(BaseModel):
    id: int = Field(description="Identificador interno de la participación")
    empresa_id: int = Field(description="ID de la empresa participada")
    titular_id: int | None = Field(default=None, description="ID de empresa titular si es corporativo")
    titular_tipo: str = Field(description="Tipo de titular: empresa, persona")
    titular_nombre: str = Field(description="Nombre del titular")
    porcentaje: float = Field(description="Porcentaje de participación (0-100)")
    tipo_participacion: str = Field(description="Tipo: directa, indirecta")
    vigencia_desde: str | None = Field(default=None, description="Fecha de inicio (YYYY-MM-DD)")
    vigencia_hasta: str | None = Field(default=None, description="Fecha de fin (YYYY-MM-DD)")
    fuente: str = Field(description="Fuente del dato (BORME, registro_mercantil, declaracion)")
    fuente_ref: str | None = Field(default=None, description="Referencia de la fuente original")
    documento_referencia: str | None = Field(default=None, description="Referencia del documento BORME asociado")


class OwnershipShareList(BaseModel):
    empresa_id: int = Field(description="ID de la empresa")
    nombre: str = Field(description="Denominación de la empresa")
    participaciones: list[OwnershipShare] = Field(default_factory=list, description="Participaciones de esta empresa")


class OwnershipRelation(BaseModel):
    id: int = Field(description="Identificador interno de la relación")
    empresa_origen_id: int = Field(description="ID de la empresa origen")
    empresa_destino_id: int = Field(description="ID de la empresa destino")
    tipo_relacion: str = Field(description="Tipo de relación societaria")
    porcentaje: float | None = Field(default=None, description="Porcentaje si aplica")
    vigencia_desde: str | None = Field(default=None, description="Fecha de inicio (YYYY-MM-DD)")
    vigencia_hasta: str | None = Field(default=None, description="Fecha de fin (YYYY-MM-DD)")
    fuente: str = Field(description="Fuente del dato")
    fuente_ref: str | None = Field(default=None, description="Referencia de la fuente original")
    documento_referencia: str | None = Field(default=None, description="Referencia del documento asociado")
    nota: str | None = Field(default=None, description="Nota adicional")


class OwnershipRelationList(BaseModel):
    empresa_id: int = Field(description="ID de la empresa")
    nombre: str = Field(description="Denominación de la empresa")
    relaciones: list[OwnershipRelation] = Field(default_factory=list, description="Relaciones societarias")


class UboRecord(BaseModel):
    id: int = Field(description="Identificador interno del registro UBO")
    empresa_id: int = Field(description="ID de la empresa beneficiada")
    nombre_persona: str = Field(description="Nombre completo del beneficiario")
    nacionalidad: str | None = Field(default=None, description="Código ISO de nacionalidad")
    fecha_nacimiento: str | None = Field(default=None, description="Fecha de nacimiento (YYYY-MM-DD)")
    pais_residencia: str | None = Field(default=None, description="Código ISO de país de residencia")
    tipo_ubo: str = Field(description="Tipo de beneficiario final")
    porcentaje_control: float | None = Field(default=None, description="Porcentaje de control")
    umbral_superado: str | None = Field(default=None, description="Umbral de control superado")
    vigencia_desde: str | None = Field(default=None, description="Fecha de inicio (YYYY-MM-DD)")
    vigencia_hasta: str | None = Field(default=None, description="Fecha de fin (YYYY-MM-DD)")
    fuente: str = Field(description="Fuente del dato")
    fuente_ref: str | None = Field(default=None, description="Referencia de la fuente original")
    documento_referencia: str | None = Field(default=None, description="Referencia del documento asociado")
    nota: str | None = Field(default=None, description="Nota adicional")


class UboRecordList(BaseModel):
    empresa_id: int = Field(description="ID de la empresa")
    nombre: str = Field(description="Denominación de la empresa")
    beneficiarios: list[UboRecord] = Field(default_factory=list, description="Beneficiarios finales")


class OwnershipGrafoNodo(BaseModel):
    id: int = Field(description="ID de la empresa en el grafo")
    nombre: str = Field(description="Denominación social")
    nif: str | None = Field(default=None, description="NIF de la empresa")


class OwnershipGrafoArista(BaseModel):
    origen_id: int = Field(description="ID de la empresa origen")
    destino_id: int = Field(description="ID de la empresa destino")
    tipo: str = Field(description="Tipo de relación")
    porcentaje: float | None = Field(default=None, description="Porcentaje si aplica")


class OwnershipGrafoResponse(BaseModel):
    empresa_id: int = Field(description="ID de la empresa raiz del grafo")
    nombre: str = Field(description="Denominación de la empresa raiz")
    profundidad: int = Field(description="Profundidad máxima del grafo consultado")
    nodos: list[OwnershipGrafoNodo] = Field(description="Nodos del grafo de control")
    aristas: list[OwnershipGrafoArista] = Field(description="Aristas/relaciones del grafo")


class OwnershipSearchResult(BaseModel):
    id: int = Field(description="ID de la empresa")
    nombre: str = Field(description="Denominación social")
    nif: str | None = Field(default=None, description="NIF de la empresa")
    tiene_participaciones: bool = Field(description="Si tiene participaciones registradas")
    tiene_ubos: bool = Field(description="Si tiene beneficiarios finales registrados")
    tiene_relaciones: bool = Field(description="Si tiene relaciones societarias registradas")
    participaciones_count: int = Field(description="Número de participaciones")
    ubos_count: int = Field(description="Número de beneficiarios finales")


class OwnershipSearchResponse(BaseModel):
    q: str = Field(description="Término de búsqueda")
    resultados: list[OwnershipSearchResult]


# ---------------------------------------------------------------------------
# Banking (Fase 17)
# ---------------------------------------------------------------------------

class IbanValidateRequest(BaseModel):
    iban: str = Field(description="IBAN a validar")


class IbanValidationResult(BaseModel):
    valid: bool = Field(description="Si el IBAN es valido")
    iban: str = Field(description="IBAN normalizado (uppercase, sin espacios)")
    country_code: str | None = Field(default=None, description="Codigo de pais (2 letras)")
    country_length_ok: bool | None = Field(default=None, description="Longitud valida para el pais (None = pais no registrado)")
    format_ok: bool = Field(description="Formato basico valido (2L + 2D + alnum)")
    check_digit_valid: bool = Field(description="Validacion mod-97 pasada")
    errors: list[str] = Field(default_factory=list, description="Lista de errores si no es valido")


class IbanValidateResponse(BaseModel):
    result: IbanValidationResult = Field(description="Resultado de la validacion")


# ---------------------------------------------------------------------------
# Banking — ISO 20022 (Fase 17.2)
# ---------------------------------------------------------------------------

class Iso20022Party(BaseModel):
    name: str | None = Field(default=None, description="Nombre de la parte")
    address: dict | None = Field(default=None, description="Direccion postal")


class Iso20022Account(BaseModel):
    iban: str | None = Field(default=None, description="IBAN de la cuenta")
    other_id: str | None = Field(default=None, description="Identificador alternativo")
    other_scheme: str | None = Field(default=None, description="Nombre del esquema alternativo")


class Iso20022Agent(BaseModel):
    bicfi: str | None = Field(default=None, description="BIC/FI del agente")
    other_id: str | None = Field(default=None, description="Identificador alternativo del agente")


class Iso20022Remittance(BaseModel):
    unstructured: str | None = Field(default=None, description="Texto de remesa no estructurado")
    structured_reference: str | None = Field(default=None, description="Referencia estructurada")
    reference_type: str | None = Field(default=None, description="Tipo de referencia estructurada")


class Iso20022PaymentType(BaseModel):
    service_level: str | None = Field(default=None, description="Nivel de servicio")
    local_instrument: str | None = Field(default=None, description="Instrumento local")
    category_purpose: str | None = Field(default=None, description="Proposito de categoria")


class Iso20022Transaction(BaseModel):
    end_to_end_id: str | None = Field(default=None, description="ID de extremo a extremo")
    instruction_id: str | None = Field(default=None, description="ID de instruccion")
    amount: str | None = Field(default=None, description="Importe")
    currency: str | None = Field(default=None, description="Moneda")
    remittance: Iso20022Remittance | None = Field(default=None, description="Informacion de remesa")
    creditor: Iso20022Party | None = Field(default=None, description="Beneficiario")
    creditor_account: Iso20022Account | None = Field(default=None, description="Cuenta del beneficiario")
    creditor_agent: Iso20022Agent | None = Field(default=None, description="Agente del beneficiario")
    charge_bearer: str | None = Field(default=None, description="Portador de comision")
    requested_execution_date: str | None = Field(default=None, description="Fecha de ejecucion solicitada")


class Iso20022PaymentInfo(BaseModel):
    payment_information_id: str | None = Field(default=None, description="ID de informacion de pago")
    payment_method: str | None = Field(default=None, description="Metodo de pago")
    batch_booking: bool | None = Field(default=None, description="Indicador de agrupacion")
    number_of_transactions: str | None = Field(default=None, description="Numero de transacciones")
    control_sum: str | None = Field(default=None, description="Suma de control")
    payment_type_info: Iso20022PaymentType | None = Field(default=None, description="Tipo de pago")
    requested_execution_date: str | None = Field(default=None, description="Fecha de ejecucion solicitada")
    debtor: Iso20022Party | None = Field(default=None, description="Ordenante")
    debtor_account: Iso20022Account | None = Field(default=None, description="Cuenta del ordenante")
    debtor_agent: Iso20022Agent | None = Field(default=None, description="Agente del ordenante")
    creditor_agent: Iso20022Agent | None = Field(default=None, description="Agente del beneficiario (por defecto)")
    cheque_instruction: dict | None = Field(default=None, description="Instruccion de cheque")
    transactions: list[Iso20022Transaction] = Field(default_factory=list, description="Transacciones individuales")


class Iso20022GroupHeader(BaseModel):
    msg_id: str | None = Field(default=None, description="Identificador del mensaje")
    creation_datetime: str | None = Field(default=None, description="Fecha y hora de creacion")
    number_of_transactions: str | None = Field(default=None, description="Numero de transacciones")
    control_sum: str | None = Field(default=None, description="Suma de control")
    instruction_priority: str | None = Field(default=None, description="Prioridad de instruccion")


class Iso20022ParseResponse(BaseModel):
    valid: bool = Field(description="Si el documento XML es valido y parseable")
    document_type: str | None = Field(default=None, description="Tipo de documento ISO 20022 (ej: pain.008.001.08)")
    namespace: str = Field(description="Namespace del documento")
    group_header: Iso20022GroupHeader | None = Field(default=None, description="Cabecera del grupo")
    payment_informations: list[Iso20022PaymentInfo] = Field(default_factory=list, description="Bloques de informacion de pago")
    total_transactions: int = Field(description="Numero total de transacciones detectadas")
    total_control_sum: str | None = Field(default=None, description="Suma de control total")
    errors: list[str] = Field(default_factory=list, description="Lista de errores de parseo")


# ---------------------------------------------------------------------------
# Fase 17.3 — Cuadernos bancarios N43/AEB
# ---------------------------------------------------------------------------

class N43TransactionSchema(BaseModel):
    order: int = Field(description="Orden secuencial del apunte")
    booking_date: str = Field(description="Fecha de contabilidad (YYYY-MM-DD)")
    value_date: str = Field(description="Fecha valor (YYYY-MM-DD)")
    amount: float = Field(description="Importe del movimiento (positivo=haber, negativo=debe)")
    currency: str = Field(description="Divisa (ISO 4217 alpha)")
    concept_common: str = Field(description="Codigo concepto comun AEB")
    concept_own: str = Field(description="Codigo concepto propio de la entidad")
    remittance: str = Field(description="Informacion de remesa/concepto completo")
    document_number: str = Field(description="Numero de documento asociado")
    reference1: str = Field(description="Referencia 1")
    reference2: str = Field(description="Referencia 2")
    balance: float = Field(description="Saldo acumulado despues del movimiento")


class N43AccountSchema(BaseModel):
    iban: str = Field(description="IBAN construido a partir de la cuenta N43")
    bank_id: str = Field(description="Clave de entidad")
    branch_id: str = Field(description="Clave de oficina")
    account_number: str = Field(description="Numero de cuenta")
    currency: str = Field(description="Divisa de la cuenta")
    balance_start: float = Field(description="Saldo inicial")
    balance_end: float = Field(description="Saldo final")
    balance_variation: float = Field(description="Variacion del saldo")
    fecha_inicial: str = Field(description="Fecha inicial del extracto")
    fecha_final: str = Field(description="Fecha final del extracto")
    cliente_nombre: str = Field(description="Nombre abreviado del cliente")
    debe_count: int = Field(description="Numero de apuntes en debe")
    debe_total: float = Field(description="Total importes en debe")
    haber_count: int = Field(description="Numero de apuntes en haber")
    haber_total: float = Field(description="Total importes en haber")
    transaction_count: int = Field(description="Numero de transacciones parseadas")
    transactions_amount: float = Field(description="Suma total de importes de transacciones")
    transactions: list[N43TransactionSchema] = Field(default_factory=list, description="Lista de transacciones")


class N43ParseResponse(BaseModel):
    valid: bool = Field(description="Si el archivo N43 es valido y parseable")
    account_count: int = Field(description="Numero de cuentas parseadas")
    raw_line_count: int = Field(description="Numero de lineas en el archivo original")
    total_record_count: int = Field(description="Numero de registros N43 parseados")
    accounts: list[N43AccountSchema] = Field(default_factory=list, description="Cuentas parseadas")
    errors: list[str] = Field(default_factory=list, description="Errores de parseo")


# ---------------------------------------------------------------------------
# Fase 18 — Capa editorial interna y criterio experto
# ---------------------------------------------------------------------------

class NotaEditorialSummary(BaseModel):
    id: str = Field(description="Identificador de la nota editorial")
    titulo: str = Field(description="Titulo de la nota editorial")
    resumen_ejecutivo: str | None = Field(default=None, description="Resumen ejecutivo de la nota")
    tipo_contenido: str = Field(description="Tipo de contenido: resumen_interno, criterio_experto, nota_operativa")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia al documento oficial")
    autor_id: str = Field(description="Autor interno de la nota")
    estado: str = Field(description="Estado: borrador, vigente, revisar, obsoleto")
    fecha_creacion: str | None = Field(default=None, description="Fecha de creacion (YYYY-MM-DD)")
    fecha_revision: str | None = Field(default=None, description="Fecha de revision (YYYY-MM-DD)")


class NotaEditorialDetail(BaseModel):
    id: str = Field(description="Identificador de la nota editorial")
    titulo: str = Field(description="Titulo de la nota editorial")
    resumen_ejecutivo: str | None = Field(default=None, description="Resumen ejecutivo")
    contexto: str | None = Field(default=None, description="Contexto normativo o practico")
    impacto_practico: str | None = Field(default=None, description="Impacto operativo para la empresa")
    advertencias: str | None = Field(default=None, description="Advertencias o limitaciones de la nota")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia al documento oficial")
    documento_origen_id: str | None = Field(default=None, description="Referencia del documento origen")
    autor_id: str = Field(description="Autor interno")
    revisor_id: str | None = Field(default=None, description="Revisor interno")
    estado: str = Field(description="Estado: borrador, vigente, revisar, obsoleto")
    tipo_contenido: str = Field(description="Tipo: resumen_interno, criterio_experto, nota_operativa")
    fecha_creacion: str | None = Field(default=None, description="Fecha de creacion (YYYY-MM-DD)")
    fecha_revision: str | None = Field(default=None, description="Fecha de revision (YYYY-MM-DD)")
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")
    updated_at: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class NotaEditorialCreate(BaseModel):
    titulo: str = Field(description="Titulo de la nota editorial")
    resumen_ejecutivo: str | None = Field(default=None, description="Resumen ejecutivo")
    contexto: str | None = Field(default=None, description="Contexto normativo o practico")
    impacto_practico: str | None = Field(default=None, description="Impacto operativo para la empresa")
    advertencias: str | None = Field(default=None, description="Advertencias o limitaciones")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia al documento oficial (ej: BOE-A-2009-133)")
    documento_origen_referencia: str | None = Field(default=None, description="Referencia del documento_interpretativo origen")
    autor_id: str = Field(description="Identificador del autor interno")
    revisor_id: str | None = Field(default=None, description="Identificador del revisor interno")
    estado: str = Field(default="borrador", description="Estado: borrador, vigente, revisar, obsoleto")
    tipo_contenido: str = Field(default="resumen_interno", description="Tipo: resumen_interno, criterio_experto, nota_operativa")
    fecha_revision: str | None = Field(default=None, description="Fecha de revision (YYYY-MM-DD)")


class NotaEditorialUpdate(BaseModel):
    titulo: str | None = Field(default=None, description="Titulo de la nota editorial")
    resumen_ejecutivo: str | None = Field(default=None, description="Resumen ejecutivo")
    contexto: str | None = Field(default=None, description="Contexto normativo o practico")
    impacto_practico: str | None = Field(default=None, description="Impacto operativo para la empresa")
    advertencias: str | None = Field(default=None, description="Advertencias o limitaciones")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia al documento oficial")
    revisor_id: str | None = Field(default=None, description="Identificador del revisor interno")
    estado: str | None = Field(default=None, description="Estado: borrador, vigente, revisar, obsoleto")
    tipo_contenido: str | None = Field(default=None, description="Tipo de contenido")
    fecha_revision: str | None = Field(default=None, description="Fecha de revision (YYYY-MM-DD)")


class NotaEditorialListResponse(BaseModel):
    notas: list[NotaEditorialSummary]
    total: int = Field(description="Total de notas que coinciden con la consulta")


class PosicionInterpretativaSummary(BaseModel):
    id: str = Field(description="Identificador de la posicion interpretativa")
    titulo: str = Field(description="Titulo de la posicion")
    descripcion: str | None = Field(default=None, description="Descripcion corta")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia al documento oficial")
    autor_id: str = Field(description="Autor interno")
    revisor_id: str | None = Field(default=None, description="Revisor interno")
    estado: str = Field(description="Estado: borrador, vigente, revisar, obsoleto")
    version: int = Field(description="Version actual de la posicion")
    vigencia_desde: str | None = Field(default=None, description="Fecha de inicio de vigencia (YYYY-MM-DD)")
    vigencia_hasta: str | None = Field(default=None, description="Fecha de fin de vigencia (YYYY-MM-DD)")


class PosicionInterpretativaDetail(BaseModel):
    id: str = Field(description="Identificador de la posicion interpretativa")
    titulo: str = Field(description="Titulo de la posicion interpretativa")
    descripcion: str | None = Field(default=None, description="Descripcion corta")
    contenido: str | None = Field(default=None, description="Contenido completo de la posicion")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia al documento oficial")
    documento_origen_id: str | None = Field(default=None, description="Referencia del documento origen")
    autor_id: str = Field(description="Autor interno")
    revisor_id: str | None = Field(default=None, description="Revisor interno")
    estado: str = Field(description="Estado: borrador, vigente, revisar, obsoleto")
    version: int = Field(description="Version de la posicion")
    vigencia_desde: str | None = Field(default=None, description="Fecha de inicio de vigencia (YYYY-MM-DD)")
    vigencia_hasta: str | None = Field(default=None, description="Fecha de fin de vigencia (YYYY-MM-DD)")
    version_anterior_id: str | None = Field(default=None, description="ID de la version anterior")
    fecha_creacion: str | None = Field(default=None, description="Fecha de creacion (YYYY-MM-DD)")
    fecha_revision: str | None = Field(default=None, description="Fecha de revision (YYYY-MM-DD)")
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")
    updated_at: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class PosicionInterpretativaCreate(BaseModel):
    titulo: str = Field(description="Titulo de la posicion interpretativa")
    descripcion: str | None = Field(default=None, description="Descripcion corta")
    contenido: str | None = Field(default=None, description="Contenido completo de la posicion")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia al documento oficial (ej: eurl:2014:65)")
    documento_origen_referencia: str | None = Field(default=None, description="Referencia del documento_interpretativo origen")
    autor_id: str = Field(description="Identificador del autor interno")
    revisor_id: str | None = Field(default=None, description="Identificador del revisor interno")
    estado: str = Field(default="borrador", description="Estado: borrador, vigente, revisar, obsoleto")
    vigencia_desde: str | None = Field(default=None, description="Fecha de inicio de vigencia (YYYY-MM-DD)")
    vigencia_hasta: str | None = Field(default=None, description="Fecha de fin de vigencia (YYYY-MM-DD)")


class PosicionInterpretativaUpdate(BaseModel):
    titulo: str | None = Field(default=None, description="Titulo de la posicion interpretativa")
    descripcion: str | None = Field(default=None, description="Descripcion corta")
    contenido: str | None = Field(default=None, description="Contenido completo de la posicion")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia al documento oficial")
    revisor_id: str | None = Field(default=None, description="Identificador del revisor interno")
    estado: str | None = Field(default=None, description="Estado: borrador, vigente, revisar, obsoleto")
    vigencia_desde: str | None = Field(default=None, description="Fecha de inicio de vigencia (YYYY-MM-DD)")
    vigencia_hasta: str | None = Field(default=None, description="Fecha de fin de vigencia (YYYY-MM-DD)")


class PosicionInterpretativaListResponse(BaseModel):
    posiciones: list[PosicionInterpretativaSummary]
    total: int = Field(description="Total de posiciones que coinciden con la consulta")


# ---------------------------------------------------------------------------
# Fase 19 — Playbooks operativos y evidencia de cumplimiento
# ---------------------------------------------------------------------------

class PlaybookOperativoSummary(BaseModel):
    id: str = Field(description="Identificador interno del playbook")
    codigo: str = Field(description="Codigo unico del playbook")
    nombre: str = Field(description="Nombre descriptivo del procedimiento")
    obligacion_codigo: str = Field(description="Codigo de la obligacion regulatoria vinculada")
    frecuencia: str | None = Field(default=None, description="Frecuencia: mensual, trimestral, anual, eventual")
    owner_rol: str | None = Field(default=None, description="Rol responsable del playbook")
    estado: str = Field(description="Estado: activo, inactivo, revisar, obsoleto")
    version: int = Field(description="Version actual del playbook")


class PlaybookOperativoDetail(BaseModel):
    id: str = Field(description="Identificador interno del playbook")
    codigo: str = Field(description="Codigo unico del playbook")
    nombre: str = Field(description="Nombre descriptivo del procedimiento")
    obligacion_codigo: str = Field(description="Codigo de la obligacion regulatoria vinculada")
    descripcion: str | None = Field(default=None, description="Descripcion operativa completa")
    frecuencia: str | None = Field(default=None, description="Frecuencia: mensual, trimestral, anual, eventual")
    owner_rol: str | None = Field(default=None, description="Rol responsable")
    owner_id: str | None = Field(default=None, description="Responsable asignado")
    sistema_apoyo: str | None = Field(default=None, description="Sistema o herramienta de apoyo")
    errores_frecuentes: str | None = Field(default=None, description="Errores comunes y como evitarlos")
    estado: str = Field(description="Estado: activo, inactivo, revisar, obsoleto")
    version: int = Field(description="Version actual")
    version_anterior_id: str | None = Field(default=None, description="ID de version anterior")
    pasos: list = Field(default_factory=list, description="Pasos del playbook")
    evidencias: list = Field(default_factory=list, description="Evidencias requeridas")
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")
    updated_at: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class PlaybookOperativoCreate(BaseModel):
    codigo: str = Field(description="Codigo unico del playbook")
    nombre: str = Field(description="Nombre descriptivo del procedimiento")
    obligacion_codigo: str = Field(description="Codigo de la obligacion regulatoria vinculada")
    descripcion: str | None = Field(default=None, description="Descripcion operativa completa")
    frecuencia: str | None = Field(default=None, description="Frecuencia: mensual, trimestral, anual, eventual")
    owner_rol: str | None = Field(default=None, description="Rol responsable")
    owner_id: str | None = Field(default=None, description="Responsable asignado")
    sistema_apoyo: str | None = Field(default=None, description="Sistema o herramienta de apoyo")
    errores_frecuentes: str | None = Field(default=None, description="Errores comunes y como evitarlos")
    estado: str = Field(default="activo", description="Estado: activo, inactivo, revisar, obsoleto")


class PlaybookOperativoUpdate(BaseModel):
    nombre: str | None = Field(default=None, description="Nombre descriptivo del procedimiento")
    descripcion: str | None = Field(default=None, description="Descripcion operativa completa")
    frecuencia: str | None = Field(default=None, description="Frecuencia: mensual, trimestral, anual, eventual")
    owner_rol: str | None = Field(default=None, description="Rol responsable")
    owner_id: str | None = Field(default=None, description="Responsable asignado")
    sistema_apoyo: str | None = Field(default=None, description="Sistema o herramienta de apoyo")
    errores_frecuentes: str | None = Field(default=None, description="Errores comunes y como evitarlos")
    estado: str | None = Field(default=None, description="Estado: activo, inactivo, revisar, obsoleto")


class PlaybookOperativoListResponse(BaseModel):
    playbooks: list[PlaybookOperativoSummary]
    total: int = Field(description="Total de playbooks que coinciden con la consulta")


class PlaybookStepSummary(BaseModel):
    id: str = Field(description="Identificador interno del paso")
    orden: int = Field(description="Orden numerico del paso")
    titulo: str = Field(description="Titulo corto del paso")
    tipo_paso: str = Field(description="Tipo: accion, revision, aprobacion, captura, verificacion, otro")
    responsable_rol: str | None = Field(default=None, description="Rol responsable del paso")
    activo: bool = Field(description="Si el paso esta activo")


class PlaybookStepDetail(BaseModel):
    id: str = Field(description="Identificador interno del paso")
    orden: int = Field(description="Orden numerico del paso")
    titulo: str = Field(description="Titulo corto del paso")
    descripcion: str | None = Field(default=None, description="Descripcion detallada")
    tipo_paso: str = Field(description="Tipo: accion, revision, aprobacion, captura, verificacion, otro")
    responsable_rol: str | None = Field(default=None, description="Rol responsable")
    input_requerido: str | None = Field(default=None, description="Inputs necesarios")
    output_esperado: str | None = Field(default=None, description="Output esperado")
    prerrequisito_step_id: str | None = Field(default=None, description="ID del paso prerrequisito")
    checklist: list = Field(default_factory=list, description="Checklist de sub-tareas")
    activo: bool = Field(description="Si el paso esta activo")
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")
    updated_at: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class PlaybookStepCreate(BaseModel):
    orden: int = Field(description="Orden numerico del paso")
    titulo: str = Field(description="Titulo corto del paso")
    descripcion: str | None = Field(default=None, description="Descripcion detallada")
    tipo_paso: str = Field(default="accion", description="Tipo: accion, revision, aprobacion, captura, verificacion, otro")
    responsable_rol: str | None = Field(default=None, description="Rol responsable")
    input_requerido: str | None = Field(default=None, description="Inputs necesarios")
    output_esperado: str | None = Field(default=None, description="Output esperado")
    prerrequisito_step_id: str | None = Field(default=None, description="ID del paso prerrequisito")
    checklist: list = Field(default_factory=list, description="Checklist de sub-tareas")


class PlaybookStepUpdate(BaseModel):
    orden: int | None = Field(default=None, description="Orden numerico del paso")
    titulo: str | None = Field(default=None, description="Titulo corto del paso")
    descripcion: str | None = Field(default=None, description="Descripcion detallada")
    tipo_paso: str | None = Field(default=None, description="Tipo de paso")
    responsable_rol: str | None = Field(default=None, description="Rol responsable")
    input_requerido: str | None = Field(default=None, description="Inputs necesarios")
    output_esperado: str | None = Field(default=None, description="Output esperado")
    prerrequisito_step_id: str | None = Field(default=None, description="ID del paso prerrequisito")
    checklist: list | None = Field(default=None, description="Checklist de sub-tareas")
    activo: bool | None = Field(default=None, description="Si el paso esta activo")


class EvidenciaControlSummary(BaseModel):
    id: str = Field(description="Identificador interno de la evidencia")
    codigo: str = Field(description="Codigo unico de evidencia")
    nombre: str = Field(description="Nombre descriptivo de la evidencia")
    tipo_evidencia: str = Field(description="Tipo: documento, log, captura, aprobacion, extracto, reporte, otro")
    obligatoria: bool = Field(description="Si la evidencia es obligatoria")
    estado: str = Field(description="Estado: requerido, capturado, verificado, rechazado, exento")
    conservacion_dias: int | None = Field(default=None, description="Dias minimos de conservacion")


class EvidenciaControlDetail(BaseModel):
    id: str = Field(description="Identificador interno de la evidencia")
    codigo: str = Field(description="Codigo unico de evidencia")
    nombre: str = Field(description="Nombre descriptivo de la evidencia")
    descripcion: str | None = Field(default=None, description="Descripcion de evidencia valida")
    tipo_evidencia: str = Field(description="Tipo: documento, log, captura, aprobacion, extracto, reporte, otro")
    formato_requerido: str | None = Field(default=None, description="Formato esperado")
    conservacion_dias: int | None = Field(default=None, description="Dias minimos de conservacion")
    obligatoria: bool = Field(description="Si es obligatoria")
    estado: str = Field(description="Estado: requerido, capturado, verificado, rechazado, exento")
    capturado_en: str | None = Field(default=None, description="Fecha de captura (YYYY-MM-DD)")
    verificado_por: str | None = Field(default=None, description="Verificador")
    verificado_en: str | None = Field(default=None, description="Fecha de verificacion (YYYY-MM-DD)")
    nota: str | None = Field(default=None, description="Nota adicional")
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")
    updated_at: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class EvidenciaControlUpdate(BaseModel):
    estado: str | None = Field(default=None, description="Estado: requerido, capturado, verificado, rechazado, exento")
    capturado_en: str | None = Field(default=None, description="Fecha de captura (YYYY-MM-DD)")
    verificado_por: str | None = Field(default=None, description="Identificador del verificador")
    verificado_en: str | None = Field(default=None, description="Fecha de verificacion (YYYY-MM-DD)")
    nota: str | None = Field(default=None, description="Nota adicional")


class EvidenciaControlListResponse(BaseModel):
    evidencias: list[EvidenciaControlSummary]
    total: int = Field(description="Total de evidencias que coinciden con la consulta")


# ---------------------------------------------------------------------------
# International Obligations (FATCA / CRS)
# ---------------------------------------------------------------------------


class ObligacionInternacionalItem(BaseModel):
    id: int = Field(description="Identificador interno")
    codigo: str = Field(description="Codigo unico de la obligacion (ej: FATCA, CRS)")
    titulo: str = Field(description="Titulo de la obligacion")
    tipo: str = Field(description="Tipo: tratado, convenio, directiva, ley")
    jurisdiccion_origen: str | None = Field(default=None, description="Jurisdiccion de origen")
    jurisdiccion_aplicacion: str | None = Field(default=None, description="Jurisdiccion de aplicacion")
    vigente_desde: str = Field(description="Fecha de entrada en vigor")
    vigente_hasta: str | None = Field(default=None, description="Fecha de fin si aplica")
    estado: str = Field(description="Estado: activo, inactivo, obsoleto")


class ObligacionInternacionalListResponse(BaseModel):
    items: list[ObligacionInternacionalItem]
    total: int = Field(description="Total de obligaciones que coinciden con la consulta")


class ObligacionInternacionalDetail(BaseModel):
    id: int = Field(description="Identificador interno")
    codigo: str = Field(description="Codigo unico de la obligacion")
    titulo: str = Field(description="Titulo completo")
    tipo: str = Field(description="Tipo: tratado, convenio, directiva, ley")
    jurisdiccion_origen: str | None = Field(default=None)
    jurisdiccion_aplicacion: str | None = Field(default=None)
    vigente_desde: str = Field(description="Fecha de entrada en vigor")
    vigente_hasta: str | None = Field(default=None)
    descripcion: str | None = Field(default=None, description="Descripcion detallada")
    estado: str = Field(description="Estado: activo, inactivo, obsoleto")
    creado_en: str | None = Field(default=None)
    actualizado_en: str | None = Field(default=None)


class ObligacionInternacionalDetailResponse(BaseModel):
    item: ObligacionInternacionalDetail


# ---------------------------------------------------------------------------
# Fase 24 — Cumplimiento Fiscal Internacional (IRS, W-8, FATCA/CRS, GIIN/FFI)
# ---------------------------------------------------------------------------


class IrsFiscalNormaSummary(BaseModel):
    id: int = Field(description="Identificador interno de la norma fiscal IRS")
    codigo: str = Field(description="Codigo de la norma (FATCA, CRS_OECD, W8_FORMS, etc.)")
    titulo: str = Field(description="Titulo de la norma")
    tipo: str = Field(description="Tipo: publicacion, forma, instruccion, ley, convenio")
    anio_vigencia: int | None = Field(default=None, description="Ano de vigencia")
    estado: str = Field(description="Estado: activo, inactivo, obsoleto")


class IrsFiscalNormaDetail(IrsFiscalNormaSummary):
    texto: str | None = Field(default=None, description="Texto completo de la norma")
    url_fuente: str | None = Field(default=None, description="URL de la fuente oficial")
    creado_en: str | None = Field(default=None, description="Fecha de creacion en sistema")
    actualizado_en: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class IrsFiscalNormaListResponse(BaseModel):
    normas: list[IrsFiscalNormaSummary]
    total: int = Field(description="Total de normas que coinciden con la consulta")


class IrsDttaConventionSummary(BaseModel):
    id: int = Field(description="Identificador interno del convenio")
    codigo: str = Field(description="Codigo del convenio (ES_US_DTA, ES_GB_DTA, etc.)")
    pais_origen: str = Field(description="Pais origen")
    pais_destino: str = Field(description="Pais destino")
    titulo: str = Field(description="Titulo del convenio")
    fecha_firma: str | None = Field(default=None, description="Fecha de firma (YYYY-MM-DD)")
    fecha_vigencia: str | None = Field(default=None, description="Fecha de vigencia (YYYY-MM-DD)")
    tipo_acuerdo: str = Field(description="Tipo: bilateral, multilateral")
    estado: str = Field(description="Estado: vigente, expirado, modificado")


class IrsDttaConventionDetail(IrsDttaConventionSummary):
    boe_referencia: str | None = Field(default=None, description="Referencia BOE")
    articulos: dict | None = Field(default=None, description="Articulos del convenio (JSONB)")
    texto_completo: str | None = Field(default=None, description="Texto completo del convenio")
    creado_en: str | None = Field(default=None, description="Fecha de creacion en sistema")
    actualizado_en: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class IrsDttaConventionListResponse(BaseModel):
    convenios: list[IrsDttaConventionSummary]
    total: int = Field(description="Total de convenios que coinciden con la consulta")


class IrsWithholdingRuleSummary(BaseModel):
    id: int = Field(description="Identificador interno de la regla de retencion")
    codigo: str = Field(description="Codigo de la regla (DIVIDEND, INTEREST, ROYALTY, etc.)")
    tipo_renta: str = Field(description="Tipo de renta (dividends, interest, royalties, capital_gains, etc.)")
    tipo_renta_espanol: str | None = Field(default=None, description="Descripcion en espanol")
    tipo_retencion_default: float = Field(description="Tipo de retencion default (%)")
    tipo_retencion_dta: float | None = Field(default=None, description="Tipo de retencion con DTA (%)")
    pais_aplicable: str | None = Field(default=None, description="Pais al que aplica")
    estado: str = Field(description="Estado: activo, inactivo")


class IrsWithholdingRuleDetail(IrsWithholdingRuleSummary):
    descripcion: str | None = Field(default=None, description="Descripcion detallada")
    norma_referencia: str | None = Field(default=None, description="Norma de referencia")
    articulo_referencia: str | None = Field(default=None, description="Articulo de referencia")
    creado_en: str | None = Field(default=None, description="Fecha de creacion en sistema")
    actualizado_en: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class IrsWithholdingRuleListResponse(BaseModel):
    reglas: list[IrsWithholdingRuleSummary]
    total: int = Field(description="Total de reglas que coinciden con la consulta")


class IrsW8FormSummary(BaseModel):
    id: int = Field(description="Identificador interno del formulario")
    codigo: str = Field(description="Codigo del formulario (W8BEN, W8BEN_E, W8EXP, W8ECF)")
    nombre: str = Field(description="Nombre del formulario")
    tipo_sujeto: str = Field(description="Tipo: persona_fisica, persona_juridica, exento")
    validez_anios: int = Field(description="Anos de validez")
    estado: str = Field(description="Estado: activo, inactivo")


class IrsW8FormDetail(IrsW8FormSummary):
    descripcion: str | None = Field(default=None, description="Descripcion del formulario")
    finalidad: str | None = Field(default=None, description="Finalidad del formulario")
    partes: dict | None = Field(default=None, description="Estructura de partes (JSONB)")
    obligacion_asociada: str | None = Field(default=None, description="Obligacion asociada")
    texto_detalle: str | None = Field(default=None, description="Texto detallado de instrucciones")
    creado_en: str | None = Field(default=None, description="Fecha de creacion en sistema")
    actualizado_en: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class IrsW8FormListResponse(BaseModel):
    formularios: list[IrsW8FormSummary]
    total: int = Field(description="Total de formularios que coinciden con la consulta")


class IrsTinReferenceSummary(BaseModel):
    id: int = Field(description="Identificador interno de la referencia TIN")
    codigo_pais: str = Field(description="Codigo del pais (ISO 3166-1 alpha-2)")
    pais_nombre: str = Field(description="Nombre del pais")
    formato_tin: str | None = Field(default=None, description="Formato del TIN")
    ejemplo_tin: str | None = Field(default=None, description="Ejemplo de TIN")
    es_ocde: bool = Field(description="Si es pais OCDE")
    es_eu_vat: bool = Field(description="Si es pais UE VAT")


class IrsTinReferenceDetail(IrsTinReferenceSummary):
    emisor_espana: str | None = Field(default=None, description="Emisor en Espana")
    emisor_pais: str | None = Field(default=None, description="Emisor en el pais de origen")
    creado_en: str | None = Field(default=None, description="Fecha de creacion en sistema")


class IrsTinReferenceListResponse(BaseModel):
    referencias: list[IrsTinReferenceSummary]
    total: int = Field(description="Total de referencias que coinciden con la consulta")


class GiinRegistrySummary(BaseModel):
    id: int = Field(description="Identificador interno del registro GIIN")
    giin: str = Field(description="GIIN (Global Intermediary Identification Number)")
    entidad_nombre: str = Field(description="Nombre de la entidad")
    entidad_pais: str = Field(description="Pais de la entidad")
    tipo_entidad: str = Field(description="Tipo: FFI, NFFE, Exempt Beneficial Owner, etc.")
    estado_fatca: str = Field(description="Estado FATCA: activo, inactivo, suspendido")
    fecha_expiracion: str | None = Field(default=None, description="Fecha de expiracion (YYYY-MM-DD)")


class GiinRegistryDetail(GiinRegistrySummary):
    es_exempt_beneficial_owner: bool = Field(description="Si es exempt beneficial owner")
    es_sponsored_ffo: bool = Field(description="Si es sponsored FFO")
    fecha_registro: str | None = Field(default=None, description="Fecha de registro (YYYY-MM-DD)")
    nota: str | None = Field(default=None, description="Nota adicional")
    creado_en: str | None = Field(default=None, description="Fecha de creacion en sistema")
    actualizado_en: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class GiinRegistryListResponse(BaseModel):
    registros: list[GiinRegistrySummary]
    total: int = Field(description="Total de registros que coinciden con la consulta")


class IrsFiscalCheckRequest(BaseModel):
    pais_residencia: str | None = Field(default=None, description="Codigo ISO del pais de residencia del contribuyente")
    tipo_renta: str = Field(description="Tipo de renta: dividends, interest, royalties, capital_gains")
    entidad_giin: str | None = Field(default=None, description="GIIN de la entidad si aplica")
    tiene_formulario_w8: bool = Field(default=False, description="Si tiene formulario W-8 vigente")


class IrsFiscalCheckResponse(BaseModel):
    pais_residencia: str | None = Field(default=None, description="Pais de residencia")
    tipo_renta: str = Field(description="Tipo de renta")
    tipo_retencion_aplicable: float = Field(description="Tipo de retencion aplicable (%)")
    tiene_convenio_dta: bool = Field(description="Si existe convenio de doble tributacion")
    codigo_convenio: str | None = Field(default=None, description="Codigo del convenio DTA si aplica")
    requiere_w8: bool = Field(description="Si requiere formulario W-8")
    formulario_recomendado: str | None = Field(default=None, description="Formulario W-8 recomendado")
    notas: str | None = Field(default=None, description="Notas adicionales")


# ---------------------------------------------------------------------------
# Fase 22 — Matriz de controles, riesgos y pruebas
# ---------------------------------------------------------------------------

class RiesgoRegulatorioSummary(BaseModel):
    id: str = Field(description="Identificador interno del riesgo")
    codigo: str = Field(description="Codigo unico del riesgo")
    nombre: str = Field(description="Nombre descriptivo del riesgo")
    obligacion_codigo: str | None = Field(default=None, description="Codigo de la obligacion regulatoria vinculada")
    categoria: str | None = Field(default=None, description="Categoria (reporting, calidad_datos, mifid, pbcft, fiscal)")
    severidad: str = Field(description="Severidad: baja, media, alta, critica")
    probabilidad: str = Field(description="Probabilidad: baja, media, alta")
    riesgo_inherente: str | None = Field(default=None, description="Nivel de riesgo inherente: bajo, medio, alto")
    area_responsable: str | None = Field(default=None, description="Area responsable")
    owner_rol: str | None = Field(default=None, description="Rol responsable")
    estado: str = Field(description="Estado: identificado, evaluado, mitigado, cerrado")


class RiesgoRegulatorioDetail(BaseModel):
    id: str = Field(description="Identificador interno del riesgo")
    codigo: str = Field(description="Codigo unico del riesgo")
    nombre: str = Field(description="Nombre descriptivo del riesgo")
    descripcion: str | None = Field(default=None, description="Descripcion detallada")
    obligacion_codigo: str | None = Field(default=None, description="Codigo de la obligacion regulatoria vinculada")
    categoria: str | None = Field(default=None, description="Categoria")
    severidad: str = Field(description="Severidad: baja, media, alta, critica")
    probabilidad: str = Field(description="Probabilidad: baja, media, alta")
    riesgo_inherente: str | None = Field(default=None, description="Nivel de riesgo inherente")
    area_responsable: str | None = Field(default=None, description="Area responsable")
    owner_rol: str | None = Field(default=None, description="Rol responsable")
    estado: str = Field(description="Estado: identificado, evaluado, mitigado, cerrado")
    controles: list = Field(default_factory=list, description="Controles que mitigan este riesgo")
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")
    updated_at: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class RiesgoRegulatorioCreate(BaseModel):
    codigo: str = Field(description="Codigo unico del riesgo")
    nombre: str = Field(description="Nombre descriptivo del riesgo")
    descripcion: str | None = Field(default=None, description="Descripcion detallada")
    obligacion_codigo: str | None = Field(default=None, description="Codigo de la obligacion regulatoria vinculada")
    categoria: str | None = Field(default=None, description="Categoria")
    severidad: str = Field(default="media", description="Severidad: baja, media, alta, critica")
    probabilidad: str = Field(default="media", description="Probabilidad: baja, media, alta")
    area_responsable: str | None = Field(default=None, description="Area responsable")
    owner_rol: str | None = Field(default=None, description="Rol responsable")
    estado: str = Field(default="identificado", description="Estado: identificado, evaluado, mitigado, cerrado")


class RiesgoRegulatorioUpdate(BaseModel):
    nombre: str | None = Field(default=None)
    descripcion: str | None = Field(default=None)
    obligacion_codigo: str | None = Field(default=None)
    categoria: str | None = Field(default=None)
    severidad: str | None = Field(default=None)
    probabilidad: str | None = Field(default=None)
    area_responsable: str | None = Field(default=None)
    owner_rol: str | None = Field(default=None)
    estado: str | None = Field(default=None)


class RiesgoRegulatorioListResponse(BaseModel):
    riesgos: list[RiesgoRegulatorioSummary]
    total: int = Field(description="Total de riesgos que coinciden con la consulta")


class ControlInternoSummary(BaseModel):
    id: str = Field(description="Identificador interno del control")
    codigo: str = Field(description="Codigo unico del control")
    nombre: str = Field(description="Nombre descriptivo del control")
    tipo_control: str | None = Field(default=None, description="Tipo: preventivo, detectivo, correctivo")
    frecuencia: str | None = Field(default=None, description="Frecuencia del control")
    owner_rol: str | None = Field(default=None, description="Rol responsable")
    estado: str = Field(description="Estado: activo, inactivo, en_revision")


class ControlInternoDetail(BaseModel):
    id: str = Field(description="Identificador interno del control")
    codigo: str = Field(description="Codigo unico del control")
    nombre: str = Field(description="Nombre descriptivo del control")
    descripcion: str | None = Field(default=None, description="Descripcion detallada")
    tipo_control: str | None = Field(default=None, description="Tipo: preventivo, detectivo, correctivo")
    frecuencia: str | None = Field(default=None, description="Frecuencia del control")
    owner_rol: str | None = Field(default=None, description="Rol responsable")
    sistema_apoyo: str | None = Field(default=None, description="Sistema o herramienta de apoyo")
    estado: str = Field(description="Estado: activo, inactivo, en_revision")
    pruebas: list = Field(default_factory=list, description="Pruebas de ejecucion del control")
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")
    updated_at: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class ControlInternoCreate(BaseModel):
    codigo: str = Field(description="Codigo unico del control")
    nombre: str = Field(description="Nombre descriptivo del control")
    descripcion: str | None = Field(default=None, description="Descripcion detallada")
    tipo_control: str = Field(default="preventivo", description="Tipo: preventivo, detectivo, correctivo")
    frecuencia: str | None = Field(default=None, description="Frecuencia del control")
    owner_rol: str | None = Field(default=None, description="Rol responsable")
    sistema_apoyo: str | None = Field(default=None, description="Sistema o herramienta de apoyo")
    estado: str = Field(default="activo", description="Estado: activo, inactivo, en_revision")


class ControlInternoUpdate(BaseModel):
    nombre: str | None = Field(default=None)
    descripcion: str | None = Field(default=None)
    tipo_control: str | None = Field(default=None)
    frecuencia: str | None = Field(default=None)
    owner_rol: str | None = Field(default=None)
    sistema_apoyo: str | None = Field(default=None)
    estado: str | None = Field(default=None)


class ControlInternoListResponse(BaseModel):
    controles: list[ControlInternoSummary]
    total: int = Field(description="Total de controles que coinciden con la consulta")


class RiesgoControlLinkSummary(BaseModel):
    id: str = Field(description="Identificador interno del vinculo")
    riesgo_codigo: str = Field(description="Codigo del riesgo vinculado")
    riesgo_nombre: str = Field(description="Nombre del riesgo vinculado")
    control_codigo: str = Field(description="Codigo del control vinculado")
    control_nombre: str = Field(description="Nombre del control vinculado")
    efectividad: str = Field(description="Efectividad del control: no_evaluada, inefectivo, parcialmente_efectivo, efectivo")
    riesgo_residual: str = Field(description="Riesgo residual tras el control: no_evaluada, bajo, medio, alto")
    frecuencia_prueba: str | None = Field(default=None, description="Frecuencia de prueba requerida")
    criterio_suficiencia: str | None = Field(default=None, description="Criterio de suficiencia de la prueba")
    caducidad_dias: int | None = Field(default=None, description="Dias de caducidad de la prueba")
    activo: bool = Field(description="Si el vinculo esta activo")


class RiesgoControlLinkCreate(BaseModel):
    riesgo_id: str = Field(description="ID del riesgo")
    control_id: str = Field(description="ID del control")
    efectividad: str = Field(default="no_evaluada", description="Efectividad del control")
    riesgo_residual: str = Field(default="no_evaluada", description="Riesgo residual tras el control")
    frecuencia_prueba: str | None = Field(default=None, description="Frecuencia de prueba requerida")
    criterio_suficiencia: str | None = Field(default=None, description="Criterio de suficiencia de la prueba")
    caducidad_dias: int | None = Field(default=None, description="Dias de caducidad de la prueba")


class RiesgoControlLinkDetail(BaseModel):
    id: str = Field(description="Identificador interno del vinculo")
    riesgo_codigo: str = Field(description="Codigo del riesgo vinculado")
    riesgo_nombre: str = Field(description="Nombre del riesgo vinculado")
    control_codigo: str = Field(description="Codigo del control vinculado")
    control_nombre: str = Field(description="Nombre del control vinculado")
    efectividad: str = Field(description="Efectividad del control")
    riesgo_residual: str = Field(description="Riesgo residual tras el control")
    frecuencia_prueba: str | None = Field(default=None, description="Frecuencia de prueba requerida")
    criterio_suficiencia: str | None = Field(default=None, description="Criterio de suficiencia de la prueba")
    caducidad_dias: int | None = Field(default=None, description="Dias de caducidad de la prueba")
    pruebas: list = Field(default_factory=list, description="Pruebas ejecutadas")
    activo: bool = Field(description="Si el vinculo esta activo")
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")
    updated_at: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class RiesgoControlLinkListResponse(BaseModel):
    links: list[RiesgoControlLinkSummary]
    total: int = Field(description="Total de vinculos que coinciden con la consulta")


class PruebaControlSummary(BaseModel):
    id: str = Field(description="Identificador interno de la prueba")
    fecha_prueba: str = Field(description="Fecha de la prueba (YYYY-MM-DD)")
    resultado: str = Field(description="Resultado: aprobado, desaprobado, con_observaciones, no_aplicable")
    evidencia_descripcion: str | None = Field(default=None, description="Descripcion de la evidencia")
    ejecutado_por: str | None = Field(default=None, description="Persona que ejecuto la prueba")


class PruebaControlCreate(BaseModel):
    link_id: str = Field(description="ID del riesgo_control_link")
    fecha_prueba: str = Field(description="Fecha de la prueba (YYYY-MM-DD)")
    resultado: str = Field(description="Resultado: aprobado, desaprobado, con_observaciones, no_aplicable")
    evidencia_descripcion: str | None = Field(default=None, description="Descripcion de la evidencia")
    evidencia_url: str | None = Field(default=None, description="URL a la evidencia")
    ejecutado_por: str | None = Field(default=None, description="Persona que ejecuto la prueba")
    nota: str | None = Field(default=None, description="Nota adicional")


class PruebaControlDetail(BaseModel):
    id: str = Field(description="Identificador interno de la prueba")
    link_id: str = Field(description="ID del riesgo_control_link vinculado")
    fecha_prueba: str = Field(description="Fecha de la prueba (YYYY-MM-DD)")
    resultado: str = Field(description="Resultado: aprobado, desaprobado, con_observaciones, no_aplicable")
    evidencia_descripcion: str | None = Field(default=None, description="Descripcion de la evidencia")
    evidencia_url: str | None = Field(default=None, description="URL a la evidencia")
    ejecutado_por: str | None = Field(default=None, description="Persona que ejecuto la prueba")
    nota: str | None = Field(default=None, description="Nota adicional")
    activo: bool = Field(description="Si la prueba esta activa")
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")
    updated_at: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class PruebaControlListResponse(BaseModel):
    pruebas: list[PruebaControlSummary]
    total: int = Field(description="Total de pruebas que coinciden con la consulta")


class ControlGap(BaseModel):
    riesgo_codigo: str = Field(description="Codigo del riesgo")
    riesgo_nombre: str = Field(description="Nombre del riesgo")
    severidad: str = Field(description="Severidad del riesgo")
    obligacion_codigo: str | None = Field(default=None, description="Codigo de la obligacion vinculada")
    controles_asignados: int = Field(description="Numero de controles asignados")
    controles_efectivos: int = Field(description="Numero de controles efectivos")
    estado: str = Field(description="Estado del gap: sin_control, parcial, completo")
    ultima_prueba_fecha: str | None = Field(default=None, description="Fecha de ultima prueba")
    ultima_prueba_resultado: str | None = Field(default=None, description="Resultado de ultima prueba")


class ControlGapsResponse(BaseModel):
    gaps: list[ControlGap] = Field(default_factory=list, description="Controles faltantes o parciales")
    total: int = Field(description="Total de gaps encontrados")
    resumen: dict = Field(description="Resumen ejecutivo: total_riesgos, sin_control, parcial, completo")


# ---------------------------------------------------------------------------
# Fase 21 — Lineas de criterio jurisprudencial/doctrinal
# ---------------------------------------------------------------------------


class LineaCriterioSummary(BaseModel):
    id: int = Field(description="Identificador interno de la linea de criterio")
    titulo: str = Field(description="Titulo corto de la linea de criterio")
    cuestion_practica: str = Field(description="Cuestion pratica que aborda")
    estado: str = Field(description="Estado: borrador, vigente, revisar, obsoleto")
    autor_id: int | None = Field(default=None, description="ID del autor interno")
    revisor_id: int | None = Field(default=None, description="ID del revisor interno")
    ultimo_cambio: str | None = Field(default=None, description="Fecha del ultimo cambio de tendencia (YYYY-MM-DD)")
    activo: bool = Field(description="Si la linea esta activa")
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")
    updated_at: str | None = Field(default=None, description="Fecha de actualizacion en sistema")


class LineaCriterioReferencia(BaseModel):
    id: int = Field(description="ID de la referencia")
    documento_referencia: str = Field(description="Referencia canonica del documento (ej: STS-2847/2025)")
    tipo_documento: str | None = Field(default=None, description="sentencia, consulta_vinculante, circular, etc.")
    organismo_emisor: str | None = Field(default=None, description="Organismo que emite (Tribunal Supremo, DGT, etc.)")
    fecha: str | None = Field(default=None, description="Fecha del documento (YYYY-MM-DD)")
    rol_en_linea: str | None = Field(default="soporte", description="doctrina_principal, soporte_complementario, base_legal")
    orden: int = Field(description="Orden dentro de la linea")


class LineaCriterioDetail(BaseModel):
    id: int = Field(description="Identificador interno de la linea de criterio")
    titulo: str = Field(description="Titulo corto")
    cuestion_practica: str = Field(description="Cuestion practica que aborda")
    descripcion: str | None = Field(default=None, description="Descripcion operativa completa")
    criterio_dominante: str | None = Field(default=None, description="Criterio dominante resumido")
    matices: str | None = Field(default=None, description="Matices y distinciones importantes")
    excepciones: str | None = Field(default=None, description="Excepciones al criterio")
    ultimo_cambio: str | None = Field(default=None, description="Fecha del ultimo cambio de tendencia")
    estado: str = Field(description="Estado: borrador, vigente, revisar, obsoleto")
    autor_id: int | None = Field(default=None)
    revisor_id: int | None = Field(default=None)
    activo: bool = Field(description="Si la linea esta activa")
    referencias: list[LineaCriterioReferencia] = Field(default_factory=list, description="Documentos soporte")
    created_at: str | None = Field(default=None)
    updated_at: str | None = Field(default=None)


class LineaCriterioCreate(BaseModel):
    titulo: str = Field(description="Titulo corto de la linea")
    cuestion_practica: str = Field(description="Cuestion practica que aborda")
    descripcion: str | None = Field(default=None, description="Descripcion operativa completa")
    criterio_dominante: str | None = Field(default=None, description="Criterio dominante resumido")
    matices: str | None = Field(default=None, description="Matices y distinciones")
    excepciones: str | None = Field(default=None, description="Excepciones al criterio")
    estado: str = Field(default="borrador", description="Estado: borrador, vigente, revisar, obsoleto")


class LineaCriterioUpdate(BaseModel):
    titulo: str | None = Field(default=None)
    cuestion_practica: str | None = Field(default=None)
    descripcion: str | None = Field(default=None)
    criterio_dominante: str | None = Field(default=None)
    matices: str | None = Field(default=None)
    excepciones: str | None = Field(default=None)
    ultimo_cambio: str | None = Field(default=None, description="Fecha (YYYY-MM-DD)")
    estado: str | None = Field(default=None, description="borrador, vigente, revisar, obsoleto")


class LineaCriterioReferenciaCreate(BaseModel):
    documento_referencia: str = Field(description="Referencia canonica del documento")
    tipo_documento: str | None = Field(default=None)
    organismo_emisor: str | None = Field(default=None)
    fecha: str | None = Field(default=None, description="YYYY-MM-DD")
    rol_en_linea: str | None = Field(default="soporte", description="doctrina_principal, soporte_complementario, base_legal")
    orden: int = Field(default=0)


class LineaCriterioListResponse(BaseModel):
    lineas: list[LineaCriterioSummary]
    total: int = Field(description="Total de lineas que coinciden con la consulta")


# ---------------------------------------------------------------------------
# Criterio — Curacion pipeline (Fase 21)
# ---------------------------------------------------------------------------


class LineaCriterioAmbitoUpdate(BaseModel):
    ambitos: list[str] = Field(
        description="Ambitos a asignar (ej: jurisprudencia_tributaria, jurisprudencia_pbcft, jurisprudencia_mercantil_regulatoria)"
    )


class DocumentoCandidato(BaseModel):
    id: int = Field(description="ID del documento_interpretativo")
    referencia: str = Field(description="Referencia canonica del documento")
    tipo_documento: str = Field(description="Tipo: sentencia, auto, providencia, etc.")
    organismo_emisor: str = Field(description="Organismo que emite el documento")
    ambito: str = Field(description="Ambito detectado automaticamente")
    fecha: str = Field(description="Fecha del documento (YYYY-MM-DD)")
    titulo: str = Field(description="Titulo del documento")
    url_fuente: str | None = Field(default=None, description="URL a la fuente oficial")
    score: int = Field(description="Puntuacion de relevancia (0-2)")


class LineaCriterioSuggestion(BaseModel):
    linea_id: int = Field(description="ID de la linea de criterio")
    linea_titulo: str = Field(description="Titulo de la linea de criterio")
    candidatos: list[DocumentoCandidato] = Field(
        default_factory=list, description="Documentos candidatos para asignar a esta linea"
    )
    total_sugeridos: int = Field(description="Total de candidatos sugeridos")


class LineaCriterioCuracionResponse(BaseModel):
    sugerencias: list[LineaCriterioSuggestion] = Field(
        default_factory=list, description="Lista de sugerencias de curacion"
    )
    total_lineas: int = Field(description="Total de lineas con sugerencias")


class CuracionAssignRequest(BaseModel):
    linea_id: int = Field(description="ID de la linea de criterio destino")
    documento_referencia: str = Field(description="Referencia canonica del documento a asignar")
    rol_en_linea: str = Field(
        default="soporte",
        description="Rol del documento en la linea: doctrina_principal, soporte_complementario, base_legal",
    )


class CuracionAssignResponse(BaseModel):
    assigned: bool = Field(description="Si se asigno correctamente")
    linea_id: int = Field(description="ID de la linea de criterio")
    documento_referencia: str = Field(description="Referencia del documento asignado")
    referencia_existia: bool = Field(description="Si la referencia ya existia en la linea")



# ---------------------------------------------------------------------------
# Micro-obligaciones — Fase 20
# ---------------------------------------------------------------------------


class MicroObligacionSummary(BaseModel):
    codigo: str = Field(description="Codigo unico de la micro-obligacion")
    nombre: str = Field(description="Nombre corto de la micro-obligacion")
    descripcion: str | None = Field(default=None, description="Descripcion operativa")
    regulacion_relacionada: str = Field(description="Regulacion EU/ES relacionada (mifid_ii, mar, pblcft, etc.)")
    ambito: str = Field(description="Ambito operativo")
    trigger_evento: str | None = Field(default=None, description="Evento que dispara la micro-obligacion")
    frecuencia: str | None = Field(default=None, description="Frecuencia: continua, anual, trimestral, mensual, eventual")
    owner_rol: str | None = Field(default=None, description="Rol responsable del cumplimiento")
    severidad: str | None = Field(default=None, description="Criticidad: baja, media, alta")
    activo: bool = Field(default=True, description="Si la micro-obligacion esta activa")


class MicroObligacionDetail(MicroObligacionSummary):
    obligaciones_relacionadas: list = Field(default_factory=list, description="Obligaciones regulatorias relacionadas con esta micro-obligacion")


class MicroObligacionListResponse(BaseModel):
    micro_obligaciones: list[MicroObligacionSummary]
    total: int = Field(description="Total de micro-obligaciones que coinciden con la consulta")


class MicroObligacionByObligacionResponse(BaseModel):
    obligacion: dict = Field(description="Obligacion regulatoria")
    micro_obligaciones: list[MicroObligacionSummary] = Field(default_factory=list, description="Micro-obligaciones relacionadas")


# ---------------------------------------------------------------------------
# Fase 17.4 — SEPA / pain.001 XML generation
# ---------------------------------------------------------------------------

class SepaBicValidateRequest(BaseModel):
    bic: str = Field(description="BIC/FI-ID to validate (8 or 11 characters)")


class SepaBicValidateResponse(BaseModel):
    result: dict = Field(description="Validation result dict with valid, bic, country_code, errors")


class SepaTransaction(BaseModel):
    creditor_name: str = Field(description="Name of the creditor/beneficiary")
    creditor_iban: str = Field(description="IBAN of the creditor")
    amount: float = Field(description="Transaction amount")
    currency: str = Field(default="EUR", description="Currency (ISO 4217)")
    creditor_bic: str | None = Field(default=None, description="BIC of the creditor's bank")
    remittance_info: str | None = Field(default=None, description="Remittance/reference info")
    end_to_end_id: str | None = Field(default=None, description="End-to-end ID")
    instruction_id: str | None = Field(default=None, description="Instruction ID")


class SepaGenerateRequest(BaseModel):
    debtor_name: str = Field(description="Name of the ordering customer")
    debtor_iban: str = Field(description="IBAN of the ordering account")
    debtor_bic: str | None = Field(default=None, description="BIC of the debtor's bank")
    execution_date: str | None = Field(default=None, description="Execution date (YYYY-MM-DD)")
    payment_info_id_prefix: str = Field(default="PAY", description="Prefix for payment info IDs")
    batch_booking: bool = Field(default=True, description="Whether to batch book transactions")
    transactions: list[SepaTransaction] = Field(description="List of transactions to include")


class SepaGenerateResponse(BaseModel):
    valid: bool = Field(description="Whether the generated XML is valid")
    document_type: str = Field(description="ISO 20022 document type")
    namespace: str = Field(description="XML namespace used")
    group_header_msg_id: str | None = Field(default=None, description="Message ID from generated document")
    group_header_creation_date: str | None = Field(default=None, description="Creation date from generated document")
    group_header_nb_of_txs: str | None = Field(default=None, description="Total number of transactions")
    group_header_control_sum: str | None = Field(default=None, description="Total control sum")
    payment_info_count: int = Field(description="Number of payment info blocks generated")
    xml_size_bytes: int = Field(description="Size of generated XML in bytes")
    errors: list[str] = Field(default_factory=list, description="Any validation or generation errors")


class SepaGroupTransactionsRequest(BaseModel):
    transactions: list[dict] = Field(description="List of transaction dicts to group")
    max_batch_size: int = Field(default=999, ge=1, le=9999, description="Max transactions per batch")
    group_by: str = Field(default="creditor_iban", description="Field to group transactions by")


class SepaGroupBatch(BaseModel):
    group_key: str = Field(description="The grouping key value")
    transaction_count: int = Field(description="Number of transactions in this batch")
    total_amount: float = Field(description="Sum of amounts in this batch")
    transactions: list[dict] = Field(description="Transactions in this batch")


class SepaGroupTransactionsResponse(BaseModel):
    total_transactions: int = Field(description="Total input transactions")
    total_batches: int = Field(description="Number of batches produced")
    batches: list[SepaGroupBatch] = Field(description="Grouped transaction batches")


# ---------------------------------------------------------------------------
# Fase 19 — Playbooks operativos y evidencia de cumplimiento
# ---------------------------------------------------------------------------

class PlaybookStepSummary(BaseModel):
    id: str = Field(description="UUID del paso")
    orden: int = Field(description="Orden numerico dentro del playbook")
    titulo: str = Field(description="Titulo corto del paso")
    descripcion: str | None = Field(default=None, description="Descripcion detallada")
    tipo_paso: str = Field(description="Tipo: accion, revision, aprobacion, captura, verificacion, otro")
    responsable_rol: str | None = Field(default=None)
    input_requerido: str | None = Field(default=None)
    output_esperado: str | None = Field(default=None)
    activo: bool = Field(description="Si el paso esta activo")
    created_at: str | None = Field(default=None)


class PlaybookStepCreate(BaseModel):
    orden: int = Field(description="Orden numerico")
    titulo: str = Field(description="Titulo del paso")
    descripcion: str | None = Field(default=None)
    tipo_paso: str = Field(default="accion")
    responsable_rol: str | None = Field(default=None)
    input_requerido: str | None = Field(default=None)
    output_esperado: str | None = Field(default=None)
    prerrequisito_step_id: str | None = Field(default=None)
    checklist: str = Field(default="[]")


class PlaybookSummary(BaseModel):
    id: str = Field(description="UUID del playbook")
    codigo: str = Field(description="Codigo unico")
    nombre: str = Field(description="Nombre descriptivo")
    obligacion_codigo: str = Field(description="Obligacion regulatoria vinculada")
    frecuencia: str | None = Field(default=None)
    owner_rol: str | None = Field(default=None)
    owner_id: str | None = Field(default=None)
    estado: str = Field(description="activo, inactivo, revisar, obsoleto")
    version: int = Field(description="Version actual")
    created_at: str | None = Field(default=None)


class PlaybookDetail(BaseModel):
    id: str = Field(description="UUID del playbook")
    codigo: str = Field(description="Codigo unico")
    nombre: str = Field(description="Nombre descriptivo")
    obligacion_codigo: str = Field(description="Obligacion regulatoria vinculada")
    descripcion: str | None = Field(default=None)
    frecuencia: str | None = Field(default=None)
    owner_rol: str | None = Field(default=None)
    owner_id: str | None = Field(default=None)
    sistema_apoyo: str | None = Field(default=None)
    errores_frecuentes: str | None = Field(default=None)
    estado: str = Field(description="activo, inactivo, revisar, obsoleto")
    version: int = Field(description="Version actual")
    steps: list[PlaybookStepSummary] = Field(default_factory=list, description="Pasos del playbook")
    created_at: str | None = Field(default=None)
    updated_at: str | None = Field(default=None)


class PlaybookCreate(BaseModel):
    codigo: str = Field(description="Codigo unico del playbook")
    nombre: str = Field(description="Nombre descriptivo")
    obligacion_codigo: str = Field(description="FK a obligacion_regulatoria.codigo")
    descripcion: str | None = Field(default=None)
    frecuencia: str | None = Field(default=None)
    owner_rol: str | None = Field(default=None)
    owner_id: str | None = Field(default=None)
    sistema_apoyo: str | None = Field(default=None)
    errores_frecuentes: str | None = Field(default=None)


class PlaybookUpdate(BaseModel):
    nombre: str | None = Field(default=None)
    descripcion: str | None = Field(default=None)
    frecuencia: str | None = Field(default=None)
    owner_rol: str | None = Field(default=None)
    owner_id: str | None = Field(default=None)
    sistema_apoyo: str | None = Field(default=None)
    errores_frecuentes: str | None = Field(default=None)
    estado: str | None = Field(default=None)


class PlaybookListResponse(BaseModel):
    playbooks: list[PlaybookSummary]
    total: int = Field(description="Total de playbooks que coinciden con la consulta")


class PlaybookDetailResponse(BaseModel):
    playbook: PlaybookDetail = Field(description="Playbook con pasos incluidos")


class EvidenciaControlSummary(BaseModel):
    id: str = Field(description="UUID de la evidencia")
    codigo: str = Field(description="Codigo unico de evidencia")
    nombre: str = Field(description="Nombre descriptivo")
    tipo_evidencia: str = Field(description="documento, log, captura, aprobacion, extracto, reporte, otro")
    formato_requerido: str | None = Field(default=None)
    conservacion_dias: int | None = Field(default=None)
    obligatoria: bool = Field(description="Si es obligatoria")
    estado: str = Field(description="requerido, capturado, verificado, rechazado, exento")
    capturado_en: str | None = Field(default=None)
    verificado_por: str | None = Field(default=None)
    verificado_en: str | None = Field(default=None)
    step_id: str | None = Field(default=None)


class EvidenciaControlDetail(BaseModel):
    id: str = Field(description="UUID de la evidencia")
    codigo: str = Field(description="Codigo unico de evidencia")
    nombre: str = Field(description="Nombre descriptivo")
    descripcion: str | None = Field(default=None)
    tipo_evidencia: str = Field(description="documento, log, captura, aprobacion, extracto, reporte, otro")
    formato_requerido: str | None = Field(default=None)
    conservacion_dias: int | None = Field(default=None)
    obligatoria: bool = Field(description="Si es obligatoria")
    estado: str = Field(description="requerido, capturado, verificado, rechazado, exento")
    capturado_en: str | None = Field(default=None)
    verificado_por: str | None = Field(default=None)
    verificado_en: str | None = Field(default=None)
    nota: str | None = Field(default=None)
    step_id: str | None = Field(default=None)
    created_at: str | None = Field(default=None)
    updated_at: str | None = Field(default=None)


class EvidenciaControlCreate(BaseModel):
    codigo: str = Field(description="Codigo unico de evidencia")
    nombre: str = Field(description="Nombre descriptivo")
    descripcion: str | None = Field(default=None)
    tipo_evidencia: str = Field(default="documento")
    formato_requerido: str | None = Field(default=None)
    conservacion_dias: int | None = Field(default=None)
    obligatoria: bool = Field(default=True)


class EvidenciaControlUpdate(BaseModel):
    estado: str | None = Field(default=None)
    capturado_en: str | None = Field(default=None)
    verificado_por: str | None = Field(default=None)
    verificado_en: str | None = Field(default=None)
    nota: str | None = Field(default=None)


class EvidenciaControlListResponse(BaseModel):
    evidencias: list[EvidenciaControlSummary]
    total: int = Field(description="Total de evidencias que coinciden con la consulta")


# ---------------------------------------------------------------------------
# Fase 31 — Expansion regulatoria: MiCA, DAC8/DAC9, Ley 10/2010, Ley 11/2021
# ---------------------------------------------------------------------------


class CaspSummary(BaseModel):
    id: int = Field(description="Identificador interno")
    name: str = Field(description="Nombre del proveedor de servicios de criptoactivos")
    registration_number: str | None = Field(default=None, description="Numero de registro MiCA")
    home_member_state: str | None = Field(default=None, description="Estado miembro de residencia")
    passport_active: bool = Field(description="Si tiene pasaporte MiCA activo")
    status: str = Field(description="Estado: active, suspended, revoked")


class CaspDetail(CaspSummary):
    services_offered: dict | None = Field(default=None, description="Servicios ofrecidos (JSON)")
    created_at: str | None = Field(default=None, description="Fecha de creacion")


class CaspCreate(BaseModel):
    name: str = Field(description="Nombre del proveedor")
    registration_number: str | None = Field(default=None, description="Numero de registro MiCA")
    home_member_state: str | None = Field(default=None, description="Estado miembro de residencia")
    passport_active: bool = Field(default=False, description="Pasaporte MiCA activo")
    services_offered: dict | None = Field(default=None, description="Servicios ofrecidos")


class CaspUpdate(BaseModel):
    name: str | None = Field(default=None)
    registration_number: str | None = Field(default=None)
    home_member_state: str | None = Field(default=None)
    passport_active: bool | None = Field(default=None)
    services_offered: dict | None = Field(default=None)
    status: str | None = Field(default=None, description="active, suspended, revoked")


class CaspListResponse(BaseModel):
    casps: list[CaspSummary]
    total: int = Field(description="Total de CASP que coinciden con la consulta")


class CryptoAssetSummary(BaseModel):
    id: int = Field(description="Identificador interno")
    asset_type: str = Field(description="Tipo: e-money_token, asset_referenced_token, utility_token, other")
    reference_uid: str | None = Field(default=None, description="UID de referencia MiCA")
    issuer_jurisdiction: str | None = Field(default=None, description="Jurisdiccion del emisor")
    is_sha: bool = Field(description="Si es SHA (significant crypto-asset)")
    market_value_eur: float | None = Field(default=None, description="Valor de mercado en EUR")
    holders_count: int | None = Field(default=None, description="Numero de titulares")
    status: str = Field(description="Estado: active, inactive, delisted")


class CryptoAssetDetail(CryptoAssetSummary):
    created_at: str | None = Field(default=None, description="Fecha de creacion")


class CryptoAssetCreate(BaseModel):
    asset_type: str = Field(description="Tipo de criptoactivo")
    reference_uid: str | None = Field(default=None)
    issuer_jurisdiction: str | None = Field(default=None)
    is_sha: bool = Field(default=False)
    market_value_eur: float | None = Field(default=None)
    holders_count: int | None = Field(default=None)


class CryptoAssetUpdate(BaseModel):
    asset_type: str | None = Field(default=None)
    reference_uid: str | None = Field(default=None)
    issuer_jurisdiction: str | None = Field(default=None)
    is_sha: bool | None = Field(default=None)
    market_value_eur: float | None = Field(default=None)
    holders_count: int | None = Field(default=None)
    status: str | None = Field(default=None, description="active, inactive, delisted")


class CryptoAssetListResponse(BaseModel):
    assets: list[CryptoAssetSummary]
    total: int = Field(description="Total de criptoactivos que coinciden con la consulta")


class TokenizedAssetSummary(BaseModel):
    id: int = Field(description="Identificador interno")
    underlying_type: str | None = Field(default=None, description="Tipo de activo subyacente")
    face_value: float | None = Field(default=None, description="Valor facial")
    total_amount: float | None = Field(default=None, description="Cantidad total emitida")
    listing_date: str | None = Field(default=None, description="Fecha de listado (YYYY-MM-DD)")
    regulated_market: str | None = Field(default=None, description="Mercado regulado asociado")
    status: str = Field(description="Estado: active, inactive, delisted")


class TokenizedAssetDetail(TokenizedAssetSummary):
    issuer_id: int | None = Field(default=None, description="ID de la entidad emisora")
    created_at: str | None = Field(default=None, description="Fecha de creacion")


class TokenizedAssetCreate(BaseModel):
    underlying_type: str | None = Field(default=None)
    issuer_id: int | None = Field(default=None)
    face_value: float | None = Field(default=None)
    total_amount: float | None = Field(default=None)
    listing_date: str | None = Field(default=None)
    regulated_market: str | None = Field(default=None)


class TokenizedAssetUpdate(BaseModel):
    underlying_type: str | None = Field(default=None)
    issuer_id: int | None = Field(default=None)
    face_value: float | None = Field(default=None)
    total_amount: float | None = Field(default=None)
    listing_date: str | None = Field(default=None)
    regulated_market: str | None = Field(default=None)
    status: str | None = Field(default=None, description="active, inactive, delisted")


class TokenizedAssetListResponse(BaseModel):
    assets: list[TokenizedAssetSummary]
    total: int = Field(description="Total de tokenized assets que coinciden con la consulta")


class WalletCustodianSummary(BaseModel):
    id: int = Field(description="Identificador interno")
    wallet_type: str | None = Field(default=None, description="Tipo de wallet: hot, cold, hybrid")
    custody_mechanism: str | None = Field(default=None, description="Mecanismo de custodia")
    insurance_coverage: float | None = Field(default=None, description="Cobertura de seguro en EUR")
    audit_frequency: str | None = Field(default=None, description="Frecuencia de auditoria")
    status: str = Field(description="Estado: active, inactive, suspended")


class WalletCustodianDetail(WalletCustodianSummary):
    entity_id: int | None = Field(default=None, description="ID de entidad vinculada")
    created_at: str | None = Field(default=None, description="Fecha de creacion")


class WalletCustodianCreate(BaseModel):
    entity_id: int | None = Field(default=None)
    wallet_type: str | None = Field(default=None)
    custody_mechanism: str | None = Field(default=None)
    insurance_coverage: float | None = Field(default=None)
    audit_frequency: str | None = Field(default=None)


class WalletCustodianUpdate(BaseModel):
    entity_id: int | None = Field(default=None)
    wallet_type: str | None = Field(default=None)
    custody_mechanism: str | None = Field(default=None)
    insurance_coverage: float | None = Field(default=None)
    audit_frequency: str | None = Field(default=None)
    status: str | None = Field(default=None, description="active, inactive, suspended")


class WalletCustodianListResponse(BaseModel):
    custodians: list[WalletCustodianSummary]
    total: int = Field(description="Total de wallet custodians que coinciden con la consulta")


class CryptoTransactionSummary(BaseModel):
    id: int = Field(description="Identificador interno")
    sender_wallet: str | None = Field(default=None, description="Wallet del remitente")
    receiver_wallet: str | None = Field(default=None, description="Wallet del destinatario")
    asset_type: str | None = Field(default=None, description="Tipo de criptoactivo")
    amount: float | None = Field(default=None, description="Cantidad transferida")
    value_eur: float | None = Field(default=None, description="Valor en EUR")
    reporting_period: str | None = Field(default=None, description="Periodo de reporte (YYYY-MM)")


class CryptoTransactionDetail(CryptoTransactionSummary):
    sender_jurisdiction: str | None = Field(default=None, description="Jurisdiccion del remitente")
    receiver_jurisdiction: str | None = Field(default=None, description="Jurisdiccion del destinatario")
    timestamp: str | None = Field(default=None, description="Timestamp de la transaccion")
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")


class CryptoTransactionCreate(BaseModel):
    sender_wallet: str | None = Field(default=None)
    receiver_wallet: str | None = Field(default=None)
    sender_jurisdiction: str | None = Field(default=None)
    receiver_jurisdiction: str | None = Field(default=None)
    asset_type: str | None = Field(default=None)
    amount: float | None = Field(default=None)
    value_eur: float | None = Field(default=None)
    timestamp: str | None = Field(default=None)
    reporting_period: str | None = Field(default=None)


class CryptoTransactionUpdate(BaseModel):
    sender_wallet: str | None = Field(default=None)
    receiver_wallet: str | None = Field(default=None)
    sender_jurisdiction: str | None = Field(default=None)
    receiver_jurisdiction: str | None = Field(default=None)
    asset_type: str | None = Field(default=None)
    amount: float | None = Field(default=None)
    value_eur: float | None = Field(default=None)
    reporting_period: str | None = Field(default=None)


class CryptoTransactionListResponse(BaseModel):
    transactions: list[CryptoTransactionSummary]
    total: int = Field(description="Total de transacciones que coinciden con la consulta")


# --- DAC8/DAC9 schemas ---


class DacReportingEntitySummary(BaseModel):
    id: int = Field(description="Identificador interno")
    tin: str | None = Field(default=None, description="NIF de la entidad")
    entity_type: str | None = Field(default=None, description="Tipo: crypto-asset service provider, exchange, custodian")
    member_state: str | None = Field(default=None, description="Estado miembro")
    dac8_registered: bool = Field(description="Registrada en DAC8")
    dac9_registered: bool = Field(description="Registrada en DAC9")
    status: str = Field(description="Estado de la entidad")


class DacReportingEntityDetail(DacReportingEntitySummary):
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")


class DacReportingEntityCreate(BaseModel):
    tin: str | None = Field(default=None)
    entity_type: str | None = Field(default=None)
    member_state: str | None = Field(default=None)
    dac8_registered: bool = Field(default=False)
    dac9_registered: bool = Field(default=False)
    status: str = Field(default="active")


class DacReportingEntityUpdate(BaseModel):
    tin: str | None = Field(default=None)
    entity_type: str | None = Field(default=None)
    member_state: str | None = Field(default=None)
    dac8_registered: bool | None = Field(default=None)
    dac9_registered: bool | None = Field(default=None)
    status: str | None = Field(default=None)


class DacReportingEntityListResponse(BaseModel):
    entities: list[DacReportingEntitySummary]
    total: int = Field(description="Total de entidades de reporte DAC8/DAC9 que coinciden con la consulta")


class DacCryptoReportSummary(BaseModel):
    id: int = Field(description="Identificador interno")
    entity_id: int | None = Field(default=None, description="ID de la entidad reportante")
    reporting_period: str | None = Field(default=None, description="Periodo de reporte (YYYY-MM)")
    status: str = Field(description="Estado del reporte")
    crypto_transactions_count: int = Field(default=0, description="Numero de transacciones reportadas")
    wallet_holders_count: int = Field(default=0, description="Numero de titulares de wallet")


class DacCryptoReportDetail(DacCryptoReportSummary):
    submitted_at: str | None = Field(default=None, description="Fecha de envio")
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")


class DacCryptoReportCreate(BaseModel):
    entity_id: int | None = Field(default=None)
    reporting_period: str | None = Field(default=None)
    submitted_at: str | None = Field(default=None)
    status: str = Field(default="draft")
    crypto_transactions_count: int = Field(default=0)
    wallet_holders_count: int = Field(default=0)


class DacCryptoReportUpdate(BaseModel):
    entity_id: int | None = Field(default=None)
    reporting_period: str | None = Field(default=None)
    submitted_at: str | None = Field(default=None)
    status: str | None = Field(default=None)
    crypto_transactions_count: int | None = Field(default=None)
    wallet_holders_count: int | None = Field(default=None)


class DacCryptoReportListResponse(BaseModel):
    reports: list[DacCryptoReportSummary]
    total: int = Field(description="Total de reportes DAC8/DAC9 que coinciden con la consulta")


class DacWalletHolderSummary(BaseModel):
    id: int = Field(description="Identificador interno")
    report_id: int | None = Field(default=None, description="ID del reporte al que pertenece")
    wallet_address: str | None = Field(default=None, description="Direccion de wallet")
    holder_tin: str | None = Field(default=None, description="NIF del titular")
    holder_member_state: str | None = Field(default=None, description="Estado miembro del titular")
    holder_type: str | None = Field(default=None, description="Tipo: individual, entity")
    total_value_eur: float | None = Field(default=None, description="Valor total en EUR")
    verification_status: str | None = Field(default=None, description="Estado de verificacion")


class DacWalletHolderDetail(DacWalletHolderSummary):
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")


class DacWalletHolderCreate(BaseModel):
    report_id: int | None = Field(default=None)
    wallet_address: str | None = Field(default=None)
    holder_tin: str | None = Field(default=None)
    holder_member_state: str | None = Field(default=None)
    holder_type: str | None = Field(default=None)
    total_value_eur: float | None = Field(default=None)
    verification_status: str | None = Field(default=None)


class DacWalletHolderUpdate(BaseModel):
    report_id: int | None = Field(default=None)
    wallet_address: str | None = Field(default=None)
    holder_tin: str | None = Field(default=None)
    holder_member_state: str | None = Field(default=None)
    holder_type: str | None = Field(default=None)
    total_value_eur: float | None = Field(default=None)
    verification_status: str | None = Field(default=None)


class DacWalletHolderListResponse(BaseModel):
    holders: list[DacWalletHolderSummary]
    total: int = Field(description="Total de titulares de wallet que coinciden con la consulta")


# --- Ley 10/2010 PBC (Prevencion Blanqueo de Capitales) schemas ---


class PbcObligatedSubjectSummary(BaseModel):
    id: int = Field(description="Identificador interno")
    subject_type: str | None = Field(default=None, description="Tipo: credit entity, PBC entity, auditor, notary, lawyer, real_estate_agency, casino, art_dealer")
    tin: str | None = Field(default=None, description="NIF de la entidad")
    registration_number: str | None = Field(default=None, description="Numero de registro")
    supervisory_authority: str | None = Field(default=None, description="Autoridad supervisora")
    pbc_license: str | None = Field(default=None, description="Licencia PBC")
    status: str = Field(description="Estado de la entidad")


class PbcObligatedSubjectDetail(PbcObligatedSubjectSummary):
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")


class PbcObligatedSubjectCreate(BaseModel):
    subject_type: str | None = Field(default=None)
    tin: str | None = Field(default=None)
    registration_number: str | None = Field(default=None)
    supervisory_authority: str | None = Field(default=None)
    pbc_license: str | None = Field(default=None)
    status: str = Field(default="active")


class PbcObligatedSubjectUpdate(BaseModel):
    subject_type: str | None = Field(default=None)
    tin: str | None = Field(default=None)
    registration_number: str | None = Field(default=None)
    supervisory_authority: str | None = Field(default=None)
    pbc_license: str | None = Field(default=None)
    status: str | None = Field(default=None)


class PbcObligatedSubjectListResponse(BaseModel):
    subjects: list[PbcObligatedSubjectSummary]
    total: int = Field(description="Total de sujetos obligados PBC que coinciden con la consulta")


class PbcInternalControlSummary(BaseModel):
    id: int = Field(description="Identificador interno")
    obligated_subject_id: int | None = Field(default=None, description="ID del sujeto obligado")
    risk_assessment_date: str | None = Field(default=None, description="Fecha de evaluacion de riesgos")
    compliance_officer: str | None = Field(default=None, description="Oficial de cumplimiento")
    internal_reporting_channel: bool = Field(description="Canal de reporte interno activo")
    training_program: bool = Field(description="Programa de formacion activo")
    audit_trail: bool = Field(description="Registro de auditoria activo")


class PbcInternalControlDetail(PbcInternalControlSummary):
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")


class PbcInternalControlCreate(BaseModel):
    obligated_subject_id: int | None = Field(default=None)
    risk_assessment_date: str | None = Field(default=None)
    compliance_officer: str | None = Field(default=None)
    internal_reporting_channel: bool = Field(default=False)
    training_program: bool = Field(default=False)
    audit_trail: bool = Field(default=False)


class PbcInternalControlUpdate(BaseModel):
    obligated_subject_id: int | None = Field(default=None)
    risk_assessment_date: str | None = Field(default=None)
    compliance_officer: str | None = Field(default=None)
    internal_reporting_channel: bool | None = Field(default=None)
    training_program: bool | None = Field(default=None)
    audit_trail: bool | None = Field(default=None)


class PbcInternalControlListResponse(BaseModel):
    controls: list[PbcInternalControlSummary]
    total: int = Field(description="Total de controles internos que coinciden con la consulta")


class SuspiciousActivityReportSummary(BaseModel):
    id: int = Field(description="Identificador interno")
    obligated_subject_id: int | None = Field(default=None, description="ID del sujeto obligado")
    submission_date: str | None = Field(default=None, description="Fecha de presentacion")
    severity: str | None = Field(default=None, description="Gravedad: low, medium, high, critical")
    status: str = Field(description="Estado: filed, under_review, investigated, closed")
    sepblac_reference: str | None = Field(default=None, description="Referencia SEPBLAC")


class SuspiciousActivityReportDetail(SuspiciousActivityReportSummary):
    description: str | None = Field(default=None, description="Descripcion del reporte")
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")


class SuspiciousActivityReportCreate(BaseModel):
    obligated_subject_id: int | None = Field(default=None)
    submission_date: str | None = Field(default=None)
    description: str | None = Field(default=None)
    severity: str | None = Field(default=None)
    status: str = Field(default="filed")
    sepblac_reference: str | None = Field(default=None)


class SuspiciousActivityReportUpdate(BaseModel):
    obligated_subject_id: int | None = Field(default=None)
    submission_date: str | None = Field(default=None)
    description: str | None = Field(default=None)
    severity: str | None = Field(default=None)
    status: str | None = Field(default=None)
    sepblac_reference: str | None = Field(default=None)


class SuspiciousActivityReportListResponse(BaseModel):
    reports: list[SuspiciousActivityReportSummary]
    total: int = Field(description="Total de reportes de actividad sospechosa que coinciden con la consulta")


class BeneficialOwnerRecordSummary(BaseModel):
    id: int = Field(description="Identificador interno")
    entity_id: int | None = Field(default=None, description="ID de la entidad")
    owner_name: str | None = Field(default=None, description="Nombre del beneficiario")
    ownership_percentage: float | None = Field(default=None, description="Porcentaje de participacion")
    acquisition_date: str | None = Field(default=None, description="Fecha de adquisicion")
    verification_method: str | None = Field(default=None, description="Metodo de verificacion")
    verification_date: str | None = Field(default=None, description="Fecha de verificacion")


class BeneficialOwnerRecordDetail(BeneficialOwnerRecordSummary):
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")


class BeneficialOwnerRecordCreate(BaseModel):
    entity_id: int | None = Field(default=None)
    owner_name: str | None = Field(default=None)
    ownership_percentage: float | None = Field(default=None)
    acquisition_date: str | None = Field(default=None)
    verification_method: str | None = Field(default=None)
    verification_date: str | None = Field(default=None)


class BeneficialOwnerRecordUpdate(BaseModel):
    entity_id: int | None = Field(default=None)
    owner_name: str | None = Field(default=None)
    ownership_percentage: float | None = Field(default=None)
    acquisition_date: str | None = Field(default=None)
    verification_method: str | None = Field(default=None)
    verification_date: str | None = Field(default=None)


class BeneficialOwnerRecordListResponse(BaseModel):
    records: list[BeneficialOwnerRecordSummary]
    total: int = Field(description="Total de registros de beneficiario real que coinciden con la consulta")


# --- Ley 11/2021 Antifraude schemas ---


class FraudPreventionProgramSummary(BaseModel):
    id: int = Field(description="Identificador interno")
    entity_id: int | None = Field(default=None, description="ID de la entidad")
    code_of_conduct: bool = Field(description="Codigo de conducta vigente")
    internal_reporting_system: bool = Field(description="Canal de reporte interno activo")
    training_schedule: str | None = Field(default=None, description="Plan de formacion")
    audit_frequency: str | None = Field(default=None, description="Frecuencia de auditoria")
    compliance_officer_name: str | None = Field(default=None, description="Nombre del oficial de cumplimiento")
    status: str = Field(description="Estado: active, inactive, suspended")


class FraudPreventionProgramDetail(FraudPreventionProgramSummary):
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")


class FraudPreventionProgramCreate(BaseModel):
    entity_id: int | None = Field(default=None)
    code_of_conduct: bool = Field(default=False)
    internal_reporting_system: bool = Field(default=False)
    training_schedule: str | None = Field(default=None)
    audit_frequency: str | None = Field(default=None)
    compliance_officer_name: str | None = Field(default=None)
    status: str = Field(default="active")


class FraudPreventionProgramUpdate(BaseModel):
    entity_id: int | None = Field(default=None)
    code_of_conduct: bool | None = Field(default=None)
    internal_reporting_system: bool | None = Field(default=None)
    training_schedule: str | None = Field(default=None)
    audit_frequency: str | None = Field(default=None)
    compliance_officer_name: str | None = Field(default=None)
    status: str | None = Field(default=None)


class FraudPreventionProgramListResponse(BaseModel):
    programs: list[FraudPreventionProgramSummary]
    total: int = Field(description="Total de programas de prevencion de fraude que coinciden con la consulta")


class FraudRiskAssessmentSummary(BaseModel):
    id: int = Field(description="Identificador interno")
    entity_id: int | None = Field(default=None, description="ID de la entidad")
    assessment_date: str | None = Field(default=None, description="Fecha de evaluacion")
    risk_areas: str | None = Field(default=None, description="Areas de riesgo (JSON)")
    mitigation_measures: str | None = Field(default=None, description="Medidas de mitigacion")
    next_review_date: str | None = Field(default=None, description="Fecha de proxima revision")


class FraudRiskAssessmentDetail(FraudRiskAssessmentSummary):
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")


class FraudRiskAssessmentCreate(BaseModel):
    entity_id: int | None = Field(default=None)
    assessment_date: str | None = Field(default=None)
    risk_areas: str | None = Field(default=None)
    mitigation_measures: str | None = Field(default=None)
    next_review_date: str | None = Field(default=None)


class FraudRiskAssessmentUpdate(BaseModel):
    entity_id: int | None = Field(default=None)
    assessment_date: str | None = Field(default=None)
    risk_areas: str | None = Field(default=None)
    mitigation_measures: str | None = Field(default=None)
    next_review_date: str | None = Field(default=None)


class FraudRiskAssessmentListResponse(BaseModel):
    assessments: list[FraudRiskAssessmentSummary]
    total: int = Field(description="Total de evaluaciones de riesgo que coinciden con la consulta")


class FraudIncidentSummary(BaseModel):
    id: int = Field(description="Identificador interno")
    entity_id: int | None = Field(default=None, description="ID de la entidad")
    incident_date: str | None = Field(default=None, description="Fecha del incidente")
    amount_eur: float | None = Field(default=None, description="Importe en euros")
    status: str = Field(description="Estado: open, under_investigation, resolved, closed")
    resolution_date: str | None = Field(default=None, description="Fecha de resolucion")
    regulatory_notification: bool = Field(description="Notificacion regulatoria realizada")


class FraudIncidentDetail(FraudIncidentSummary):
    description: str | None = Field(default=None, description="Descripcion del incidente")
    created_at: str | None = Field(default=None, description="Fecha de creacion en sistema")


class FraudIncidentCreate(BaseModel):
    entity_id: int | None = Field(default=None)
    incident_date: str | None = Field(default=None)
    description: str | None = Field(default=None)
    amount_eur: float | None = Field(default=None)
    status: str = Field(default="open")
    resolution_date: str | None = Field(default=None)
    regulatory_notification: bool = Field(default=False)


class FraudIncidentUpdate(BaseModel):
    entity_id: int | None = Field(default=None)
    incident_date: str | None = Field(default=None)
    description: str | None = Field(default=None)
    amount_eur: float | None = Field(default=None)
    status: str | None = Field(default=None)
    resolution_date: str | None = Field(default=None)
    regulatory_notification: bool | None = Field(default=None)


class FraudIncidentListResponse(BaseModel):
    incidents: list[FraudIncidentSummary]
    total: int = Field(description="Total de incidentes de fraude que coinciden con la consulta")
