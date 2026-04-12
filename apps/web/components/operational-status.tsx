import { getStatus } from "@/lib/api";
import { Activity, AlertCircle } from "lucide-react";

export default async function OperationalStatus() {
  let status: Awaited<ReturnType<typeof getStatus>> | null = null;

  try {
    status = await getStatus();
  } catch {
    return (
      <div className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-white p-5 shadow-sm h-full w-full justify-center">
        <AlertCircle aria-hidden="true" className="h-4 w-4 text-stone-400" />
        <span className="text-sm font-medium text-stone-500">Estado no disponible</span>
      </div>
    );
  }

  const apiOk = status.api === "ok";
  const workers = status.workers;
  const lastFinished = Object.values(workers)
    .map((w) => (w as { finished_at?: string | null }).finished_at)
    .filter((v): v is string => typeof v === "string" && v.length > 0)
    .sort()
    .reverse()[0];

  const lastDate = lastFinished
    ? new Date(lastFinished).toLocaleDateString("es-ES", { year: "numeric", month: "short", day: "numeric" })
    : null;

  return (
    <div className={`flex flex-col justify-center rounded-xl border p-5 shadow-sm h-full w-full transition-colors
      ${apiOk ? "border-emerald-100 bg-emerald-50/30" : "border-amber-100 bg-amber-50/30"}`}>
      <div className="flex items-center gap-2 mb-2">
        <div className={`relative flex h-3 w-3 items-center justify-center`}>
          {apiOk && <span aria-hidden="true" className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>}
          <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${apiOk ? "bg-emerald-500" : "bg-amber-500"}`}></span>
        </div>
        <span className={`text-sm font-semibold ${apiOk ? "text-emerald-800" : "text-amber-800"}`}>
          {apiOk ? "Sistema operativo" : "Estado degradado"}
        </span>
      </div>
      {lastDate && (
        <span className="text-xs text-stone-500 flex items-center gap-1.5 bg-white rounded-md p-2 border border-stone-100 w-fit">
          <Activity aria-hidden="true" className="h-3.5 w-3.5 text-stone-400" />
          Actualizado {lastDate}
        </span>
      )}
    </div>
  );
}
