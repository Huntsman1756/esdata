// ============================================================
// Types typed against the real esdata FastAPI responses.
// ============================================================

// --- Status ---
export interface WorkerStatus {
  last_run: string | null;
  finished_at: string | null;
  status: "ok" | "failed" | "running" | null;
  bloques_processed: number;
  articulos_upserted: number;
  documentos_processed: number;
  documentos_upserted: number;
  doctrina_links_created: number;
  error: string | null;
  stale: boolean;
}

export interface StatusResponse {
  workers: Record<string, WorkerStatus | { status: "never_run"; stale: boolean }>;
  api: string;
  timestamp: string;
}

// --- Legislacion / Cobertura ---
export interface NormaCobertura {
  codigo: string;
  titulo: string;
  articulos: number;
  versiones: number;
  ultima_version: string | null;
}

export interface CoberturaResponse {
  normas: NormaCobertura[];
}

// --- Norma ---
export interface Norma {
  codigo: string;
  titulo: string;
  jurisdiccion: string;
  tipo_fuente: string;
  tipo_documento: string;
  ambito: string;
  estado_cobertura: string;
}

export interface NormasResponse {
  normas: Norma[];
}

// --- Articulo ---
export interface Articulo {
  numero: string;
  titulo: string;
  tipo: string;
}

export interface ArticulosListResponse {
  norma: string;
  articulos: Articulo[];
}

export interface ConfianzaInfo {
  nivel: number;
  fuentes: string[];
  aviso: string | null;
}

export interface ArticuloDetail {
  norma: string;
  numero: string;
  texto: string;
  vigente_desde: string | null;
  vigente_hasta: string | null;
  confianza: ConfianzaInfo;
}

export interface ArticuloVersion {
  texto: string;
  vigente_desde: string | null;
  vigente_hasta: string | null;
}

export interface ArticuloHistorial {
  norma: string;
  numero: string;
  historial: ArticuloVersion[];
}

// --- Buscar (legislacion) ---
export interface SearchResult {
  tipo: string;
  norma: string;
  numero: string;
  texto: string;
  fragmento: string;
  vigente_desde: string | null;
  vigente_hasta: string | null;
  rank: number;
  confianza: ConfianzaInfo;
}

export interface SearchResponse {
  q: string;
  resultados: SearchResult[];
}

// --- Doctrina ---
export interface ArticuloRelacionado {
  norma: string;
  numero: string;
  metodo_enlace: string;
  confianza_enlace: number;
}

export interface DoctrinaDetail {
  referencia: string;
  tipo_documento: string;
  organismo_emisor: string;
  texto: string;
  articulos_relacionados: ArticuloRelacionado[];
  confianza: ConfianzaInfo;
}

export interface DoctrinaSearchResult {
  referencia: string;
  tipo_documento: string;
  organismo_emisor: string;
  fecha: string | null;
  titulo: string;
  nivel_enlace: number;
  norma?: string;
  numero?: string;
  fragmento: string;
}

export interface DoctrinaSearchResponse {
  q: string;
  resultados: DoctrinaSearchResult[];
}

// --- Materias ---
export interface Materia {
  slug: string;
  etiqueta: string;
  articulos_count: number;
}

export interface MateriasResponse {
  materias: Materia[];
}

export interface MateriaArticulo {
  norma: string;
  numero: string;
  relevancia: number;
}

export interface MateriaDetail {
  slug: string;
  etiqueta: string;
  articulos: MateriaArticulo[];
}

// --- Modelos AEAT ---
export interface ModeloSummary {
  codigo: string;
  nombre: string;
  periodo: string | null;
  impuesto: string | null;
  articulos_count: number;
  casillas_count: number;
}

export interface ModelosListResponse {
  modelos: ModeloSummary[];
}

export interface ModeloArticulo {
  norma: string;
  numero: string;
  titulo: string | null;
  casilla: string | null;
  nota: string | null;
  fuente: string;
  url_fuente: string | null;
}

export interface DoctrinaViaArticulo {
  norma: string;
  numero: string;
}

export interface DoctrinaRelacionada {
  referencia: string;
  organismo_emisor: string;
  fecha: string | null;
  via_articulos: DoctrinaViaArticulo[];
}

export interface ModeloCasilla {
  codigo: string;
  etiqueta: string;
  descripcion: string | null;
  tipo_casilla: string | null;
  pagina: number | null;
  orden: number | null;
}

export interface ModeloClave {
  codigo: string;
  etiqueta: string;
  descripcion: string | null;
  tipo_clave: string | null;
}

export interface ModeloInstruccion {
  seccion: string;
  titulo: string;
  contenido: string;
  orden: number;
}

export interface ModeloNormativa {
  boe_id: string | null;
  titulo: string;
  fecha: string | null;
  url_boe: string | null;
  resumen: string | null;
}

export interface ModeloCampana {
  campana: string;
  activo: boolean;
}

export interface ModeloDetail {
  codigo: string;
  nombre: string;
  periodo: string | null;
  impuesto: string | null;
  url_info: string | null;
  campana_activa: string | null;
  campanas: ModeloCampana[];
  articulos: ModeloArticulo[];
  casillas: ModeloCasilla[];
  claves: ModeloClave[];
  instrucciones: ModeloInstruccion[];
  normativa: ModeloNormativa[];
  doctrina_relacionada: DoctrinaRelacionada[];
}

export interface ModeloArticulosResponse {
  codigo: string;
  articulos: ModeloArticulo[];
}
