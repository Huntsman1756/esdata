import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "esdata — Admin",
  description: "Interfaz interna de gestion de cambios regulatorios y workflow de compliance.",
};

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-stone-100">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <Link href="/" className="text-sm font-serif text-stone-400 hover:text-stone-600">
                &larr; esdata
              </Link>
              <h1 className="mt-1 text-xl font-serif font-medium text-stone-900">
                Admin
              </h1>
            </div>
            <nav className="flex gap-1">
              <Link
                href="/admin/cambios"
                className="rounded-md px-3 py-1.5 text-sm text-stone-600 hover:bg-stone-100 hover:text-stone-900"
              >
                Cambios
              </Link>
              <Link
                href="/admin/workflow"
                className="rounded-md px-3 py-1.5 text-sm text-stone-600 hover:bg-stone-100 hover:text-stone-900"
              >
                Workflow
              </Link>
            </nav>
          </div>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}
