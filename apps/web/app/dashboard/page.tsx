"use client";

import { SignInButton, SignOutButton, useUser } from "@clerk/nextjs";
import { useEffect, useMemo, useState } from "react";

type HealthState = {
  ok: boolean;
  status: string;
};

function HealthRow({
  label,
  baseUrl,
  state,
}: {
  label: string;
  baseUrl: string;
  state: HealthState;
}) {
  const normalizedBase = baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
  return (
    <li>
      {label}: <code>{normalizedBase}/health</code> ({state.status})
    </li>
  );
}

export default function DashboardPage() {
  const { isLoaded, isSignedIn, user } = useUser();
  const [apiHealth, setApiHealth] = useState<HealthState>({ ok: false, status: "loading" });
  const [workerHealth, setWorkerHealth] = useState<HealthState>({
    ok: false,
    status: "loading",
  });

  const role = useMemo(() => {
    const value = user?.publicMetadata?.role;
    return typeof value === "string" ? value : "guest";
  }, [user]);
  const allowed = role === "admin" || role === "brokerage_agent" || role === "operations";

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const workerBaseUrl = process.env.NEXT_PUBLIC_WORKER_BASE_URL ?? "http://localhost:8001";

  useEffect(() => {
    let mounted = true;

    async function loadHealth() {
      async function fetchHealth(target: "api" | "worker"): Promise<HealthState> {
        try {
          const res = await fetch(`/api/health?target=${target}`, { cache: "no-store" });
          if (!res.ok) return { ok: false, status: `http_${res.status}` };
          const json = (await res.json()) as { ok: boolean; status: string };
          return { ok: json.ok, status: json.status };
        } catch {
          return { ok: false, status: "unreachable" };
        }
      }

      const [api, worker] = await Promise.all([fetchHealth("api"), fetchHealth("worker")]);
      if (!mounted) return;
      setApiHealth(api);
      setWorkerHealth(worker);
    }

    loadHealth();
    return () => {
      mounted = false;
    };
  }, []);

  if (!isLoaded) {
    return (
      <main className="container">
        <h1>Dashboard</h1>
        <p>Loading...</p>
      </main>
    );
  }

  if (!isSignedIn) {
    return (
      <main className="container">
        <h1>Dashboard</h1>
        <p>You are signed out.</p>
        <SignInButton mode="modal">
          <button>Sign In</button>
        </SignInButton>
      </main>
    );
  }

  return (
    <main className="container">
      <h1>Dashboard</h1>
      <p>User: {user?.id}</p>
      <p>Role: {role}</p>
      {!allowed ? (
        <>
          <p>Access denied. Ask admin to assign role `brokerage_agent`, `operations`, or `admin`.</p>
          <p>After role update, sign out and sign in again.</p>
          <SignOutButton redirectUrl="/">
            <button>Log out</button>
          </SignOutButton>
        </>
      ) : (
        <>
          <p>Access granted.</p>
          <ul>
            <HealthRow label="API health" baseUrl={apiBaseUrl} state={apiHealth} />
            <HealthRow label="Worker health" baseUrl={workerBaseUrl} state={workerHealth} />
            <li>
              Evidence: <code>/evidence/reliability-evidence.json</code> in repo
            </li>
          </ul>
          {!apiHealth.ok || !workerHealth.ok ? (
            <p>Warning: one or more backend services are unreachable from web runtime.</p>
          ) : null}
        </>
      )}
    </main>
  );
}
