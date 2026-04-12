import Link from "next/link";
import SearchBox from "@/components/search-box";
import Coverage from "@/components/coverage";
import OperationalStatus from "@/components/operational-status";

export const dynamic = "force-dynamic";

export default function Home() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-16">
      {/* Brand */}
      <h1 className="mb-8 text-2xl font-semibold tracking-tight text-stone-900">
        <Link href="/" className="hover:underline">esdata</Link>
      </h1>

      <section className="mb-10 max-w-3xl">
        <h2 className="font-serif text-3xl leading-tight text-stone-900 sm:text-4xl">
          Encuentra criterio fiscal aplicable, no solo texto legal.
        </h2>
        <p className="mt-3 text-base leading-relaxed text-stone-600 sm:text-lg">
          Consulta legislacion vigente y doctrina DGT o TEAC enlazada con articulos concretos para entender que aplica realmente.
        </p>
      </section>

      {/* Search */}
      <SearchBox />

      {/* Coverage + Status */}
      <Coverage />
      <OperationalStatus />
    </div>
  );
}
