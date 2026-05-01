import { NextRequest } from "next/server";

import { proxyApiGet } from "@/lib/api-proxy";

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  return proxyApiGet("/v1/consulta", url.searchParams);
}
