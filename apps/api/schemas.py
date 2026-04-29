"""Pydantic response models for the esdata API.

Focused on the endpoints exposed to Custom GPT Actions.
"""

from pydantic import BaseModel, Field


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
    jurisdiccion: str = Field(description="Jurisdicción (es, autonomico, etc.)")
    tipo_fuente: str = Field(description="Tipo de fuente (boe, autonomica, etc.)")
    tipo_documento: str = Field(
        description="Tipo de documento (ley, real_decreto_legislativo, etc.)"
    )
    ambito: str = Field(description="Ámbito temático (tributario, etc.)")
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
    tipo_casilla: str | None = Field(
        default=None, description="Tipo (importe, checkbox, texto, etc.)"
    )
    pagina: int | None = Field(default=None, description="Página del PDF donde aparece")
    orden: int | None = Field(default=None, description="Orden de aparición")


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
    fuentes_recomendadas: list[str] = Field(default_factory=list, description="Fuentes oficiales recomendadas")


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
    articulos: list[ModeloArticulo] = Field(
        default_factory=list, description="Artículos de ley vinculados"
    )
    casillas: list[ModeloCasilla] = Field(
        default_factory=list, description="Casillas de la campaña activa"
    )
    claves: list[ModeloClave] = Field(
        default_factory=list, description="Claves de la campaña activa"
    )
    instrucciones: list[ModeloInstruccion] = Field(
        default_factory=list, description="Instrucciones"
    )
    normativa: list[ModeloNormativa] = Field(
        default_factory=list, description="Normativa BOE"
    )
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


class DoctrinaSearchResponse(BaseModel):
    q: str = Field(description="Término de búsqueda")
    resultados: list[DoctrinaSearchResult]


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
    fuentes_recomendadas: list[str] = Field(default_factory=list, description="Fuentes recomendadas")


class ModeloArtefactosResponse(BaseModel):
    codigo: str = Field(description="Código del modelo")
    nombre: str = Field(description="Nombre completo")
    campana: str | None = Field(default=None, description="Campaña activa")
    articulos: list[ModeloArticulo] = Field(default_factory=list, description="Artículos")
    casillas: list[ModeloCasilla] = Field(default_factory=list, description="Casillas")
    claves: list[ModeloClave] = Field(default_factory=list, description="Claves")
    instrucciones: list[ModeloInstruccion] = Field(default_factory=list, description="Instrucciones")
    normativa: list[ModeloNormativa] = Field(default_factory=list, description="Normativa BOE")


class ModelosCampanasOperativasResponse(BaseModel):
    codigos: list[str] = Field(description="Códigos solicitados")
    campana: str | None = Field(default=None, description="Campaña aplicada")
    resultados: list[ModeloCampanaOperativaResponse] = Field(default_factory=list, description="Resultados")


class ModelosListResponse(BaseModel):
    modelos: list[ModeloSummary]
