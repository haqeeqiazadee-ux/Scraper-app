/**
 * ActorDetailPage — Shows full detail for a single actor.
 * Loads actor from local chunk data or falls back to API.
 */

import { useState, useEffect } from "react";
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

  return (
    <div style={{ padding: "24px 32px", maxWidth: 800, margin: "0 auto" }}>
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
            background: "#3b82f6",
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
    </div>
  );
}

function InfoCard({ label, children }: { label: string; children: React.ReactNode }) {
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
