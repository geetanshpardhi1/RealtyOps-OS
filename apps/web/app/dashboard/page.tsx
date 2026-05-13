import { auth } from "@clerk/nextjs/server";
import { clerkClient } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { SignOutButton } from "@clerk/nextjs";

function getRole(sessionClaims: Record<string, unknown> | null | undefined): string {
  if (!sessionClaims) return "guest";
  const metadata = sessionClaims["metadata"] as Record<string, unknown> | undefined;
  const publicMetadata =
    sessionClaims["public_metadata"] as Record<string, unknown> | undefined;
  const role = metadata?.["role"] ?? publicMetadata?.["role"];
  return typeof role === "string" ? role : "guest";
}

type HealthState = {
  ok: boolean;
  status: string;
};

function trimTrailingSlash(url: string): string {
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

async function fetchHealth(baseUrl: string): Promise<HealthState> {
  const url = `${trimTrailingSlash(baseUrl)}/health`;
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      return { ok: false, status: `http_${response.status}` };
    }
    const json = (await response.json()) as Record<string, unknown>;
    const status = typeof json.status === "string" ? json.status : "unknown";
    return { ok: status === "ok", status };
  } catch {
    return { ok: false, status: "unreachable" };
  }
}

export default async function DashboardPage() {
  const { userId, sessionClaims } = await auth();
  if (!userId) redirect("/");

  const client = await clerkClient();
  const user = await client.users.getUser(userId);
  const roleFromUser = user.publicMetadata?.role;
  const roleFromClaims = getRole(sessionClaims as Record<string, unknown> | undefined);
  const role =
    typeof roleFromUser === "string" && roleFromUser.length > 0
      ? roleFromUser
      : roleFromClaims;
  const allowed = role === "admin" || role === "brokerage_agent" || role === "operations";
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const workerBaseUrl = process.env.NEXT_PUBLIC_WORKER_BASE_URL ?? "http://localhost:8001";
  const [apiHealth, workerHealth] = await Promise.all([
    fetchHealth(apiBaseUrl),
    fetchHealth(workerBaseUrl),
  ]);

  return (
    <main className="container">
      <h1>Dashboard</h1>
      <p>User: {userId}</p>
      <p>Role: {role}</p>
      {!allowed ? (
        <>
          <p>Access denied. Ask admin to assign role `brokerage_agent`, `operations`, or `admin`.</p>
          <p>After role update, sign out and sign in again to refresh session claims.</p>
          <SignOutButton redirectUrl="/">
            <button>Log out</button>
          </SignOutButton>
        </>
      ) : (
        <>
          <p>Access granted.</p>
          <ul>
            <li>
              API health:{" "}
              <code>{trimTrailingSlash(apiBaseUrl)}/health</code> ({apiHealth.status})
            </li>
            <li>
              Worker health:{" "}
              <code>{trimTrailingSlash(workerBaseUrl)}/health</code> ({workerHealth.status})
            </li>
            <li>Evidence: <code>/evidence/reliability-evidence.json</code> in repo</li>
          </ul>
          {!apiHealth.ok || !workerHealth.ok ? (
            <p>Warning: one or more backend services are unreachable from the web app runtime.</p>
          ) : null}
        </>
      )}
    </main>
  );
}
