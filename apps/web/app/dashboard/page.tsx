"use client";

import { SignInButton, SignOutButton, useUser } from "@clerk/nextjs";
import { useEffect, useMemo, useState } from "react";

type HealthState = {
  ok: boolean;
  status: string;
};

type LeadInboxItem = {
  lead_id: string;
  status: string;
  qualification_state: string;
  owner_agent_id: string | null;
  updated_at: string | null;
  last_activity_at: string | null;
};

type LeadInboxResponse = {
  items: LeadInboxItem[];
  count: number;
};

type LeadTimelineResponse = {
  lead_id: string;
  items: Array<Record<string, unknown>>;
  count: number;
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

  const [statusFilter, setStatusFilter] = useState("");
  const [qualificationFilter, setQualificationFilter] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("");
  const [inboxLoading, setInboxLoading] = useState(false);
  const [inbox, setInbox] = useState<LeadInboxResponse>({ items: [], count: 0 });
  const [selectedLeadId, setSelectedLeadId] = useState<string>("");
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timeline, setTimeline] = useState<LeadTimelineResponse>({ lead_id: "", items: [], count: 0 });

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

  useEffect(() => {
    let mounted = true;

    async function loadInbox() {
      if (!allowed) return;
      setInboxLoading(true);
      try {
        const params = new URLSearchParams();
        if (statusFilter) params.set("status", statusFilter);
        if (qualificationFilter) params.set("qualification_state", qualificationFilter);
        if (ownerFilter) params.set("owner_agent_id", ownerFilter);
        const query = params.toString();
        const res = await fetch(`/api/leads${query ? `?${query}` : ""}`, { cache: "no-store" });
        const json = (await res.json()) as LeadInboxResponse;
        if (!mounted) return;
        const items = Array.isArray(json.items) ? json.items : [];
        setInbox({ items, count: typeof json.count === "number" ? json.count : items.length });
        if (!selectedLeadId && items.length > 0) {
          setSelectedLeadId(items[0].lead_id);
        } else if (selectedLeadId && !items.some((item) => item.lead_id === selectedLeadId)) {
          setSelectedLeadId(items[0]?.lead_id ?? "");
        }
      } finally {
        if (mounted) setInboxLoading(false);
      }
    }

    loadInbox();
    return () => {
      mounted = false;
    };
  }, [allowed, ownerFilter, qualificationFilter, selectedLeadId, statusFilter]);

  useEffect(() => {
    let mounted = true;
    async function loadTimeline() {
      if (!allowed || !selectedLeadId) {
        if (mounted) setTimeline({ lead_id: "", items: [], count: 0 });
        return;
      }
      setTimelineLoading(true);
      try {
        const res = await fetch(`/api/leads/${selectedLeadId}/timeline?limit=50`, { cache: "no-store" });
        const json = (await res.json()) as LeadTimelineResponse;
        if (!mounted) return;
        setTimeline({
          lead_id: typeof json.lead_id === "string" ? json.lead_id : selectedLeadId,
          items: Array.isArray(json.items) ? json.items : [],
          count: typeof json.count === "number" ? json.count : 0,
        });
      } finally {
        if (mounted) setTimelineLoading(false);
      }
    }

    loadTimeline();
    return () => {
      mounted = false;
    };
  }, [allowed, selectedLeadId]);

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
    <main className="dashboard-shell">
      <header className="dashboard-head">
        <div>
          <h1>Dashboard</h1>
          <p>User: {user?.id}</p>
          <p>Role: {role}</p>
        </div>
        <SignOutButton redirectUrl="/">
          <button>Log out</button>
        </SignOutButton>
      </header>

      {!allowed ? (
        <section className="dashboard-card">
          <p>Access denied. Ask admin to assign role `brokerage_agent`, `operations`, or `admin`.</p>
          <p>After role update, sign out and sign in again.</p>
        </section>
      ) : (
        <>
          <section className="dashboard-card">
            <p>Access granted.</p>
            <ul>
              <HealthRow label="API health" baseUrl={apiBaseUrl} state={apiHealth} />
              <HealthRow label="Worker health" baseUrl={workerBaseUrl} state={workerHealth} />
              <li>
                Evidence: <code>/evidence/reliability-evidence.json</code> in repo
              </li>
            </ul>
          </section>

          <section className="dashboard-card">
            <h2>Lead Inbox</h2>
            <div className="filter-row">
              <label>
                Status
                <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                  <option value="">all</option>
                  <option value="new">new</option>
                  <option value="qualifying">qualifying</option>
                  <option value="assigned">assigned</option>
                  <option value="booked">booked</option>
                  <option value="closed">closed</option>
                </select>
              </label>
              <label>
                Qualification
                <select value={qualificationFilter} onChange={(e) => setQualificationFilter(e.target.value)}>
                  <option value="">all</option>
                  <option value="unqualified">unqualified</option>
                  <option value="partially_qualified">partially_qualified</option>
                  <option value="fully_qualified">fully_qualified</option>
                </select>
              </label>
              <label>
                Owner
                <input
                  value={ownerFilter}
                  onChange={(e) => setOwnerFilter(e.target.value)}
                  placeholder="agent_001"
                />
              </label>
            </div>

            <div className="inbox-layout">
              <div className="lead-table-wrap">
                <p>{inboxLoading ? "Loading leads..." : `${inbox.count} lead(s)`}</p>
                <table className="lead-table">
                  <thead>
                    <tr>
                      <th>Lead</th>
                      <th>Status</th>
                      <th>Qualification</th>
                      <th>Owner</th>
                      <th>Updated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {inbox.items.map((lead) => (
                      <tr
                        key={lead.lead_id}
                        onClick={() => setSelectedLeadId(lead.lead_id)}
                        className={lead.lead_id === selectedLeadId ? "selected" : ""}
                      >
                        <td>{lead.lead_id}</td>
                        <td>{lead.status}</td>
                        <td>{lead.qualification_state}</td>
                        <td>{lead.owner_agent_id || "-"}</td>
                        <td>{lead.updated_at || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <aside className="timeline-panel">
                <h3>Lead Timeline</h3>
                {!selectedLeadId ? <p>Select a lead.</p> : null}
                {timelineLoading ? <p>Loading timeline...</p> : null}
                {!timelineLoading && selectedLeadId ? (
                  <ul className="timeline-list">
                    {timeline.items.length === 0 ? (
                      <li>No events yet.</li>
                    ) : (
                      timeline.items.map((event, idx) => {
                        const eventType = typeof event.event_type === "string" ? event.event_type : "event";
                        const occurredAt = typeof event.occurred_at === "string" ? event.occurred_at : "-";
                        const eventId = typeof event.event_id === "string" ? event.event_id : `event_${idx}`;
                        return (
                          <li key={eventId}>
                            <p>
                              <strong>{eventType}</strong>
                            </p>
                            <p>{occurredAt}</p>
                          </li>
                        );
                      })
                    )}
                  </ul>
                ) : null}
              </aside>
            </div>
          </section>
        </>
      )}
    </main>
  );
}
