import { NextRequest, NextResponse } from "next/server";

function trimTrailingSlash(url: string): string {
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

export async function GET(req: NextRequest) {
  const target = req.nextUrl.searchParams.get("target");
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const workerBase = process.env.NEXT_PUBLIC_WORKER_BASE_URL ?? "http://localhost:8001";

  const baseUrl = target === "worker" ? workerBase : apiBase;
  const url = `${trimTrailingSlash(baseUrl)}/health`;

  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      return NextResponse.json({ ok: false, status: `http_${response.status}` }, { status: 200 });
    }
    const json = (await response.json()) as Record<string, unknown>;
    const status = typeof json.status === "string" ? json.status : "unknown";
    return NextResponse.json({ ok: status === "ok", status }, { status: 200 });
  } catch {
    return NextResponse.json({ ok: false, status: "unreachable" }, { status: 200 });
  }
}
