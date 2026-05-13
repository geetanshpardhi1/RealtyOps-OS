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
            <li>API health: <code>/health</code></li>
            <li>Worker health: <code>/health</code> (worker service)</li>
            <li>Evidence: <code>/evidence/reliability-evidence.json</code> in repo</li>
          </ul>
        </>
      )}
    </main>
  );
}
