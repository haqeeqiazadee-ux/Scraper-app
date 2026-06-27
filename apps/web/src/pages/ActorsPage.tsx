/**
 * ActorsPage — Apify Store-style actor catalog browser.
 *
 * Displays 27,753 actors from hard-coded local data chunks.
 * Works offline without Apify API access.
 * Uses chunked loading from /data/actors/ for performance.
 */

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import type { CSSProperties } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

/* ── Types ── */

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

interface CatalogStats {
  total: number;
  by_strategy: Record<string, number>;
  by_category: Record<string, number>;
  by_developer: Record<string, number>;
  by_pricing_model: Record<string, number>;
  categories: string[];
  developers: string[];
  pricing_models: string[];
}

interface ActorProofSummary {
  proof_ledger_count: number;
  live_e2e_passed_count: number;
  fixture_replay_passed_count: number;
  runtime_smoke_passed_count: number;
  ui_route_passed_count: number;
  unverified_actor_count: number;
  full_catalog_live_e2e_proven: boolean;
}

/* ── Strategy Colors ── */

const STRATEGY_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  native_pipeline:      { bg: "#065f46", text: "#6ee7b7", label: "Native" },
  yt_dlp:              { bg: "#713f12", text: "#fbbf24", label: "yt-dlp" },
  job_board_schema:    { bg: "#1e3a5f", text: "#93c5fd", label: "Job Board" },
  real_estate_schema:  { bg: "#581c87", text: "#c4b5fd", label: "Real Estate" },
  apify_api:           { bg: "#374151", text: "#9ca3af", label: "Apify API" },
  unsupported:         { bg: "#7f1d1d", text: "#fca5a5", label: "Unsupported" },
};

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

function formatCompact(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(value);
}

function formatLabel(value: string): string {
  return value.replace(/_/g, " ");
}

/* ── Page Size ── */

const PAGE_SIZE = 48;

/* ── Component ── */

export function ActorsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // State
  const [stats, setStats] = useState<CatalogStats | null>(null);
  const [allActors, setAllActors] = useState<Actor[]>([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCompact, setIsCompact] = useState(false);
  const [proofSummary, setProofSummary] = useState<ActorProofSummary | null>(null);

  // Filters from URL params
  const query = searchParams.get("q") || "";
  const category = searchParams.get("category") || "";
  const developer = searchParams.get("developer") || "";
  const pricing = searchParams.get("pricing") || "";
  const strategy = searchParams.get("strategy") || "";
  const sort = searchParams.get("sort") || "relevant";
  const pageParam = parseInt(searchParams.get("page") || "1", 10);

  const setFilter = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams);
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      if (key !== "page") params.delete("page");
      setSearchParams(params, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  // Load stats + index
  useEffect(() => {
    fetch("/data/actors/stats.json")
      .then((r) => r.json())
      .then((s) => setStats(s))
      .catch(() => setError("Failed to load actor stats"));

    fetch("/data/actors/index.json")
      .then((r) => r.json())
      .then((idx) => setTotalChunks(idx.chunk_count))
      .catch(() => {});

    fetch("/api/v1/actors/proof/summary", { headers: { "X-Tenant-ID": "default" } })
      .then((r) => (r.ok ? r.json() : null))
      .then((payload) => {
        if (payload?.success && payload.data) setProofSummary(payload.data);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const updateLayout = () => setIsCompact(window.innerWidth < 900);
    updateLayout();
    window.addEventListener("resize", updateLayout);
    return () => window.removeEventListener("resize", updateLayout);
  }, []);

  // Load all chunks progressively
  useEffect(() => {
    if (totalChunks === 0) return;
    let cancelled = false;

    async function loadAll() {
      setLoading(true);
      const accumulated: Actor[] = [];
      for (let i = 0; i < totalChunks; i++) {
        if (cancelled) break;
        try {
          const resp = await fetch(`/data/actors/chunk-${i}.json`);
          const chunk: Actor[] = await resp.json();
          accumulated.push(...chunk);
          // Update after each chunk for progressive display
          if (i === 0 || i === totalChunks - 1 || i % 5 === 0) {
            setAllActors([...accumulated]);
          }
        } catch {
          // Skip failed chunks silently
        }
      }
      if (!cancelled) {
        setAllActors([...accumulated]);
        setLoading(false);
      }
    }

    loadAll();
    return () => { cancelled = true; };
  }, [totalChunks]);

  // Filter + sort
  const filtered = useMemo(() => {
    let result = allActors;

    if (query) {
      const q = query.toLowerCase();
      result = result.filter(
        (a) =>
          a.title.toLowerCase().includes(q) ||
          a.name.toLowerCase().includes(q) ||
          a.description.toLowerCase().includes(q),
      );
    }

    if (category) {
      result = result.filter((a) => a.categories.includes(category));
    }

    if (developer) {
      result = result.filter((a) => a.developer === developer);
    }

    if (pricing) {
      result = result.filter((a) => a.pricing_model === pricing);
    }

    if (strategy) {
      result = result.filter((a) => a.route_strategy === strategy);
    }

    if (sort === "name") {
      result = [...result].sort((a, b) => a.title.localeCompare(b.title));
    } else if (sort === "popular") {
      result = [...result].sort(
        (a, b) => (b.total_users - a.total_users) || (b.total_runs - a.total_runs),
      );
    } else if (sort === "runs") {
      result = [...result].sort((a, b) => b.total_runs - a.total_runs);
    } else if (sort === "rating") {
      result = [...result].sort(
        (a, b) => ((b.rating || 0) - (a.rating || 0)) || (b.review_count - a.review_count),
      );
    }

    return result;
  }, [allActors, query, category, developer, pricing, strategy, sort]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const page = Math.max(1, Math.min(pageParam, totalPages || 1));
  const pageActors = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const topCategories = useMemo(
    () =>
      Object.entries(stats?.by_category || {})
        .sort(([, a], [, b]) => b - a)
        .slice(0, 12),
    [stats],
  );
  const featuredActors = useMemo(
    () =>
      filtered
        .filter((a) => a.runnable_status === "runnable")
        .slice()
        .sort(
          (a, b) =>
            (b.total_users - a.total_users) ||
            (b.total_runs - a.total_runs) ||
            ((b.rating || 0) - (a.rating || 0)),
        )
        .slice(0, 4),
    [filtered],
  );
  const activeFilters = [
    query && { key: "q", label: `Search: ${query}` },
    category && { key: "category", label: `Category: ${formatLabel(category)}` },
    developer && { key: "developer", label: `Developer: ${developer}` },
    pricing && { key: "pricing", label: `Pricing: ${formatLabel(pricing)}` },
    strategy && {
      key: "strategy",
      label: `Strategy: ${STRATEGY_COLORS[strategy]?.label || strategy}`,
    },
  ].filter(Boolean) as Array<{ key: string; label: string }>;
  const clearFilters = useCallback(() => setSearchParams({}, { replace: true }), [setSearchParams]);

  // Search input ref
  const searchRef = useRef<HTMLInputElement>(null);

  if (error && !stats) {
    return (
      <div style={{ padding: 40, color: "#f87171" }}>
        <h2>Actor Catalog</h2>
        <p>{error}</p>
        <p style={{ color: "#9ca3af", fontSize: 13 }}>
          Make sure the app is served from a build that includes /data/actors/ chunks.
        </p>
      </div>
    );
  }

  return (
    <main
      style={{
        padding: "24px 32px",
        maxWidth: 1480,
        margin: "0 auto",
        color: "var(--text-primary, #f1f5f9)",
      }}
    >
      {/* Header */}
      <header style={{ marginBottom: 24 }}>
        <h1
          style={{
            fontSize: 30,
            fontWeight: 700,
            color: "var(--text-primary, #f1f5f9)",
            margin: 0,
          }}
        >
          Actor Store
        </h1>
        <p style={{ color: "var(--text-secondary, #94a3b8)", fontSize: 14, margin: "6px 0 0" }}>
          {stats
            ? `${stats.total.toLocaleString()} actors available`
            : "Loading catalog..."}
          {loading && allActors.length > 0
            ? ` (${allActors.length.toLocaleString()} loaded...)`
            : ""}
        </p>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: isCompact ? "1fr" : "minmax(190px, 220px) minmax(0, 1fr)",
          gap: 24,
          alignItems: "start",
        }}
      >
        <aside
          aria-label="Actor categories"
          style={{
            position: isCompact ? "static" : "sticky",
            top: 16,
            background: "var(--panel-bg, #111827)",
            border: "1px solid var(--border-muted, #334155)",
            borderRadius: 8,
            padding: 14,
          }}
        >
          <div style={{ fontSize: 12, color: "var(--text-muted, #64748b)", marginBottom: 10 }}>
            Categories
          </div>
          <button
            onClick={() => setFilter("category", "")}
            aria-pressed={!category}
            style={categoryNavStyle(!category)}
          >
            All actors
            <span>{stats?.total.toLocaleString() || "..."}</span>
          </button>
          {topCategories.map(([name, count]) => (
            <button
              key={name}
              onClick={() => setFilter("category", category === name ? "" : name)}
              aria-pressed={category === name}
              style={categoryNavStyle(category === name)}
            >
              {formatLabel(name)}
              <span>{formatCompact(count)}</span>
            </button>
          ))}
        </aside>

        <section aria-label="Actor catalog results" style={{ minWidth: 0 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: isCompact ? "1fr" : "minmax(0, 1.25fr) minmax(220px, 0.75fr)",
              gap: 14,
              marginBottom: 20,
              background: "var(--panel-bg, #111827)",
              border: "1px solid var(--border-muted, #334155)",
              borderRadius: 8,
              padding: 18,
            }}
          >
            <div>
              <div style={{ color: "var(--text-primary, #f8fafc)", fontSize: 18, fontWeight: 700 }}>
                API-first workflows with native execution
              </div>
              <p style={{ color: "var(--text-secondary, #94a3b8)", fontSize: 13, lineHeight: 1.5, margin: "8px 0 0" }}>
                Browse Apify-compatible workflow metadata, then run supported actors through this platform's provider ladder, profiles, fixtures, and value metrics.
              </p>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: 8,
              }}
            >
              <CatalogStat label="Native" value={formatCompact(stats?.by_strategy.native_pipeline || 0)} />
              <CatalogStat label="Proofed" value={formatCompact(proofSummary?.proof_ledger_count || 0)} />
              <CatalogStat label="Live E2E" value={formatCompact(proofSummary?.live_e2e_passed_count || 0)} />
              <CatalogStat label="API" value="/v1" />
            </div>
          </div>

          {featuredActors.length > 0 && (
            <section aria-label="Featured runnable actors" style={{ marginBottom: 20 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 12,
                  marginBottom: 10,
                }}
              >
                <h2 style={{ color: "var(--text-primary, #f8fafc)", fontSize: 16, margin: 0 }}>
                  Featured runnable workflows
                </h2>
                <span style={{ color: "var(--text-muted, #64748b)", fontSize: 12 }}>
                  Ranked by users, runs, and rating
                </span>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                  gap: 12,
                }}
              >
                {featuredActors.map((actor) => (
                  <ActorCard
                    key={actor.id}
                    actor={actor}
                    featured
                    onClick={() => navigate(`/actors/${actor.id}`)}
                  />
                ))}
              </div>
            </section>
          )}

      {/* Stats Cards */}
      {stats && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
            gap: 12,
            marginBottom: 20,
          }}
        >
          {Object.entries(stats.by_strategy).map(([s, count]) => {
            const info = STRATEGY_COLORS[s] || {
              bg: "#1f2937",
              text: "#9ca3af",
              label: s,
            };
            return (
              <button
                key={s}
                onClick={() => setFilter("strategy", strategy === s ? "" : s)}
                style={{
                  background: strategy === s ? info.bg : "#1e293b",
                  border: strategy === s ? `1px solid ${info.text}` : "1px solid #334155",
                  borderRadius: 10,
                  padding: "12px 14px",
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                <div
                  style={{
                    fontSize: 20,
                    fontWeight: 700,
                    color: info.text,
                  }}
                >
                  {count.toLocaleString()}
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
                  {info.label}
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Search + Filters Bar */}
      <div
        role="search"
        aria-label="Search and filter actors"
        style={{
          display: "flex",
          gap: 10,
          marginBottom: activeFilters.length > 0 ? 10 : 20,
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        {/* Search */}
        <div style={{ position: "relative", flex: "1 1 280px", minWidth: 200 }}>
          <input
            ref={searchRef}
            type="text"
            placeholder="Search actors..."
            aria-label="Search actors"
            value={query}
            onChange={(e) => setFilter("q", e.target.value)}
            style={{
              width: "100%",
              padding: "9px 12px 9px 36px",
              background: "#1e293b",
              border: "1px solid #334155",
              borderRadius: 8,
              color: "#e2e8f0",
              fontSize: 13,
              outline: "none",
            }}
          />
          <svg
            width="14"
            height="14"
            viewBox="0 0 16 16"
            fill="none"
            stroke="#64748b"
            strokeWidth="2"
            style={{ position: "absolute", left: 12, top: 12 }}
          >
            <circle cx="7" cy="7" r="4.5" />
            <line x1="10.5" y1="10.5" x2="14" y2="14" />
          </svg>
        </div>

        {/* Category Filter */}
        <select
          value={category}
          onChange={(e) => setFilter("category", e.target.value)}
          aria-label="Filter by category"
          style={{
            padding: "9px 12px",
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: 8,
            color: "#e2e8f0",
            fontSize: 13,
            minWidth: 140,
          }}
        >
          <option value="">All Categories</option>
          {stats?.categories.map((c) => (
            <option key={c} value={c}>
              {c.replace(/_/g, " ")} ({stats.by_category[c]?.toLocaleString()})
            </option>
          ))}
        </select>

        {/* Pricing Filter */}
        <select
          value={pricing}
          onChange={(e) => setFilter("pricing", e.target.value)}
          aria-label="Filter by pricing model"
          style={{
            padding: "9px 12px",
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: 8,
            color: "#e2e8f0",
            fontSize: 13,
            minWidth: 130,
          }}
        >
          <option value="">All Pricing</option>
          {stats?.pricing_models.map((p) => (
            <option key={p} value={p}>
              {p.replace(/_/g, " ")} ({stats.by_pricing_model[p]?.toLocaleString()})
            </option>
          ))}
        </select>

        {/* Developer Filter */}
        <select
          value={developer}
          onChange={(e) => setFilter("developer", e.target.value)}
          aria-label="Filter by developer"
          style={{
            padding: "9px 12px",
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: 8,
            color: "#e2e8f0",
            fontSize: 13,
            minWidth: 150,
            maxWidth: 220,
          }}
        >
          <option value="">All Developers</option>
          {stats?.developers.map((d) => (
            <option key={d} value={d}>
              {d} ({stats.by_developer[d]?.toLocaleString()})
            </option>
          ))}
        </select>

        {/* Strategy Filter */}
        <select
          value={strategy}
          onChange={(e) => setFilter("strategy", e.target.value)}
          aria-label="Filter by route strategy"
          style={{
            padding: "9px 12px",
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: 8,
            color: "#e2e8f0",
            fontSize: 13,
            minWidth: 140,
          }}
        >
          <option value="">All Strategies</option>
          {Object.entries(STRATEGY_COLORS).map(([key, info]) => (
            <option key={key} value={key}>
              {info.label}
            </option>
          ))}
        </select>

        {/* Sort */}
        <select
          value={sort}
          onChange={(e) => setFilter("sort", e.target.value)}
          aria-label="Sort actors"
          style={{
            padding: "9px 12px",
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: 8,
            color: "#e2e8f0",
            fontSize: 13,
            minWidth: 100,
          }}
        >
          <option value="relevant">Relevant</option>
          <option value="popular">Most popular</option>
          <option value="runs">Most runs</option>
          <option value="rating">Highest rated</option>
          <option value="name">Name A-Z</option>
        </select>
      </div>

      {activeFilters.length > 0 && (
        <div
          aria-label="Active filters"
          style={{
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            alignItems: "center",
            marginBottom: 18,
          }}
        >
          {activeFilters.map((filter) => (
            <button
              key={filter.key}
              onClick={() => setFilter(filter.key, "")}
              style={{
                border: "1px solid var(--border-muted, #334155)",
                background: "var(--panel-bg, #111827)",
                borderRadius: 999,
                color: "var(--text-secondary, #94a3b8)",
                cursor: "pointer",
                fontSize: 12,
                padding: "5px 10px",
              }}
              title={`Remove ${filter.label}`}
            >
              {filter.label} x
            </button>
          ))}
          <button
            onClick={clearFilters}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--accent, #93c5fd)",
              cursor: "pointer",
              fontSize: 12,
              padding: "5px 8px",
            }}
          >
            Clear all
          </button>
        </div>
      )}

      {/* Results count */}
      <div
        aria-live="polite"
        style={{
          fontSize: 13,
          color: "#64748b",
          marginBottom: 12,
        }}
      >
        {filtered.length.toLocaleString()} actors
        {query || category || developer || pricing || strategy ? " matching filters" : ""}
        {loading ? " (still loading...)" : ""}
      </div>

      {/* Actor Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: 14,
        }}
      >
        {pageActors.map((actor) => (
          <ActorCard
            key={actor.id}
            actor={actor}
            onClick={() => navigate(`/actors/${actor.id}`)}
          />
        ))}
      </div>

      {pageActors.length === 0 && !loading && (
        <div
          style={{
            textAlign: "center",
            padding: 60,
            color: "#64748b",
          }}
        >
          <p style={{ fontSize: 16 }}>No actors match your filters</p>
          <button
            onClick={() => {
              setSearchParams({});
            }}
            style={{
              marginTop: 12,
              padding: "8px 20px",
              background: "#334155",
              border: "none",
              borderRadius: 8,
              color: "#e2e8f0",
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            Clear Filters
          </button>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: 8,
            marginTop: 24,
          }}
        >
          <PaginationButton
            disabled={page <= 1}
            onClick={() => setFilter("page", String(page - 1))}
            label="Previous"
          />
          <span style={{ color: "#94a3b8", fontSize: 13, padding: "0 8px" }}>
            Page {page} of {totalPages.toLocaleString()}
          </span>
          <PaginationButton
            disabled={page >= totalPages}
            onClick={() => setFilter("page", String(page + 1))}
            label="Next"
          />
        </div>
      )}
        </section>
      </div>
    </main>
  );
}

/* ── Actor Card ── */

function categoryNavStyle(active: boolean): CSSProperties {
  return {
    alignItems: "center",
    background: active ? "var(--accent-bg, #1e3a5f)" : "transparent",
    border: active ? "1px solid var(--accent, #93c5fd)" : "1px solid transparent",
    borderRadius: 6,
    color: active ? "var(--text-primary, #f8fafc)" : "var(--text-secondary, #94a3b8)",
    cursor: "pointer",
    display: "flex",
    fontSize: 12,
    justifyContent: "space-between",
    marginBottom: 4,
    padding: "8px 9px",
    textAlign: "left",
    width: "100%",
  };
}

function CatalogStat({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        background: "var(--panel-strong, #0f172a)",
        border: "1px solid var(--border-subtle, #1f2937)",
        borderRadius: 8,
        padding: 10,
        minHeight: 64,
      }}
    >
      <div style={{ color: "var(--text-muted, #64748b)", fontSize: 11, marginBottom: 8 }}>
        {label}
      </div>
      <div style={{ color: "var(--text-primary, #f8fafc)", fontSize: 18, fontWeight: 700 }}>
        {value}
      </div>
    </div>
  );
}

function ActorCard({
  actor,
  onClick,
  featured = false,
}: {
  actor: Actor;
  onClick: () => void;
  featured?: boolean;
}) {
  const stratInfo = STRATEGY_COLORS[actor.route_strategy] || {
    bg: "#1f2937",
    text: "#9ca3af",
    label: actor.route_strategy,
  };
  const bgColor = getInitialsColor(actor.id);

  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        flexDirection: "column",
        background: featured ? "var(--panel-bg, #111827)" : "var(--panel-strong, #1e293b)",
        border: featured ? "1px solid var(--accent, #93c5fd)" : "1px solid var(--border-muted, #334155)",
        borderRadius: 8,
        padding: featured ? 18 : 16,
        cursor: "pointer",
        textAlign: "left",
        transition: "border-color 0.15s, background 0.15s",
        minHeight: featured ? 184 : 160,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = featured ? "#bfdbfe" : "#475569";
        e.currentTarget.style.background = "#172033";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = featured ? "#93c5fd" : "#334155";
        e.currentTarget.style.background = featured ? "#111827" : "#1e293b";
      }}
    >
      {/* Top row: initials + title */}
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: 10,
            background: bgColor,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
            fontWeight: 700,
            color: "#fff",
            flexShrink: 0,
          }}
        >
          {actor.initials}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 14,
              fontWeight: 600,
              color: "#f1f5f9",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {actor.title}
          </div>
          <div
            style={{
              fontSize: 11,
              color: "#64748b",
              marginTop: 2,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {actor.username ? `${actor.username}/` : ""}
            {actor.name}
          </div>
        </div>
      </div>

      {/* Description */}
      <div
        style={{
          fontSize: 12,
          color: "#94a3b8",
          marginTop: 10,
          lineHeight: 1.4,
          overflow: "hidden",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          flex: 1,
        }}
      >
        {actor.description}
      </div>

      {/* Store metrics */}
      <div
        style={{
          display: "flex",
          gap: 10,
          alignItems: "center",
          color: "#64748b",
          fontSize: 11,
          marginTop: 10,
          minHeight: 16,
        }}
      >
        {actor.rating ? <span>Rating {actor.rating.toFixed(1)} ({actor.review_count})</span> : <span>No rating</span>}
        {actor.total_users > 0 && <span>{formatCompact(actor.total_users)} users</span>}
        {actor.total_runs > 0 && <span>{formatCompact(actor.total_runs)} runs</span>}
      </div>

      {/* Bottom: strategy badge + categories */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          marginTop: 12,
        }}
      >
        <span
          style={{
            fontSize: 10,
            fontWeight: 600,
            color: stratInfo.text,
            background: stratInfo.bg,
            padding: "3px 8px",
            borderRadius: 6,
            letterSpacing: "0.02em",
          }}
        >
          {stratInfo.label}
        </span>
        <div
          style={{
            display: "flex",
            gap: 4,
            overflow: "hidden",
            flex: 1,
            justifyContent: "flex-end",
          }}
        >
          {actor.categories.slice(0, 2).map((c) => (
            <span
              key={c}
              style={{
                fontSize: 9,
                color: "#64748b",
                background: "#0f172a",
                padding: "2px 6px",
                borderRadius: 4,
                whiteSpace: "nowrap",
              }}
            >
              {c.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      </div>
    </button>
  );
}

/* ── Pagination Button ── */

function PaginationButton({
  disabled,
  onClick,
  label,
}: {
  disabled: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      style={{
        padding: "8px 16px",
        background: disabled ? "#1e293b" : "#334155",
        border: "1px solid #475569",
        borderRadius: 8,
        color: disabled ? "#475569" : "#e2e8f0",
        cursor: disabled ? "not-allowed" : "pointer",
        fontSize: 13,
      }}
    >
      {label}
    </button>
  );
}
