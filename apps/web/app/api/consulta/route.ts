import { NextRequest } from "next/server";

import { proxyApiGet } from "@/lib/api-proxy";

// Server-side proxy: forwards to FastAPI with ESDATA_API_KEY via buildApiHeaders().
// The client component (consulta-client.tsx) calls this route, not the backend directly,
// so the API key is always attached server-side. No auth bypass.

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  return proxyApiGet("/v1/consulta", url.searchParams);
}
