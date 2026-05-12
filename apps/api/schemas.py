"""Pydantic response models for the esdata API.

Focused on the endpoints exposed to Custom GPT Actions.
"""

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


class ConfianzaInfo(BaseModel):
    nivel: int = Field(description="Nivel de confianza (0-2)")
    fuentes: list[str] = Field(description="Fuentes que respaldan la respuesta")
    aviso: str | None = Field(
        default=None, description="Advertencia si la confianza es baja"
    )


# ---------------------------------------------------------------------------
# Legislacion
# ---------------------------------------------------------------------------


class Norma(BaseModel):
    codigo: str = Field(description="Código de la norma (ej: LIVA, LIRPF)")
    titulo: str = Field(description="Título completo de la norma")
    boe_id: str | None = Field(default=None, description="Identificador BOE")
    eli_uri: str | None = Field(default=None, description="URI ELI de la norma")
    jurisdiccion: str = Field(description="Jurisdicción (es, autonomico, etc.)")
    tipo_fuente: str = Field(description="Tipo de fuente (boe, autonomica, etc.)")
    tipo_documento: str = Field(
        description="Tipo de documento (ley, real_decreto_legislativo, etc.)"
    )
    ambito: str = Field(description="Ámbito temático (tributario, etc.)")
    regulacion_relacionada: str | None = Field(
        default=None, description="Regulación relacionada"
    )
    estado_cobertura: str = Field(
        description="Estado de cobertura (ingestada, parcial, etc.)"
    )


class ArticuloListItem(BaseModel):
    numero: str = Field(description="Número del artículo")
    titulo: str | None = Field(default=None, description="Título del artículo")
    tipo: str = Field(description="Tipo (articulo, disposicion, etc.)")


class ArticuloDetail(BaseModel):
    norma: str = Field(description="Código de la norma")
    numero: str = Field(description="Número del artículo")
    texto: str = Field(description="Texto vigente del artículo")
    vigente_desde: str | None = Field(
        default=None, description="Fecha de inicio de vigencia (YYYY-MM-DD)"
    )
    vigente_hasta: str | None = Field(
        default=None, description="Fecha de fin de vigencia (YYYY-MM-DD)"
    )
    confianza: ConfianzaInfo = Field(description="Información de confianza del dato")


class ArticuloHistoryItem(BaseModel):
    numero: str = Field(description="Número del artículo")
    titulo: str | None = Field(default=None, description="Título del artículo")
    tipo: str = Field(description="Tipo (articulo, disposicion, etc.)")
    texto: str = Field(description="Texto de la versión del artículo")
    vigente_desde: str | None = Field(
        default=None, description="Fecha de inicio de vigencia (YYYY-MM-DD)"
    )
    vigente_hasta: str | None = Field(
        default=None, description="Fecha de fin de vigencia (YYYY-MM-DD)"
    )


class SearchResult(BaseModel):
    tipo: str = Field(description="Tipo de resultado (articulo, norma, etc.)")
    norma: str = Field(description="Código de la norma")
    numero: str = Field(description="Número del artículo")
    texto: str = Field(description="Texto del artículo")
    fragmento: str = Field(description="Fragmento destacado con el término buscado")
    vigente_desde: str | None = Field(
        default=None, description="Fecha de inicio de vigencia"
    )
    vigente_hasta: str | None = Field(
        default=None, description="Fecha de fin de vigencia"
    )
    rank: float | None = Field(
        default=None, description="Puntuación de relevancia (ts_rank)"
    )
    fuente_norma: str | None = Field(
        default=None, description="Referencia de la fuente normativa"
    )
    boe_reference: str | None = Field(
        default=None, description="Identificador BOE cuando la fuente sea BOE"
    )
    source_url: str | None = Field(
        default=None, description="URL oficial trazable del resultado"
    )
    chunk_id: int | str | None = Field(
        default=None, description="Identificador interno del fragmento recuperado"
    )
    source_hash: str | None = Field(
        default=None, description="Hash de trazabilidad del contenido recuperado"
    )
    motivo_ranking: str | None = Field(
        default=None, description="Motivo de ranking o mecanismo de coincidencia"
    )
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
    referencia: str = Field(
        description="Referencia del documento (ej: V0000-26, 00/1234/2024)"
    )
    tipo_documento: str = Field(
        description="Tipo (consulta_vinculante, resolucion_teac, etc.)"
    )
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
    fecha: str | None = Field(
        default=None, description="Fecha del documento (YYYY-MM-DD)"
    )
    titulo: str | None = Field(default=None, description="Título del documento")
    nivel_enlace: float = Field(description="Máxima confianza de enlace (0-1)")
    norma: str | None = Field(default=None, description="Código de norma vinculada")
    numero: str | None = Field(default=None, description="Número de artículo vinculado")
    fragmento: str = Field(description="Fragmento del texto con el término buscado")
    source_url: str | None = Field(
        default=None,
        description="URL oficial del documento (boe.es, portal organismo emisor, etc.) para citación verificable",
    )


class JurisprudenciaSearchResult(BaseModel):
    referencia: str = Field(description="Referencia del documento")
    tipo_documento: str = Field(description="Tipo de documento")
    organismo_emisor: str = Field(description="Organismo emisor")
    fecha: str | None = Field(
        default=None, description="Fecha del documento (YYYY-MM-DD)"
    )
    titulo: str | None = Field(default=None, description="Título del documento")
    nivel_enlace: float = Field(description="Máxima confianza de enlace (0-1)")
    norma: str | None = Field(default=None, description="Código de norma vinculada")
    numero: str | None = Field(default=None, description="Número de artículo vinculado")
    fragmento: str = Field(description="Fragmento del texto con el término buscado")
    source_url: str | None = Field(
        default=None,
        description="URL oficial de la resolución (cendoj.es, poderjudicial.es, etc.)",
    )


class JurisprudenciaSearchResponse(BaseModel):
    q: str = Field(description="Término de búsqueda")
    resultados: list[JurisprudenciaSearchResult]


class JurisprudenciaArticuloRelacionado(BaseModel):
    norma: str = Field(description="Código de la norma vinculada")
    numero: str = Field(description="Número del artículo vinculado")
    titulo: str | None = Field(
        default=None, description="Título del artículo vinculado"
    )
    metodo_enlace: str = Field(description="Método de enlace (manual, auto_link, etc.)")
    confianza_enlace: float = Field(description="Confianza del enlace (0-1)")
    nota: str | None = Field(default=None, description="Nota del enlace")


class JurisprudenciaDetail(BaseModel):
    referencia: str = Field(description="Referencia del documento")
    tipo_documento: str = Field(description="Tipo de documento")
    organismo_emisor: str = Field(description="Organismo emisor")
    jurisdiccion: str = Field(description="Jurisdicción")
    fecha: str | None = Field(default=None, description="Fecha del documento")
    titulo: str | None = Field(default=None, description="Título del documento")
    texto: str = Field(description="Texto o resumen del documento")
    url_fuente: str | None = Field(default=None, description="URL de la fuente")
    articulos: list[JurisprudenciaArticuloRelacionado] = Field(
        default_factory=list, description="Artículos de ley vinculados"
    )
    doctrina_relacionada: list["DoctrinaRelacionada"] = Field(
        default_factory=list, description="Doctrina relacionada vía artículos"
    )


# ---------------------------------------------------------------------------
# Modelos AEAT
# ---------------------------------------------------------------------------


class ModeloSummary(BaseModel):
    codigo: str = Field(description="Código del modelo (ej: 100, 303)")
    nombre: str = Field(description="Nombre completo del modelo")
    periodo: str | None = Field(
        default=None, description="Periodo de presentación (anual, trimestral, etc.)"
    )
    impuesto: str = Field(description="Impuesto asociado (IRPF, IVA, etc.)")
    articulos_count: int = Field(description="Número de artículos de ley vinculados")
    casillas_count: int = Field(description="Número de casillas en la campaña activa")
    url_info: str | None = Field(
        default=None,
        description="URL oficial del modelo en la sede AEAT (procedimientoini/GNNN.shtml)",
    )
    url_listado: str | None = Field(
        default=None,
        description="URL del listado canónico AEAT donde este modelo se publica",
    )


class ModeloArticulo(BaseModel):
    norma: str = Field(description="Código de la norma verificada para el enlace visible")
    numero: str = Field(description="Número del artículo verificado para el enlace visible")
    titulo: str | None = Field(default=None, description="Título del artículo visible enlazado de forma verificada")
    casilla: str | None = Field(default=None, description="Casilla asociada al enlace verificado visible")
    nota: str | None = Field(default=None, description="Nota explicativa del enlace verificado visible")
    fuente: str = Field(description="Fuente oficial usada para verificar el enlace visible")
    url_fuente: str | None = Field(default=None, description="URL oficial que respalda el enlace visible")


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
    tipo_casilla: str | None = Field(
        default=None, description="Tipo (importe, checkbox, texto, etc.)"
    )
    pagina: int | None = Field(default=None, description="Página del PDF donde aparece")
    orden: int | None = Field(default=None, description="Orden de aparición")


class ModeloCasillasResponse(BaseModel):
    codigo: str = Field(description="Codigo del modelo")
    campana: str | None = Field(default=None, description="Campana consultada")
    campana_activa: str | None = Field(
        default=None, description="Campana marcada como activa para el modelo"
    )
    selection_notice: str | None = Field(
        default=None, description="Aviso si la campana usada difiere de la activa"
    )
    casillas: list[ModeloCasilla] = Field(default_factory=list, description="Pagina de casillas devueltas")
    total: int = Field(description="Total de casillas que cumplen los filtros")
    limit: int = Field(description="Tamano de pagina aplicado")
    offset: int = Field(description="Offset aplicado")
    has_more: bool = Field(description="Si hay mas casillas disponibles")
    next_offset: int | None = Field(default=None, description="Offset para continuar, si hay mas")
    filters: dict = Field(default_factory=dict, description="Filtros aplicados")
    classification: str = Field(
        description=(
            "confirmado si hay casillas oficiales devueltas; "
            "sin_casillas_esperadas si el modelo esta verificado como sin casillas "
            "estructuradas; requiere_verificacion si no"
        )
    )
    obligation_notice: str = Field(description="Aviso de que casilla no implica obligatoriedad por supuesto")
    completeness: str = Field(description="Estado de completitud del modelo/campana")
    verified: bool = Field(description="Si la respuesta queda verificada con base suficiente")
    evidence_status: str = Field(description="Estado de evidencia para consumo por agentes")
    evidence_notice: str = Field(description="Aviso operativo sobre limites de evidencia")
    confidence: dict = Field(default_factory=dict, description="Confianza y revision requerida")


class ModeloClave(BaseModel):
    codigo: str = Field(description="Código de la clave")
    etiqueta: str = Field(description="Etiqueta descriptiva")
    descripcion: str | None = Field(default=None, description="Descripción de la clave")
    tipo_clave: str | None = Field(
        default=None, description="Tipo (rendimiento, regimen, etc.)"
    )


class ModeloInstruccion(BaseModel):
    seccion: str = Field(
        description="Sección (caracteristicas, quien-debe, como-rellenar, plazo)"
    )
    titulo: str = Field(description="Título de la sección")
    contenido: str = Field(description="Contenido paso a paso")
    orden: int = Field(description="Orden de presentación")


class ModeloNormativa(BaseModel):
    boe_id: str | None = Field(default=None, description="Identificador BOE")
    titulo: str = Field(description="Título de la norma")
    fecha: str | None = Field(
        default=None, description="Fecha de publicación (YYYY-MM-DD)"
    )
    url_boe: str | None = Field(default=None, description="URL al BOE")
    resumen: str | None = Field(default=None, description="Breve descripción")


class ModeloCampanaOperativaResponse(BaseModel):
    codigo: str = Field(description="Código del modelo")
    nombre: str = Field(description="Nombre completo")
    campana: str | None = Field(default=None, description="Campaña activa")
    impuesto: str = Field(description="Impuesto asociado")
    periodo: str | None = Field(default=None, description="Periodo")
    frecuencia_presentacion: str | None = Field(default=None, description="Frecuencia de presentación")
    ventana_presentacion: str | None = Field(default=None, description="Ventana de presentación")
    canal_presentacion: str | None = Field(default=None, description="Canal de presentación")
    categoria_obligado: str | None = Field(default=None, description="Categoría del obligado")
    norma_base: str | None = Field(default=None, description="Norma base aplicable")
    obligados_resumen: str | None = Field(default=None, description="Resumen de obligados")
    plazo_resumen: str | None = Field(default=None, description="Resumen del plazo")
    presentacion_resumen: str | None = Field(default=None, description="Resumen de presentación")
    origen_metadato: str | None = Field(default=None, description="Origen del metadato")
    estado_metadato: str | None = Field(default=None, description="Estado del metadato")
    completeness_estado: str | None = Field(
        default=None,
        description=(
            "Estado explicito curado para sobrescribir el contrato: completa, parcial, "
            "no-casillas-expected o deprecated"
        ),
    )
    completeness: str = Field(
        description=(
            "Estado de completitud: completa, parcial, no-casillas-expected o deprecated"
        )
    )
    verified: bool = Field(description="Si la respuesta queda verificada con base suficiente")
    evidence_status: str = Field(description="Estado de evidencia para consumo por agentes")
    evidence_notice: str = Field(description="Aviso operativo sobre limites de evidencia")
    fuentes_recomendadas: list["ModeloFuenteOficial"] = Field(default_factory=list, description="Fuentes oficiales recomendadas")


class ModeloCampana(BaseModel):
    campana: str = Field(description="Año/campaña (2025, 2024, etc.)")
    activo: bool = Field(description="Si es la campaña activa")


class ModeloDetail(BaseModel):
    codigo: str = Field(description="Código del modelo")
    nombre: str = Field(description="Nombre completo")
    periodo: str | None = Field(default=None, description="Periodo")
    impuesto: str = Field(description="Impuesto asociado")
    url_info: str | None = Field(default=None, description="URL a la sede AEAT")
    campana_activa: str | None = Field(default=None, description="Campaña activa (año)")
    campanas: list[ModeloCampana] = Field(
        default_factory=list, description="Campañas disponibles"
    )
    campanas_total: int = Field(default=0, description="Total de campanas disponibles")
    articulos: list[ModeloArticulo] = Field(
        default_factory=list, description="Artículos de ley vinculados"
    )
    articulos_total: int = Field(default=0, description="Total de articulos vinculados disponibles")
    articulos_limit: int = Field(default=0, description="Limite aplicado a articulos en esta respuesta")
    articulos_offset: int = Field(default=0, description="Offset aplicado a articulos en esta respuesta")
    articulos_has_more: bool = Field(default=False, description="Si hay mas articulos disponibles")
    articulos_next_offset: int | None = Field(default=None, description="Offset para continuar articulos")
    casillas: list[ModeloCasilla] = Field(
        default_factory=list, description="Casillas de la campaña activa"
    )
    casillas_total: int = Field(default=0, description="Total de casillas disponibles para la campaña activa")
    casillas_limit: int = Field(default=0, description="Límite aplicado a casillas en esta respuesta")
    casillas_offset: int = Field(default=0, description="Offset aplicado a casillas en esta respuesta")
    casillas_has_more: bool = Field(default=False, description="Si hay más casillas disponibles")
    casillas_next_offset: int | None = Field(default=None, description="Offset para continuar casillas")
    casillas_campana: str | None = Field(
        default=None, description="Campana usada para devolver casillas"
    )
    casillas_selection_notice: str | None = Field(
        default=None, description="Aviso si las casillas proceden de una campana distinta de la activa"
    )
    claves: list[ModeloClave] = Field(
        default_factory=list, description="Claves de la campaña activa"
    )
    claves_total: int = Field(default=0, description="Total de claves disponibles")
    instrucciones: list[ModeloInstruccion] = Field(
        default_factory=list, description="Instrucciones"
    )
    instrucciones_total: int = Field(default=0, description="Total de instrucciones disponibles")
    normativa: list[ModeloNormativa] = Field(
        default_factory=list, description="Normativa BOE"
    )
    normativa_total: int = Field(default=0, description="Total de referencias normativas disponibles")
    doctrina_relacionada: list[DoctrinaRelacionada] = Field(
        default_factory=list, description="Doctrina relacionada vía artículos"
    )
    doctrina_relacionada_total: int = Field(default=0, description="Total de doctrina relacionada devuelta")
    completeness: str = Field(
        description=(
            "Estado de completitud: completa, parcial, no-casillas-expected o deprecated"
        )
    )
    verified: bool = Field(description="Si la respuesta queda verificada con base suficiente")
    evidence_status: str = Field(description="Estado de evidencia para consumo por agentes")
    evidence_notice: str = Field(description="Aviso operativo sobre limites de evidencia")


# ---------------------------------------------------------------------------
# Envelopes (list/search responses)
# ---------------------------------------------------------------------------


class NormasListResponse(BaseModel):
    normas: list[Norma]
    total: int | None = None


class ArticulosListResponse(BaseModel):
    norma: str = Field(description="Código de la norma")
    articulos: list[ArticuloListItem]
    total: int | None = None
    limit: int | None = Field(default=None, description="Límite aplicado")
    offset: int | None = Field(default=None, description="Offset aplicado")
    has_more: bool | None = Field(default=None, description="Si existen más resultados")
    next_offset: int | None = Field(default=None, description="Offset de continuación")


class ArticulosHistoryResponse(BaseModel):
    norma: str = Field(description="Código de la norma")
    articulos: list[ArticuloHistoryItem]


class LegislacionSearchResponse(BaseModel):
    q: str = Field(description="Término de búsqueda")
    resultados: list[SearchResult]


class DoctrinaSearchResponse(BaseModel):
    q: str = Field(description="Término de búsqueda")
    resultados: list[DoctrinaSearchResult]


class ObligacionResumen(BaseModel):
    model_config = {"extra": "allow"}

    codigo: str = Field(description="Codigo de la obligacion")
    nombre: str = Field(description="Nombre de la obligacion")
    fuente: str = Field(description="Fuente principal")
    organismo_emisor: str = Field(description="Organismo emisor")
    tipo_obligacion: str = Field(description="Tipo de obligacion")
    sujeto_obligado: str = Field(description="Sujeto obligado")
    periodicidad: str | None = Field(default=None, description="Periodicidad base")
    reporte_modelo: str | None = Field(default=None, description="Modelo asociado")
    ambito: str = Field(description="Ambito")
    estado_vigencia: str = Field(description="Estado de vigencia")
    plazo_dias: int | None = Field(default=None, description="Plazo en dias")
    frecuencia_presentacion: str | None = Field(
        default=None, description="Frecuencia de presentacion"
    )
    ventana_presentacion: str | None = Field(
        default=None, description="Ventana de presentacion"
    )
    trigger_presentacion: str | None = Field(
        default=None, description="Trigger de presentacion"
    )
    sancion_min: str | float | int | None = Field(
        default=None, description="Sancion minima"
    )
    sancion_max: str | float | int | None = Field(
        default=None, description="Sancion maxima"
    )
    prescripcion_anos: int | None = Field(
        default=None, description="Anos de prescripcion"
    )


class ObligacionDocumento(BaseModel):
    referencia: str = Field(description="Referencia del documento")
    organismo_emisor: str = Field(description="Organismo emisor")
    tipo_fuente: str = Field(description="Tipo de fuente")
    tipo_documento: str = Field(description="Tipo de documento")
    tipo_relacion: str = Field(description="Tipo de relacion con la obligacion")


class ObligacionDetail(ObligacionResumen):
    model_config = {"extra": "allow"}

    documento_origen_tipo: str | None = Field(
        default=None, description="Tipo de documento origen"
    )
    documento_origen_ref: str | None = Field(
        default=None, description="Referencia del documento origen"
    )
    seccion_origen: str | None = Field(default=None, description="Seccion origen")
    anexo_origen: str | None = Field(default=None, description="Anexo origen")
    nota: str | None = Field(default=None, description="Nota interna")
    canal_presentacion: str | None = Field(
        default=None, description="Canal de presentacion"
    )
    obligados_resumen: str | None = Field(
        default=None, description="Resumen de obligados"
    )
    recargo_voluntario: str | float | int | None = Field(
        default=None, description="Recargo voluntario"
    )
    recargo_involuntario: str | float | int | None = Field(
        default=None, description="Recargo involuntario"
    )
    interes_demora: str | float | int | None = Field(
        default=None, description="Interes de demora"
    )
    deposito_previo: str | None = Field(default=None, description="Deposito previo")
    fuentes_operativas: list | dict | None = Field(
        default=None, description="Fuentes operativas estructuradas"
    )
    ultima_actualizacion: str | None = Field(
        default=None, description="Ultima actualizacion"
    )
    origen_metadato: str | None = Field(
        default=None, description="Origen del metadato"
    )
    estado_metadato: str | None = Field(
        default=None, description="Estado del metadato"
    )
    documentos: list[ObligacionDocumento] = Field(
        default_factory=list, description="Documentos relacionados"
    )


class ObligacionesListResponse(BaseModel):
    obligaciones: list[ObligacionResumen]


class ObligacionesAplicablesResponse(BaseModel):
    perfil: dict = Field(description="Perfil regulatorio aplicado")
    obligaciones: list[ObligacionResumen]
    status: str | None = Field(default=None, description="matched o evidence_limited")
    verified: bool | None = Field(default=None, description="Si hay aplicabilidad verificada para el perfil")
    confidence: dict | None = Field(default=None, description="Confianza y revision requerida")
    total: int | None = Field(default=None, description="Total de obligaciones aplicables antes de paginar")
    limit: int | None = Field(default=None, description="Límite aplicado")
    offset: int | None = Field(default=None, description="Offset aplicado")
    has_more: bool | None = Field(default=None, description="Si existen más resultados")
    next_offset: int | None = Field(default=None, description="Offset de continuación")


class EmpresaResumen(BaseModel):
    id: int = Field(description="ID de la empresa")
    nombre: str = Field(description="Nombre")
    nif: str | None = Field(default=None, description="NIF")
    domicilio: str | None = Field(default=None, description="Domicilio")
    fuente_inicial: str = Field(description="Fuente inicial")
    documentos_count: int = Field(description="Numero de documentos enlazados")


class EmpresaDocumento(BaseModel):
    referencia: str = Field(description="Referencia del documento")
    organismo_emisor: str = Field(description="Organismo emisor")
    tipo_fuente: str = Field(description="Tipo de fuente")
    tipo_documento: str = Field(description="Tipo de documento")
    fecha: str | None = Field(default=None, description="Fecha")
    rol: str = Field(description="Rol de la empresa en el documento")
    confianza_extraccion: float = Field(description="Confianza de extraccion")


class EmpresaDetail(BaseModel):
    id: int = Field(description="ID de la empresa")
    nombre: str = Field(description="Nombre")
    nif: str | None = Field(default=None, description="NIF")
    domicilio: str | None = Field(default=None, description="Domicilio")
    fuente_inicial: str = Field(description="Fuente inicial")
    documentos: list[EmpresaDocumento] = Field(
        default_factory=list, description="Documentos vinculados"
    )


class EmpresasListResponse(BaseModel):
    empresas: list[EmpresaResumen]


class ModeloFuenteOficial(BaseModel):
    tipo: str = Field(description="Tipo de fuente")
    titulo: str = Field(description="Título")
    url: str = Field(description="URL")
    organismo: str = Field(description="Organismo emisor")
    campana: str | None = Field(default=None, description="Campaña")
    boe_id: str | None = Field(default=None, description="ID BOE")
    fecha: str | None = Field(default=None, description="Fecha")
    oficial: bool = Field(description="Si es fuente oficial")
    nota: str | None = Field(default=None, description="Nota descriptiva")


class ModeloFuentesOficialesResponse(BaseModel):
    codigo: str = Field(description="Código del modelo")
    nombre: str | None = Field(default=None, description="Nombre completo")
    campana_activa: str | None = Field(default=None, description="Campaña activa")
    fuentes_oficiales: list[ModeloFuenteOficial] = Field(default_factory=list, description="Fuentes oficiales")


class ModeloResumenOperativoResponse(BaseModel):
    codigo: str = Field(description="Código del modelo")
    nombre: str = Field(description="Nombre completo")
    impuesto: str = Field(description="Impuesto asociado")
    periodo: str | None = Field(default=None, description="Periodo")
    campana_activa: str | None = Field(default=None, description="Campaña activa")
    quien_debe_presentarlo: str | None = Field(default=None, description="Quién debe presentarlo")
    plazo_presentacion: str | None = Field(default=None, description="Plazo de presentación")
    fuentes_recomendadas: list[ModeloFuenteOficial] = Field(default_factory=list, description="Fuentes recomendadas")


class ModeloArtefacto(BaseModel):
    tipo: str = Field(description="Tipo de artefacto")
    titulo: str = Field(description="Título")
    url: str = Field(description="URL")
    campana: str | None = Field(default=None, description="Campaña")
    boe_id: str | None = Field(default=None, description="ID BOE")
    fecha: str | None = Field(default=None, description="Fecha")
    formato: str | None = Field(default=None, description="Formato")
    oficial: bool = Field(description="Si es un artefacto oficial")
    nota: str | None = Field(default=None, description="Nota descriptiva")


class ModeloArtefactosResponse(BaseModel):
    codigo: str = Field(description="Código del modelo")
    campana_activa: str | None = Field(default=None, description="Campaña activa")
    criterio_validacion: str = Field(description="Criterio de validación")
    artefactos: list[ModeloArtefacto] = Field(default_factory=list, description="Artefactos del modelo")


class ModelosCampanasOperativasResponse(BaseModel):
    codigos: list[str] = Field(description="Códigos solicitados")
    campana: str | None = Field(default=None, description="Campaña aplicada")
    resultados: list[ModeloCampanaOperativaResponse] = Field(default_factory=list, description="Resultados")


class ModeloSupuestoEvidencia(BaseModel):
    source: str = Field(description="Tabla o fuente interna usada como evidencia")
    source_document: str | None = Field(default=None, description="Identificador documental")
    source_url: str | None = Field(default=None, description="URL oficial o trazable")
    excerpt: str = Field(description="Texto exacto o resumen de evidencia")
    official: bool = Field(description="Si la fuente procede del corpus oficial")


class ModeloSupuestoCandidate(BaseModel):
    codigo: str = Field(description="Codigo AEAT")
    nombre: str = Field(description="Nombre del modelo en ESData")
    clasificacion: str = Field(description="confirmado, candidato o requiere_verificacion")
    condicion_aplicacion: str = Field(description="Condicion explicita para considerar el modelo")
    motivo: str = Field(description="Razon de la clasificacion")
    ambito: str = Field(description="Ambito del supuesto fiscal")
    periodo: str | None = Field(default=None, description="Periodo de presentacion")
    impuesto: str | None = Field(default=None, description="Impuesto asociado")
    candidate_score: float = Field(description="Puntuacion conservadora 0-1")
    matched_factors: list[str] = Field(default_factory=list, description="Factores del supuesto cubiertos")
    missing_factors: list[str] = Field(default_factory=list, description="Factores aun no acreditados")
    evidencia: list[ModeloSupuestoEvidencia] = Field(default_factory=list, description="Evidencia trazable")


class ModeloSupuestoExcluded(BaseModel):
    codigo: str = Field(description="Codigo excluido")
    reason: str = Field(description="Motivo de exclusion")


class ModelosPorSupuestoResponse(BaseModel):
    status: str = Field(description="confirmed, evidence_limited o no_verified")
    verified: bool = Field(description="Si la aplicabilidad esta verificada con evidencia explicita")
    scenario_inputs: dict = Field(description="Parametros del supuesto usados")
    modelos: list[ModeloSupuestoCandidate] = Field(default_factory=list, description="Modelos clasificados")
    excluded_modelos: list[ModeloSupuestoExcluded] = Field(default_factory=list, description="Modelos descartados")
    warnings: list[str] = Field(default_factory=list, description="Advertencias de no invencion")
    confidence: dict = Field(description="Confianza operacional")


class ModelosListResponse(BaseModel):
    modelos: list[ModeloSummary]
    total: int | None = None
    limit: int | None = None
    offset: int | None = None
    has_more: bool | None = None
    next_offset: int | None = None


class AEATModeloListItem(BaseModel):
    codigo: str = Field(description="Codigo del modelo AEAT")
    nombre: str = Field(description="Nombre completo")
    activo: bool = Field(description="Si el modelo sigue activo en el portal")
    impuesto: str | None = Field(default=None, description="Impuesto asociado")
    campana: str | None = Field(default=None, description="Campana activa o solicitada")
    estado_publicacion: str | None = Field(default=None, description="Estado de publicacion detectado")
    recursos_activos: int = Field(description="Numero de recursos activos para la campana")


class AEATModeloListResponse(BaseModel):
    total: int = Field(description="Numero total de modelos devueltos")
    items: list[AEATModeloListItem] = Field(default_factory=list, description="Modelos AEAT")


class AEATModeloRecurso(BaseModel):
    tipo_recurso: str = Field(description="Tipo de recurso")
    formato: str = Field(description="Formato del recurso")
    url_recurso: str = Field(description="URL oficial del recurso")
    sha256_contenido: str = Field(description="Hash SHA-256 del contenido")
    fecha_publicacion_recurso: str | None = Field(default=None, description="Fecha de publicacion del recurso")
    first_seen_at: str = Field(description="Primera vez visto por el worker")
    last_seen_at: str = Field(description="Ultima vez visto por el worker")
    activa: bool = Field(description="Si esta version es la vigente")


class AEATCampanaDetail(BaseModel):
    campana: str = Field(description="Campana fiscal")
    activo: bool = Field(description="Si es la campana activa")
    estado_publicacion: str | None = Field(default=None, description="Estado de publicacion detectado")
    fecha_publicacion_portal: str | None = Field(default=None, description="Fecha publicada en el portal")
    fecha_actualizacion_portal: str | None = Field(default=None, description="Fecha de actualizacion del portal")
    recursos: list[AEATModeloRecurso] = Field(default_factory=list, description="Recursos del modelo para esta campana")


class AEATModeloDetail(BaseModel):
    codigo: str = Field(description="Codigo del modelo")
    nombre: str = Field(description="Nombre completo")
    activo: bool = Field(description="Si el modelo sigue activo")
    completeness: str = Field(description="Contrato de completitud operativo del modelo")
    verified: bool = Field(description="Si el contrato de completitud permite respuesta autoritativa")
    evidence_status: str = Field(description="Estado de evidencia para consumo por agentes")
    evidence_notice: str = Field(description="Aviso operativo sobre limites de evidencia")
    casillas_total: int = Field(default=0, description="Numero de casillas/campos oficiales cargados para la campana consultada")
    casillas_campana: str | None = Field(default=None, description="Campana usada para contar casillas/campos")
    casillas_selection_notice: str | None = Field(default=None, description="Aviso si las casillas proceden de una campana distinta")
    campana_actual: AEATCampanaDetail | None = Field(default=None, description="Campana actual con recursos activos")
    historial: list[AEATCampanaDetail] | None = Field(default=None, description="Historial de campanas y versiones si include_history=true")


# ---------------------------------------------------------------------------
# Criterio jurisprudencial/doctrinal
# ---------------------------------------------------------------------------


class LineaCriterioSummary(BaseModel):
    id: int
    titulo: str
    cuestion_practica: str
    estado: str
    autor_id: int | None = None
    revisor_id: int | None = None
    ultimo_cambio: str | None = None
    activo: bool
    created_at: str | None = None
    updated_at: str | None = None


class LineaCriterioReferencia(BaseModel):
    id: int
    documento_referencia: str
    tipo_documento: str | None = None
    organismo_emisor: str | None = None
    fecha: str | None = None
    rol_en_linea: str | None = None
    orden: int


class LineaCriterioDetail(LineaCriterioSummary):
    descripcion: str | None = None
    criterio_dominante: str | None = None
    matices: str | None = None
    excepciones: str | None = None
    referencias: list[LineaCriterioReferencia] = Field(default_factory=list)


class LineaCriterioCreate(BaseModel):
    titulo: str
    cuestion_practica: str
    descripcion: str | None = None
    criterio_dominante: str | None = None
    matices: str | None = None
    excepciones: str | None = None
    estado: str | None = None


class LineaCriterioUpdate(BaseModel):
    titulo: str | None = None
    cuestion_practica: str | None = None
    descripcion: str | None = None
    criterio_dominante: str | None = None
    matices: str | None = None
    excepciones: str | None = None
    estado: str | None = None
    ultimo_cambio: str | None = None


class LineaCriterioReferenciaCreate(BaseModel):
    documento_referencia: str
    tipo_documento: str | None = None
    organismo_emisor: str | None = None
    fecha: str | None = None
    rol_en_linea: str | None = None
    orden: int = 0


class LineaCriterioListResponse(BaseModel):
    lineas: list[LineaCriterioSummary] = Field(default_factory=list)
    total: int


class CuracionCandidate(BaseModel):
    id: int
    referencia: str
    tipo_documento: str | None = None
    organismo_emisor: str | None = None
    ambito: str | None = None
    fecha: str | None = None
    titulo: str | None = None
    url_fuente: str | None = None
    score: int


class LineaCriterioCuracionItem(BaseModel):
    linea_id: int
    linea_titulo: str
    candidatos: list[CuracionCandidate] = Field(default_factory=list)
    total_sugeridos: int


class LineaCriterioCuracionResponse(BaseModel):
    sugerencias: list[LineaCriterioCuracionItem] = Field(default_factory=list)
    total_lineas: int


class CuracionAssignRequest(BaseModel):
    linea_id: int
    documento_referencia: str
    rol_en_linea: str = "soporte"


class CuracionAssignResponse(BaseModel):
    assigned: bool
    linea_id: int
    documento_referencia: str
    referencia_existia: bool


# ---------------------------------------------------------------------------
# Playbooks operativos y evidencias
# ---------------------------------------------------------------------------


class PlaybookStepSummary(BaseModel):
    id: str
    orden: int
    titulo: str
    tipo_paso: str | None = None
    responsable_rol: str | None = None
    activo: bool


class PlaybookStepDetail(PlaybookStepSummary):
    descripcion: str | None = None
    input_requerido: str | None = None
    output_esperado: str | None = None
    prerrequisito_step_id: str | None = None
    checklist: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class PlaybookStepCreate(BaseModel):
    orden: int
    titulo: str
    descripcion: str | None = None
    tipo_paso: str | None = None
    responsable_rol: str | None = None
    input_requerido: str | None = None
    output_esperado: str | None = None
    prerrequisito_step_id: str | None = None
    checklist: list[str] | None = None


class PlaybookStepUpdate(BaseModel):
    orden: int | None = None
    titulo: str | None = None
    descripcion: str | None = None
    tipo_paso: str | None = None
    responsable_rol: str | None = None
    input_requerido: str | None = None
    output_esperado: str | None = None
    prerrequisito_step_id: str | None = None
    checklist: list[str] | None = None
    activo: bool | None = None


class EvidenciaControlSummary(BaseModel):
    id: str
    codigo: str
    nombre: str
    tipo_evidencia: str | None = None
    obligatoria: bool
    estado: str | None = None
    conservacion_dias: int | None = None


class EvidenciaControlDetail(EvidenciaControlSummary):
    descripcion: str | None = None
    formato_requerido: str | None = None
    capturado_en: str | None = None
    verificado_por: str | None = None
    verificado_en: str | None = None
    nota: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class EvidenciaControlUpdate(BaseModel):
    estado: str | None = None
    capturado_en: str | None = None
    verificado_por: str | None = None
    verificado_en: str | None = None
    nota: str | None = None


class EvidenciaControlListResponse(BaseModel):
    evidencias: list[EvidenciaControlSummary] = Field(default_factory=list)
    total: int


class PlaybookOperativoSummary(BaseModel):
    id: str
    codigo: str
    nombre: str
    obligacion_codigo: str | None = None
    frecuencia: str | None = None
    owner_rol: str | None = None
    estado: str
    version: int


class PlaybookOperativoDetail(PlaybookOperativoSummary):
    descripcion: str | None = None
    owner_id: str | None = None
    sistema_apoyo: str | None = None
    errores_frecuentes: str | None = None
    version_anterior_id: str | None = None
    pasos: list[PlaybookStepDetail] = Field(default_factory=list)
    evidencias: list[EvidenciaControlDetail] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class PlaybookOperativoCreate(BaseModel):
    codigo: str
    nombre: str
    obligacion_codigo: str | None = None
    descripcion: str | None = None
    frecuencia: str | None = None
    owner_rol: str | None = None
    owner_id: str | None = None
    sistema_apoyo: str | None = None
    errores_frecuentes: str | None = None
    estado: str = "activo"


class PlaybookOperativoUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    frecuencia: str | None = None
    owner_rol: str | None = None
    owner_id: str | None = None
    sistema_apoyo: str | None = None
    errores_frecuentes: str | None = None
    estado: str | None = None


class PlaybookOperativoListResponse(BaseModel):
    playbooks: list[PlaybookOperativoSummary] = Field(default_factory=list)
    total: int


# ---------------------------------------------------------------------------
# Risk-control matrix
# ---------------------------------------------------------------------------


class RiesgoControlLinkPruebaSummary(BaseModel):
    id: str
    fecha_prueba: str | None = None
    resultado: str
    evidencia_descripcion: str | None = None
    ejecutado_por: str | None = None


class RiesgoRegulatorioSummary(BaseModel):
    id: str
    codigo: str
    nombre: str
    obligacion_codigo: str | None = None
    categoria: str | None = None
    severidad: str | None = None
    probabilidad: str | None = None
    riesgo_inherente: str | None = None
    area_responsable: str | None = None
    owner_rol: str | None = None
    estado: str


class RiesgoRegulatorioDetail(RiesgoRegulatorioSummary):
    descripcion: str | None = None
    controles: list[dict] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class RiesgoRegulatorioCreate(BaseModel):
    codigo: str
    nombre: str
    descripcion: str | None = None
    obligacion_codigo: str | None = None
    categoria: str | None = None
    severidad: str | None = None
    probabilidad: str | None = None
    area_responsable: str | None = None
    owner_rol: str | None = None
    estado: str = "identificado"


class RiesgoRegulatorioUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    obligacion_codigo: str | None = None
    categoria: str | None = None
    severidad: str | None = None
    probabilidad: str | None = None
    area_responsable: str | None = None
    owner_rol: str | None = None
    estado: str | None = None


class RiesgoRegulatorioListResponse(BaseModel):
    riesgos: list[RiesgoRegulatorioSummary] = Field(default_factory=list)
    total: int


class ControlInternoSummary(BaseModel):
    id: str
    codigo: str
    nombre: str
    tipo_control: str | None = None
    frecuencia: str | None = None
    owner_rol: str | None = None
    estado: str


class ControlInternoDetail(ControlInternoSummary):
    descripcion: str | None = None
    sistema_apoyo: str | None = None
    pruebas: list[RiesgoControlLinkPruebaSummary] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class ControlInternoCreate(BaseModel):
    codigo: str
    nombre: str
    descripcion: str | None = None
    tipo_control: str | None = None
    frecuencia: str | None = None
    owner_rol: str | None = None
    sistema_apoyo: str | None = None
    estado: str = "activo"


class ControlInternoUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    tipo_control: str | None = None
    frecuencia: str | None = None
    owner_rol: str | None = None
    sistema_apoyo: str | None = None
    estado: str | None = None


class ControlInternoListResponse(BaseModel):
    controles: list[ControlInternoSummary] = Field(default_factory=list)
    total: int


class RiesgoControlLinkDetail(BaseModel):
    id: str
    riesgo_codigo: str
    riesgo_nombre: str
    control_codigo: str
    control_nombre: str
    efectividad: str | None = None
    riesgo_residual: str | None = None
    frecuencia_prueba: str | None = None
    criterio_suficiencia: str | None = None
    caducidad_dias: int | None = None
    activo: bool
    pruebas: list[RiesgoControlLinkPruebaSummary] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class RiesgoControlLinkCreate(BaseModel):
    riesgo_id: str
    control_id: str
    efectividad: str | None = None
    riesgo_residual: str | None = None
    frecuencia_prueba: str | None = None
    criterio_suficiencia: str | None = None
    caducidad_dias: int | None = None


class RiesgoControlLinkListResponse(BaseModel):
    links: list[RiesgoControlLinkDetail] = Field(default_factory=list)
    total: int


class PruebaControlDetail(BaseModel):
    id: str
    link_id: str
    fecha_prueba: str
    resultado: str
    evidencia_descripcion: str | None = None
    evidencia_url: str | None = None
    ejecutado_por: str | None = None
    nota: str | None = None
    activo: bool
    created_at: str | None = None
    updated_at: str | None = None


class PruebaControlCreate(BaseModel):
    link_id: str
    fecha_prueba: str
    resultado: str
    evidencia_descripcion: str | None = None
    evidencia_url: str | None = None
    ejecutado_por: str | None = None
    nota: str | None = None


class PruebaControlListResponse(BaseModel):
    pruebas: list[RiesgoControlLinkPruebaSummary] = Field(default_factory=list)
    total: int


class ControlGapItem(BaseModel):
    riesgo_codigo: str
    riesgo_nombre: str
    severidad: str | None = None
    obligacion_codigo: str | None = None
    controles_asignados: int
    controles_efectivos: int
    estado: str
    ultima_prueba_fecha: str | None = None
    ultima_prueba_resultado: str | None = None


class ControlGapResumen(BaseModel):
    sin_control: int = 0
    parcial: int = 0
    completo: int = 0
    total: int = 0


class ControlGapsResponse(BaseModel):
    gaps: list[ControlGapItem] = Field(default_factory=list)
    total: int
    resumen: ControlGapResumen


# ---------------------------------------------------------------------------
# Consulta fiscal inteligente
# ---------------------------------------------------------------------------


class ChunkCitation(BaseModel):
    chunk_id: str = Field(description="ID del chunk recuperado")
    source_document: str = Field(description="Documento fuente del chunk")
    article_number: str | None = Field(default=None, description="Numero de articulo si aplica")
    rerank_score: float = Field(description="Puntuacion de reranking")
    excerpt: str = Field(description="Vista previa del contenido del chunk")


class ClaimCitation(BaseModel):
    claim: dict = Field(description="Afirmacion factual estructurada")
    citations: list[ChunkCitation] = Field(default_factory=list, description="Chunks que respaldan la afirmacion")
    grounded: bool | None = Field(default=None, description="Si la afirmacion esta respaldada por evidencia")


class ObligacionInternacionalItem(BaseModel):
    id: int
    codigo: str
    titulo: str
    tipo: str
    jurisdiccion_origen: str | None = None
    jurisdiccion_aplicacion: str | None = None
    vigente_desde: str | None = None
    vigente_hasta: str | None = None
    estado: str
    descripcion: str | None = None
    creado_en: str | None = None
    actualizado_en: str | None = None
    source_url: str | None = Field(default=None, description="URL oficial registrada en source_revision")
    source_worker: str | None = Field(default=None, description="Worker que cargo la referencia")
    source_fetched_at: str | None = Field(default=None, description="Fecha de captura de la fuente")


class ObligacionInternacionalListResponse(BaseModel):
    items: list[ObligacionInternacionalItem] = Field(default_factory=list)
    total: int
    limit: int | None = None
    offset: int | None = None
    has_more: bool | None = None
    next_offset: int | None = None


class ObligacionInternacionalDetailResponse(BaseModel):
    item: ObligacionInternacionalItem


class MCPConfidenceInfo(BaseModel):
    score: float = Field(description="Puntuacion de confianza de 0 a 1")
    label: str = Field(description="Etiqueta cualitativa de confianza")


class MCPSourceInfo(BaseModel):
    title: str | None = Field(default=None, description="Titulo legible de la fuente")
    url: str | None = Field(default=None, description="URL de la fuente cuando exista")
    chunk_id: str | None = Field(default=None, description="Chunk usado como evidencia")
    norma: str | None = Field(default=None, description="Codigo de norma si aplica")
    numero: str | None = Field(default=None, description="Numero de articulo si aplica")
    referencia: str | None = Field(default=None, description="Referencia doctrinal o documental")
    organismo_emisor: str | None = Field(default=None, description="Organismo emisor si aplica")
    trust_tier: str | None = Field(default=None, description="Jerarquia de confianza de la fuente")


class MCPMinimumResponseContract(BaseModel):
    request_id: str = Field(description="Identificador correlacionado de la respuesta")
    tool_name: str = Field(description="Nombre estable de la tool o superficie")
    sources: list[dict] = Field(default_factory=list, description="Fuentes o chunks que respaldan la respuesta")
    confidence: dict = Field(description="Confianza operativa de la respuesta")
    completeness: str = Field(
        description=(
            "Estado de completitud: completa, parcial, no-casillas-expected o deprecated"
        )
    )
    verified: bool = Field(description="Si la respuesta queda verificada con base suficiente")


class QueryAuditEntryResponse(MCPMinimumResponseContract):
    entry_id: str = Field(description="Unique entry identifier")
    user_id: str | None = Field(default=None, description="Authenticated user ID")
    path: str = Field(description="API path that was queried")
    query_text: str = Field(description="The query text sent")
    retrieved_chunks: list[dict] = Field(default_factory=list, description="Chunks retrieved")
    response_summary: str = Field(default="", description="Summary of the response")
    model_version: str | None = Field(default=None, description="Model version used")
    config_version: str | None = Field(default=None, description="Config version used")
    created_at: str = Field(description="When the query was recorded (ISO 8601)")
    grounding_status: str | None = Field(default=None, description="Grounding status persisted for the response")
    prompt_injection_detected: bool = Field(default=False, description="If prompt injection signals were detected in retrieved chunks")
    grounding_summary: dict = Field(default_factory=dict, description="Persisted grounding summary for the response")


class QueryAuditLogResponse(BaseModel):
    total: int = Field(description="Total entries matching the query")
    path: str | None = Field(default=None, description="Path filter applied")
    entries: list[QueryAuditEntryResponse] = Field(default_factory=list, description="Audit log entries")


class QueryAuditByRequestResponse(BaseModel):
    request_id: str = Field(description="The request ID queried")
    total: int = Field(description="Total entries for this request")
    entries: list[QueryAuditEntryResponse] = Field(default_factory=list, description="Audit entries for the request")


# ---------------------------------------------------------------------------
# MiCA — Crypto-Asset Service Providers
# ---------------------------------------------------------------------------


class CASPCreate(BaseModel):
    name: str = Field(description="Nombre del CASP")
    registration_number: str | None = Field(default=None, description="Número de registro ESMA")
    home_member_state: str | None = Field(default=None, description="Estado miembro ISO 3166-1 alpha-2")
    passport_active: bool = Field(default=False, description="Si tiene pasaporte activo")
    services_offered: list[str] = Field(default_factory=list, description="Servicios: custody, exchange, execution, payment")


class CASPUpdate(BaseModel):
    name: str | None = Field(default=None, description="Nombre del CASP")
    registration_number: str | None = Field(default=None, description="Número de registro ESMA")
    home_member_state: str | None = Field(default=None, description="Estado miembro ISO 3166-1 alpha-2")
    passport_active: bool | None = Field(default=None, description="Si tiene pasaporte activo")
    services_offered: list[str] | None = Field(default=None, description="Servicios: custody, exchange, execution, payment")
    status: str | None = Field(default=None, description="Estado: active, suspended, revoked")


class CASPSummary(BaseModel):
    id: int = Field(description="ID del CASP")
    name: str = Field(description="Nombre del CASP")
    registration_number: str | None = Field(default=None, description="Número de registro")
    home_member_state: str | None = Field(default=None, description="Estado miembro")
    passport_active: bool = Field(description="Pasaporte activo")
    services_offered: list[str] = Field(default_factory=list, description="Servicios ofrecidos")
    status: str = Field(description="Estado: active, suspended, revoked")


class CASPDetail(BaseModel):
    id: int = Field(description="ID del CASP")
    name: str = Field(description="Nombre del CASP")
    registration_number: str | None = Field(default=None, description="Número de registro")
    home_member_state: str | None = Field(default=None, description="Estado miembro")
    passport_active: bool = Field(description="Pasaporte activo")
    services_offered: list[str] = Field(default_factory=list, description="Servicios ofrecidos")
    status: str = Field(description="Estado: active, suspended, revoked")
    created_at: str = Field(description="Fecha de creación")
    updated_at: str = Field(description="Fecha de actualización")


class CASPListResponse(BaseModel):
    items: list[CASPSummary]
    total: int


# ---------------------------------------------------------------------------
# MiCA — Crypto Assets
# ---------------------------------------------------------------------------


class CryptoAssetCreate(BaseModel):
    asset_type: str = Field(description="asset-referenced, e-money, utility, other")
    reference_uid: str | None = Field(default=None, description="Identificador único del emisor")
    issuer_jurisdiction: str | None = Field(default=None, description="ISO 3166-1 alpha-2")
    is_sha: bool = Field(default=False, description="Significant crypto-asset")
    market_value_eur: float | None = Field(default=None, description="Valor de mercado en EUR")
    holders_count: int | None = Field(default=None, description="Número de holders")
    status: str = Field(default="active", description="Estado")


class CryptoAssetSummary(BaseModel):
    id: int = Field(description="ID del criptoactivo")
    asset_type: str = Field(description="Tipo de activo")
    reference_uid: str | None = Field(default=None, description="UID de referencia")
    issuer_jurisdiction: str | None = Field(default=None, description="Jurisdicción emisor")
    is_sha: bool = Field(description="SHA")
    market_value_eur: float | None = Field(default=None, description="Valor en EUR")
    holders_count: int | None = Field(default=None, description="Holders count")
    status: str = Field(description="Estado")


class CryptoAssetDetail(BaseModel):
    id: int = Field(description="ID del criptoactivo")
    asset_type: str = Field(description="Tipo de activo")
    reference_uid: str | None = Field(default=None, description="UID de referencia")
    issuer_jurisdiction: str | None = Field(default=None, description="Jurisdicción emisor")
    is_sha: bool = Field(description="SHA")
    market_value_eur: float | None = Field(default=None, description="Valor en EUR")
    holders_count: int | None = Field(default=None, description="Holders count")
    status: str = Field(description="Estado")
    created_at: str = Field(description="Fecha de creación")
    updated_at: str = Field(description="Fecha de actualización")


class CryptoAssetListResponse(BaseModel):
    items: list[CryptoAssetSummary]
    total: int


# ---------------------------------------------------------------------------
# MiCA — Crypto Transactions (DAC8/DAC9)
# ---------------------------------------------------------------------------


class CryptoTransactionCreate(BaseModel):
    sender_wallet: str = Field(description="Wallet del remitente")
    receiver_wallet: str = Field(description="Wallet del destinatario")
    sender_jurisdiction: str | None = Field(default=None, description="ISO 3166-1 alpha-2")
    receiver_jurisdiction: str | None = Field(default=None, description="ISO 3166-1 alpha-2")
    asset_type: str = Field(description="cryptocurrency, stablecoin, defi_token, other")
    amount: float = Field(description="Cantidad")
    value_eur: float | None = Field(default=None, description="Valor en EUR")
    timestamp: str | None = Field(default=None, description="ISO 8601 timestamp")
    reporting_period: str | None = Field(default=None, description="YYYY-QN")
    status: str = Field(default="reported", description="Estado")


class CryptoTransactionSummary(BaseModel):
    id: int = Field(description="ID del registro")
    sender_wallet: str = Field(description="Wallet remitente")
    receiver_wallet: str = Field(description="Wallet destinatario")
    sender_jurisdiction: str | None = Field(default=None, description="Jurisdicción remitente")
    receiver_jurisdiction: str | None = Field(default=None, description="Jurisdicción destinatario")
    asset_type: str = Field(description="Tipo de activo")
    amount: float = Field(description="Cantidad")
    value_eur: float | None = Field(default=None, description="Valor en EUR")
    reporting_period: str | None = Field(default=None, description="Período")
    status: str = Field(description="Estado")


class CryptoTransactionDetail(BaseModel):
    id: int = Field(description="ID del registro")
    sender_wallet: str = Field(description="Wallet remitente")
    receiver_wallet: str = Field(description="Wallet destinatario")
    sender_jurisdiction: str | None = Field(default=None, description="Jurisdicción remitente")
    receiver_jurisdiction: str | None = Field(default=None, description="Jurisdicción destinatario")
    asset_type: str = Field(description="Tipo de activo")
    amount: float = Field(description="Cantidad")
    value_eur: float | None = Field(default=None, description="Valor en EUR")
    timestamp: str = Field(description="Timestamp")
    reporting_period: str | None = Field(default=None, description="Período")
    status: str = Field(description="Estado")
    created_at: str = Field(description="Fecha de creación")
    updated_at: str = Field(description="Fecha de actualización")


class CryptoTransactionListResponse(BaseModel):
    items: list[CryptoTransactionSummary]
    total: int


# ---------------------------------------------------------------------------
# MiCA — Tokenized Assets
# ---------------------------------------------------------------------------


class TokenizedAssetSummary(BaseModel):
    id: int = Field(description="ID del activo tokenizado")
    underlying_type: str = Field(description="equity, bond, fund, real-estate, other")
    issuer_id: int | None = Field(default=None, description="ID del emisor")
    face_value: float | None = Field(default=None, description="Valor facial en EUR")
    total_amount: float | None = Field(default=None, description="Monto total en EUR")
    listing_date: str | None = Field(default=None, description="Fecha de listado")
    regulated_market: str | None = Field(default=None, description="Mercado regulado")
    status: str = Field(description="Estado")


class TokenizedAssetDetail(BaseModel):
    id: int = Field(description="ID del activo tokenizado")
    underlying_type: str = Field(description="Tipo de subyacente")
    issuer_id: int | None = Field(default=None, description="ID del emisor")
    face_value: float | None = Field(default=None, description="Valor facial")
    total_amount: float | None = Field(default=None, description="Monto total")
    listing_date: str | None = Field(default=None, description="Fecha de listado")
    regulated_market: str | None = Field(default=None, description="Mercado regulado")
    status: str = Field(description="Estado")
    created_at: str = Field(description="Fecha de creación")
    updated_at: str = Field(description="Fecha de actualización")


class TokenizedAssetListResponse(BaseModel):
    items: list[TokenizedAssetSummary]
    total: int


# ---------------------------------------------------------------------------
# MiCA — Wallet Custodians
# ---------------------------------------------------------------------------


class WalletCustodianSummary(BaseModel):
    id: int = Field(description="ID del custodio")
    entity_id: int | None = Field(default=None, description="ID de la entidad")
    wallet_type: str = Field(description="Tipo de wallet")
    custody_mechanism: str | None = Field(default=None, description="Mecanismo de custodia")
    insurance_coverage: float | None = Field(default=None, description="Cobertura de seguro en EUR")
    audit_frequency: str | None = Field(default=None, description="Frecuencia de auditoría")
    status: str = Field(description="Estado")


class WalletCustodianDetail(BaseModel):
    id: int = Field(description="ID del custodio")
    entity_id: int | None = Field(default=None, description="ID de la entidad")
    wallet_type: str = Field(description="Tipo de wallet")
    custody_mechanism: str | None = Field(default=None, description="Mecanismo de custodia")
    insurance_coverage: float | None = Field(default=None, description="Cobertura de seguro en EUR")
    audit_frequency: str | None = Field(default=None, description="Frecuencia de auditoría")
    status: str = Field(description="Estado")
    created_at: str = Field(description="Fecha de creación")
    updated_at: str = Field(description="Fecha de actualización")


class WalletCustodianListResponse(BaseModel):
    items: list[WalletCustodianSummary]
    total: int


# ---------------------------------------------------------------------------
# AIFMD / UCITS
# ---------------------------------------------------------------------------


class AifmdFundSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    fund_name: str = Field(description="Nombre del fondo")
    aifm_id: int | None = Field(default=None, description="ID del AIFM")
    fund_type: str = Field(description="Tipo de fondo")
    registration_date: str = Field(description="Fecha de registro")
    home_member_state: str | None = Field(default=None, description="Estado miembro de origen")
    cross_border_passport: bool = Field(description="Passporting")
    total_aum_eur: float | None = Field(default=None, description="AUM total EUR")
    investor_type: str | None = Field(default=None, description="Tipo de inversor")
    lock_up_period: str | None = Field(default=None, description="Periodo lock-up")
    redemption_frequency: str | None = Field(default=None, description="Frecuencia de reembolso")
    leverage_method: str | None = Field(default=None, description="Metodo de apalancamiento")
    leverage_max_pct: float | None = Field(default=None, description="Apalancamiento maximo")
    status: str = Field(description="Estado")

    @field_validator("registration_date", mode="before")
    @classmethod
    def _dt_to_str(cls, v):
        if v is None or isinstance(v, str):
            return v
        return v.isoformat()


class AifmdFundDetail(AifmdFundSummary):
    created_at: str = Field(description="Fecha de creacion")

    @field_validator("created_at", mode="before")
    @classmethod
    def _created_at_to_str(cls, v):
        if v is None or isinstance(v, str):
            return v
        return v.isoformat()


class AifmdFundListResponse(BaseModel):
    items: list[AifmdFundSummary]
    total: int


class AifmdRegulatoryReportSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    fund_id: int = Field(description="ID del fondo")
    report_type: str = Field(description="Tipo de reporte")
    reporting_period: str | None = Field(default=None, description="Periodo")
    url: str | None = Field(default=None, description="URL")
    filed_date: str | None = Field(default=None, description="Fecha de presentacion")
    status: str = Field(description="Estado")

    @field_validator("filed_date", mode="before")
    @classmethod
    def _filed_date_to_str(cls, v):
        if v is None or isinstance(v, str):
            return v
        return v.isoformat()


class AifmdRegulatoryReportDetail(AifmdRegulatoryReportSummary):
    created_at: str = Field(description="Fecha de creacion")

    @field_validator("created_at", mode="before")
    @classmethod
    def _created_at_to_str(cls, v):
        if v is None or isinstance(v, str):
            return v
        return v.isoformat()


class AifmdRegulatoryReportListResponse(BaseModel):
    items: list[AifmdRegulatoryReportSummary]
    total: int


class AifmdLiquidityManagementSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    fund_id: int = Field(description="ID del fondo")
    redemption_suspended: bool = Field(description="Reembolso suspendido")
    suspension_date: str | None = Field(default=None, description="Fecha de suspension")
    gating_applied: bool = Field(description="Gating aplicado")
    swing_price_applied: bool = Field(description="Swing pricing aplicado")
    side_pocket_applied: bool = Field(description="Side pocket aplicado")
    stress_test_result: str | None = Field(default=None, description="Resultado stress test")
    valuation_frequency: str | None = Field(default=None, description="Frecuencia valoracion")

    @field_validator("suspension_date", mode="before")
    @classmethod
    def _suspension_date_to_str(cls, v):
        if v is None or isinstance(v, str):
            return v
        return v.isoformat()


class AifmdLiquidityManagementDetail(AifmdLiquidityManagementSummary):
    created_at: str = Field(description="Fecha de creacion")

    @field_validator("created_at", mode="before")
    @classmethod
    def _created_at_to_str(cls, v):
        if v is None or isinstance(v, str):
            return v
        return v.isoformat()


class AifmdLiquidityManagementListResponse(BaseModel):
    items: list[AifmdLiquidityManagementSummary]
    total: int


class UcitsFundSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    fund_name: str = Field(description="Nombre del fondo")
    management_company: str | None = Field(default=None, description="Gestora")
    registration_date: str = Field(description="Fecha de registro")
    home_member_state: str | None = Field(default=None, description="Estado miembro de origen")
    cross_border_passport: bool = Field(description="Passporting")
    total_aum_eur: float | None = Field(default=None, description="AUM total EUR")
    depositary_id: int | None = Field(default=None, description="ID del depositario")
    krid_url: str | None = Field(default=None, description="URL KRID")
    investment_strategy: str | None = Field(default=None, description="Estrategia")
    risk_profile: str | None = Field(default=None, description="Perfil de riesgo")
    status: str = Field(description="Estado")

    @field_validator("registration_date", mode="before")
    @classmethod
    def _registration_date_to_str(cls, v):
        if v is None or isinstance(v, str):
            return v
        return v.isoformat()


class UcitsFundDetail(UcitsFundSummary):
    created_at: str = Field(description="Fecha de creacion")

    @field_validator("created_at", mode="before")
    @classmethod
    def _created_at_to_str(cls, v):
        if v is None or isinstance(v, str):
            return v
        return v.isoformat()


class UcitsFundListResponse(BaseModel):
    items: list[UcitsFundSummary]
    total: int


class UcitsRegulatoryReportSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    fund_id: int = Field(description="ID del fondo")
    report_type: str = Field(description="Tipo de reporte")
    reporting_period: str | None = Field(default=None, description="Periodo")
    url: str | None = Field(default=None, description="URL")
    filed_date: str | None = Field(default=None, description="Fecha de presentacion")
    status: str = Field(description="Estado")

    @field_validator("filed_date", mode="before")
    @classmethod
    def _filed_date_to_str(cls, v):
        if v is None or isinstance(v, str):
            return v
        return v.isoformat()


class UcitsRegulatoryReportDetail(UcitsRegulatoryReportSummary):
    created_at: str = Field(description="Fecha de creacion")

    @field_validator("created_at", mode="before")
    @classmethod
    def _created_at_to_str(cls, v):
        if v is None or isinstance(v, str):
            return v
        return v.isoformat()


class UcitsRegulatoryReportListResponse(BaseModel):
    items: list[UcitsRegulatoryReportSummary]
    total: int


# ---------------------------------------------------------------------------
# CRD/CRR — Capital Position
# ---------------------------------------------------------------------------


class CrdCapitalPositionCreate(BaseModel):
    entity_id: int = Field(description="ID de la entidad")
    reporting_date: str = Field(description="Fecha YYYY-MM-DD")
    cet1_ratio: float | None = Field(default=None, description="Ratio CET1")
    tier1_ratio: float | None = Field(default=None, description="Ratio Tier1")
    total_capital_ratio: float | None = Field(default=None, description="Ratio capital total")
    cet1_amount: float | None = Field(default=None, description="Monto CET1")
    tier1_amount: float | None = Field(default=None, description="Monto Tier1")
    total_capital_amount: float | None = Field(default=None, description="Monto capital total")
    leverage_ratio: float | None = Field(default=None, description="Ratio apalancamiento")
    risk_weighted_assets: float | None = Field(default=None, description="Activos ponderados por riesgo")
    status: str = Field(default="filed", description="Estado")


class CrdCapitalPositionSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    entity_id: int = Field(description="ID entidad")
    reporting_date: str = Field(description="Fecha reporting")
    cet1_ratio: float | None = Field(default=None, description="Ratio CET1")
    tier1_ratio: float | None = Field(default=None, description="Ratio Tier1")
    total_capital_ratio: float | None = Field(default=None, description="Ratio capital total")
    cet1_amount: float | None = Field(default=None, description="Monto CET1")
    tier1_amount: float | None = Field(default=None, description="Monto Tier1")
    total_capital_amount: float | None = Field(default=None, description="Monto capital total")
    leverage_ratio: float | None = Field(default=None, description="Ratio apalancamiento")
    risk_weighted_assets: float | None = Field(default=None, description="Activos ponderados")
    status: str = Field(description="Estado")

    @field_validator("reporting_date", mode="before")
    @classmethod
    def _dt_to_str(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return v
        return v.isoformat()


class CrdCapitalPositionDetail(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    entity_id: int = Field(description="ID entidad")
    reporting_date: str = Field(description="Fecha reporting")
    cet1_ratio: float | None = Field(default=None, description="Ratio CET1")
    tier1_ratio: float | None = Field(default=None, description="Ratio Tier1")
    total_capital_ratio: float | None = Field(default=None, description="Ratio capital total")
    cet1_amount: float | None = Field(default=None, description="Monto CET1")
    tier1_amount: float | None = Field(default=None, description="Monto Tier1")
    total_capital_amount: float | None = Field(default=None, description="Monto capital total")
    leverage_ratio: float | None = Field(default=None, description="Ratio apalancamiento")
    risk_weighted_assets: float | None = Field(default=None, description="Activos ponderados")
    status: str = Field(description="Estado")
    created_at: str = Field(description="Fecha de creación")

    @field_validator("reporting_date", "created_at", mode="before")
    @classmethod
    def _dt_to_str(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return v
        return v.isoformat()


class CrdCapitalPositionUpdate(BaseModel):
    cet1_ratio: float | None = Field(default=None, description="Ratio CET1")
    tier1_ratio: float | None = Field(default=None, description="Ratio Tier1")
    total_capital_ratio: float | None = Field(default=None, description="Ratio capital total")
    cet1_amount: float | None = Field(default=None, description="Monto CET1")
    tier1_amount: float | None = Field(default=None, description="Monto Tier1")
    total_capital_amount: float | None = Field(default=None, description="Monto capital total")
    leverage_ratio: float | None = Field(default=None, description="Ratio apalancamiento")
    risk_weighted_assets: float | None = Field(default=None, description="Activos ponderados por riesgo")
    status: str | None = Field(default=None, description="Estado")


class CrdCapitalPositionListResponse(BaseModel):
    items: list[CrdCapitalPositionSummary]
    total: int


# ---------------------------------------------------------------------------
# CRD — Stress Tests
# ---------------------------------------------------------------------------


class CrdStressTestCreate(BaseModel):
    entity_id: int = Field(description="ID de la entidad")
    test_date: str = Field(description="Fecha YYYY-MM-DD")
    scenario_name: str | None = Field(default=None, description="Nombre del escenario")
    cet1_impact_pct: float | None = Field(default=None, description="Impacto CET1 %")
    tier1_impact_pct: float | None = Field(default=None, description="Impacto Tier1 %")
    capital_ratio_post_test: float | None = Field(default=None, description="Ratio post-test")
    competent_authority: str | None = Field(default=None, description="Autoridad competente")
    status: str = Field(default="published", description="Estado")


class CrdStressTestSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    entity_id: int = Field(description="ID entidad")
    test_date: str = Field(description="Fecha test")
    scenario_name: str | None = Field(default=None, description="Escenario")
    cet1_impact_pct: float | None = Field(default=None, description="Impacto CET1 %")
    tier1_impact_pct: float | None = Field(default=None, description="Impacto Tier1 %")
    capital_ratio_post_test: float | None = Field(default=None, description="Ratio post-test")
    competent_authority: str | None = Field(default=None, description="Autoridad competente")
    status: str = Field(description="Estado")

    @field_validator("test_date", mode="before")
    @classmethod
    def _dt_to_str(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return v
        return v.isoformat()


class CrdStressTestDetail(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    entity_id: int = Field(description="ID entidad")
    test_date: str = Field(description="Fecha test")
    scenario_name: str | None = Field(default=None, description="Escenario")
    cet1_impact_pct: float | None = Field(default=None, description="Impacto CET1 %")
    tier1_impact_pct: float | None = Field(default=None, description="Impacto Tier1 %")
    capital_ratio_post_test: float | None = Field(default=None, description="Ratio post-test")
    competent_authority: str | None = Field(default=None, description="Autoridad competente")
    status: str = Field(description="Estado")
    created_at: str = Field(description="Fecha de creación")

    @field_validator("test_date", "created_at", mode="before")
    @classmethod
    def _dt_to_str(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return v
        return v.isoformat()


class CrdStressTestUpdate(BaseModel):
    scenario_name: str | None = Field(default=None, description="Escenario")
    cet1_impact_pct: float | None = Field(default=None, description="Impacto CET1 %")
    tier1_impact_pct: float | None = Field(default=None, description="Impacto Tier1 %")
    capital_ratio_post_test: float | None = Field(default=None, description="Ratio post-test")
    competent_authority: str | None = Field(default=None, description="Autoridad competente")
    status: str | None = Field(default=None, description="Estado")


class CrdStressTestListResponse(BaseModel):
    items: list[CrdStressTestSummary]
    total: int


# ---------------------------------------------------------------------------
# BRRD — Bail-In / MREL
# ---------------------------------------------------------------------------


class BrrdBailInCreate(BaseModel):
    entity_id: int = Field(description="ID de la entidad")
    total_eligible_liabilities: float | None = Field(default=None, description="Liabilidades elegibles")
    mrel_target_pct: float | None = Field(default=None, description="Target MREL %")
    mrel_compliance_pct: float | None = Field(default=None, description="Cumplimiento MREL %")
    internal_mrel: float | None = Field(default=None, description="MREL interno")
    resolution_status: str | None = Field(default=None, description="Estado de resolución")
    status: str = Field(default="active", description="Estado")


class BrrdBailInSummary(BaseModel):
    id: int = Field(description="ID")
    entity_id: int = Field(description="ID entidad")
    total_eligible_liabilities: float | None = Field(default=None, description="Liabilidades elegibles")
    mrel_target_pct: float | None = Field(default=None, description="Target MREL %")
    mrel_compliance_pct: float | None = Field(default=None, description="Cumplimiento MREL %")
    internal_mrel: float | None = Field(default=None, description="MREL interno")
    resolution_status: str | None = Field(default=None, description="Estado resolución")
    status: str = Field(description="Estado")


class BrrdBailInDetail(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    entity_id: int = Field(description="ID entidad")
    total_eligible_liabilities: float | None = Field(default=None, description="Liabilidades elegibles")
    mrel_target_pct: float | None = Field(default=None, description="Target MREL %")
    mrel_compliance_pct: float | None = Field(default=None, description="Cumplimiento MREL %")
    internal_mrel: float | None = Field(default=None, description="MREL interno")
    resolution_status: str | None = Field(default=None, description="Estado resolución")
    status: str = Field(description="Estado")
    created_at: str = Field(description="Fecha de creación")

    @field_validator("created_at", mode="before")
    @classmethod
    def _dt_to_str(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return v
        return v.isoformat()


class BrrdBailInUpdate(BaseModel):
    total_eligible_liabilities: float | None = Field(default=None, description="Liabilidades elegibles")
    mrel_target_pct: float | None = Field(default=None, description="Target MREL %")
    mrel_compliance_pct: float | None = Field(default=None, description="Cumplimiento MREL %")
    internal_mrel: float | None = Field(default=None, description="MREL interno")
    resolution_status: str | None = Field(default=None, description="Estado resolución")
    status: str | None = Field(default=None, description="Estado")


class BrrdBailInListResponse(BaseModel):
    items: list[BrrdBailInSummary]
    total: int


# ---------------------------------------------------------------------------
# EMIR — Trade Reports
# ---------------------------------------------------------------------------


class EmirTradeReportCreate(BaseModel):
    trade_id: str = Field(description="ID del trade")
    asset_class: str = Field(description="Clase de activo")
    instrument_class: str = Field(description="Clase de instrumento")
    clearing_obligation_applied: bool = Field(default=False, description="Obligación de clearing")
    reporting_delay_days: int | None = Field(default=None, description="Días de delay reporting")
    counterparty_type: str = Field(description="Tipo de contraparte")
    status: str = Field(default="reported", description="Estado")


class EmirTradeReportSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    trade_id: str = Field(description="ID trade")
    asset_class: str = Field(description="Clase de activo")
    instrument_class: str = Field(description="Clase de instrumento")
    clearing_obligation_applied: bool = Field(description="Clearing aplicado")
    reporting_delay_days: int | None = Field(default=None, description="Delay reporting")
    counterparty_type: str = Field(description="Tipo contraparte")
    status: str = Field(description="Estado")


class EmirTradeReportDetail(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    trade_id: str = Field(description="ID trade")
    asset_class: str = Field(description="Clase de activo")
    instrument_class: str = Field(description="Clase de instrumento")
    clearing_obligation_applied: bool = Field(description="Clearing aplicado")
    reporting_delay_days: int | None = Field(default=None, description="Delay reporting")
    counterparty_type: str = Field(description="Tipo contraparte")
    status: str = Field(description="Estado")
    created_at: str = Field(description="Fecha de creación")

    @field_validator("created_at", mode="before")
    @classmethod
    def _dt_to_str(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return v
        return v.isoformat()


class EmirTradeReportUpdate(BaseModel):
    asset_class: str | None = Field(default=None, description="Clase de activo")
    instrument_class: str | None = Field(default=None, description="Clase de instrumento")
    clearing_obligation_applied: bool | None = Field(default=None, description="Clearing aplicado")
    reporting_delay_days: int | None = Field(default=None, description="Delay reporting")
    counterparty_type: str | None = Field(default=None, description="Tipo contraparte")
    status: str | None = Field(default=None, description="Estado")


class EmirTradeReportListResponse(BaseModel):
    items: list[EmirTradeReportSummary]
    total: int


# ---------------------------------------------------------------------------
# EMIR — Clearing Members
# ---------------------------------------------------------------------------


class EmirClearingMemberCreate(BaseModel):
    entity_id: int = Field(description="ID de la entidad")
    emir_registration: str = Field(description="Registro EMIR")
    clearing_type: str = Field(description="Tipo de clearing")
    status: str = Field(default="active", description="Estado")


class EmirClearingMemberSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    entity_id: int = Field(description="ID entidad")
    emir_registration: str = Field(description="Registro EMIR")
    clearing_type: str = Field(description="Tipo de clearing")
    status: str = Field(description="Estado")


class EmirClearingMemberDetail(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    entity_id: int = Field(description="ID entidad")
    emir_registration: str = Field(description="Registro EMIR")
    clearing_type: str = Field(description="Tipo de clearing")
    status: str = Field(description="Estado")
    created_at: str = Field(description="Fecha de creación")

    @field_validator("created_at", mode="before")
    @classmethod
    def _dt_to_str(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return v
        return v.isoformat()


class EmirClearingMemberUpdate(BaseModel):
    emir_registration: str | None = Field(default=None, description="Registro EMIR")
    clearing_type: str | None = Field(default=None, description="Tipo de clearing")
    status: str | None = Field(default=None, description="Estado")


class EmirClearingMemberListResponse(BaseModel):
    items: list[EmirClearingMemberSummary]
    total: int


# ---------------------------------------------------------------------------
# Corpus Editorial — Nota editorial interna
# ---------------------------------------------------------------------------


class NotaEditorialSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    titulo: str = Field(description="Título")
    resumen_ejecutivo: str | None = Field(default=None, description="Resumen ejecutivo")
    tipo_contenido: str | None = Field(default=None, description="Tipo: resumen_interno, criterio_experto, nota_operativa")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia fuente oficial (BOE, etc.)")
    fuente_verificada: bool = Field(default=False, description="Si la fuente fue verificada por humano")
    autor_id: str | None = Field(default=None, description="ID autor")
    estado: str | None = Field(default=None, description="Estado: borrador, vigente, revisar, obsoleto")
    fecha_creacion: str | None = Field(default=None, description="Fecha de creación")
    fecha_revision: str | None = Field(default=None, description="Fecha de revisión")


class NotaEditorialDetail(NotaEditorialSummary):
    resumen_ejecutivo: str | None = Field(default=None, description="Resumen ejecutivo")
    contexto: str | None = Field(default=None, description="Contexto de la nota")
    impacto_practico: str | None = Field(default=None, description="Impacto práctico")
    advertencias: str | None = Field(default=None, description="Advertencias")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia fuente oficial")
    fuente_verificada: bool = Field(default=False, description="Si la fuente fue verificada por humano")
    documento_origen_id: str | None = Field(default=None, description="ID documento interpretativo origen")
    autor_id: str | None = Field(default=None, description="ID autor")
    revisor_id: str | None = Field(default=None, description="ID revisor")
    fecha_creacion: str | None = Field(default=None, description="Fecha de creación")
    fecha_revision: str | None = Field(default=None, description="Fecha de revisión")
    created_at: str | None = Field(default=None, description="Fecha de creación registro")
    updated_at: str | None = Field(default=None, description="Fecha de actualización registro")


class NotaEditorialCreate(BaseModel):
    titulo: str = Field(description="Título de la nota")
    resumen_ejecutivo: str | None = Field(default=None, description="Resumen ejecutivo")
    contexto: str | None = Field(default=None, description="Contexto")
    impacto_practico: str | None = Field(default=None, description="Impacto práctico")
    advertencias: str | None = Field(default=None, description="Advertencias")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia fuente oficial (BOE-A-..., etc.)")
    documento_origen_referencia: str | None = Field(default=None, description="Referencia documento interpretativo origen")
    autor_id: str | None = Field(default=None, description="ID autor")
    revisor_id: str | None = Field(default=None, description="ID revisor")
    estado: str = Field(default="borrador", description="Estado: borrador, vigente, revisar, obsoleto")
    tipo_contenido: str | None = Field(default=None, description="Tipo: resumen_interno, criterio_experto, nota_operativa")
    fecha_revision: str | None = Field(default=None, description="Fecha de revisión")


class NotaEditorialUpdate(BaseModel):
    titulo: str | None = Field(default=None, description="Título")
    resumen_ejecutivo: str | None = Field(default=None, description="Resumen ejecutivo")
    contexto: str | None = Field(default=None, description="Contexto")
    impacto_practico: str | None = Field(default=None, description="Impacto práctico")
    advertencias: str | None = Field(default=None, description="Advertencias")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia fuente oficial")
    revisor_id: str | None = Field(default=None, description="ID revisor")
    estado: str | None = Field(default=None, description="Estado")
    tipo_contenido: str | None = Field(default=None, description="Tipo")
    fecha_revision: str | None = Field(default=None, description="Fecha de revisión")


class NotaEditorialListResponse(BaseModel):
    notas: list[NotaEditorialSummary]
    total: int


# ---------------------------------------------------------------------------
# Corpus Editorial — Posición interpretativa
# ---------------------------------------------------------------------------


class PosicionInterpretativaSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int = Field(description="ID")
    titulo: str = Field(description="Título")
    descripcion: str | None = Field(default=None, description="Descripción")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia fuente oficial")
    fuente_verificada: bool = Field(default=False, description="Si la fuente fue verificada por humano")
    autor_id: str | None = Field(default=None, description="ID autor")
    estado: str | None = Field(default=None, description="Estado")
    version: int | None = Field(default=None, description="Versión")
    vigencia_desde: str | None = Field(default=None, description="Vigencia desde")
    vigencia_hasta: str | None = Field(default=None, description="Vigencia hasta")


class PosicionInterpretativaDetail(PosicionInterpretativaSummary):
    descripcion: str | None = Field(default=None, description="Descripción")
    contenido: str | None = Field(default=None, description="Contenido")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia fuente oficial")
    fuente_verificada: bool = Field(default=False, description="Si la fuente fue verificada por humano")
    documento_origen_id: str | None = Field(default=None, description="ID documento origen")
    autor_id: str | None = Field(default=None, description="ID autor")
    revisor_id: str | None = Field(default=None, description="ID revisor")
    version: int | None = Field(default=None, description="Versión")
    vigencia_desde: str | None = Field(default=None, description="Vigencia desde")
    vigencia_hasta: str | None = Field(default=None, description="Vigencia hasta")
    version_anterior_id: str | None = Field(default=None, description="ID versión anterior")
    fecha_creacion: str | None = Field(default=None, description="Fecha de creación")
    fecha_revision: str | None = Field(default=None, description="Fecha de revisión")
    created_at: str | None = Field(default=None, description="Fecha de creación registro")
    updated_at: str | None = Field(default=None, description="Fecha de actualización registro")


class PosicionInterpretativaCreate(BaseModel):
    titulo: str = Field(description="Título")
    descripcion: str | None = Field(default=None, description="Descripción")
    contenido: str | None = Field(default=None, description="Contenido")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia fuente oficial (BOE-A-..., etc.)")
    documento_origen_referencia: str | None = Field(default=None, description="Referencia documento interpretativo origen")
    autor_id: str | None = Field(default=None, description="ID autor")
    revisor_id: str | None = Field(default=None, description="ID revisor")
    estado: str = Field(default="borrador", description="Estado: borrador, vigente, revisar, obsoleto")
    vigencia_desde: str | None = Field(default=None, description="Vigencia desde")
    vigencia_hasta: str | None = Field(default=None, description="Vigencia hasta")


class PosicionInterpretativaUpdate(BaseModel):
    titulo: str | None = Field(default=None, description="Título")
    descripcion: str | None = Field(default=None, description="Descripción")
    contenido: str | None = Field(default=None, description="Contenido")
    fuente_oficial_referencia: str | None = Field(default=None, description="Referencia fuente oficial")
    revisor_id: str | None = Field(default=None, description="ID revisor")
    estado: str | None = Field(default=None, description="Estado")
    vigencia_desde: str | None = Field(default=None, description="Vigencia desde")
    vigencia_hasta: str | None = Field(default=None, description="Vigencia hasta")


class PosicionInterpretativaListResponse(BaseModel):
    posiciones: list[PosicionInterpretativaSummary]
    total: int


# ---------------------------------------------------------------------------
# Banking
# ---------------------------------------------------------------------------


class IbanValidateRequest(BaseModel):
    iban: str = Field(description="IBAN a validar")


class IbanValidateResponse(BaseModel):
    result: dict = Field(description="Resultado de validacion IBAN")


class Iso20022ParseResponse(BaseModel):
    valid: bool = Field(description="Si el XML es valido")
    document_type: str | None = Field(default=None, description="Tipo de documento")
    namespace: str | None = Field(default=None, description="Namespace detectado")
    group_header: dict | None = Field(default=None, description="Cabecera de grupo")
    payment_informations: list[dict] = Field(default_factory=list, description="Bloques de pago")
    total_transactions: int | None = Field(default=None, description="Numero total de transacciones")
    total_control_sum: str | None = Field(default=None, description="Importe total")
    errors: list[str] = Field(default_factory=list, description="Errores de parseo")


class N43ParseResponse(BaseModel):
    model_config = {"extra": "allow"}


class SepaBicValidateRequest(BaseModel):
    bic: str = Field(description="BIC a validar")


class SepaBicValidateResponse(BaseModel):
    result: dict = Field(description="Resultado de validacion BIC")


class SepaTransactionInput(BaseModel):
    creditor_name: str | None = Field(default=None, description="Nombre del acreedor")
    creditor_iban: str = Field(description="IBAN del acreedor")
    amount: float = Field(description="Importe")
    currency: str = Field(default="EUR", description="Divisa")
    creditor_bic: str | None = Field(default=None, description="BIC del acreedor")
    remittance_info: str | None = Field(default=None, description="Concepto")
    end_to_end_id: str | None = Field(default=None, description="EndToEndId")
    instruction_id: str | None = Field(default=None, description="InstructionId")


class SepaGenerateRequest(BaseModel):
    debtor_name: str = Field(description="Nombre del ordenante")
    debtor_iban: str = Field(description="IBAN del ordenante")
    debtor_bic: str | None = Field(default=None, description="BIC del ordenante")
    execution_date: str | None = Field(default=None, description="Fecha de ejecucion")
    payment_info_id_prefix: str | None = Field(default=None, description="Prefijo payment info")
    batch_booking: bool = Field(default=False, description="Batch booking")
    transactions: list[SepaTransactionInput] = Field(default_factory=list, description="Transacciones")


class SepaGenerateResponse(BaseModel):
    valid: bool = Field(description="Si la generacion fue valida")
    document_type: str = Field(description="Tipo de documento")
    namespace: str = Field(description="Namespace")
    group_header_msg_id: str | None = Field(default=None, description="MsgId")
    group_header_creation_date: str | None = Field(default=None, description="Fecha creacion")
    group_header_nb_of_txs: str | None = Field(default=None, description="Numero transacciones")
    group_header_control_sum: str | None = Field(default=None, description="Suma control")
    payment_info_count: int = Field(description="Numero de bloques payment info")
    xml_size_bytes: int = Field(description="Tamano XML")


class SepaGroupTransactionInput(BaseModel):
    creditor_iban: str = Field(description="Campo de agrupacion por defecto")
    amount: float = Field(description="Importe")

    model_config = {"extra": "allow"}


class SepaGroupTransactionsRequest(BaseModel):
    transactions: list[SepaGroupTransactionInput] = Field(default_factory=list, description="Transacciones")
    max_batch_size: int | None = Field(default=None, description="Tamano maximo por lote")
    group_by: str = Field(default="creditor_iban", description="Campo de agrupacion")


class SepaGroupBatch(BaseModel):
    group_key: str = Field(description="Clave del grupo")
    transaction_count: int = Field(description="Numero de transacciones")
    total_amount: float = Field(description="Importe total")
    transactions: list[dict] = Field(default_factory=list, description="Transacciones del lote")


class SepaGroupTransactionsResponse(BaseModel):
    total_transactions: int = Field(description="Numero total de transacciones")
    total_batches: int = Field(description="Numero total de lotes")
    batches: list[SepaGroupBatch] = Field(default_factory=list, description="Lotes")


# ---------------------------------------------------------------------------
# CSRD
# ---------------------------------------------------------------------------


class CsrdEntityReportSummary(BaseModel):
    id: int
    entity_id: int
    reporting_year: int
    esap_url: str | None = None
    assurance_status: str | None = None
    reporting_standard: str | None = None
    status: str


class CsrdEntityReportDetail(CsrdEntityReportSummary):
    created_at: str | None = None


class CsrdEntityReportListResponse(BaseModel):
    items: list[CsrdEntityReportSummary]
    total: int


class CsrdEsgDataPointSummary(BaseModel):
    id: int
    report_id: int
    topic: str
    indicator_code: str
    value: float | None = None
    unit: str | None = None
    scope: int | None = None
    verification_status: str | None = None


class CsrdEsgDataPointDetail(CsrdEsgDataPointSummary):
    created_at: str | None = None


class CsrdEsgDataPointListResponse(BaseModel):
    items: list[CsrdEsgDataPointSummary]
    total: int


class CsrdEssSummary(BaseModel):
    id: int
    standard_code: str
    topic: str
    applicable_from_year: int | None = None
    description: str | None = None
    status: str


class CsrdEssDetail(CsrdEssSummary):
    created_at: str | None = None


class CsrdEssListResponse(BaseModel):
    items: list[CsrdEssSummary]
    total: int


class CsrdDoubleMaterialitySummary(BaseModel):
    id: int
    entity_id: int
    impact_materiality: dict | str | None = None
    financial_materiality: dict | str | None = None
    assessment_date: str | None = None
    key_impacts: str | None = None
    key_dependencies: str | None = None
    status: str


class CsrdDoubleMaterialityDetail(CsrdDoubleMaterialitySummary):
    created_at: str | None = None


class CsrdDoubleMaterialityListResponse(BaseModel):
    items: list[CsrdDoubleMaterialitySummary]
    total: int


# ---------------------------------------------------------------------------
# DAC8 / DORA / Entity Identity
# ---------------------------------------------------------------------------


class DacReportingEntitySummary(BaseModel):
    id: int
    tin: str
    entity_type: str
    member_state: str
    dac8_registered: bool
    dac9_registered: bool
    status: str


class DacReportingEntityDetail(DacReportingEntitySummary):
    created_at: str | None = None


class DacReportingEntityListResponse(BaseModel):
    entities: list[DacReportingEntitySummary]
    total: int


class DacCryptoReportSummary(BaseModel):
    id: int
    entity_id: int
    reporting_period: str
    status: str
    crypto_transactions_count: int
    wallet_holders_count: int


class DacCryptoReportDetail(DacCryptoReportSummary):
    submitted_at: str | None = None
    created_at: str | None = None


class DacCryptoReportListResponse(BaseModel):
    reports: list[DacCryptoReportSummary]
    total: int


class DacWalletHolderSummary(BaseModel):
    id: int
    report_id: int
    wallet_address: str
    holder_tin: str | None = None
    holder_member_state: str | None = None
    holder_type: str
    total_value_eur: float | None = None
    verification_status: str | None = None


class DacWalletHolderDetail(DacWalletHolderSummary):
    created_at: str | None = None


class DacWalletHolderListResponse(BaseModel):
    holders: list[DacWalletHolderSummary]
    total: int


class DoraTicIncidentSummary(BaseModel):
    id: int
    incident_severity: str
    classification: str | None = None
    status: str


class DoraTicIncidentDetail(DoraTicIncidentSummary):
    entity_id: int
    description: str | None = None
    impact_scope: str | None = None
    detection_date: str | None = None
    resolution_date: str | None = None
    root_cause: str | None = None
    created_at: str | None = None


class DoraTicIncidentListResponse(BaseModel):
    items: list[DoraTicIncidentSummary]
    total: int


class DoraThirdPartyProviderSummary(BaseModel):
    id: int
    provider_name: str
    provider_type: str
    criticality_assessment: str | None = None
    status: str


class DoraThirdPartyProviderDetail(DoraThirdPartyProviderSummary):
    contract_start: str | None = None
    contract_end: str | None = None
    eu_supervision_status: str | None = None
    exit_strategy: str | None = None
    created_at: str | None = None


class DoraThirdPartyProviderListResponse(BaseModel):
    items: list[DoraThirdPartyProviderSummary]
    total: int


class DoraIctRiskRegisterSummary(BaseModel):
    id: int
    risk_description: str
    likelihood: str | None = None
    impact: str | None = None
    owner: str | None = None
    status: str


class DoraIctRiskRegisterDetail(DoraIctRiskRegisterSummary):
    entity_id: int
    mitigation: str | None = None
    review_date: str | None = None
    created_at: str | None = None


class DoraIctRiskRegisterListResponse(BaseModel):
    items: list[DoraIctRiskRegisterSummary]
    total: int


class DoraPenetrationTestSummary(BaseModel):
    id: int
    test_type: str
    tester: str | None = None
    findings_count: int | None = None
    critical_findings: int | None = None
    status: str


class DoraPenetrationTestDetail(DoraPenetrationTestSummary):
    entity_id: int
    test_date: str | None = None
    remediation_deadline: str | None = None
    created_at: str | None = None


class DoraPenetrationTestListResponse(BaseModel):
    items: list[DoraPenetrationTestSummary]
    total: int


class DoraIncidentClassificationFrameworkSummary(BaseModel):
    id: int
    framework_version: str
    effective_date: str | None = None
    status: str


class DoraIncidentClassificationFrameworkDetail(DoraIncidentClassificationFrameworkSummary):
    severity_thresholds: dict | str | None = None
    reporting_timelines: dict | str | None = None
    created_at: str | None = None


class DoraIncidentClassificationFrameworkListResponse(BaseModel):
    items: list[DoraIncidentClassificationFrameworkSummary]
    total: int


class EntityAlias(BaseModel):
    alias: str
    alias_normalizado: str
    fuente: str | None = None
    confianza: float


class EntityIdentifier(BaseModel):
    id: int
    lei: str
    nombre_legal: str
    pais: str | None = None
    estado: str | None = None
    vigencia_desde: str | None = None
    vigencia_hasta: str | None = None
    vlei_status: str | None = None
    vlei_cred_url: str | None = None
    fuente_ref: str | None = None
    aliases: list[EntityAlias] = Field(default_factory=list)


class EntityLeiResponse(BaseModel):
    entidad: EntityIdentifier


class EntitySearchResult(BaseModel):
    id: int
    nombre: str
    lei: str | None = None
    nombre_legal: str | None = None
    pais: str | None = None
    estado: str | None = None
    confianza: float
    motivo: str


class EntitySearchResponse(BaseModel):
    q: str
    resultados: list[EntitySearchResult]


class FraudPreventionProgramSummary(BaseModel):
    id: int
    entity_id: int
    code_of_conduct: bool
    internal_reporting_system: bool
    training_schedule: str | None = None
    audit_frequency: str | None = None
    compliance_officer_name: str | None = None
    status: str


class FraudPreventionProgramDetail(FraudPreventionProgramSummary):
    created_at: str | None = None


class FraudPreventionProgramListResponse(BaseModel):
    programs: list[FraudPreventionProgramSummary] = Field(default_factory=list)
    total: int


class FraudRiskAssessmentSummary(BaseModel):
    id: int
    entity_id: int
    assessment_date: str
    risk_areas: str | None = None
    mitigation_measures: str | None = None
    next_review_date: str | None = None


class FraudRiskAssessmentDetail(FraudRiskAssessmentSummary):
    created_at: str | None = None


class FraudRiskAssessmentListResponse(BaseModel):
    assessments: list[FraudRiskAssessmentSummary] = Field(default_factory=list)
    total: int


class FraudIncidentSummary(BaseModel):
    id: int
    entity_id: int
    incident_date: str
    amount_eur: float | None = None
    status: str
    resolution_date: str | None = None
    regulatory_notification: bool


class FraudIncidentDetail(FraudIncidentSummary):
    description: str
    created_at: str | None = None


class FraudIncidentListResponse(BaseModel):
    incidents: list[FraudIncidentSummary] = Field(default_factory=list)
    total: int


class MarInsiderTransactionSummary(BaseModel):
    id: int
    ppi_name: str
    instrument: str
    transaction_type: str
    value_eur: float | None = None
    status: str


class MarInsiderTransactionDetail(MarInsiderTransactionSummary):
    ppi_role: str | None = None
    quantity: float | None = None
    price: float | None = None
    date_time: str | None = None
    country: str | None = None
    created_at: str | None = None


class MarInsiderTransactionListResponse(BaseModel):
    items: list[MarInsiderTransactionSummary] = Field(default_factory=list)
    total: int


class MarSuspiciousTransactionReportSummary(BaseModel):
    id: int
    instrument: str
    severity: str | None = None
    submitted_to_cnmv: bool
    cnmv_reference: str | None = None
    status: str


class MarSuspiciousTransactionReportDetail(MarSuspiciousTransactionReportSummary):
    entity_id: int
    pattern_description: str | None = None
    detection_method: str | None = None
    created_at: str | None = None


class MarSuspiciousTransactionReportListResponse(BaseModel):
    items: list[MarSuspiciousTransactionReportSummary] = Field(default_factory=list)
    total: int


class MarMarketManipulationIndicatorSummary(BaseModel):
    id: int
    pattern_type: str
    instrument: str
    confidence_score: float | None = None
    status: str


class MarMarketManipulationIndicatorDetail(MarMarketManipulationIndicatorSummary):
    time_window: str | None = None
    volume_anomaly_pct: float | None = None
    price_anomaly_pct: float | None = None
    created_at: str | None = None


class MarMarketManipulationIndicatorListResponse(BaseModel):
    items: list[MarMarketManipulationIndicatorSummary] = Field(default_factory=list)
    total: int


class MarInsiderCommunicationSummary(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content_summary: str | None = None
    channel: str | None = None
    timestamp: str | None = None


class MarInsiderCommunicationDetail(MarInsiderCommunicationSummary):
    inside_info_reference: str | None = None
    created_at: str | None = None


class MarInsiderCommunicationListResponse(BaseModel):
    items: list[MarInsiderCommunicationSummary] = Field(default_factory=list)
    total: int


class MifidClientCategorySummary(BaseModel):
    id: int
    entity_id: int
    category: str
    assessment_date: str
    status: str


class MifidClientCategoryDetail(MifidClientCategorySummary):
    knowledge_level: str | None = None
    experience_level: str | None = None
    created_at: str | None = None


class MifidClientCategoryListResponse(BaseModel):
    items: list[MifidClientCategorySummary] = Field(default_factory=list)
    total: int


class MifidSuitabilityReportSummary(BaseModel):
    id: int
    client_id: int
    product_id: int
    assessment_date: str
    suitability_score: int | float
    recommendation: str
    status: str


class MifidSuitabilityReportDetail(MifidSuitabilityReportSummary):
    advisor_id: int | None = None
    created_at: str | None = None


class MifidSuitabilityReportListResponse(BaseModel):
    items: list[MifidSuitabilityReportSummary] = Field(default_factory=list)
    total: int


class MifidBestExecutionRecordSummary(BaseModel):
    id: int
    order_id: int
    venue: str
    execution_price: float | None = None
    status: str


class MifidBestExecutionRecordDetail(MifidBestExecutionRecordSummary):
    market_impact: float | None = None
    speed_ms: int | None = None
    quality_metrics: dict | str | None = None
    execution_timestamp: str | None = None
    created_at: str | None = None


class MifidBestExecutionRecordListResponse(BaseModel):
    items: list[MifidBestExecutionRecordSummary] = Field(default_factory=list)
    total: int


class MifidConflictOfInterestSummary(BaseModel):
    id: int
    department: str
    conflict_type: str
    status: str


class MifidConflictOfInterestDetail(MifidConflictOfInterestSummary):
    description: str | None = None
    mitigation_measure: str | None = None
    identified_date: str | None = None
    review_date: str | None = None
    created_at: str | None = None


class MifidConflictOfInterestListResponse(BaseModel):
    items: list[MifidConflictOfInterestSummary] = Field(default_factory=list)
    total: int


class MifidProductGovernanceSummary(BaseModel):
    id: int
    product_id: int
    target_market: str
    risk_level: int | float | None = None
    status: str


class MifidProductGovernanceDetail(MifidProductGovernanceSummary):
    distribution_channels: str | None = None
    key_features: str | None = None
    review_date: str | None = None
    created_at: str | None = None


class MifidProductGovernanceListResponse(BaseModel):
    items: list[MifidProductGovernanceSummary] = Field(default_factory=list)
    total: int


class MifidOrderRecordSummary(BaseModel):
    id: int
    client_id: int
    instrument: str
    direction: str
    quantity: float | None = None
    price: float | None = None
    status: str


class MifidOrderRecordDetail(MifidOrderRecordSummary):
    timestamp: str | None = None
    venue: str | None = None
    retention_until: str | None = None
    created_at: str | None = None


class MifidOrderRecordListResponse(BaseModel):
    items: list[MifidOrderRecordSummary] = Field(default_factory=list)
    total: int


class MifidInsiderListSummary(BaseModel):
    id: int
    insider_name: str
    entity_id: int
    inside_information_description: str
    status: str


class MifidInsiderListDetail(MifidInsiderListSummary):
    insider_tin: str | None = None
    date_created: str | None = None
    date_removed: str | None = None
    created_at: str | None = None


class MifidInsiderListResponse(BaseModel):
    items: list[MifidInsiderListSummary] = Field(default_factory=list)
    total: int


class MifidCompensationPolicySummary(BaseModel):
    id: int
    entity_id: int
    policy_version: str
    alignment_score: int | float | None = None
    status: str


class MifidCompensationPolicyDetail(MifidCompensationPolicySummary):
    risk_adjustment_applied: bool | None = None
    approval_date: str | None = None
    next_review: str | None = None
    created_at: str | None = None


class MifidCompensationPolicyListResponse(BaseModel):
    items: list[MifidCompensationPolicySummary] = Field(default_factory=list)
    total: int


class PbcObligatedSubjectSummary(BaseModel):
    id: int
    subject_type: str
    tin: str
    registration_number: str
    supervisory_authority: str
    pbc_license: str | None = None
    status: str


class PbcObligatedSubjectDetail(PbcObligatedSubjectSummary):
    created_at: str | None = None


class PbcObligatedSubjectListResponse(BaseModel):
    subjects: list[PbcObligatedSubjectSummary] = Field(default_factory=list)
    total: int


class PbcInternalControlSummary(BaseModel):
    id: int
    obligated_subject_id: int
    risk_assessment_date: str | None = None
    compliance_officer: str | None = None
    internal_reporting_channel: bool | None = None
    training_program: bool | None = None
    audit_trail: bool | None = None


class PbcInternalControlDetail(PbcInternalControlSummary):
    created_at: str | None = None


class PbcInternalControlListResponse(BaseModel):
    controls: list[PbcInternalControlSummary] = Field(default_factory=list)
    total: int


class SuspiciousActivityReportSummary(BaseModel):
    id: int
    obligated_subject_id: int
    submission_date: str | None = None
    severity: str | None = None
    status: str
    sepblac_reference: str | None = None


class SuspiciousActivityReportDetail(SuspiciousActivityReportSummary):
    description: str | None = None
    created_at: str | None = None


class SuspiciousActivityReportListResponse(BaseModel):
    reports: list[SuspiciousActivityReportSummary] = Field(default_factory=list)
    total: int


class BeneficialOwnerRecordSummary(BaseModel):
    id: int
    entity_id: int
    owner_name: str
    ownership_percentage: float | None = None
    acquisition_date: str | None = None
    verification_method: str | None = None
    verification_date: str | None = None


class BeneficialOwnerRecordDetail(BeneficialOwnerRecordSummary):
    created_at: str | None = None


class BeneficialOwnerRecordListResponse(BaseModel):
    records: list[BeneficialOwnerRecordSummary] = Field(default_factory=list)
    total: int


class IrsFiscalNormaSummary(BaseModel):
    id: int
    codigo: str
    titulo: str
    tipo: str
    anio_vigencia: int | None = None
    estado: str


class IrsFiscalNormaDetail(IrsFiscalNormaSummary):
    texto: str | None = None
    url_fuente: str | None = None
    creado_en: str | None = None
    actualizado_en: str | None = None


class IrsFiscalNormaListResponse(BaseModel):
    normas: list[IrsFiscalNormaSummary] = Field(default_factory=list)
    total: int


class IrsDttaConventionSummary(BaseModel):
    id: int
    codigo: str
    pais_origen: str
    pais_destino: str
    titulo: str
    fecha_firma: str | None = None
    fecha_vigencia: str | None = None
    tipo_acuerdo: str | None = None
    estado: str


class IrsDttaConventionDetail(IrsDttaConventionSummary):
    boe_referencia: str | None = None
    articulos: str | None = None
    texto_completo: str | None = None
    creado_en: str | None = None
    actualizado_en: str | None = None


class IrsDttaConventionListResponse(BaseModel):
    convenios: list[IrsDttaConventionSummary] = Field(default_factory=list)
    total: int
    limit: int | None = None
    offset: int | None = None
    has_more: bool | None = None
    next_offset: int | None = None


class IrsWithholdingRuleSummary(BaseModel):
    id: int
    codigo: str
    tipo_renta: str
    tipo_renta_espanol: str | None = None
    tipo_retencion_default: float
    tipo_retencion_dta: float | None = None
    pais_aplicable: str | None = None
    estado: str


class IrsWithholdingRuleDetail(IrsWithholdingRuleSummary):
    descripcion: str | None = None
    norma_referencia: str | None = None
    articulo_referencia: str | None = None
    creado_en: str | None = None
    actualizado_en: str | None = None


class IrsWithholdingRuleListResponse(BaseModel):
    reglas: list[IrsWithholdingRuleSummary] = Field(default_factory=list)
    total: int
    limit: int | None = None
    offset: int | None = None
    has_more: bool | None = None
    next_offset: int | None = None


class IrsW8FormSummary(BaseModel):
    id: int
    codigo: str
    nombre: str
    tipo_sujeto: str
    validez_anios: int | None = None
    estado: str


class IrsW8FormDetail(IrsW8FormSummary):
    descripcion: str | None = None
    finalidad: str | None = None
    partes: str | None = None
    obligacion_asociada: str | None = None
    texto_detalle: str | None = None
    creado_en: str | None = None
    actualizado_en: str | None = None


class IrsW8FormListResponse(BaseModel):
    formularios: list[IrsW8FormSummary] = Field(default_factory=list)
    total: int


class IrsTinReferenceSummary(BaseModel):
    id: int
    codigo_pais: str
    pais_nombre: str
    formato_tin: str | None = None
    ejemplo_tin: str | None = None
    es_ocde: bool
    es_eu_vat: bool


class IrsTinReferenceDetail(IrsTinReferenceSummary):
    emisor_espana: str | None = None
    emisor_pais: str | None = None
    creado_en: str | None = None


class IrsTinReferenceListResponse(BaseModel):
    referencias: list[IrsTinReferenceSummary] = Field(default_factory=list)
    total: int


class GiinRegistrySummary(BaseModel):
    id: int
    giin: str
    entidad_nombre: str
    entidad_pais: str | None = None
    tipo_entidad: str
    estado_fatca: str
    fecha_expiracion: str | None = None


class GiinRegistryDetail(GiinRegistrySummary):
    fecha_registro: str | None = None
    es_exempt_beneficial_owner: bool | None = None
    es_sponsored_ffo: bool | None = None
    nota: str | None = None
    creado_en: str | None = None
    actualizado_en: str | None = None


class GiinRegistryListResponse(BaseModel):
    registros: list[GiinRegistrySummary] = Field(default_factory=list)
    total: int
    limit: int | None = None
    offset: int | None = None
    has_more: bool | None = None
    next_offset: int | None = None


class IrsFiscalCheckRequest(BaseModel):
    pais_residencia: str | None = None
    tipo_renta: str
    tiene_formulario_w8: bool = False
    entidad_giin: str | None = None


class IrsFiscalCheckResponse(BaseModel):
    pais_residencia: str | None = None
    tipo_renta: str
    tipo_retencion_aplicable: float
    tiene_convenio_dta: bool
    codigo_convenio: str | None = None
    requiere_w8: bool
    formulario_recomendado: str | None = None
    notas: str | None = None


class PriipsKidSummary(BaseModel):
    id: int
    product_id: int
    product_type: str
    risk_scale: int | float | None = None
    cost_impact: dict | str | None = None
    status: str


class PriipsKidDetail(PriipsKidSummary):
    currency: str | None = None
    negative_scenario_returns: dict | str | None = None
    version: str | None = None
    publication_date: str | None = None
    created_at: str | None = None


class PriipsKidListResponse(BaseModel):
    items: list[PriipsKidSummary] = Field(default_factory=list)
    total: int


class PriipsProductSummary(BaseModel):
    id: int
    product_name: str
    currency: str | None = None
    status: str


class PriipsProductDetail(PriipsProductSummary):
    issuer_id: int | None = None
    underlying_assets: dict | list | str | None = None
    maturity_date: str | None = None
    min_investment: float | None = None
    distribution_channels: dict | list | str | None = None
    created_at: str | None = None


class PriipsProductListResponse(BaseModel):
    items: list[PriipsProductSummary] = Field(default_factory=list)
    total: int


class LivmcClientProtectionSummary(BaseModel):
    id: int
    client_id: int
    protection_type: str
    coverage_amount: float | None = None
    status: str


class LivmcClientProtectionDetail(LivmcClientProtectionSummary):
    provider_id: int | None = None
    created_at: str | None = None


class LivmcClientProtectionListResponse(BaseModel):
    items: list[LivmcClientProtectionSummary] = Field(default_factory=list)
    total: int


class LivmcVoiceProcedureSummary(BaseModel):
    id: int
    entity_id: int
    procedure_type: str
    description: str | None = None
    effective_date: str | None = None
    status: str


class LivmcVoiceProcedureDetail(LivmcVoiceProcedureSummary):
    next_review: str | None = None
    created_at: str | None = None


class LivmcVoiceProcedureListResponse(BaseModel):
    items: list[LivmcVoiceProcedureSummary] = Field(default_factory=list)
    total: int


class SfdrProductSummary(BaseModel):
    id: int
    product_name: str
    product_type: str
    sustainability_strategy: str | None = None
    principal_adverse_impact: str | bool | None = None
    paci_aggregated: dict | str | None = None
    distribution_country: list | str | None = None
    status: str


class SfdrProductDetail(SfdrProductSummary):
    paci_detailed_url: str | None = None
    created_at: str | None = None


class SfdrProductListResponse(BaseModel):
    items: list[SfdrProductSummary] = Field(default_factory=list)
    total: int


class SfdrPaciiIndicatorSummary(BaseModel):
    id: int
    product_id: int
    indicator_code: str
    indicator_name: str
    value: float | None = None
    unit: str | None = None
    reference_period: str | None = None
    status: str


class SfdrPaciiIndicatorDetail(SfdrPaciiIndicatorSummary):
    methodology: str | None = None
    created_at: str | None = None


class SfdrPaciiIndicatorListResponse(BaseModel):
    items: list[SfdrPaciiIndicatorSummary] = Field(default_factory=list)
    total: int


class SfdrEntityPaciSummary(BaseModel):
    id: int
    entity_id: int
    reporting_year: int
    aggregated_paci: dict | str | None = None
    sectoral_decarbonization: dict | str | None = None
    status: str


class SfdrEntityPaciDetail(SfdrEntityPaciSummary):
    created_at: str | None = None


class SfdrEntityPaciListResponse(BaseModel):
    items: list[SfdrEntityPaciSummary] = Field(default_factory=list)
    total: int


class SfdrPreContractualSummary(BaseModel):
    id: int
    product_id: int
    document_type: str
    url: str
    published_date: str | None = None
    version: str | None = None
    status: str


class SfdrPreContractualDetail(SfdrPreContractualSummary):
    created_at: str | None = None


class SfdrPreContractualListResponse(BaseModel):
    items: list[SfdrPreContractualSummary] = Field(default_factory=list)
    total: int


class SfdrAnnualReportSummary(BaseModel):
    id: int
    entity_id: int
    reporting_year: int
    paci_results: dict | str | None = None
    engagement_activities: dict | str | None = None
    good_practice_examples: str | None = None
    url: str | None = None
    published_date: str | None = None
    status: str


class SfdrAnnualReportDetail(SfdrAnnualReportSummary):
    created_at: str | None = None


class SfdrAnnualReportListResponse(BaseModel):
    items: list[SfdrAnnualReportSummary] = Field(default_factory=list)
    total: int


class TransparencyIssuerSummary(BaseModel):
    id: int
    issuer_id: int
    ticker: str
    listing_market: str
    status: str


class TransparencyIssuerDetail(TransparencyIssuerSummary):
    reporting_frequency: str | None = None
    home_member_state: str | None = None
    created_at: str | None = None


class TransparencyIssuerListResponse(BaseModel):
    items: list[TransparencyIssuerSummary] = Field(default_factory=list)
    total: int


class TransparencyRegulatedInfoSummary(BaseModel):
    id: int
    issuer_id: int
    info_type: str
    publication_date: str | None = None
    filing_reference: str | None = None
    status: str


class TransparencyRegulatedInfoDetail(TransparencyRegulatedInfoSummary):
    content_url: str | None = None
    created_at: str | None = None


class TransparencyRegulatedInfoListResponse(BaseModel):
    items: list[TransparencyRegulatedInfoSummary] = Field(default_factory=list)
    total: int


class TransparencyVotingRightsSummary(BaseModel):
    id: int
    issuer_id: int
    shareholder_id: int
    voting_rights_pct: float | None = None
    date_acquired: str | None = None
    status: str


class TransparencyVotingRightsDetail(TransparencyVotingRightsSummary):
    date_reported: str | None = None
    created_at: str | None = None


class TransparencyVotingRightsListResponse(BaseModel):
    items: list[TransparencyVotingRightsSummary] = Field(default_factory=list)
    total: int


class TransparencyInternalRuleSummary(BaseModel):
    id: int
    entity_id: int
    designated_persons: list | str | None = None
    internal_procedure: str | None = None
    retention_period: str | None = None
    status: str


class TransparencyInternalRuleDetail(TransparencyInternalRuleSummary):
    created_at: str | None = None


class TransparencyInternalRuleListResponse(BaseModel):
    items: list[TransparencyInternalRuleSummary] = Field(default_factory=list)
    total: int


class MicroObligacionSummary(BaseModel):
    codigo: str
    nombre: str
    descripcion: str | None = None
    regulacion_relacionada: str
    ambito: str | None = None
    trigger_evento: str | None = None
    frecuencia: str | None = None
    owner_rol: str | None = None
    severidad: str | None = None
    activo: bool


class MicroObligacionRelacion(BaseModel):
    obligacion_id: int


class MicroObligacionDetail(MicroObligacionSummary):
    id: int
    obligaciones_relacionadas: list[MicroObligacionRelacion] = Field(default_factory=list)


class MicroObligacionListResponse(BaseModel):
    micro_obligaciones: list[MicroObligacionSummary] = Field(default_factory=list)
    total: int


class ObligacionRegulatoriaSummary(BaseModel):
    id: int
    codigo: str
    nombre: str
    fuente: str | None = None
    organismo_emisor: str | None = None
    tipo_obligacion: str | None = None
    sujeto_obligado: str | None = None
    periodicidad: str | None = None
    reporte_modelo: str | None = None
    ambito: str | None = None
    estado_vigencia: str | None = None
    plazo_dias: int | None = None
    frecuencia_presentacion: str | None = None
    ventana_presentacion: str | None = None
    trigger_presentacion: str | None = None
    sancion_min: float | None = None
    sancion_max: float | None = None
    prescripcion_anos: int | None = None


class MicroObligacionByObligacionResponse(BaseModel):
    obligacion: ObligacionRegulatoriaSummary
    micro_obligaciones: list[MicroObligacionSummary] = Field(default_factory=list)


class ObligacionesListResponse(BaseModel):
    obligaciones: list[ObligacionRegulatoriaSummary] = Field(default_factory=list)


class ObligacionDetail(ObligacionRegulatoriaSummary):
    documento_origen_tipo: str | None = None
    documento_origen_ref: str | None = None
    seccion_origen: str | None = None
    anexo_origen: str | None = None
    nota: str | None = None
    canal_presentacion: str | None = None
    obligados_resumen: str | None = None
    recargo_voluntario: float | None = None
    recargo_involuntario: float | None = None
    interes_demora: float | None = None
    deposito_previo: bool | None = None
    fuentes_operativas: list | dict | str | None = None
    ultima_actualizacion: str | None = None
    origen_metadato: str | None = None
    estado_metadato: str | None = None
    documentos: list[dict] = Field(default_factory=list)


class ObligacionesAplicablesResponse(BaseModel):
    perfil: dict
    obligaciones: list[ObligacionRegulatoriaSummary] = Field(default_factory=list)
    status: str | None = None
    verified: bool | None = None
    confidence: dict | None = None
    total: int | None = None
    limit: int | None = None
    offset: int | None = None
    has_more: bool | None = None
    next_offset: int | None = None


class EmpresaSummary(BaseModel):
    id: int
    nombre: str
    nif: str | None = None
    domicilio: str | None = None
    fuente_inicial: str | None = None
    documentos_count: int = 0


class EmpresaDetail(BaseModel):
    id: int
    nombre: str
    nif: str | None = None
    domicilio: str | None = None
    fuente_inicial: str | None = None
    documentos: list[dict] = Field(default_factory=list)


class EmpresasListResponse(BaseModel):
    empresas: list[EmpresaSummary] = Field(default_factory=list)


class ScreeningList(BaseModel):
    id: int
    codigo: str
    nombre: str
    tipo: str
    organismo: str
    pais: str | None = None
    url_fuente: str | None = None
    descripcion: str | None = None
    actualizada: str | None = None
    activo: bool


class ScreeningEntry(BaseModel):
    id: int
    entidad_id: str
    nombre: str
    tipo_entidad: str
    pais: str | None = None
    nif: str | None = None
    fecha_nacimiento: str | None = None
    aliases: list[str] = Field(default_factory=list)
    categorias: list[str] = Field(default_factory=list)
    descripcion: str | None = None
    fecha_sancion: str | None = None
    fecha_baja: str | None = None
    activo: bool = True
    lista: ScreeningList


class ScreeningMatch(BaseModel):
    id: int | None = None
    empresa_id: int | None = None
    entry: ScreeningEntry
    confianza: float
    motivo: str
    match_campo: str
    match_texto: str | None = None
    revisado: bool = False
    revisor: str | None = None
    revisado_at: str | None = None
    notas: str | None = None


class ScreeningCheckRequest(BaseModel):
    empresa_id: int | None = None
    nombre: str | None = None
    nif: str | None = None
    tipo_entidad: str | None = None
    listas: list[str] | None = None

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("nombre must not be empty")
        return value


class ScreeningCheckResponse(BaseModel):
    empresa_id: int | None = None
    nombre_evaluado: str
    nif_evaluado: str | None = None
    matches: list[ScreeningMatch] = Field(default_factory=list)
    sin_coincidencias: bool


class ScreeningEntriesResponse(BaseModel):
    total: int
    limit: int
    entries: list[ScreeningEntry] = Field(default_factory=list)


class ScreeningMatchesResponse(BaseModel):
    empresa_id: int
    nombre: str
    matches: list[ScreeningMatch] = Field(default_factory=list)


class OwnershipShare(BaseModel):
    id: int
    empresa_id: int
    titular_id: int | None = None
    titular_tipo: str | None = None
    titular_nombre: str | None = None
    porcentaje: float | None = None
    tipo_participacion: str | None = None
    vigencia_desde: str | None = None
    vigencia_hasta: str | None = None
    fuente: str | None = None
    fuente_ref: str | None = None
    documento_referencia: str | None = None


class OwnershipShareList(BaseModel):
    empresa_id: int
    nombre: str
    participaciones: list[OwnershipShare] = Field(default_factory=list)


class OwnershipRelation(BaseModel):
    id: int
    empresa_origen_id: int
    empresa_destino_id: int
    tipo_relacion: str
    porcentaje: float | None = None
    vigencia_desde: str | None = None
    vigencia_hasta: str | None = None
    fuente: str | None = None
    fuente_ref: str | None = None
    documento_referencia: str | None = None
    nota: str | None = None


class OwnershipRelationList(BaseModel):
    empresa_id: int
    nombre: str
    relaciones: list[OwnershipRelation] = Field(default_factory=list)


class UboRecord(BaseModel):
    id: int
    empresa_id: int
    nombre_persona: str
    nacionalidad: str | None = None
    fecha_nacimiento: str | None = None
    pais_residencia: str | None = None
    tipo_ubo: str | None = None
    porcentaje_control: float | None = None
    umbral_superado: bool | None = None
    vigencia_desde: str | None = None
    vigencia_hasta: str | None = None
    fuente: str | None = None
    fuente_ref: str | None = None
    documento_referencia: str | None = None
    nota: str | None = None


class UboRecordList(BaseModel):
    empresa_id: int
    nombre: str
    beneficiarios: list[UboRecord] = Field(default_factory=list)


class OwnershipGrafoNodo(BaseModel):
    id: int
    nombre: str
    nif: str | None = None
    tipo: str | None = None


class OwnershipGrafoArista(BaseModel):
    origen_id: int
    destino_id: int
    tipo: str
    porcentaje: float | None = None


class OwnershipGrafoResponse(BaseModel):
    empresa_id: int
    nombre: str
    profundidad: int
    nodos: list[OwnershipGrafoNodo] = Field(default_factory=list)
    aristas: list[OwnershipGrafoArista] = Field(default_factory=list)


class OwnershipSearchResult(BaseModel):
    id: int
    nombre: str
    nif: str | None = None
    tiene_participaciones: bool
    tiene_ubos: bool
    tiene_relaciones: bool = False
    participaciones_count: int = 0
    ubos_count: int = 0


class OwnershipSearchResponse(BaseModel):
    q: str
    resultados: list[OwnershipSearchResult] = Field(default_factory=list)


class ConsultaFiscalResponse(BaseModel):
    consulta: str = Field(description="Pregunta fiscal recibida")
    modelos: list[dict] = Field(default_factory=list, description="Modelos AEAT identificados")
    resultados: list[dict] = Field(default_factory=list, description="Resultados de búsqueda unificados")
    total_resultados: int = Field(description="Número total de resultados")
    result_metadata: dict = Field(
        default_factory=dict,
        description="Metadatos de resultados para agentes: returned_count, truncated/partial y limites internos.",
    )
    relevancia: dict = Field(description="Información de relevancia de los resultados")
    confianza: dict | None = Field(default=None, description="Información de confianza (faithfulness, grounding)")
    cited_chunks: list[ChunkCitation] = Field(default_factory=list, description="Chunks citados con evidencia")
    claim_citations: list[ClaimCitation] = Field(default_factory=list, description="Citas por afirmación factual")


# --- PGC / XBRL ------------------------------------------------------------

class PgcMarco(BaseModel):
    codigo: str
    titulo: str
    tipo: str
    anio: int | None = None
    texto: str | None = None
    url_boe: str | None = None
    vigente: bool | None = None


class PgcCuentaItem(BaseModel):
    codigo: str
    descripcion: str
    nivel: int
    padre_codigo: str | None = None
    grupo: str | None = None
    clase: str | None = None
    saldo_normal: str | None = None
    tipo_cuenta: str | None = None
    vigente: bool | None = None
    nota: str | None = None


class PgcNormaValoracionItem(BaseModel):
    norma_ref: str
    articulo: str | None = None
    descripcion: str | None = None
    cuenta_codigo: str | None = None
    cuenta_descripcion: str | None = None


class PgcEstadoFinancieroItem(BaseModel):
    id: str
    estado: str
    tipo_presentacion: str | None = None
    orden: int
    periodo: str
    importe_base: float | None = None
    importe_anterior: float | None = None
    nota_pieds: str | None = None
    cuenta_codigo: str | None = None
    cuenta_descripcion: str | None = None


class PgcReferenciaFiscalItem(BaseModel):
    modelo: str
    casilla: str | None = None
    ejercicio: str | None = None
    nota: str | None = None
    cuenta_codigo: str | None = None
    cuenta_descripcion: str | None = None


class PgcAeatReferenceItem(BaseModel):
    modelo_id: int
    campana: str | None = None
    nota: str | None = None
    cuenta_codigo: str | None = None
    cuenta_descripcion: str | None = None


class PgcCuentasResponse(BaseModel):
    marco: PgcMarco | None = None
    cuentas: list[PgcCuentaItem] = Field(default_factory=list)


class PgcBuscarResponse(BaseModel):
    marco: PgcMarco | None = None
    resultados: list[PgcCuentaItem] = Field(default_factory=list)


class PgcNormasValoracionResponse(BaseModel):
    marco: PgcMarco | None = None
    normas: list[PgcNormaValoracionItem] = Field(default_factory=list)


class PgcEstadosFinancierosResponse(BaseModel):
    marco: PgcMarco | None = None
    estados: list[PgcEstadoFinancieroItem] = Field(default_factory=list)


class PgcReferenciasFiscalesResponse(BaseModel):
    marco: PgcMarco | None = None
    referencias: list[PgcReferenciaFiscalItem] = Field(default_factory=list)


class PgcAeatReferencesResponse(BaseModel):
    marco: PgcMarco | None = None
    referencias: list[PgcAeatReferenceItem] = Field(default_factory=list)


class XbrlFact(BaseModel):
    filing_id: int
    concept: str
    value_raw: str
    value_numeric: float | None = None
    unit: str | None = None
    context_ref: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    entity_identifier: str | None = None
    decimals: str | None = None


class XbrlFiling(BaseModel):
    id: int
    source_name: str
    source_path: str
    entity_identifier: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    filing_type: str
    created_at: str | None = None


class XbrlFactsResponse(BaseModel):
    entity_id: str | None = None
    concept: str | None = None
    facts: list[XbrlFact] = Field(default_factory=list)


class XbrlFilingDetailResponse(BaseModel):
    filing: XbrlFiling
    facts: list[XbrlFact] = Field(default_factory=list)


class PgcXbrlMappingItem(BaseModel):
    xbrl_concept_qname: str
    pgc_account_codigo: str
    pgc_account_descripcion: str | None = None
    confidence: str | None = None
    mapping_type: str
    note: str | None = None


class PgcXbrlMappingsResponse(BaseModel):
    xbrl_concept: str | None = None
    pgc_account: str | None = None
    confidence: str | None = None
    mappings: list[PgcXbrlMappingItem] = Field(default_factory=list)


class XbrlTaxonomyEntry(BaseModel):
    concept_qname: str
    namespace: str | None = None
    label: str
    label_language: str
    label_role: str
    standard: str
    data_type: str | None = None
    period_type: str | None = None
    is_monetary: bool
    is_negative_allowed: bool


class XbrlTaxonomyResponse(BaseModel):
    standard: str | None = None
    language: str | None = None
    concept: str | None = None
    entries: list[XbrlTaxonomyEntry] = Field(default_factory=list)


class XbrlFactWithPgc(XbrlFact):
    pgc_account_codigo: str | None = None
    pgc_account_descripcion: str | None = None
    mapping_confidence: str | None = None
    mapping_type: str | None = None
    mapping_note: str | None = None


class XbrlFactsWithPgcResponse(BaseModel):
    entity_id: str | None = None
    concept: str | None = None
    pgc_account: str | None = None
    confidence: str | None = None
    facts: list[XbrlFactWithPgc] = Field(default_factory=list)


# --- EUR-Lex ---------------------------------------------------------------
# Domain notes: backed by `norma + articulo + version_articulo` (no
# `documento_interpretativo`). Field naming preserves API contract used by
# `tests/test_eurlex_router.py`; SQL aliases map storage to contract.

class EurLexListItem(BaseModel):
    referencia: str = Field(description="Identificador CELEX (norma.codigo)")
    fecha: str | None = Field(default=None, description="vigente_desde (ISO date)")
    titulo: str = Field(description="Titulo oficial de la norma")
    tipo_documento: str = Field(description="reglamento | directiva | decision")
    ambito: str = Field(description="Ambito EU (mercado_interior, fiscal_ue, ...)")
    fragmento: str = Field(description="Extracto truncado (<=223 chars) del primer articulo vigente")
    url_fuente: str | None = Field(default=None, description="URI ELI EUR-Lex (norma.eli_uri)")
    articulos_total: int = Field(default=0, description="Numero de articulos/versiones vigentes cargados")
    coverage_status: str = Field(description="article_text_available | metadata_only")
    articles_expected: int | None = Field(default=None, description="Conteo esperado de articulos si el worker pudo medirlo")
    articles_parsed: int | None = Field(default=None, description="Conteo de articulos parseados registrado por el worker")
    articles_empty_official: int | None = Field(
        default=None,
        description="Bloques oficiales EUR-Lex publicados sin cuerpo de texto en la manifestacion vigente",
    )
    quality_status: str | None = Field(default=None, description="metadata_only | partial | article_text_available")
    verified: bool = Field(description="True solo si hay texto oficial de articulado cargado")
    completeness: str = Field(description="completa | parcial")
    evidence_notice: str | None = Field(default=None, description="Aviso de evidencia limitada si falta articulado")


class EurLexListResponse(BaseModel):
    documentos: list[EurLexListItem]
    total: int | None = None
    limit: int | None = None
    offset: int | None = None
    has_more: bool | None = None
    next_offset: int | None = None


class EurLexDetail(BaseModel):
    referencia: str = Field(description="Identificador CELEX (norma.codigo)")
    fecha: str | None = Field(default=None, description="vigente_desde (ISO date)")
    titulo: str = Field(description="Titulo oficial de la norma")
    tipo_documento: str = Field(description="reglamento | directiva | decision")
    ambito: str = Field(description="Ambito EU")
    texto: str = Field(description="Concatenacion de articulos vigentes")
    url_fuente: str | None = Field(default=None, description="URI ELI EUR-Lex")
    articulos_total: int = Field(default=0, description="Numero de articulos/versiones vigentes cargados")
    coverage_status: str = Field(description="article_text_available | metadata_only")
    articles_expected: int | None = Field(default=None, description="Conteo esperado de articulos si el worker pudo medirlo")
    articles_parsed: int | None = Field(default=None, description="Conteo de articulos parseados registrado por el worker")
    articles_empty_official: int | None = Field(
        default=None,
        description="Bloques oficiales EUR-Lex publicados sin cuerpo de texto en la manifestacion vigente",
    )
    quality_status: str | None = Field(default=None, description="metadata_only | partial | article_text_available")
    verified: bool = Field(description="True solo si hay texto oficial de articulado cargado")
    completeness: str = Field(description="completa | parcial")
    evidence_notice: str | None = Field(default=None, description="Aviso de evidencia limitada si falta articulado")


# --- BORME -----------------------------------------------------------------

class BORMEListItem(BaseModel):
    referencia: str = Field(description="Referencia oficial del acto/anuncio BORME")
    fecha: str | None = Field(default=None, description="Fecha del acto/anuncio")
    titulo: str | None = Field(default=None, description="Titulo detectado")
    tipo_documento: str | None = Field(default=None, description="Tipo de acto detectado")
    fragmento: str = Field(description="Extracto truncado del texto oficial")
    url_fuente: str | None = Field(default=None, description="URL oficial BORME/BOE")


class BORMEListResponse(BaseModel):
    actos: list[BORMEListItem]
    total: int | None = None
    limit: int | None = None
    offset: int | None = None
    has_more: bool | None = None
    next_offset: int | None = None


class BORMEEmpresaRelacionada(BaseModel):
    id: int
    nombre: str
    rol: str | None = None
    confianza_extraccion: float


class BORMEDetail(BaseModel):
    referencia: str
    fecha: str | None = None
    titulo: str | None = None
    tipo_documento: str | None = None
    texto: str
    url_fuente: str | None = None
    empresas_relacionadas: list[BORMEEmpresaRelacionada] = Field(default_factory=list)


# --- documento_interpretativo (cnmv / bde / aepd / cendoj) -----------------
# Contrato compartido. Campos opcionales se pueblan solo cuando el router del
# dominio los proyecta en el SELECT (cendoj -> organismo_emisor;
# cnmv -> estado_vigencia, numero_circular, fecha_publicacion, referencia_boe).

class DocInterpretativoListItem(BaseModel):
    referencia: str = Field(description="Identificador del documento")
    fecha: str | None = Field(default=None, description="Fecha (ISO date)")
    titulo: str | None = Field(default=None, description="Titulo")
    tipo_documento: str = Field(description="Tipo de documento")
    ambito: str = Field(description="Ambito")
    fragmento: str = Field(description="Extracto truncado (<=223 chars)")
    url_fuente: str | None = Field(default=None, description="URL fuente oficial")
    organismo_emisor: str | None = Field(default=None, description="Organismo emisor (cendoj)")
    estado_vigencia: str | None = Field(default=None, description="Estado vigencia (cnmv)")


class DocInterpretativoListResponse(BaseModel):
    documentos: list[DocInterpretativoListItem]
    skip: int | None = Field(default=None, description="Offset paginacion (cnmv)")
    limit: int | None = Field(default=None, description="Limite paginacion (cnmv)")
    total: int | None = Field(default=None, description="Total resultados (cnmv)")


class DocInterpretativoDetail(BaseModel):
    referencia: str
    fecha: str | None = None
    titulo: str | None = None
    tipo_documento: str
    ambito: str
    texto: str
    url_fuente: str | None = None
    organismo_emisor: str | None = Field(default=None, description="Organismo emisor (cendoj)")
    estado_vigencia: str | None = Field(default=None, description="Estado vigencia (cnmv)")
    numero_circular: str | None = Field(default=None, description="Numero circular (cnmv)")
    fecha_publicacion: str | None = Field(default=None, description="Fecha publicacion (cnmv)")
    referencia_boe: str | None = Field(default=None, description="Referencia BOE (cnmv)")


# --- BOE diario non-consolidated documents ---------------------------------

class BOEDiarioListItem(BaseModel):
    referencia: str = Field(description="Identificador oficial BOE-B/BOE-S/BOE-N")
    fecha: str | None = Field(default=None, description="Fecha de publicacion")
    titulo: str | None = Field(default=None, description="Titulo oficial del documento")
    tipo_documento: str = Field(description="anuncio_boe | suplemento_boe | notificacion_boe")
    fragmento: str = Field(description="Extracto truncado del texto oficial")
    url_fuente: str | None = Field(default=None, description="XML o PDF oficial utilizado")
    row_completeness: str | None = Field(default=None, description="complete | partial")
    row_provenance: str | None = Field(default=None, description="official_exact | official_best_effort")


class BOEDiarioListResponse(BaseModel):
    documentos: list[BOEDiarioListItem]
    total: int | None = None
    limit: int | None = None
    offset: int | None = None
    has_more: bool | None = None
    next_offset: int | None = None


class BOEDiarioDetail(BaseModel):
    referencia: str
    fecha: str | None = None
    titulo: str | None = None
    tipo_documento: str
    texto: str
    url_fuente: str | None = None
    row_completeness: str | None = None
    row_provenance: str | None = None
    metadata: dict | str | None = None


# --- CNMV-specific link / version surfaces --------------------------------

class CNMVVersionItem(BaseModel):
    version_num: int
    cambio_tipo: str
    fecha_version: str | None = None
    nota: str | None = None
    url_version: str | None = None
    texto: str


class CNMVVersionResponse(BaseModel):
    referencia: str
    versiones: list[CNMVVersionItem]
    total: int


class CNMVRegulationLinkItem(BaseModel):
    regulacion_id: str
    relacion_tipo: str
    nota: str | None = None


class CNMVRegulationLinkResponse(BaseModel):
    referencia: str
    regulaciones: list[CNMVRegulationLinkItem]
    total: int


class CNMVObligationLinkItem(BaseModel):
    tipo_obligacion: str
    nota: str | None = None


class CNMVObligationLinkResponse(BaseModel):
    referencia: str
    obligaciones: list[CNMVObligationLinkItem]
    total: int
