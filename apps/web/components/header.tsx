import Link from "next/link";

interface HeaderProps {
  query?: string;
}

export default function Header({ query }: HeaderProps) {
  return (
    <header className="border-b border-stone-200">
      <div className="mx-auto flex max-w-5xl items-center gap-4 px-6 py-4">
        <Link href="/" className="shrink-0 text-lg font-semibold tracking-tight text-stone-900">
          esdata
        </Link>
        <form action="/buscar" method="GET" className="min-w-0 flex-1">
          <input
            type="text"
            name="q"
            defaultValue={query}
            placeholder="Buscar legislaci\u00f3n, doctrina, criterios..."
            className="w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm
                       text-stone-900 placeholder:text-stone-400
                       focus:border-stone-500 focus:outline-none focus:ring-1 focus:ring-stone-500"
          />
        </form>
      </div>
    </header>
  );
}
