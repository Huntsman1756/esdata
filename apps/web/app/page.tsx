import Link from "next/link";
import SearchBox from "@/components/search-box";
import Coverage from "@/components/coverage";
import OperationalStatus from "@/components/operational-status";
import { Scale, CheckCircle2, Briefcase, Target } from "lucide-react";

export const dynamic = "force-dynamic";

export default function Home() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-16">
      {/* Brand */}
      <h1 className="mb-10 flex items-center gap-2 text-2xl font-bold tracking-tight text-stone-900">
        <Scale aria-hidden="true" className="h-6 w-6 text-stone-700" />
        <Link href="/" className="hover:text-stone-600 transition-colors">esdata</Link>
      </h1>

      <section className="mb-12 max-w-3xl">
        <h2 className="font-serif text-4xl leading-tight text-stone-900 sm:text-5xl tracking-tight">
          Encuentra criterio fiscal trazable, no solo texto legal.
        </h2>
        <p className="mt-4 text-lg leading-relaxed text-stone-600 sm:text-xl">
          Consulta norma vigente, doctrina DGT y TEAC enlazada con art\u00edculos concretos y modelos AEAT relacionados para entender qu\u00e9 aplica, por qu\u00e9 aplica y con qu\u00e9 fundamento oficial.
        </p>
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-stone-100">
              <CheckCircle2 aria-hidden="true" className="h-5 w-5 text-stone-700" />
            </div>
            <p className="font-semibold text-stone-900">Fundamento verificable</p>
            <p className="mt-2 text-sm text-stone-600 leading-relaxed">Cada enlace \u00fatil debe poder remontarse a norma, doctrina o fuente oficial.</p>
          </div>
          <div className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-stone-100">
              <Briefcase aria-hidden="true" className="h-5 w-5 text-stone-700" />
            </div>
            <p className="font-semibold text-stone-900">Pensado para trabajo real</p>
            <p className="mt-2 text-sm text-stone-600 leading-relaxed">\u00datil para despacho, producto o agente que necesita criterio aplicable y trazabilidad.</p>
          </div>
          <div className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-stone-100">
              <Target aria-hidden="true" className="h-5 w-5 text-stone-700" />
            </div>
            <p className="font-semibold text-stone-900">Cobertura con foco</p>
            <p className="mt-2 text-sm text-stone-600 leading-relaxed">Hoy cubre LGT, LIRPF, LIS, LIVA, ITPAJD, IRNR, IIEE, HL y la capa DAC6 de España/UE. No promete m\u00e1s de lo que ya est\u00e1 verificado.</p>
          </div>
        </div>
        <p className="mt-6 text-sm leading-relaxed text-stone-500 bg-stone-100/50 p-4 rounded-lg border border-stone-100">
          <span className="font-medium text-stone-700">Nota sobre cobertura:</span> En una herramienta de gesti\u00f3n fiscal tambi\u00e9n importan capas como UNE 19602, PLACE, BORME o BDNS. Son relevantes para la evoluci\u00f3n del producto, pero no forman parte de la cobertura actual.
        </p>
        <p className="mt-1 text-sm leading-relaxed text-stone-600 sm:text-base">
          Hoy muestra soporte para LGT, LIRPF, LIS, LIVA, ITPAJD, IRNR, IIEE, HL, `DAC6`, `DAC6RD` y `DAC6EU`. La verificaci\u00f3n desplegada de estas incorporaciones depende del siguiente ciclo de ingesta y despliegue.
        </p>
        <p className="mt-2 text-sm leading-relaxed text-stone-500 sm:text-base">
          Lo siguiente sigue en cola por separado: UNE 19602, PLACE, BORME y BDNS.
        </p>
      </section>

      {/* Search */}
      <div className="mb-12 rounded-2xl bg-white p-6 sm:p-8 shadow-sm border border-stone-200">
        <SearchBox />
      </div>

      {/* Coverage + Status */}
      <div className="flex flex-col gap-6 sm:flex-row sm:items-stretch sm:justify-between">
        <div className="w-full sm:w-2/3">
          <Coverage />
        </div>
        <div className="w-full sm:w-1/3 flex sm:justify-end">
          <OperationalStatus />
        </div>
      </div>
    </div>
  );
}
