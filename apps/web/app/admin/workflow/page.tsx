"use client";

import { useState, useEffect, Suspense } from "react";
import {
  CheckCircle2,
  Circle,
  Clock,
  AlertCircle,
  FileText,
  User,
  Calendar,
  ClipboardList,
} from "lucide-react";

type WorkflowCase = {
  workflow_id: string;
  cambio_codigo: string;
  obligacion_codigo: string;
  estado: string;
  owner_rol: string;
  fecha_objetivo: string | null;
  evidencia_requerida: string[] | string;
  checklist: string[] | string;
  resultado_revision: string | null;
  notas: string | null;
  accion_recomendada_confirmada: string[] | string;
};

const ESTADO_BADGE: Record<string, { icon: React.ReactNode; color: string }> = {
  abierto: { icon: <Circle className="h-4 w-4" />, color: "bg-stone-50 text-stone-600 border-stone-200" },
  en_progreso: { icon: <Clock className="h-4 w-4" />, color: "bg-blue-50 text-blue-700 border-blue-200" },
  en_revision: { icon: <AlertCircle className="h-4 w-4" />, color: "bg-amber-50 text-amber-700 border-amber-200" },
  completado: { icon: <CheckCircle2 className="h-4 w-4" />, color: "bg-green-50 text-green-700 border-green-200" },
  rechazado: { icon: <AlertCircle className="h-4 w-4" />, color: "bg-red-50 text-red-700 border-red-200" },
};

function parseList(value: string | string[] | undefined): string[] {
  if (Array.isArray(value)) return value;
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [value];
    } catch {
      return [value];
    }
  }
  return [];
}

function WorkflowContent() {
  const [cases, setCases] = useState<WorkflowCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchCases() {
      try {
        setLoading(true);
        const res = await fetch("/api/workflow");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setCases(await res.json());
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error desconocido");
      } finally {
        setLoading(false);
      }
    }
    fetchCases();
  }, []);

  const estados = cases.map((c) => c.estado);
  const conteo: Record<string, number> = {};
  for (const e of estados) conteo[e] = (conteo[e] || 0) + 1;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      {/* Summary */}
      {!loading && !error && cases.length > 0 && (
        <div className="mb-6 flex gap-2 flex-wrap">
          {Object.entries(conteo).map(([estado, count]) => (
            <span
              key={estado}
              className="rounded-full border px-3 py-1 text-xs flex items-center gap-1.5"
            >
              {ESTADO_BADGE[estado]?.icon || <Circle className="h-3 w-3" />}
              <span className="font-medium">{estado}</span>
              <span className="text-stone-400">{count}</span>
            </span>
          ))}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-stone-300 border-t-stone-600" />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-700">Error: {error}</p>
          <p className="mt-1 text-xs text-red-500">
            Verifica que la API este corriendo en {API_URL}
          </p>
        </div>
      )}

      {!loading && !error && cases.length === 0 && (
        <div className="rounded-lg border border-stone-200 bg-white p-12 text-center">
          <ClipboardList className="mx-auto h-8 w-8 text-stone-300 mb-2" />
          <p className="text-sm text-stone-500">No hay casos de workflow registrados</p>
        </div>
      )}

      {/* Cases */}
      {!loading && !error && cases.length > 0 && (
        <div className="space-y-4">
          {cases.map((c) => (
            <div
              key={c.workflow_id}
              className="rounded-lg border border-stone-200 bg-white overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between border-b border-stone-100 px-5 py-3 bg-stone-50">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm font-medium text-stone-900">
                    {c.workflow_id}
                  </span>
                  <span className={`rounded-full border px-2 py-0.5 text-xs flex items-center gap-1 ${ESTADO_BADGE[c.estado]?.color || "bg-stone-50 text-stone-600 border-stone-200"}`}>
                    {ESTADO_BADGE[c.estado]?.icon}
                    {c.estado}
                  </span>
                </div>
                <span className="text-xs text-stone-400 font-mono">{c.cambio_codigo}</span>
              </div>

              {/* Body */}
              <div className="p-5">
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="flex items-start gap-2">
                    <FileText className="h-4 w-4 text-stone-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-xs text-stone-400">Cambio</p>
                      <p className="text-sm font-mono text-stone-700">{c.cambio_codigo}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <FileText className="h-4 w-4 text-stone-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-xs text-stone-400">Obligacion</p>
                      <p className="text-sm font-mono text-stone-700">{c.obligacion_codigo}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <User className="h-4 w-4 text-stone-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-xs text-stone-400">Owner</p>
                      <p className="text-sm text-stone-700">{c.owner_rol}</p>
                    </div>
                  </div>
                  {c.fecha_objetivo && (
                    <div className="flex items-start gap-2">
                      <Calendar className="h-4 w-4 text-stone-400 mt-0.5 shrink-0" />
                      <div>
                        <p className="text-xs text-stone-400">Fecha objetivo</p>
                        <p className="text-sm text-stone-700">{c.fecha_objetivo}</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Checklist */}
                {parseList(c.checklist).length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-medium text-stone-500 mb-1.5">Checklist</p>
                    <div className="space-y-1">
                      {parseList(c.checklist).map((item, i) => (
                        <label key={i} className="flex items-center gap-2 text-sm text-stone-600">
                          <input type="checkbox" disabled className="rounded border-stone-300" />
                          <span className="line-clamp-1">{item}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                {/* Acciones recomendadas */}
                {parseList(c.accion_recomendada_confirmada).length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-medium text-stone-500 mb-1.5">Acciones recomendadas</p>
                    <div className="space-y-1">
                      {parseList(c.accion_recomendada_confirmada).map((item, i) => (
                        <p key={i} className="text-sm text-stone-600">
                          <span className="text-stone-400">&mdash; </span>{item}
                        </p>
                      ))}
                    </div>
                  </div>
                )}

                {/* Notas */}
                {c.notas && (
                  <div className="rounded-md bg-stone-50 border border-stone-100 p-3">
                    <p className="text-xs text-stone-400 mb-1">Notas</p>
                    <p className="text-sm text-stone-700">{c.notas}</p>
                  </div>
                )}

                {/* Resultado revision */}
                {c.resultado_revision && (
                  <div className="rounded-md bg-stone-50 border border-stone-100 p-3 mt-3">
                    <p className="text-xs text-stone-400 mb-1">Resultado revision</p>
                    <p className="text-sm text-stone-700">{c.resultado_revision}</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function WorkflowPage() {
  return (
    <Suspense>
      <WorkflowContent />
    </Suspense>
  );
}
