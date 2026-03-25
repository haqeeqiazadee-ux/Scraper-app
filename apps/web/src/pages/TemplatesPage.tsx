/**
 * Templates page — Browse and apply pre-built scraping templates.
 * Shows 55 templates across e-commerce, social media, videos, etc.
 * Users can filter by category, search, view details, and apply to create policies.
 */

import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  templates as templatesApi,
  tasks as tasksApi,
  type TemplateSummary,
  type TemplateDetail,
  type TemplateCategory,
} from "../api/client";

/* ── Styles ── */

const PAGE_STYLE: React.CSSProperties = {
  padding: "32px 40px",
  maxWidth: 1400,
};

const HEADER_STYLE: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  marginBottom: 24,
};

const FILTER_BAR: React.CSSProperties = {
  display: "flex",
  gap: 8,
  flexWrap: "wrap",
  marginBottom: 24,
};

const CHIP_STYLE = (active: boolean): React.CSSProperties => ({
  padding: "6px 14px",
  borderRadius: 20,
  border: "1px solid var(--color-border)",
  background: active ? "var(--color-primary)" : "var(--color-surface)",
  color: active ? "#fff" : "var(--color-text)",
  fontSize: 13,
  fontWeight: active ? 600 : 500,
  cursor: "pointer",
  transition: "all 0.15s",
});

const SEARCH_STYLE: React.CSSProperties = {
  padding: "8px 14px",
  borderRadius: 8,
  border: "1px solid var(--color-border)",
  background: "var(--color-surface)",
  color: "var(--color-text)",
  fontSize: 14,
  width: 280,
  outline: "none",
};

const GRID_STYLE: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
  gap: 16,
};

const CARD_STYLE: React.CSSProperties = {
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: 12,
  padding: 20,
  cursor: "pointer",
  transition: "border-color 0.15s, box-shadow 0.15s",
};

const TAG_STYLE: React.CSSProperties = {
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: 4,
  background: "rgba(37,99,235,0.1)",
  color: "var(--color-primary)",
  fontSize: 11,
  fontWeight: 500,
};

const BADGE_STYLE = (color: string): React.CSSProperties => ({
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: 4,
  background: `${color}20`,
  color,
  fontSize: 11,
  fontWeight: 600,
});

const LANE_COLORS: Record<string, string> = {
  api: "#10b981",
  http: "#3b82f6",
  browser: "#f59e0b",
  hard_target: "#ef4444",
  auto: "#8b5cf6",
};

/* ── Modal Overlay ── */

const OVERLAY: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.5)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
};

const MODAL: React.CSSProperties = {
  background: "var(--color-bg)",
  border: "1px solid var(--color-border)",
  borderRadius: 16,
  width: "90%",
  maxWidth: 700,
  maxHeight: "85vh",
  overflow: "auto",
  padding: 32,
};

/* ── Component ── */

export function TemplatesPage() {
  const [items, setItems] = useState<TemplateSummary[]>([]);
  const [categories, setCategories] = useState<TemplateCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedDetail, setSelectedDetail] = useState<TemplateDetail | null>(null);
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState<string | null>(null);
  const [scrapeUrl, setScrapeUrl] = useState("");
  const [scraping, setScraping] = useState(false);
  const [scrapeStatus, setScrapeStatus] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (activeCategory) params.category = activeCategory;
      if (search.trim()) params.q = search.trim();
      const [tmplRes, catRes] = await Promise.all([
        templatesApi.list(params),
        templatesApi.categories(),
      ]);
      setItems(tmplRes.items);
      setCategories(catRes.categories);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load templates");
    } finally {
      setLoading(false);
    }
  }, [activeCategory, search]);

  useEffect(() => {
    const timer = setTimeout(fetchTemplates, search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [fetchTemplates, search]);

  const openDetail = async (id: string) => {
    try {
      const detail = await templatesApi.get(id);
      setSelectedDetail(detail);
      setApplyResult(null);
      setScrapeUrl("");
      setScrapeStatus(null);
    } catch {
      // ignore
    }
  };

  const applyTemplate = async () => {
    if (!selectedDetail) return;
    setApplying(true);
    setApplyResult(null);
    try {
      const res = await templatesApi.apply(selectedDetail.id);
      setApplyResult(`Policy "${res.policy_name}" created successfully!`);
    } catch (err) {
      setApplyResult(
        `Error: ${err instanceof Error ? err.message : "Failed to apply template"}`
      );
    } finally {
      setApplying(false);
    }
  };

  const runScrape = async () => {
    if (!selectedDetail || !scrapeUrl.trim()) return;
    setScraping(true);
    setScrapeStatus(null);
    try {
      // 1. Apply template as policy
      const policyRes = await templatesApi.apply(selectedDetail.id);

      // 2. Create task with the URL and policy
      const task = await tasksApi.create({
        name: `${selectedDetail.name} — ${new URL(scrapeUrl).hostname}`,
        url: scrapeUrl.trim(),
        policy_id: policyRes.policy_id,
      });

      // 3. Execute the task
      await tasksApi.execute(task.id);

      setScrapeStatus("Scrape started! Redirecting to task...");

      // 4. Navigate to task detail page
      setTimeout(() => {
        setSelectedDetail(null);
        navigate(`/tasks/${task.id}`);
      }, 1000);
    } catch (err) {
      setScrapeStatus(
        `Error: ${err instanceof Error ? err.message : "Failed to start scrape"}`
      );
    } finally {
      setScraping(false);
    }
  };

  return (
    <div style={PAGE_STYLE}>
      {/* Header */}
      <div style={HEADER_STYLE}>
        <div>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 700 }}>Templates</h1>
          <p style={{ margin: "4px 0 0", color: "var(--color-text-muted)", fontSize: 14 }}>
            Pre-built scraping templates for popular platforms. Click to view details or apply as a policy.
          </p>
        </div>
        <input
          type="text"
          placeholder="Search templates..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={SEARCH_STYLE}
        />
      </div>

      {/* Category filter chips */}
      <div style={FILTER_BAR}>
        <button
          style={CHIP_STYLE(!activeCategory)}
          onClick={() => setActiveCategory(null)}
        >
          All ({items.length})
        </button>
        {categories
          .filter((c) => c.count > 0)
          .map((cat) => (
            <button
              key={cat.name}
              style={CHIP_STYLE(activeCategory === cat.name)}
              onClick={() =>
                setActiveCategory(activeCategory === cat.name ? null : cat.name)
              }
            >
              {cat.label} ({cat.count})
            </button>
          ))}
      </div>

      {/* Loading / Error */}
      {loading && (
        <div style={{ textAlign: "center", padding: 40, color: "var(--color-text-muted)" }}>
          Loading templates...
        </div>
      )}
      {error && (
        <div
          style={{
            padding: 16,
            background: "rgba(239,68,68,0.1)",
            borderRadius: 8,
            color: "#ef4444",
            marginBottom: 16,
          }}
        >
          {error}
        </div>
      )}

      {/* Template Grid */}
      {!loading && !error && (
        <>
          <p style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 12 }}>
            {items.length} template{items.length !== 1 ? "s" : ""}
            {activeCategory ? ` in ${activeCategory.replace("_", " ")}` : ""}
          </p>
          <div style={GRID_STYLE}>
            {items.map((t) => (
              <div
                key={t.id}
                style={CARD_STYLE}
                onClick={() => openDetail(t.id)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--color-primary)";
                  e.currentTarget.style.boxShadow = "0 2px 12px rgba(37,99,235,0.15)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--color-border)";
                  e.currentTarget.style.boxShadow = "none";
                }}
              >
                {/* Card header */}
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                  <span style={{ fontSize: 24 }}>{t.icon}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 15, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {t.name}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                      {t.platform}
                    </div>
                  </div>
                  <span style={BADGE_STYLE(LANE_COLORS[t.preferred_lane] ?? "#888")}>
                    {t.preferred_lane}
                  </span>
                </div>

                {/* Description */}
                <p
                  style={{
                    fontSize: 13,
                    color: "var(--color-text-muted)",
                    margin: "0 0 12px",
                    lineHeight: 1.5,
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                  }}
                >
                  {t.description}
                </p>

                {/* Meta row */}
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                    {t.field_count} fields
                  </span>
                  {t.browser_required && (
                    <span style={BADGE_STYLE("#f59e0b")}>Browser</span>
                  )}
                  {t.stealth_required && (
                    <span style={BADGE_STYLE("#ef4444")}>Stealth</span>
                  )}
                  {t.tags.slice(0, 3).map((tag) => (
                    <span key={tag} style={TAG_STYLE}>
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Detail Modal */}
      {selectedDetail && (
        <div style={OVERLAY} onClick={() => setSelectedDetail(null)}>
          <div style={MODAL} onClick={(e) => e.stopPropagation()}>
            {/* Modal header */}
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
              <span style={{ fontSize: 32 }}>{selectedDetail.icon}</span>
              <div style={{ flex: 1 }}>
                <h2 style={{ margin: 0, fontSize: 22 }}>{selectedDetail.name}</h2>
                <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                  {selectedDetail.platform} &middot; v{selectedDetail.version} &middot;{" "}
                  {selectedDetail.category.replace("_", " ")}
                </div>
              </div>
              <button
                onClick={() => setSelectedDetail(null)}
                style={{
                  background: "none",
                  border: "none",
                  fontSize: 20,
                  cursor: "pointer",
                  color: "var(--color-text-muted)",
                  padding: 4,
                }}
              >
                x
              </button>
            </div>

            <p style={{ fontSize: 14, lineHeight: 1.6, marginBottom: 20 }}>
              {selectedDetail.description}
            </p>

            {/* Config details */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
              <div>
                <div style={{ fontSize: 11, color: "var(--color-text-muted)", fontWeight: 600, marginBottom: 4 }}>
                  PREFERRED LANE
                </div>
                <span style={BADGE_STYLE(LANE_COLORS[selectedDetail.config.preferred_lane] ?? "#888")}>
                  {selectedDetail.config.preferred_lane}
                </span>
              </div>
              <div>
                <div style={{ fontSize: 11, color: "var(--color-text-muted)", fontWeight: 600, marginBottom: 4 }}>
                  RATE LIMIT
                </div>
                {selectedDetail.config.rate_limit_rpm} req/min
              </div>
              <div>
                <div style={{ fontSize: 11, color: "var(--color-text-muted)", fontWeight: 600, marginBottom: 4 }}>
                  TIMEOUT
                </div>
                {(selectedDetail.config.timeout_ms / 1000).toFixed(0)}s
              </div>
              <div>
                <div style={{ fontSize: 11, color: "var(--color-text-muted)", fontWeight: 600, marginBottom: 4 }}>
                  PROXY
                </div>
                {selectedDetail.config.proxy_required
                  ? `Required (${selectedDetail.config.proxy_type ?? "any"})`
                  : "Not required"}
              </div>
            </div>

            {/* Target domains */}
            {selectedDetail.config.target_domains.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, color: "var(--color-text-muted)", fontWeight: 600, marginBottom: 6 }}>
                  TARGET DOMAINS
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {selectedDetail.config.target_domains.map((d) => (
                    <span key={d} style={TAG_STYLE}>{d}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Fields table */}
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 11, color: "var(--color-text-muted)", fontWeight: 600, marginBottom: 6 }}>
                EXTRACTION FIELDS ({selectedDetail.config.fields.length})
              </div>
              <div
                style={{
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  overflow: "hidden",
                  maxHeight: 240,
                  overflowY: "auto",
                }}
              >
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: "var(--color-surface)" }}>
                      <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Field</th>
                      <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Type</th>
                      <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Required</th>
                      <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Selector</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedDetail.config.fields.map((f) => (
                      <tr key={f.name} style={{ borderTop: "1px solid var(--color-border)" }}>
                        <td style={{ padding: "6px 12px", fontWeight: 500 }}>{f.name}</td>
                        <td style={{ padding: "6px 12px", color: "var(--color-text-muted)" }}>{f.field_type}</td>
                        <td style={{ padding: "6px 12px" }}>
                          {f.required ? (
                            <span style={{ color: "#ef4444", fontWeight: 600 }}>Yes</span>
                          ) : (
                            <span style={{ color: "var(--color-text-muted)" }}>No</span>
                          )}
                        </td>
                        <td
                          style={{
                            padding: "6px 12px",
                            fontSize: 11,
                            color: "var(--color-text-muted)",
                            fontFamily: "monospace",
                            maxWidth: 180,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {f.css_selector || f.xpath_selector || f.json_path || f.ai_hint || "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Example URLs */}
            {selectedDetail.config.example_urls.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 11, color: "var(--color-text-muted)", fontWeight: 600, marginBottom: 6 }}>
                  EXAMPLE URLS
                </div>
                {selectedDetail.config.example_urls.map((url) => (
                  <div
                    key={url}
                    style={{
                      fontSize: 12,
                      fontFamily: "monospace",
                      padding: "4px 0",
                      color: "var(--color-primary)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {url}
                  </div>
                ))}
              </div>
            )}

            {/* Tags */}
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 24 }}>
              {selectedDetail.tags.map((tag) => (
                <span key={tag} style={TAG_STYLE}>{tag}</span>
              ))}
            </div>

            {/* Run Scrape section */}
            <div
              style={{
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: 12,
                padding: 20,
                marginBottom: 20,
              }}
            >
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>
                Run Scrape with this Template
              </div>
              <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
                <input
                  type="url"
                  placeholder={
                    selectedDetail.config.example_urls[0] ??
                    "Enter URL to scrape..."
                  }
                  value={scrapeUrl}
                  onChange={(e) => setScrapeUrl(e.target.value)}
                  style={{
                    flex: 1,
                    padding: "10px 14px",
                    borderRadius: 8,
                    border: "1px solid var(--color-border)",
                    background: "var(--color-bg)",
                    color: "var(--color-text)",
                    fontSize: 14,
                    outline: "none",
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && scrapeUrl.trim()) {
                      runScrape();
                    }
                  }}
                />
                <button
                  onClick={runScrape}
                  disabled={scraping || !scrapeUrl.trim()}
                  style={{
                    padding: "10px 24px",
                    borderRadius: 8,
                    border: "none",
                    background: "#10b981",
                    color: "#fff",
                    fontSize: 14,
                    fontWeight: 600,
                    cursor:
                      scraping || !scrapeUrl.trim()
                        ? "not-allowed"
                        : "pointer",
                    opacity: scraping || !scrapeUrl.trim() ? 0.6 : 1,
                    whiteSpace: "nowrap",
                  }}
                >
                  {scraping ? "Starting..." : "Scrape Now"}
                </button>
              </div>
              {selectedDetail.config.example_urls.length > 0 && (
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                  <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
                    Try:
                  </span>
                  {selectedDetail.config.example_urls.slice(0, 3).map((url) => (
                    <button
                      key={url}
                      onClick={() => setScrapeUrl(url)}
                      style={{
                        padding: "2px 8px",
                        borderRadius: 4,
                        border: "1px solid var(--color-border)",
                        background: "transparent",
                        color: "var(--color-primary)",
                        fontSize: 11,
                        cursor: "pointer",
                        maxWidth: 200,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {url.replace(/^https?:\/\//, "").substring(0, 40)}...
                    </button>
                  ))}
                </div>
              )}
              {scrapeStatus && (
                <div
                  style={{
                    marginTop: 10,
                    padding: "8px 12px",
                    borderRadius: 6,
                    fontSize: 13,
                    fontWeight: 500,
                    background: scrapeStatus.startsWith("Error")
                      ? "rgba(239,68,68,0.1)"
                      : "rgba(16,185,129,0.1)",
                    color: scrapeStatus.startsWith("Error")
                      ? "#ef4444"
                      : "#10b981",
                  }}
                >
                  {scrapeStatus}
                </div>
              )}
            </div>

            {/* Apply as Policy button */}
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <button
                onClick={applyTemplate}
                disabled={applying}
                style={{
                  padding: "10px 24px",
                  borderRadius: 8,
                  border: "1px solid var(--color-border)",
                  background: "var(--color-surface)",
                  color: "var(--color-text)",
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: applying ? "not-allowed" : "pointer",
                  opacity: applying ? 0.6 : 1,
                }}
              >
                {applying ? "Applying..." : "Save as Policy"}
              </button>
              {applyResult && (
                <span
                  style={{
                    fontSize: 13,
                    color: applyResult.startsWith("Error") ? "#ef4444" : "#10b981",
                    fontWeight: 500,
                  }}
                >
                  {applyResult}
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default TemplatesPage;
