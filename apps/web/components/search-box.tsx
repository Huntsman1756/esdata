"use client";

import { useState, type FormEvent } from "react";

const EXAMPLES: { label: string; q: string; tab: string; extra?: Record<string, string> }[] = [
  { label: "deducciones inversi\u00f3n", q: "deducciones inversion", tab: "legislacion", extra: { norma: "LIS" } },
  { label: "entregas inmuebles IVA", q: "entregas inmuebles IVA", tab: "dgt" },
  { label: "prorrata general", q: "prorrata general", tab: "legislacion" },
  { label: "criterio IRPF teletrabajo", q: "teletrabajo IRPF", tab: "teac" },
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
      {/* Tabs + Input */}
      <form onSubmit={onSubmit}>
        <div className="flex gap-1 mb-3">
          {(["legislacion", "dgt", "teac"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors
                ${tab === t
                  ? "bg-stone-900 text-white"
                  : "text-stone-500 hover:bg-stone-200 hover:text-stone-900"
                }`}
            >
              {t === "legislacion" ? "Legislaci\u00f3n" : t}
            </button>
          ))}
        </div>
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar legislaci\u00f3n, doctrina, criterios..."
            className="w-full rounded-md border border-stone-300 bg-white px-4 py-3 text-base
                       text-stone-900 placeholder:text-stone-400 shadow-sm
                       focus:border-stone-500 focus:outline-none focus:ring-1 focus:ring-stone-500"
            autoFocus
          />
        </div>
      </form>

      {/* Examples */}
      <div className="mt-4">
        <p className="text-xs font-medium text-stone-400 uppercase tracking-wide mb-2">
          Ejemplos de b\u00fasqueda
        </p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              onClick={() => go(ex.q, ex.tab, ex.extra)}
              className="rounded-md border border-stone-200 bg-stone-50 px-3 py-1.5
                         text-sm text-stone-600 hover:border-stone-400 hover:text-stone-900
                         transition-colors"
            >
              {ex.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
