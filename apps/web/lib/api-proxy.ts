import { NextResponse } from "next/server";

import { fetchApiRaw } from "./api";

function buildPath(path: string, searchParams?: URLSearchParams): string {
  const query = searchParams?.toString();
  return query ? `${path}?${query}` : path;
}

export async function proxyApiGet(path: string, searchParams?: URLSearchParams) {
  try {
    const upstream = await fetchApiRaw(buildPath(path, searchParams), {
      cache: "no-store",
    });
    const body = await upstream.text();

    return new NextResponse(body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") || "application/json",
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "API error",
      },
      { status: 502 }
    );
  }
}
