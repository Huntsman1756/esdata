import { getCobertura } from "@/lib/api";

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
      <section className="mt-12 border-t border-stone-200 pt-8">
        <h2 className="mb-3 text-sm font-semibold text-stone-500 uppercase tracking-wide">
          Cobertura actual
        </h2>
        <p className="text-sm text-stone-400">No se pudo cargar la informaci\u00f3n de cobertura.</p>
      </section>
    );
  }

  const totalArticulos = cobertura.normas.reduce((s, n) => s + n.articulos, 0);
  const totalVersiones = cobertura.normas.reduce((s, n) => s + n.versiones, 0);

  return (
    <section className="mt-12 border-t border-stone-200 pt-8">
      <h2 className="mb-4 text-sm font-semibold text-stone-500 uppercase tracking-wide">
        Cobertura actual
      </h2>
      <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm sm:grid-cols-4">
        {cobertura.normas.map((n) => (
          <div key={n.codigo} className="flex flex-col">
            <span className="font-mono text-xs text-stone-400">{n.codigo}</span>
            <span className="font-medium text-stone-900">{n.articulos} art\u00edculos</span>
          </div>
        ))}
      </div>
      <p className="mt-4 text-xs text-stone-400">
        {totalArticulos} art\u00edcul
        os \u00b7 {totalVersiones} versiones
      </p>
    </section>
  );
}
