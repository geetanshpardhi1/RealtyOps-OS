import { NextRequest, NextResponse } from "next/server";

function trimTrailingSlash(url: string): string {
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

type RouteContext = {
  params: {
    leadId: string;
  };
};

export async function GET(req: NextRequest, context: RouteContext) {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const leadId = context.params.leadId;
  const url = new URL(`${trimTrailingSlash(apiBase)}/leads/${leadId}/timeline`);

  const limit = req.nextUrl.searchParams.get("limit");
  if (limit) url.searchParams.set("limit", limit);

  try {
    const response = await fetch(url.toString(), { cache: "no-store" });
    if (!response.ok) {
      return NextResponse.json({ lead_id: leadId, items: [], count: 0, error: `http_${response.status}` }, { status: 200 });
    }
    const json = (await response.json()) as Record<string, unknown>;
    return NextResponse.json(json, { status: 200 });
  } catch {
    return NextResponse.json({ lead_id: leadId, items: [], count: 0, error: "unreachable" }, { status: 200 });
  }
}
