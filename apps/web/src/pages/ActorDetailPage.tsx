/**
 * ActorDetailPage — Shows full detail for a single actor.
 * Loads actor from local chunk data or falls back to API.
 */

import { useState, useEffect } from "react";
import type { FormEvent, ReactNode } from "react";
import { useParams, useNavigate } from "react-router-dom";

interface Actor {
  id: string;
  name: string;
  title: string;
  username: string;
  developer: string;
  url: string;
  description: string;
  categories: string[];
  pricing_model: string;
  total_runs: number;
  total_users: number;
  rating: number | null;
  review_count: number;
  bookmarks: number;
  initials: string;
  route_strategy: string;
  runnable_status: string;
  missing_components: string;
}

interface ActorValueMetrics {
  total_runs: number;
  successful_runs: number;
  failed_or_blocked_runs: number;
  success_rate: number;
  cache_hits: number;
  cache_hit_rate: number;
  estimated_time_saved_seconds: number;
  estimated_cost_saved_usd: number;
  total_items: number;
  average_quality_score: number;
  learning_event_count: number;
  patch_proposal_count: number;
  active_profile_version: string | null;
  fixture_status_counts: Record<string, number>;
  value_signals: {
    avoided_reruns: number;
    quality_improvement_candidates: number;
    accepted_fixtures: number;
  };
}

interface ActorProofRecord {
  proof_level: string;
  live_e2e_passed: boolean;
  fixture_replay_passed: boolean;
  ui_route_passed: boolean;
  items_count: number;
  last_verified_at: string;
  failure_class: string;
  claim_boundary: string;
  persisted: boolean;
}

interface ActorRunPayload {
  run_id?: string;
  status?: string;
  dataset_id?: string;
  result_summary?: Record<string, unknown>;
  status_history?: Array<Record<string, unknown>>;
  logs?: Array<Record<string, unknown>>;
  usage?: Record<string, unknown>;
  output_preview?: unknown;
  runtime_metadata?: Record<string, unknown>;
}

const INITIALS_COLORS = [
  "#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b",
  "#10b981", "#ef4444", "#06b6d4", "#84cc16",
];

function getInitialsColor(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash + id.charCodeAt(i)) | 0;
  }
  return INITIALS_COLORS[Math.abs(hash) % INITIALS_COLORS.length];
}

const STRATEGY_LABELS: Record<string, { color: string; label: string; desc: string }> = {
  native_pipeline:     { color: "#6ee7b7", label: "Native Pipeline", desc: "Runs through our built-in HTTP/Browser scraping chain." },
  yt_dlp:             { color: "#fbbf24", label: "yt-dlp Media", desc: "Uses yt-dlp for media metadata extraction." },
  job_board_schema:   { color: "#93c5fd", label: "Job Board", desc: "Requires Job Board Pydantic schemas for structured output." },
  real_estate_schema: { color: "#c4b5fd", label: "Real Estate", desc: "Requires Real Estate Pydantic schemas for structured output." },
  apify_api:          { color: "#9ca3af", label: "External metadata", desc: "Metadata-only legacy strategy; native execution is not delegated to Apify." },
  unsupported:        { color: "#fca5a5", label: "Unsupported", desc: "Not currently supported." },
};

export function ActorDetailPage() {
  const { actorId } = useParams<{ actorId: string }>();
  const navigate = useNavigate();
  const [actor, setActor] = useState<Actor | null>(null);
  const [valueMetrics, setValueMetrics] = useState<ActorValueMetrics | null>(null);
  const [actorProof, setActorProof] = useState<ActorProofRecord | null>(null);
  const [runTarget, setRunTarget] = useState("");
  const [runBusy, setRunBusy] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<ActorRunPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!actorId) return;

    // Search through chunks for this actor
    async function findActor() {
      setLoading(true);
      setError(null);

      try {
        // Try API first
        const apiResp = await fetch(`/api/v1/actors/${actorId}`);
        if (apiResp.ok) {
          const data = await apiResp.json();
          if (data.success && data.data) {
            const d = data.data;
            setActor({
              id: d.actor_id,
              name: d.name,
              title: d.title,
              username: d.username || "",
              developer: d.developer || d.username || "",
              url: d.url || "",
              description: d.description || "",
              categories: d.categories || [],
              pricing_model: d.pricing_model || "unknown",
              total_runs: d.total_runs || 0,
              total_users: d.total_users || 0,
              rating: d.rating || null,
              review_count: d.review_count || 0,
              bookmarks: d.bookmarks || 0,
              initials: d.initials || "??",
              route_strategy: d.route_strategy,
              runnable_status: d.runnable_status,
              missing_components: d.missing_components || "",
            });
            setLoading(false);
            return;
          }
        }
      } catch {
        // API not available, search chunks
      }

      // Fallback: search local chunks
      try {
        const indexResp = await fetch("/data/actors/index.json");
        const index = await indexResp.json();

        for (let i = 0; i < index.chunk_count; i++) {
          const chunkResp = await fetch(`/data/actors/chunk-${i}.json`);
          const chunk: Actor[] = await chunkResp.json();
          const found = chunk.find((a) => a.id === actorId);
          if (found) {
            setActor(found);
            setLoading(false);
            return;
          }
        }
        setError("Actor not found");
      } catch {
        setError("Failed to load actor data");
      }
      setLoading(false);
    }

    findActor();
  }, [actorId]);

  useEffect(() => {
    if (!actorId) return;
    let cancelled = false;
    async function loadValueMetrics() {
      try {
        const response = await fetch(`/api/v1/actors/${actorId}/value-metrics`, {
          headers: { "X-Tenant-ID": "default" },
        });
        if (!response.ok) return;
        const payload = await response.json();
        if (!cancelled && payload.success && payload.data) {
          setValueMetrics(payload.data);
        }
      } catch {
        if (!cancelled) setValueMetrics(null);
      }
    }
    loadValueMetrics();
    return () => { cancelled = true; };
  }, [actorId]);

  useEffect(() => {
    if (!actorId) return;
    let cancelled = false;
    async function loadActorProof() {
      try {
        const response = await fetch(`/api/v1/actors/${actorId}/proof`, {
          headers: { "X-Tenant-ID": "default" },
        });
        if (!response.ok) return;
        const payload = await response.json();
        if (!cancelled && payload.success && payload.data) {
          setActorProof(payload.data);
        }
      } catch {
        if (!cancelled) setActorProof(null);
      }
    }
    loadActorProof();
    return () => { cancelled = true; };
  }, [actorId]);

  useEffect(() => {
    if (actor && !runTarget) {
      setRunTarget(actor.url || actor.name || actor.id);
    }
  }, [actor, runTarget]);

  async function runActor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!actor) return;
    setRunBusy(true);
    setRunError(null);
    setRunResult(null);

    try {
      const response = await fetch(`/api/v1/actors/${actor.id}/runs`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Tenant-ID": "default",
        },
        body: JSON.stringify({
          input: { target: runTarget || actor.url || actor.name },
          options: { source: "actor_detail_console" },
        }),
      });
      const payload = await response.json();
      if (!response.ok || payload.success === false) {
        throw new Error(payload.error?.message || payload.message || "Actor run failed");
      }
      setRunResult(payload.data || payload);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "Actor run failed");
    } finally {
      setRunBusy(false);
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 40, color: "#94a3b8" }}>Loading actor...</div>
    );
  }

  if (error || !actor) {
    return (
      <div style={{ padding: 40 }}>
        <h2 style={{ color: "#f87171" }}>Actor Not Found</h2>
        <p style={{ color: "#94a3b8" }}>{error || "No actor with this ID"}</p>
        <button
          onClick={() => navigate("/actors")}
          style={{
            marginTop: 16,
            padding: "8px 20px",
            background: "#334155",
            border: "none",
            borderRadius: 8,
            color: "#e2e8f0",
            cursor: "pointer",
          }}
        >
          Back to Catalog
        </button>
      </div>
    );
  }

  const stratInfo = STRATEGY_LABELS[actor.route_strategy] || {
    color: "#9ca3af",
    label: actor.route_strategy,
    desc: "",
  };
  const avatarColor = getInitialsColor(actor.id);

  return (
    <main style={{ padding: "24px 32px", maxWidth: 1080, margin: "0 auto" }}>
      {/* Back */}
      <button
        onClick={() => navigate("/actors")}
        style={{
          background: "none",
          border: "none",
          color: "#64748b",
          cursor: "pointer",
          fontSize: 13,
          padding: 0,
          marginBottom: 20,
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        &larr; Back to Catalog
      </button>

      {/* Title */}
      <div style={{ display: "flex", gap: 16, alignItems: "flex-start", marginBottom: 24 }}>
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: 14,
            background: avatarColor,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 20,
            fontWeight: 700,
            color: "#fff",
            flexShrink: 0,
          }}
        >
          {actor.initials}
        </div>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>
            {actor.title}
          </h1>
          <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0" }}>
            {actor.username ? `${actor.username}/` : ""}{actor.name}
          </p>
        </div>
      </div>

      {/* Info Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          marginBottom: 24,
        }}
      >
        {/* Strategy */}
        <InfoCard label="Route Strategy">
          <span style={{ color: stratInfo.color, fontWeight: 600 }}>
            {stratInfo.label}
          </span>
          <p style={{ fontSize: 12, color: "#94a3b8", margin: "4px 0 0" }}>
            {stratInfo.desc}
          </p>
        </InfoCard>

        {/* Status */}
        <InfoCard label="Runnable Status">
          <span
            style={{
              color:
                actor.runnable_status === "runnable"
                  ? "#6ee7b7"
                  : actor.runnable_status === "blocked"
                    ? "#fca5a5"
                    : "#fbbf24",
              fontWeight: 600,
            }}
          >
            {actor.runnable_status.replace(/_/g, " ")}
          </span>
        </InfoCard>

        <InfoCard label="Proof Status">
          <span
            style={{
              color: actorProof?.live_e2e_passed
                ? "#6ee7b7"
                : actorProof?.fixture_replay_passed || actorProof?.ui_route_passed
                  ? "#93c5fd"
                  : "#fbbf24",
              fontWeight: 600,
            }}
          >
            {formatProofLevel(actorProof?.proof_level || "api_mapped")}
          </span>
          <p style={{ fontSize: 12, color: "#94a3b8", margin: "4px 0 0" }}>
            {actorProof?.claim_boundary === "live_e2e_proven"
              ? `${actorProof.items_count} items verified`
              : "Mapped, not live E2E proven"}
          </p>
        </InfoCard>

        {/* Categories */}
        <InfoCard label="Categories">
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {actor.categories.map((c) => (
              <span
                key={c}
                style={{
                  fontSize: 11,
                  background: "#0f172a",
                  color: "#94a3b8",
                  padding: "3px 8px",
                  borderRadius: 6,
                }}
              >
                {c.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </InfoCard>

        {/* Actor ID */}
        <InfoCard label="Actor ID">
          <code style={{ fontSize: 12, color: "#94a3b8" }}>{actor.id}</code>
        </InfoCard>

        {/* Pricing */}
        <InfoCard label="Pricing Model">
          <span style={{ color: "#e2e8f0" }}>{actor.pricing_model.replace(/_/g, " ")}</span>
        </InfoCard>

        {/* Developer */}
        <InfoCard label="Developer">
          <span style={{ color: "#e2e8f0" }}>{actor.developer || "Unknown"}</span>
        </InfoCard>

        {/* Store Metrics */}
        <InfoCard label="Store Metrics">
          <span style={{ color: "#e2e8f0" }}>
            {actor.rating ? `Rating ${actor.rating.toFixed(1)} (${actor.review_count})` : "No rating"}
          </span>
          <p style={{ fontSize: 12, color: "#94a3b8", margin: "4px 0 0" }}>
            {actor.total_users.toLocaleString()} users / {actor.total_runs.toLocaleString()} runs / {actor.bookmarks.toLocaleString()} bookmarks
          </p>
        </InfoCard>

        {/* Source metadata */}
        {actor.url && (
          <InfoCard label="Apify Source Metadata">
            <a
              href={actor.url}
              target="_blank"
              rel="noreferrer"
              style={{ color: "#93c5fd", fontSize: 12, wordBreak: "break-all" }}
            >
              {actor.url}
            </a>
          </InfoCard>
        )}
      </div>

      {/* Customer Value */}
      <div
        style={{
          background: "#111827",
          border: "1px solid #334155",
          borderRadius: 10,
          padding: 16,
          marginBottom: 24,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 14 }}>
          <div>
            <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>Customer Value</div>
            <div style={{ fontSize: 16, color: "#f8fafc", fontWeight: 700 }}>
              Runtime savings and quality signals
            </div>
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8", textAlign: "right" }}>
            Profile {valueMetrics?.active_profile_version || "default"}
          </div>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
            gap: 10,
          }}
        >
          <MetricTile label="Success Rate" value={formatPercent(valueMetrics?.success_rate)} trend={valueMetrics?.success_rate || 0} />
          <MetricTile label="Cache Hit Rate" value={formatPercent(valueMetrics?.cache_hit_rate)} trend={valueMetrics?.cache_hit_rate || 0} />
          <MetricTile label="Time Saved" value={formatDuration(valueMetrics?.estimated_time_saved_seconds || 0)} trend={Math.min((valueMetrics?.estimated_time_saved_seconds || 0) / 3600, 1)} />
          <MetricTile label="Cost Saved" value={`$${(valueMetrics?.estimated_cost_saved_usd || 0).toFixed(2)}`} trend={Math.min((valueMetrics?.estimated_cost_saved_usd || 0) / 10, 1)} />
          <MetricTile label="Quality" value={formatPercent(valueMetrics?.average_quality_score)} trend={valueMetrics?.average_quality_score || 0} />
          <MetricTile label="Accepted Fixtures" value={String(valueMetrics?.value_signals.accepted_fixtures || 0)} trend={Math.min((valueMetrics?.value_signals.accepted_fixtures || 0) / 5, 1)} />
        </div>
      </div>

      {/* Run Console */}
      <section
        aria-label="Run actor console"
        style={{
          background: "#111827",
          border: "1px solid #334155",
          borderRadius: 10,
          padding: 16,
          marginBottom: 24,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 14 }}>
          <div>
            <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>Run Actor</div>
            <div style={{ fontSize: 16, color: "#f8fafc", fontWeight: 700 }}>
              API-first execution console
            </div>
          </div>
          <code style={{ color: "#93c5fd", fontSize: 12, alignSelf: "start" }}>
            POST /api/v1/actors/{actor.id}/runs
          </code>
        </div>

        <form onSubmit={runActor} style={{ display: "grid", gap: 10 }}>
          <label style={{ color: "#94a3b8", fontSize: 12 }} htmlFor="actor-run-target">
            Target URL or query
          </label>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <input
              id="actor-run-target"
              value={runTarget}
              onChange={(event) => setRunTarget(event.target.value)}
              placeholder="https://example.com/products or search query"
              style={{
                flex: "1 1 320px",
                minWidth: 220,
                padding: "10px 12px",
                background: "#0f172a",
                border: "1px solid #334155",
                borderRadius: 8,
                color: "#e2e8f0",
                fontSize: 13,
                outline: "none",
              }}
            />
            <button
              type="submit"
              disabled={runBusy || actor.runnable_status === "blocked"}
              style={{
                padding: "10px 16px",
                background: runBusy || actor.runnable_status === "blocked" ? "#1e293b" : "#2563eb",
                border: "1px solid #3b82f6",
                borderRadius: 8,
                color: "#f8fafc",
                cursor: runBusy || actor.runnable_status === "blocked" ? "not-allowed" : "pointer",
                fontSize: 13,
                fontWeight: 700,
              }}
            >
              {runBusy ? "Running..." : "Run actor"}
            </button>
          </div>
        </form>

        {actor.runnable_status === "blocked" && (
          <p style={{ color: "#fbbf24", fontSize: 12, margin: "10px 0 0" }}>
            This catalog entry is currently blocked by policy or missing runtime components.
          </p>
        )}
        {runError && (
          <p role="alert" style={{ color: "#fca5a5", fontSize: 12, margin: "10px 0 0" }}>
            {runError}
          </p>
        )}
        {runResult && (
          <div
            aria-live="polite"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: 12,
              marginTop: 14,
            }}
          >
            <div style={{ background: "#0f172a", border: "1px solid #1f2937", borderRadius: 8, padding: 12 }}>
              <div style={{ color: "#64748b", fontSize: 11, marginBottom: 8 }}>Run Status</div>
              <div style={{ color: "#e2e8f0", fontSize: 18, fontWeight: 700 }}>
                {runResult.status || "submitted"}
              </div>
              <p style={{ color: "#94a3b8", fontSize: 12, lineHeight: 1.5 }}>
                Run {runResult.run_id || "pending"} {runResult.dataset_id ? `saved to ${runResult.dataset_id}` : ""}
              </p>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {runResult.run_id && (
                  <>
                    <a href={`/api/v1/actors/${actor.id}/runs/${runResult.run_id}/export?format=json`} style={{ color: "#93c5fd", fontSize: 12 }}>
                      JSON export
                    </a>
                    <a href={`/api/v1/actors/${actor.id}/runs/${runResult.run_id}/export?format=csv`} style={{ color: "#93c5fd", fontSize: 12 }}>
                      CSV export
                    </a>
                  </>
                )}
              </div>
            </div>
            <pre
              style={{
                background: "#0f172a",
                border: "1px solid #1f2937",
                borderRadius: 8,
                color: "#cbd5e1",
                fontSize: 11,
                lineHeight: 1.5,
                margin: 0,
                maxHeight: 260,
                overflow: "auto",
                padding: 12,
                whiteSpace: "pre-wrap",
              }}
            >
              {JSON.stringify(
                {
                  result_summary: runResult.result_summary,
                  status_history: runResult.status_history,
                  usage: runResult.usage,
                  output_preview: runResult.output_preview,
                  runtime_metadata: runResult.runtime_metadata,
                },
                null,
                2,
              )}
            </pre>
          </div>
        )}
      </section>

      {/* Missing Components */}
      {actor.missing_components && (
        <div
          style={{
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: 10,
            padding: 16,
            marginBottom: 24,
          }}
        >
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>
            Missing Components
          </div>
          <div style={{ fontSize: 13, color: "#fbbf24" }}>
            {actor.missing_components}
          </div>
        </div>
      )}

      {/* Description */}
      <div
        style={{
          background: "#1e293b",
          border: "1px solid #334155",
          borderRadius: 10,
          padding: 16,
        }}
      >
        <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>
          Description
        </div>
        <p style={{ fontSize: 14, color: "#e2e8f0", lineHeight: 1.6, margin: 0 }}>
          {actor.description}
        </p>
      </div>
    </main>
  );
}

function formatPercent(value?: number): string {
  return `${Math.round((value || 0) * 100)}%`;
}

function formatDuration(seconds: number): string {
  if (seconds >= 3600) return `${Math.round(seconds / 3600)}h`;
  if (seconds >= 60) return `${Math.round(seconds / 60)}m`;
  return `${seconds}s`;
}

function formatProofLevel(value: string): string {
  return value.replace(/_/g, " ");
}

function MetricTile({ label, value, trend = 0 }: { label: string; value: string; trend?: number }) {
  const clamped = Math.max(0, Math.min(1, trend));
  const lineEnd = 16 + Math.round(clamped * 60);
  return (
    <div
      style={{
        background: "#0f172a",
        border: "1px solid #1f2937",
        borderRadius: 8,
        padding: 12,
        minHeight: 72,
      }}
    >
      <div style={{ fontSize: 11, color: "#64748b", marginBottom: 8 }}>{label}</div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
        <div style={{ fontSize: 20, color: "#e2e8f0", fontWeight: 700 }}>{value}</div>
        <svg width="82" height="28" viewBox="0 0 82 28" aria-hidden="true">
          <polyline
            points={`2,24 16,${22 - clamped * 8} 34,${18 - clamped * 8} 52,${20 - clamped * 12} ${lineEnd},${10 - clamped * 4}`}
            fill="none"
            stroke="#93c5fd"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    </div>
  );
}

function InfoCard({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div
      style={{
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: 10,
        padding: 14,
      }}
    >
      <div style={{ fontSize: 11, color: "#64748b", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 13 }}>{children}</div>
    </div>
  );
}
