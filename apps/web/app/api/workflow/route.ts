import { proxyApiGet } from "@/lib/api-proxy";

export async function GET() {
  return proxyApiGet("/v1/compliance/workflow");
}
