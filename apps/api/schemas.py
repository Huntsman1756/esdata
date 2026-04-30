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


# ---------------------------------------------------------------------------
# Consulta fiscal inteligente
# ---------------------------------------------------------------------------


class ChunkCitation(BaseModel):
    chunk_id: str = Field(description="ID del chunk recuperado")
    content_preview: str = Field(description="Vista previa del contenido del chunk")
    relevance_score: float = Field(description="Puntuación de relevancia")


class ClaimCitation(BaseModel):
    claim: str = Field(description="Afirmación factual")
    source_chunk_id: str = Field(description="Chunk que respalda la afirmación")
    source_url: str | None = Field(default=None, description="URL de la fuente original")
    grounded: bool = Field(description="Si la afirmación está respaldada por evidencia")
    confidence: float = Field(description="Confianza del grounding (0-1)")


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


class ConsultaFiscalResponse(BaseModel):
    consulta: str = Field(description="Pregunta fiscal recibida")
    modelos: list[dict] = Field(default_factory=list, description="Modelos AEAT identificados")
    resultados: list[dict] = Field(default_factory=list, description="Resultados de búsqueda unificados")
    total_resultados: int = Field(description="Número total de resultados")
    relevancia: dict = Field(description="Información de relevancia de los resultados")
    confianza: dict | None = Field(default=None, description="Información de confianza (faithfulness, grounding)")
    cited_chunks: list[ChunkCitation] = Field(default_factory=list, description="Chunks citados con evidencia")
    claim_citations: list[ClaimCitation] = Field(default_factory=list, description="Citas por afirmación factual")
