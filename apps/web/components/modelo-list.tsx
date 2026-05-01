import { fetchApiRaw, getModelos } from "@/lib/api";
import ModeloBadge from "./modelo-badge";

export default async function ModeloList({
  articuloNorma,
  articuloNumero,
}: {
  articuloNorma: string;
  articuloNumero: string;
}) {
  let modelos: Awaited<ReturnType<typeof getModelos>>["modelos"] = [];

  try {
    const data = await getModelos();
    // Filter models that have this specific article
    const modelDetails = await Promise.all(
      data.modelos.map(async (m) => {
        try {
          const res = await fetchApiRaw(
            `/v1/modelos/${m.codigo}/articulos`,
            { next: { revalidate: 3600 } }
          );
          if (!res.ok) return null;
          const json = await res.json();
          const hasArticle = json.articulos.some(
            (a: { norma: string; numero: string }) =>
              a.norma === articuloNorma && a.numero === articuloNumero
          );
          return hasArticle ? m : null;
        } catch {
          return null;
        }
      })
    );
    modelos = modelDetails.filter(Boolean) as typeof modelos;
  } catch {
    return null;
  }

  if (modelos.length === 0) return null;

  return (
    <section className="mt-4 pt-4 border-t border-stone-100">
      <h3 className="mb-2 text-xs font-semibold text-stone-500 uppercase tracking-wide">
        Modelos AEAT relacionados
      </h3>
      <ul className="space-y-2">
        {modelos.map((m) => (
          <li key={m.codigo}>
            <ModeloBadge
              codigo={m.codigo}
              nombre={m.nombre}
              periodo={m.periodo}
              href={`/modelo/${m.codigo}`}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}
