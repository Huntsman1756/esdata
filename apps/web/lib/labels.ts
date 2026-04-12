export function formatDocumentType(value: string): string {
  const known: Record<string, string> = {
    resolucion_teac: "Resolución TEAC",
    consulta_vinculante: "Consulta vinculante",
    resolucion_dgt: "Resolución DGT",
    sentencia: "Sentencia",
    auto: "Auto",
    providencia: "Providencia",
  };

  return known[value] ?? value.replaceAll("_", " ");
}

export function formatLinkMethod(value: string): string {
  const known: Record<string, string> = {
    auto_link: "Auto-link",
  };

  return known[value] ?? value.replaceAll("_", " ");
}
