"use client";

import { useState, useEffect, Suspense } from "react";
import {
  CheckCircle2,
  Circle,
  Clock,
  AlertCircle,
  Search,
  X,
} from "lucide-react";

type Cambio = {
  codigo: string;
  fuente: string;
  impacto: string;
  estado: string;
  obligaciones_afectadas: string[];
  accion_recomendada: string;
  prioridad: string;
  fecha_detectado: string;
};

const PRIORIDAD_ICON: Record<string, { icon: React.ReactNode; color: string }> = {
  alta: { icon: <AlertCircle className="h-4 w-4" />, color: "text-red-600" },
  media: { icon: <Clock className="h-4 w-4" />, color: "text-amber-600" },
  baja: { icon: <Circle className="h-4 w-4" />, color: "text-stone-400" },
};

const ESTADO_BADGE: Record<string, { icon: React.ReactNode; color: string }> = {
  nuevo: { icon: <Circle className="h-4 w-4" />, color: "bg-blue-50 text-blue-700 border-blue-200" },
  en_progreso: { icon: <Clock className="h-4 w-4" />, color: "bg-amber-50 text-amber-700 border-amber-200" },
  resuelto: { icon: <CheckCircle2 className="h-4 w-4" />, color: "bg-green-50 text-green-700 border-green-200" },
};

function CambiosContent() {
  const [cambios, setCambios] = useState<Cambio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fuente, setFuente] = useState("");
  const [estado, setEstado] = useState("");
  const [prioridad, setPrioridad] = useState("");
  const [obligacion, setObligacion] = useState("");

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  async function fetchChanges() {
    const params = new URLSearchParams();
    if (fuente) params.set("fuente", fuente);
    if (estado) params.set("estado", estado);
    if (prioridad) params.set("prioridad", prioridad);
    if (obligacion) params.set("obligacion_afectada", obligacion);

    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/v1/cambios?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setCambios(await res.json());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchChanges();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fuente, estado, prioridad, obligacion]);

  function clearFilters() {
    setFuente("");
    setEstado("");
    setPrioridad("");
    setObligacion("");
  }

  const hasFilters = fuente || estado || prioridad || obligacion;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      {/* Filters */}
      <div className="mb-6 rounded-lg border border-stone-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-3">
          <Search className="h-4 w-4 text-stone-400" />
          <h2 className="text-sm font-medium text-stone-700">Filtros</h2>
          {hasFilters && (
            <button
              onClick={clearFilters}
              className="ml-auto text-xs text-stone-400 hover:text-stone-600 flex items-center gap-1"
            >
              <X className="h-3 w-3" /> Limpiar
            </button>
          )}
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div>
            <label className="mb-1 block text-xs text-stone-500">Fuente</label>
            <input
              type="text"
              placeholder="cnmv, sepblac..."
              value={fuente}
              onChange={(e) => setFuente(e.target.value)}
              className="w-full rounded-md border border-stone-200 bg-stone-50 px-2.5 py-1.5 text-sm focus:border-stone-400 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-stone-500">Estado</label>
            <input
              type="text"
              placeholder="nuevo, resuelto..."
              value={estado}
              onChange={(e) => setEstado(e.target.value)}
              className="w-full rounded-md border border-stone-200 bg-stone-50 px-2.5 py-1.5 text-sm focus:border-stone-400 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-stone-500">Prioridad</label>
            <input
              type="text"
              placeholder="alta, media, baja"
              value={prioridad}
              onChange={(e) => setPrioridad(e.target.value)}
              className="w-full rounded-md border border-stone-200 bg-stone-50 px-2.5 py-1.5 text-sm focus:border-stone-400 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-stone-500">Obligacion</label>
            <input
              type="text"
              placeholder="codigo..."
              value={obligacion}
              onChange={(e) => setObligacion(e.target.value)}
              className="w-full rounded-md border border-stone-200 bg-stone-50 px-2.5 py-1.5 text-sm focus:border-stone-400 focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Results */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-stone-300 border-t-stone-600" />
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-700">Error: {error}</p>
          <p className="mt-1 text-xs text-red-500">
            Verifica que la API este corriendo en {API_URL}
          </p>
        </div>
      )}

      {!loading && !error && cambios.length === 0 && (
        <div className="rounded-lg border border-stone-200 bg-white p-12 text-center">
          <p className="text-sm text-stone-500">Sin resultados para los filtros aplicados</p>
        </div>
      )}

      {!loading && !error && cambios.length > 0 && (
        <div className="space-y-3">
          {cambios.map((c) => (
            <div
              key={c.codigo}
              className="rounded-lg border border-stone-200 bg-white p-5 transition-colors hover:border-stone-300"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-mono text-sm font-medium text-stone-900">
                      {c.codigo}
                    </span>
                    <span className={`rounded-full border px-2 py-0.5 text-xs ${ESTADO_BADGE[c.estado]?.color || "bg-stone-50 text-stone-600 border-stone-200"}`}>
                      {ESTADO_BADGE[c.estado]?.icon}
                      <span className="ml-1">{c.estado}</span>
                    </span>
                    <span className={`flex items-center gap-1 text-xs ${PRIORIDAD_ICON[c.prioridad]?.color || "text-stone-500"}`}>
                      {PRIORIDAD_ICON[c.prioridad]?.icon}
                      {c.prioridad}
                    </span>
                    <span className="rounded-md bg-stone-100 px-2 py-0.5 text-xs text-stone-600">
                      {c.fuente}
                    </span>
                  </div>
                  <p className="text-sm text-stone-700">{c.impacto}</p>
                  <p className="mt-2 text-xs text-stone-500">
                    <span className="font-medium text-stone-600">Accion:</span> {c.accion_recomendada}
                  </p>
                  <div className="mt-2 flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-stone-400">{c.fecha_detectado}</span>
                    {c.obligaciones_afectadas.length > 0 && (
                      <>
                        <span className="text-xs text-stone-300">|</span>
                        <div className="flex gap-1 flex-wrap">
                          {c.obligaciones_afectadas.map((o) => (
                            <span
                              key={o}
                              className="rounded bg-stone-50 border border-stone-200 px-1.5 py-0.5 text-xs font-mono text-stone-600"
                            >
                              {o}
                            </span>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function CambiosPage() {
  return (
    <Suspense>
      <CambiosContent />
    </Suspense>
  );
}
