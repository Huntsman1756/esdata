import type {
  StatusResponse,
  CoberturaResponse,
  NormasResponse,
  SearchResponse,
  DoctrinaSearchResponse,
  DoctrinaDetail,
  ArticuloDetail,
  ArticuloHistorial,
  ModelosListResponse,
  ModeloDetail,
  ModeloArticulosResponse,
} from "./types";

// The API base is a server-side-only env var.
// It must NOT leak to the browser.
function apiBase(): string {
  return (
    process.env.ESDATA_API_BASE_URL || "http://localhost:8000"
  ).replace(/\/+$/, "");
}

async function fetchApi<T>(path: string): Promise<T> {
  const url = `${apiBase()}${path}`;
  const res = await fetch(url, {
    next: { revalidate: 3600 },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status} at ${path}`);
  }
  return res.json() as Promise<T>;
}

// --- Status ---
export async function getStatus(): Promise<StatusResponse> {
  return fetchApi<StatusResponse>("/status");
}

// --- Legislacion ---
export async function getCobertura(): Promise<CoberturaResponse> {
  return fetchApi<CoberturaResponse>("/v1/legislacion/cobertura");
}

export async function getNormas(): Promise<NormasResponse> {
  return fetchApi<NormasResponse>("/v1/legislacion");
}

export async function getArticulo(
  codigo: string,
  numero: string,
  vigenteEn?: string
): Promise<ArticuloDetail> {
  const params = vigenteEn ? `?vigente_en=${vigenteEn}` : "";
  return fetchApi<ArticuloDetail>(
    `/v1/legislacion/${codigo}/articulos/${numero}${params}`
  );
}

export async function getArticuloHistorial(
  codigo: string,
  numero: string
): Promise<ArticuloHistorial> {
  return fetchApi<ArticuloHistorial>(
    `/v1/legislacion/${codigo}/articulos/${numero}/historial`
  );
}

// --- Buscar ---
export async function searchLegislacion(
  q: string,
  opts?: {
    norma?: string;
    fuente?: string;
    ambito?: string;
    tipo?: string;
    vigenteEn?: string;
  }
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q });
  if (opts?.norma) params.set("norma", opts.norma);
  if (opts?.fuente) params.set("fuente", opts.fuente);
  if (opts?.ambito) params.set("ambito", opts.ambito);
  if (opts?.tipo) params.set("tipo", opts.tipo);
  if (opts?.vigenteEn) params.set("vigente_en", opts.vigenteEn);
  return fetchApi<SearchResponse>(`/v1/buscar?${params.toString()}`);
}

// --- Doctrina ---
export async function searchDoctrina(
  q: string,
  opts?: {
    organismoEmisor?: string;
    tipo?: string;
    desde?: string;
  }
): Promise<DoctrinaSearchResponse> {
  const params = new URLSearchParams({ q });
  if (opts?.organismoEmisor) params.set("organismo_emisor", opts.organismoEmisor);
  if (opts?.tipo) params.set("tipo", opts.tipo);
  if (opts?.desde) params.set("desde", opts.desde);
  return fetchApi<DoctrinaSearchResponse>(
    `/v1/doctrina/buscar?${params.toString()}`
  );
}

export async function getDoctrina(referencia: string): Promise<DoctrinaDetail> {
  return fetchApi<DoctrinaDetail>(`/v1/doctrina/${referencia}`);
}

// --- Modelos AEAT ---
export async function getModelos(): Promise<ModelosListResponse> {
  return fetchApi<ModelosListResponse>("/v1/modelos");
}

export async function getModelo(
  codigo: string,
  campana?: string
): Promise<ModeloDetail> {
  const params = campana ? `?campana=${campana}` : "";
  return fetchApi<ModeloDetail>(`/v1/modelos/${codigo}${params}`);
}

export async function getModeloArticulos(
  codigo: string
): Promise<ModeloArticulosResponse> {
  return fetchApi<ModeloArticulosResponse>(`/v1/modelos/${codigo}/articulos`);
}
