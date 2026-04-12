"use client";

import { useState, type FormEvent } from "react";
import { Search, Lightbulb, Scale, FileText, Landmark } from "lucide-react";

const EXAMPLES: { label: string; q: string; tab: string; extra?: Record<string, string> }[] = [
  { label: "ganancias patrimoniales acciones", q: "ganancias patrimoniales acciones", tab: "legislacion", extra: { norma: "LIRPF" } },
  { label: "mercado regulado IRPF", q: "mercado regulado", tab: "legislacion", extra: { norma: "LIRPF" } },
  { label: "deducciones inversi\u00f3n LIS", q: "deducciones inversion", tab: "legislacion", extra: { norma: "LIS" } },
  { label: "entregas inmuebles IVA", q: "entregas inmuebles IVA", tab: "dgt" },
  { label: "prorrata LIVA", q: "prorrata", tab: "legislacion", extra: { norma: "LIVA" } },
  { label: "criterio TEAC art. 111 LGT", q: "recargo", tab: "teac" },
];

export default function SearchBox() {
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState<"legislacion" | "dgt" | "teac">("legislacion");

  function go(q: string, t: string, extra?: Record<string, string>) {
    if (!q.trim()) return;
    const params = new URLSearchParams({ q, tab: t });
    if (extra) Object.entries(extra).forEach(([k, v]) => params.set(k, v));
    window.location.href = `/buscar?${params.toString()}`;
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    go(query, tab);
  }

  return (
    <div>
      <noscript>
        <form action="/buscar" method="GET" className="mb-4 flex gap-2">
          <input type="hidden" name="tab" value="legislacion" />
          <label htmlFor="noscript-search" className="sr-only">
            Buscar contenido fiscal
          </label>
          <input
            id="noscript-search"
            type="text"
            name="q"
            placeholder="Conceptos fiscales, art\u00edculos, doctrina..."
            className="w-full rounded-lg border border-stone-300 bg-stone-50 px-4 py-3 text-base text-stone-900 focus:bg-white"
          />
          <button type="submit" className="rounded-lg bg-stone-900 px-5 py-3 text-sm font-medium text-white hover:bg-stone-800 transition-colors">
            Buscar
          </button>
        </form>
      </noscript>

      {/* Tabs + Input */}
      <form onSubmit={onSubmit}>
        <div className="flex flex-wrap gap-2 mb-4">
          {(["legislacion", "dgt", "teac"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium transition-colors
                ${tab === t
                  ? "bg-stone-900 text-white shadow-md ring-1 ring-stone-900"
                  : "bg-stone-100 text-stone-600 hover:bg-stone-200 hover:text-stone-900"
                }`}
            >
              {t === "legislacion" && <Scale aria-hidden="true" className="h-4 w-4" />}
              {t === "dgt" && <FileText aria-hidden="true" className="h-4 w-4" />}
              {t === "teac" && <Landmark aria-hidden="true" className="h-4 w-4" />}
              {t === "legislacion" ? "Legislaci\u00f3n" : t.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="relative group">
          <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
            <Search aria-hidden="true" className="h-5 w-5 text-stone-400 group-focus-within:text-stone-600 transition-colors" />
          </div>
          <input
            type="text"
            name="q"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Buscar contenido fiscal"
            autoComplete="off"
            placeholder="Conceptos fiscales, art\u00edculos, doctrina..."
            className="block w-full rounded-xl border border-stone-300 bg-stone-50 py-4 pl-11 pr-[100px] text-base
                       text-stone-900 placeholder:text-stone-400 shadow-sm transition-colors
                       focus-visible:border-stone-500 focus-visible:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-stone-500/20"
            autoFocus
          />
          <button 
            type="submit" 
            className="absolute inset-y-2 right-2 rounded-lg bg-stone-900 px-6 text-sm font-medium text-white hover:bg-stone-800 transition-colors shadow-sm"
          >
            Buscar
          </button>
        </div>
        <p className="mt-3 flex items-start sm:items-center gap-1.5 text-sm text-stone-500">
          <Lightbulb aria-hidden="true" className="h-4 w-4 text-amber-500 shrink-0 sm:mt-0 mt-0.5" />
          Prueba con conceptos fiscales, art\u00edculos o referencias DGT/TEAC, no con preguntas en lenguaje natural.
        </p>
      </form>

      {/* Examples */}
      <div className="mt-8 border-t border-stone-100 pt-6">
        <p className="text-xs font-semibold text-stone-400 uppercase tracking-wider mb-3">
          B\u00fasquedas sugeridas
        </p>
        <div className="flex flex-wrap gap-2.5">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              onClick={() => go(ex.q, ex.tab, ex.extra)}
              className="rounded-full border border-stone-200 bg-white px-4 py-1.5
                         text-sm font-medium text-stone-600 shadow-sm transition-colors
                         hover:border-stone-400 hover:text-stone-900 hover:shadow"
            >
              {ex.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
