import { getCobertura } from "@/lib/api";
import { Database, FileCode2 } from "lucide-react";

export default async function Coverage() {
  let cobertura: Awaited<ReturnType<typeof getCobertura>> | null = null;
  let error: string | null = null;

  try {
    cobertura = await getCobertura();
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  if (error || !cobertura) {
    return (
      <section className="flex-1 rounded-xl border border-stone-200 bg-white p-5 shadow-sm h-full flex flex-col">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-stone-900 border-b border-stone-100 pb-3">
          <Database aria-hidden="true" className="h-4 w-4 text-stone-500" />
          Cobertura actual
        </h2>
        <p className="text-sm text-stone-500 bg-stone-50 rounded-lg p-3 border border-stone-100 flex-1">
          No se pudo cargar la informaci\u00f3n de cobertura.
        </p>
      </section>
    );
  }

  const totalArticulos = cobertura.normas.reduce((s, n) => s + n.articulos, 0);
  const totalVersiones = cobertura.normas.reduce((s, n) => s + n.versiones, 0);

  return (
    <section className="flex-1 rounded-xl border border-stone-200 bg-white p-5 shadow-sm h-full flex flex-col">
      <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-stone-900 border-b border-stone-100 pb-3">
        <Database aria-hidden="true" className="h-4 w-4 text-stone-500" />
        Cobertura legal indexada
      </h2>
      <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4 mb-4 flex-1">
        {cobertura.normas.map((n) => (
          <div key={n.codigo} className="flex flex-col gap-1 rounded-lg bg-stone-50 p-3 border border-stone-100">
            <span className="font-mono text-xs font-semibold text-stone-500">{n.codigo}</span>
            <span className="font-medium text-stone-900">{n.articulos} art.</span>
          </div>
        ))}
      </div>
      <div className="flex items-center justify-between text-xs text-stone-500 bg-stone-50/50 rounded-md p-2 mt-auto">
        <div className="flex items-center gap-1.5">
          <FileCode2 aria-hidden="true" className="h-3.5 w-3.5" />
          <span>{totalArticulos} art\u00edculos</span>
        </div>
        <span>{totalVersiones} versiones</span>
      </div>
    </section>
  );
}
