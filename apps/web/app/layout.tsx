import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "esdata — Buscador fiscal",
  description:
    "Motor fiscal para encontrar criterio aplicable rapido. Legislacion, doctrina DGT y TEAC enlazadas en un solo lugar.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className="font-sans">{children}</body>
    </html>
  );
}
