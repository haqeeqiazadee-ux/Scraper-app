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
import "./TemplatesPage.css";

/* ── Helpers ── */

function laneClass(lane: string): string {
  const known = ["api", "http", "browser", "hard_target", "auto"];
  return known.includes(lane) ? `lane-badge lane-badge--${lane}` : "lane-badge";
}

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
    <div className="templates-page">
      {/* Header */}
      <div className="templates-header">
        <div>
          <h1>Templates</h1>
          <p>
            Pre-built scraping templates for popular platforms. Click to view details or apply as a policy.
          </p>
        </div>
        <input
          type="text"
          placeholder="Search templates..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="templates-search"
        />
      </div>

      {/* Category filter chips */}
      <div className="templates-filter-bar">
        <button
          className={`templates-chip${!activeCategory ? " templates-chip--active" : ""}`}
          onClick={() => setActiveCategory(null)}
        >
          All ({items.length})
        </button>
        {categories
          .filter((c) => c.count > 0)
          .map((cat) => (
            <button
              key={cat.name}
              className={`templates-chip${activeCategory === cat.name ? " templates-chip--active" : ""}`}
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
        <div className="templates-loading">
          Loading templates...
        </div>
      )}
      {error && (
        <div className="templates-error">
          {error}
        </div>
      )}

      {/* Template Grid */}
      {!loading && !error && (
        <>
          <p className="templates-count">
            {items.length} template{items.length !== 1 ? "s" : ""}
            {activeCategory ? ` in ${activeCategory.replace("_", " ")}` : ""}
          </p>
          <div className="templates-grid">
            {items.map((t) => (
              <div
                key={t.id}
                className="template-card"
                onClick={() => openDetail(t.id)}
              >
                {/* Card header */}
                <div className="template-card__header">
                  <span className="template-card__icon">{t.icon}</span>
                  <div className="template-card__info">
                    <div className="template-card__name">
                      {t.name}
                    </div>
                    <div className="template-card__platform">
                      {t.platform}
                    </div>
                  </div>
                  <span className={laneClass(t.preferred_lane)}>
                    {t.preferred_lane}
                  </span>
                </div>

                {/* Description */}
                <p className="template-card__desc">
                  {t.description}
                </p>

                {/* Meta row */}
                <div className="template-card__meta">
                  <span className="template-card__fields">
                    {t.field_count} fields
                  </span>
                  {t.browser_required && (
                    <span className="capability-badge--browser">Browser</span>
                  )}
                  {t.stealth_required && (
                    <span className="capability-badge--stealth">Stealth</span>
                  )}
                  {t.tags.slice(0, 3).map((tag) => (
                    <span key={tag} className="template-tag">
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
        <div className="modal-overlay" onClick={() => setSelectedDetail(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            {/* Modal header */}
            <div className="template-modal__header">
              <span className="template-modal__icon">{selectedDetail.icon}</span>
              <div className="template-modal__title-area">
                <h2>{selectedDetail.name}</h2>
                <div className="template-modal__subtitle">
                  {selectedDetail.platform} &middot; v{selectedDetail.version} &middot;{" "}
                  {selectedDetail.category.replace("_", " ")}
                </div>
              </div>
              <button
                onClick={() => setSelectedDetail(null)}
                className="template-modal__close"
              >
                x
              </button>
            </div>

            <p className="template-modal__desc">
              {selectedDetail.description}
            </p>

            {/* Config details */}
            <div className="template-config-grid">
              <div>
                <div className="template-config-label">
                  PREFERRED LANE
                </div>
                <span className={laneClass(selectedDetail.config.preferred_lane)}>
                  {selectedDetail.config.preferred_lane}
                </span>
              </div>
              <div>
                <div className="template-config-label">
                  RATE LIMIT
                </div>
                {selectedDetail.config.rate_limit_rpm} req/min
              </div>
              <div>
                <div className="template-config-label">
                  TIMEOUT
                </div>
                {(selectedDetail.config.timeout_ms / 1000).toFixed(0)}s
              </div>
              <div>
                <div className="template-config-label">
                  PROXY
                </div>
                {selectedDetail.config.proxy_required
                  ? `Required (${selectedDetail.config.proxy_type ?? "any"})`
                  : "Not required"}
              </div>
            </div>

            {/* Target domains */}
            {selectedDetail.config.target_domains.length > 0 && (
              <div className="template-section">
                <div className="template-section__label">
                  TARGET DOMAINS
                </div>
                <div className="template-tag-list">
                  {selectedDetail.config.target_domains.map((d) => (
                    <span key={d} className="template-tag">{d}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Fields table */}
            <div className="template-section--fields">
              <div className="template-section__label">
                EXTRACTION FIELDS ({selectedDetail.config.fields.length})
              </div>
              <div className="template-fields-table-wrap">
                <table className="template-fields-table">
                  <thead>
                    <tr>
                      <th>Field</th>
                      <th>Type</th>
                      <th>Required</th>
                      <th>Selector</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedDetail.config.fields.map((f) => (
                      <tr key={f.name}>
                        <td className="field-name">{f.name}</td>
                        <td className="field-type">{f.field_type}</td>
                        <td>
                          {f.required ? (
                            <span className="field-required-yes">Yes</span>
                          ) : (
                            <span className="field-required-no">No</span>
                          )}
                        </td>
                        <td className="field-selector">
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
              <div className="template-section--example-urls">
                <div className="template-section__label">
                  EXAMPLE URLS
                </div>
                {selectedDetail.config.example_urls.map((url) => (
                  <div key={url} className="template-example-url">
                    {url}
                  </div>
                ))}
              </div>
            )}

            {/* Tags */}
            <div className="template-tag-list template-tag-list--bottom">
              {selectedDetail.tags.map((tag) => (
                <span key={tag} className="template-tag">{tag}</span>
              ))}
            </div>

            {/* Run Scrape section */}
            <div className="template-scrape-section">
              <div className="template-scrape-section__title">
                Run Scrape with this Template
              </div>
              <div className="template-scrape-section__row">
                <input
                  type="url"
                  placeholder={
                    selectedDetail.config.example_urls[0] ??
                    "Enter URL to scrape..."
                  }
                  value={scrapeUrl}
                  onChange={(e) => setScrapeUrl(e.target.value)}
                  className="form-input template-scrape-section__input"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && scrapeUrl.trim()) {
                      runScrape();
                    }
                  }}
                />
                <button
                  onClick={runScrape}
                  disabled={scraping || !scrapeUrl.trim()}
                  className="btn btn-success btn-lg"
                >
                  {scraping ? "Starting..." : "Scrape Now"}
                </button>
              </div>
              {selectedDetail.config.example_urls.length > 0 && (
                <div className="template-scrape-section__try">
                  <span className="template-scrape-section__try-label">
                    Try:
                  </span>
                  {selectedDetail.config.example_urls.slice(0, 3).map((url) => (
                    <button
                      key={url}
                      onClick={() => setScrapeUrl(url)}
                      className="template-try-url-btn"
                    >
                      {url.replace(/^https?:\/\//, "").substring(0, 40)}...
                    </button>
                  ))}
                </div>
              )}
              {scrapeStatus && (
                <div
                  className={`template-scrape-status ${
                    scrapeStatus.startsWith("Error")
                      ? "template-scrape-status--error"
                      : "template-scrape-status--success"
                  }`}
                >
                  {scrapeStatus}
                </div>
              )}
            </div>

            {/* Apply as Policy button */}
            <div className="template-apply-row">
              <button
                onClick={applyTemplate}
                disabled={applying}
                className="btn btn-secondary btn-lg"
              >
                {applying ? "Applying..." : "Save as Policy"}
              </button>
              {applyResult && (
                <span
                  className={`template-apply-result ${
                    applyResult.startsWith("Error")
                      ? "template-apply-result--error"
                      : "template-apply-result--success"
                  }`}
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
