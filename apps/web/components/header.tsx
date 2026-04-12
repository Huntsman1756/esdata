import Link from "next/link";
import { Search, Scale } from "lucide-react";

interface HeaderProps {
  query?: string;
}

export default function Header({ query }: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 border-b border-stone-200 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-5xl items-center gap-6 px-6 py-4">
        <Link href="/" className="flex items-center gap-2 shrink-0 text-lg font-bold tracking-tight text-stone-900 hover:text-stone-600 transition-colors">
          <Scale aria-hidden="true" className="h-5 w-5 text-stone-700" />
          esdata
        </Link>
        <form action="/buscar" method="GET" className="min-w-0 flex-1 max-w-2xl relative group">
          <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
            <Search aria-hidden="true" className="h-4 w-4 text-stone-400 group-focus-within:text-stone-600 transition-colors" />
          </div>
          <input
            type="text"
            name="q"
            defaultValue={query}
            aria-label="Buscar contenido fiscal"
            autoComplete="off"
            placeholder="Buscar conceptos fiscales, art\u00edculos, doctrina..."
            className="w-full rounded-full border border-stone-300 bg-stone-50 py-2 pl-9 pr-4 text-sm
                       text-stone-900 placeholder:text-stone-400 transition-colors
                       focus-visible:border-stone-500 focus-visible:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-stone-500/20"
          />
        </form>
      </div>
    </header>
  );
}
