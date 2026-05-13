import { NextRequest, NextResponse } from "next/server";

function trimTrailingSlash(url: string): string {
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

export async function GET(req: NextRequest) {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const url = new URL(`${trimTrailingSlash(apiBase)}/leads`);

  const status = req.nextUrl.searchParams.get("status");
  const qualificationState = req.nextUrl.searchParams.get("qualification_state");
  const ownerAgentId = req.nextUrl.searchParams.get("owner_agent_id");

  if (status) url.searchParams.set("status", status);
  if (qualificationState) url.searchParams.set("qualification_state", qualificationState);
  if (ownerAgentId) url.searchParams.set("owner_agent_id", ownerAgentId);

  try {
    const response = await fetch(url.toString(), { cache: "no-store" });
    if (!response.ok) {
      return NextResponse.json({ items: [], count: 0, error: `http_${response.status}` }, { status: 200 });
    }
    const json = (await response.json()) as Record<string, unknown>;
    return NextResponse.json(json, { status: 200 });
  } catch {
    return NextResponse.json({ items: [], count: 0, error: "unreachable" }, { status: 200 });
  }
}
