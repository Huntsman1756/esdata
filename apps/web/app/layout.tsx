import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "esdata — Criterio fiscal enlazado con norma vigente",
  description:
    "Encuentra norma vigente y criterio DGT o TEAC enlazado con articulos concretos en un solo lugar.",
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
