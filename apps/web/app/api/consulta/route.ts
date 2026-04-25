import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const searchParams = url.searchParams;

  const target = new URL("/v1/consulta", process.env.ESDATA_API_BASE_URL || "http://localhost:8000");
  searchParams.forEach((v, k) => target.searchParams.set(k, v));

  try {
    const res = await fetch(target.toString(), { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json({ error: e.message || "API error" }, { status: 502 });
  }
}
