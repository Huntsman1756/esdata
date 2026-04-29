import { NextResponse } from "next/server";

export async function GET() {
  const target = new URL("/v1/compliance/workflow", process.env.ESDATA_API_BASE_URL || "http://localhost:8000");

  try {
    const res = await fetch(target.toString(), { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json({ error: e.message || "API error" }, { status: 502 });
  }
}
