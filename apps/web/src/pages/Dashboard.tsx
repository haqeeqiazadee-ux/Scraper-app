/**
 * Dashboard — Apify-style SaaS overview.
 *
 * Top stats row, scraper catalog cards, recent runs table, usage summary.
 * Polls tasks every 10s for live updates.
 */

import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { tasks, health } from "../api/client";
import type { TaskListItem } from "../api/types";

/* ── Helpers ── */

function countByStatus(items: TaskListItem[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const item of items) {
    counts[item.status] = (counts[item.status] ?? 0) + 1;
  }
  return counts;
}

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function statusClass(status: string): string {
  switch (status) {
    case "completed": case "success": return "badge--success";
    case "running": return "badge--running";
    case "queued": case "pending": return "badge--queued";
    case "failed": case "error": return "badge--error";
    case "cancelled": return "badge--cancelled";
    default: return "badge--neutral";
  }
}

/* ── Scraper Catalog ── */

interface CatalogItem {
  title: string;
  description: string;
  route: string;
  icon: string;
  category: string;
}

const CATALOG: CatalogItem[] = [
  { title: "Smart Scraper", description: "Auto-detect & extract any website", route: "/scraper", icon: "S", category: "Scraping" },
  { title: "Amazon Products", description: "Product data via Keepa API", route: "/amazon", icon: "A", category: "Data Source" },
  { title: "Google Maps", description: "Business listings & details", route: "/google-maps", icon: "G", category: "Data Source" },
  { title: "Facebook Groups", description: "Group posts & members", route: "/facebook-groups", icon: "F", category: "Data Source" },
  { title: "Templates", description: "55 pre-built scraper configs", route: "/templates", icon: "T", category: "Library" },
  { title: "Feed Management", description: "Manage data feeds", route: "/fms", icon: "D", category: "Data" },
];

const CATALOG_COLORS: Record<string, string> = {
  S: "#2563eb",
  A: "#f59e0b",
  G: "#16a34a",
  F: "#3b82f6",
  T: "#8b5cf6",
  D: "#0891b2",
};

/* ── Component ── */

export function Dashboard() {
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery({
    queryKey: ["tasks", "dashboard"],
    queryFn: () => tasks.list({ limit: 15 }),
    refetchInterval: 10_000,
  });

  const { data: healthData } = useQuery({
    queryKey: ["health"],
    queryFn: () => health.check(),
    refetchInterval: 30_000,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const counts = countByStatus(items);

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h2>Dashboard</h2>
          <p>Overview of your scraping platform.</p>
        </div>
        <div className="page-header-actions">
          {healthData && (
            <span className={`badge ${healthData.status === "healthy" ? "badge--success" : "badge--warning"}`}>
              <span className={`status-dot ${healthData.status === "healthy" ? "status-dot--success" : "status-dot--warning"}`} />
              API {healthData.status}
            </span>
          )}
          <button className="btn btn-primary btn-sm" onClick={() => navigate("/scraper")}>
            New Scrape
          </button>
        </div>
      </div>

      <div className="page-body">
        {/* Stats row */}
        <div className="dash-stats">
          <div className="dash-stat">
            <div className="dash-stat-value">{total}</div>
            <div className="dash-stat-label">Total Runs</div>
          </div>
          <div className="dash-stat">
            <div className="dash-stat-value" style={{ color: "var(--color-primary)" }}>{counts["running"] ?? 0}</div>
            <div className="dash-stat-label">Running</div>
          </div>
          <div className="dash-stat">
            <div className="dash-stat-value" style={{ color: "var(--color-success)" }}>{counts["completed"] ?? 0}</div>
            <div className="dash-stat-label">Succeeded</div>
          </div>
          <div className="dash-stat">
            <div className="dash-stat-value" style={{ color: "var(--color-error)" }}>{counts["failed"] ?? 0}</div>
            <div className="dash-stat-label">Failed</div>
          </div>
        </div>

        {/* Two column layout: catalog + usage */}
        <div className="dash-grid">
          {/* Left: Scraper Catalog */}
          <div className="dash-main">
            <div className="dash-section-header">
              <h3>Scrapers</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => navigate("/templates")}>
                View all
              </button>
            </div>
            <div className="catalog-grid">
              {CATALOG.map((item) => (
                <button
                  key={item.route}
                  className="catalog-card"
                  onClick={() => navigate(item.route)}
                >
                  <div className="catalog-icon" style={{ background: CATALOG_COLORS[item.icon] ?? "#6366f1" }}>
                    {item.icon}
                  </div>
                  <div className="catalog-info">
                    <div className="catalog-title">{item.title}</div>
                    <div className="catalog-desc">{item.description}</div>
                  </div>
                  <span className="catalog-category">{item.category}</span>
                </button>
              ))}
            </div>

            {/* Recent Runs */}
            <div className="dash-section-header" style={{ marginTop: 28 }}>
              <h3>Recent Runs</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => navigate("/results")}>
                View all
              </button>
            </div>

            {isLoading && <div className="loading">Loading runs...</div>}

            {error && (
              <div className="dash-empty">
                <p>Failed to load runs. Is the backend reachable?</p>
              </div>
            )}

            {!isLoading && !error && items.length === 0 && (
              <div className="dash-empty">
                <p>No runs yet. Start your first scrape to see results here.</p>
                <button className="btn btn-primary btn-sm" onClick={() => navigate("/scraper")} style={{ marginTop: 12 }}>
                  Start Scraping
                </button>
              </div>
            )}

            {!isLoading && !error && items.length > 0 && (
              <div className="runs-table-wrap">
                <table className="runs-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Target</th>
                      <th>Status</th>
                      <th>Created</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.slice(0, 10).map((task) => (
                      <tr key={task.id} onClick={() => navigate(`/tasks/${task.id}`)} style={{ cursor: "pointer" }}>
                        <td style={{ fontWeight: 500, maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {task.name || "(untitled)"}
                        </td>
                        <td className="url-cell">{task.url}</td>
                        <td>
                          <span className={`badge ${statusClass(task.status)}`}>
                            {task.status}
                          </span>
                        </td>
                        <td style={{ fontSize: 12, color: "var(--color-text-secondary)", whiteSpace: "nowrap" }}>
                          {task.created_at ? relativeTime(task.created_at) : "—"}
                        </td>
                        <td style={{ width: 32 }}>
                          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="var(--color-text-tertiary)" strokeWidth="2" strokeLinecap="round">
                            <polyline points="6,4 10,8 6,12" />
                          </svg>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Right: Quick Links + Usage */}
          <div className="dash-side">
            {/* Quick Links */}
            <div className="dash-panel">
              <h4 className="dash-panel-title">Quick Links</h4>
              <div className="dash-links">
                <button className="dash-link" onClick={() => navigate("/api-keys")}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"><path d="M14.5 1.5l-1.5 1.5m-4.5 4.5a3.5 3.5 0 11-5 5 3.5 3.5 0 015-5zm0 0L10 7m0 0l2 2 2.5-2.5-2-2" /></svg>
                  API Keys
                </button>
                <button className="dash-link" onClick={() => navigate("/schedules")}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><circle cx="8" cy="8" r="6.5" /><polyline points="8,4.5 8,8 10.5,10" /></svg>
                  Schedules
                </button>
                <button className="dash-link" onClick={() => navigate("/results")}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="8" cy="4" rx="6" ry="2" /><path d="M2 4v3c0 1.1 2.7 2 6 2s6-.9 6-2V4" /><path d="M2 7v3c0 1.1 2.7 2 6 2s6-.9 6-2V7" /></svg>
                  Results & Export
                </button>
                <button className="dash-link" onClick={() => navigate("/changes")}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><rect x="1" y="1" width="6" height="14" rx="1" /><rect x="9" y="1" width="6" height="14" rx="1" /><line x1="3" y1="5" x2="5" y2="5" /><line x1="4" y1="4" x2="4" y2="6" /><line x1="11" y1="11" x2="13" y2="11" /></svg>
                  Change Detection
                </button>
                <button className="dash-link" onClick={() => navigate("/mcp")}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M6 1.5v3M10 1.5v3M4 4.5h8v3a4 4 0 01-8 0v-3z" /><line x1="8" y1="11.5" x2="8" y2="14.5" /></svg>
                  MCP Server
                </button>
              </div>
            </div>

            {/* Usage Summary */}
            <div className="dash-panel">
              <h4 className="dash-panel-title">Usage</h4>
              <div className="dash-usage-row">
                <span className="dash-usage-label">Total Runs</span>
                <span className="dash-usage-value">{total}</span>
              </div>
              <div className="dash-usage-row">
                <span className="dash-usage-label">Success Rate</span>
                <span className="dash-usage-value">
                  {total > 0
                    ? `${Math.round(((counts["completed"] ?? 0) / total) * 100)}%`
                    : "—"}
                </span>
              </div>
              <div className="dash-usage-row">
                <span className="dash-usage-label">Active Schedules</span>
                <span className="dash-usage-value">—</span>
              </div>
              <div className="dash-usage-meter">
                <div className="dash-usage-meter-label">
                  <span>Credits Used</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}>— / —</span>
                </div>
                <div className="dash-usage-track">
                  <div className="dash-usage-bar" style={{ width: "0%" }} />
                </div>
              </div>
            </div>

            {/* Platform Info */}
            <div className="dash-panel">
              <h4 className="dash-panel-title">Platform</h4>
              <div className="dash-usage-row">
                <span className="dash-usage-label">API</span>
                <span className={`badge badge--${healthData?.status === "healthy" ? "success" : "warning"}`} style={{ fontSize: 10 }}>
                  {healthData?.status ?? "unknown"}
                </span>
              </div>
              <div className="dash-usage-row">
                <span className="dash-usage-label">Endpoints</span>
                <span className="dash-usage-value">24</span>
              </div>
              <div className="dash-usage-row">
                <span className="dash-usage-label">Version</span>
                <span className="dash-usage-value" style={{ fontFamily: "var(--font-mono)" }}>v1.0</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
