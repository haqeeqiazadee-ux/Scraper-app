/**
 * Templates page — Browse pre-built scraping templates and configure scrape jobs.
 * Clicking a template opens an Apify-style configuration form where users can:
 * - Add multiple URLs to scrape
 * - Select which fields to extract (checkboxes)
 * - Set max results, timeout, and pagination options
 * - Start the scrape with one click
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

  // Config form state
  const [selectedDetail, setSelectedDetail] = useState<TemplateDetail | null>(null);
  const [urls, setUrls] = useState<string[]>([""]);
  const [enabledFields, setEnabledFields] = useState<Record<string, boolean>>({});
  const [maxResults, setMaxResults] = useState(100);
  const [maxPages, setMaxPages] = useState(10);
  const [timeoutSec, setTimeoutSec] = useState(30);
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
      setUrls([detail.config.example_urls[0] || ""]);
      // Enable all fields by default
      const fields: Record<string, boolean> = {};
      detail.config.fields.forEach((f) => {
        fields[f.name] = true;
      });
      setEnabledFields(fields);
      setTimeoutSec(Math.round(detail.config.timeout_ms / 1000));
      setMaxResults(100);
      setMaxPages(10);
      setScrapeStatus(null);
    } catch {
      // ignore
    }
  };

  const addUrl = () => setUrls([...urls, ""]);
  const removeUrl = (i: number) => setUrls(urls.filter((_, idx) => idx !== i));
  const updateUrl = (i: number, val: string) => {
    const next = [...urls];
    next[i] = val;
    setUrls(next);
  };

  const toggleField = (name: string) => {
    setEnabledFields((prev) => ({ ...prev, [name]: !prev[name] }));
  };
  const toggleAllFields = (on: boolean) => {
    const next: Record<string, boolean> = {};
    selectedDetail?.config.fields.forEach((f) => {
      next[f.name] = on;
    });
    setEnabledFields(next);
  };

  const validUrls = urls.filter((u) => u.trim().length > 0);
  const enabledFieldNames = Object.entries(enabledFields)
    .filter(([, v]) => v)
    .map(([k]) => k);

  const startScrape = async () => {
    if (!selectedDetail || validUrls.length === 0) return;
    setScraping(true);
    setScrapeStatus(null);
    try {
      // 1. Apply template as policy
      const policyRes = await templatesApi.apply(selectedDetail.id, {
        timeout_ms: timeoutSec * 1000,
      });

      // 2. Create a task for each URL
      const taskIds: string[] = [];
      for (const url of validUrls) {
        let hostname: string;
        try {
          hostname = new URL(url).hostname;
        } catch {
          hostname = url.substring(0, 30);
        }
        const task = await tasksApi.create({
          name: `${selectedDetail.name} — ${hostname}`,
          url: url.trim(),
          policy_id: policyRes.policy_id,
          metadata: {
            enabled_fields: enabledFieldNames,
            max_results: maxResults,
            max_pages: maxPages,
          },
        });
        taskIds.push(task.id);
      }

      // 3. Execute all tasks
      for (const id of taskIds) {
        await tasksApi.execute(id);
      }

      setScrapeStatus(
        `Started ${taskIds.length} scrape${taskIds.length > 1 ? "s" : ""}! Redirecting...`
      );

      setTimeout(() => {
        setSelectedDetail(null);
        if (taskIds.length === 1) {
          navigate(`/tasks/${taskIds[0]}`);
        } else {
          navigate("/tasks");
        }
      }, 1000);
    } catch (err) {
      setScrapeStatus(
        `Error: ${err instanceof Error ? err.message : "Failed to start scrape"}`
      );
    } finally {
      setScraping(false);
    }
  };

  // ── Browse view ──
  if (!selectedDetail) {
    return (
      <div className="templates-page">
        <div className="templates-header">
          <div>
            <h1>Templates</h1>
            <p>Pre-built scraping templates for popular platforms. Click to configure and run.</p>
          </div>
          <input
            type="text"
            placeholder="Search templates..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="templates-search"
          />
        </div>

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

        {loading && <div className="templates-loading">Loading templates...</div>}
        {error && <div className="templates-error">{error}</div>}

        {!loading && !error && (
          <>
            <p className="templates-count">
              {items.length} template{items.length !== 1 ? "s" : ""}
              {activeCategory ? ` in ${activeCategory.replace("_", " ")}` : ""}
            </p>
            <div className="templates-grid">
              {items.map((t) => (
                <div key={t.id} className="template-card" onClick={() => openDetail(t.id)}>
                  <div className="template-card__header">
                    <span className="template-card__icon">{t.icon}</span>
                    <div className="template-card__info">
                      <div className="template-card__name">{t.name}</div>
                      <div className="template-card__platform">{t.platform}</div>
                    </div>
                    <span className={laneClass(t.preferred_lane)}>{t.preferred_lane}</span>
                  </div>
                  <p className="template-card__desc">{t.description}</p>
                  <div className="template-card__meta">
                    <span className="template-card__fields">{t.field_count} fields</span>
                    {t.browser_required && <span className="capability-badge--browser">Browser</span>}
                    {t.stealth_required && <span className="capability-badge--stealth">Stealth</span>}
                    {t.tags.slice(0, 3).map((tag) => (
                      <span key={tag} className="template-tag">{tag}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    );
  }

  // ── Configuration form view (Apify-style) ──
  const allEnabled = selectedDetail.config.fields.every((f) => enabledFields[f.name]);
  const noneEnabled = selectedDetail.config.fields.every((f) => !enabledFields[f.name]);

  return (
    <div className="templates-page">
      {/* Header with back button */}
      <div className="config-header">
        <button className="config-back" onClick={() => setSelectedDetail(null)}>
          &larr; Back to Templates
        </button>
        <div className="config-header__right">
          <button
            className="btn btn-primary btn-lg"
            onClick={startScrape}
            disabled={scraping || validUrls.length === 0 || enabledFieldNames.length === 0}
          >
            {scraping ? "Starting..." : "Start Scrape"}
          </button>
        </div>
      </div>

      {/* Template info bar */}
      <div className="config-title-bar">
        <span className="config-title-icon">{selectedDetail.icon}</span>
        <div>
          <h1 className="config-title">{selectedDetail.name}</h1>
          <div className="config-subtitle">
            {selectedDetail.platform} &middot; v{selectedDetail.version} &middot;{" "}
            {selectedDetail.category.replace("_", " ")} &middot;{" "}
            <span className={laneClass(selectedDetail.config.preferred_lane)}>
              {selectedDetail.config.preferred_lane}
            </span>
          </div>
        </div>
      </div>

      <p className="config-description">{selectedDetail.description}</p>

      {/* Status message */}
      {scrapeStatus && (
        <div
          className={`config-status ${
            scrapeStatus.startsWith("Error") ? "config-status--error" : "config-status--success"
          }`}
        >
          {scrapeStatus}
        </div>
      )}

      {/* ── Section 1: URLs ── */}
      <div className="config-section">
        <h3 className="config-section__title">URLs (required)</h3>
        <p className="config-section__hint">
          Enter one or more URLs to scrape. Each URL will create a separate task.
        </p>
        <div className="config-urls">
          {urls.map((url, i) => (
            <div key={i} className="config-url-row">
              <input
                type="url"
                className="form-input config-url-input"
                placeholder={selectedDetail.config.example_urls[0] ?? "https://example.com/product/123"}
                value={url}
                onChange={(e) => updateUrl(i, e.target.value)}
              />
              {urls.length > 1 && (
                <button className="config-url-remove" onClick={() => removeUrl(i)} title="Remove URL">
                  x
                </button>
              )}
            </div>
          ))}
          <div className="config-url-actions">
            <button className="btn btn-sm btn-primary" onClick={addUrl}>+ Add</button>
            {selectedDetail.config.example_urls.length > 0 && (
              <span className="config-url-examples">
                <span className="config-url-examples__label">Try:</span>
                {selectedDetail.config.example_urls.slice(0, 2).map((exUrl) => (
                  <button
                    key={exUrl}
                    className="config-url-example-btn"
                    onClick={() => {
                      if (urls.length === 1 && urls[0] === "") {
                        setUrls([exUrl]);
                      } else {
                        setUrls([...urls, exUrl]);
                      }
                    }}
                  >
                    {exUrl.replace(/^https?:\/\//, "").substring(0, 45)}
                  </button>
                ))}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── Section 2: Fields to Extract ── */}
      <div className="config-section">
        <h3 className="config-section__title">
          Fields to Extract ({enabledFieldNames.length} of {selectedDetail.config.fields.length})
        </h3>
        <p className="config-section__hint">
          Select which data fields you want to extract from each page.
        </p>
        <div className="config-fields-toolbar">
          <button
            className="btn btn-sm btn-secondary"
            onClick={() => toggleAllFields(true)}
            disabled={allEnabled}
          >
            Select All
          </button>
          <button
            className="btn btn-sm btn-secondary"
            onClick={() => toggleAllFields(false)}
            disabled={noneEnabled}
          >
            Deselect All
          </button>
        </div>
        <div className="config-fields-grid">
          {selectedDetail.config.fields.map((f) => (
            <label key={f.name} className={`config-field-item ${enabledFields[f.name] ? "config-field-item--active" : ""}`}>
              <input
                type="checkbox"
                checked={!!enabledFields[f.name]}
                onChange={() => toggleField(f.name)}
                className="config-field-checkbox"
              />
              <div className="config-field-info">
                <span className="config-field-name">{f.name}</span>
                <span className="config-field-type">{f.field_type}</span>
              </div>
              {f.required && <span className="config-field-required">Required</span>}
              {f.description && (
                <span className="config-field-desc" title={f.description}>
                  {f.description.length > 40 ? f.description.substring(0, 40) + "..." : f.description}
                </span>
              )}
            </label>
          ))}
        </div>
      </div>

      {/* ── Section 3: Scrape Options ── */}
      <div className="config-section">
        <h3 className="config-section__title">Scrape Options</h3>
        <div className="config-options-grid">
          <div className="config-option">
            <label className="config-option__label">Max Results per URL</label>
            <input
              type="number"
              className="form-input"
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value) || 1)}
              min={1}
              max={10000}
            />
            <span className="config-option__hint">Maximum items to extract</span>
          </div>
          <div className="config-option">
            <label className="config-option__label">Max Pages</label>
            <input
              type="number"
              className="form-input"
              value={maxPages}
              onChange={(e) => setMaxPages(Number(e.target.value) || 1)}
              min={1}
              max={100}
            />
            <span className="config-option__hint">Pages to follow via pagination</span>
          </div>
          <div className="config-option">
            <label className="config-option__label">Timeout (seconds)</label>
            <input
              type="number"
              className="form-input"
              value={timeoutSec}
              onChange={(e) => setTimeoutSec(Number(e.target.value) || 10)}
              min={5}
              max={300}
            />
            <span className="config-option__hint">Per-page timeout</span>
          </div>
          <div className="config-option">
            <label className="config-option__label">Rate Limit</label>
            <div className="config-option__static">
              {selectedDetail.config.rate_limit_rpm} req/min
            </div>
            <span className="config-option__hint">Set by template</span>
          </div>
        </div>
      </div>

      {/* ── Section 4: Run Options (collapsible) ── */}
      <details className="config-section config-section--collapsible">
        <summary className="config-section__summary">
          <h3 className="config-section__title">Run Options</h3>
          <div className="config-run-options-preview">
            <span>TIMEOUT {timeoutSec}s</span>
            <span>PROXY {selectedDetail.config.proxy_required ? selectedDetail.config.proxy_type ?? "auto" : "none"}</span>
            <span>LANE {selectedDetail.config.preferred_lane}</span>
          </div>
        </summary>
        <div className="config-run-options-detail">
          <div className="config-options-grid">
            <div className="config-option">
              <label className="config-option__label">Proxy</label>
              <div className="config-option__static">
                {selectedDetail.config.proxy_required
                  ? `Required (${selectedDetail.config.proxy_type ?? "auto"})`
                  : "Not required"}
              </div>
            </div>
            <div className="config-option">
              <label className="config-option__label">Lane</label>
              <div className="config-option__static">
                <span className={laneClass(selectedDetail.config.preferred_lane)}>
                  {selectedDetail.config.preferred_lane}
                </span>
              </div>
            </div>
            <div className="config-option">
              <label className="config-option__label">Stealth Mode</label>
              <div className="config-option__static">
                {selectedDetail.config.stealth_required ? "Enabled" : "Disabled"}
              </div>
            </div>
            <div className="config-option">
              <label className="config-option__label">Robots.txt</label>
              <div className="config-option__static">
                {selectedDetail.config.robots_compliance ? "Respected" : "Ignored"}
              </div>
            </div>
          </div>
          {selectedDetail.config.target_domains.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <label className="config-option__label">Target Domains</label>
              <div className="template-tag-list" style={{ marginTop: 6 }}>
                {selectedDetail.config.target_domains.map((d) => (
                  <span key={d} className="template-tag">{d}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </details>

      {/* ── Start Button (bottom) ── */}
      <div className="config-footer">
        <button
          className="btn btn-primary btn-lg"
          onClick={startScrape}
          disabled={scraping || validUrls.length === 0 || enabledFieldNames.length === 0}
        >
          {scraping
            ? "Starting..."
            : `Start Scrape (${validUrls.length} URL${validUrls.length !== 1 ? "s" : ""})`}
        </button>
        <button className="btn btn-secondary" onClick={() => setSelectedDetail(null)}>
          Cancel
        </button>
      </div>
    </div>
  );
}

export default TemplatesPage;
