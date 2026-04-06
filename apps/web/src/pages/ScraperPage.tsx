/**
 * ScraperPage — Unified Smart Scraper.
 *
 * One input (URL or search query) + one button.
 * Collapsible advanced options, live status feed, results display.
 */

import { useState, useRef, type FormEvent, type ChangeEvent } from "react";
import { smartScrape } from "../api/client";

/* ============================================================
 * Shared sub-components
 * ============================================================ */

function InfoBox({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      padding: "14px 18px",
      marginBottom: 20,
      borderRadius: 10,
      border: "1px solid var(--color-border)",
      background: "rgba(99, 102, 241, 0.05)",
      display: "flex",
      alignItems: "flex-start",
      gap: 10,
      fontSize: 13,
      color: "var(--color-text-secondary)",
      lineHeight: 1.5,
    }}>
      <span style={{ fontSize: 18 }}>&#x1f4a1;</span>
      <span>{children}</span>
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div className="form-error-banner" style={{ marginBottom: 16 }}>
      {message}
    </div>
  );
}

function StatsGrid({ stats }: { stats: { label: string; value: string | number; color?: string; fontSize?: number }[] }) {
  return (
    <div className="stats-grid" style={{ marginBottom: 16 }}>
      {stats.map((s) => (
        <div className="stat-card" key={s.label}>
          <div className="stat-label">{s.label}</div>
          <div className="stat-value" style={{
            fontSize: s.fontSize ?? 20,
            color: s.color,
            textTransform: s.label === "Method" ? "capitalize" as const : undefined,
          }}>
            {s.value}
          </div>
        </div>
      ))}
    </div>
  );
}

function DataTable({ data }: { data: Record<string, unknown>[] }) {
  if (!data || data.length === 0) return null;
  const keys = Object.keys(data[0]).filter((k) => !k.startsWith("_") && k !== "full_content");
  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="card-header">
        <h3>Extracted Data ({data.length} items)</h3>
      </div>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              {keys.map((key) => (<th key={key}>{key}</th>))}
            </tr>
          </thead>
          <tbody>
            {data.map((item, i) => (
              <tr key={i}>
                {keys.map((key) => {
                  const val = item[key];
                  return (
                    <td key={key} className="url-cell">
                      {typeof val === "boolean" ? (val ? "Yes" : "No") : String(val ?? "").substring(0, 200)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ============================================================
 * Step timeline component
 * ============================================================ */

interface StepEntry {
  step: string;
  timestamp: number;
  duration_ms: number;
}

function StepTimeline({ steps, loading }: { steps: StepEntry[]; loading: boolean }) {
  if (!steps || steps.length === 0) {
    if (!loading) return null;
    return (
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header"><h3>Status</h3></div>
        <div style={{ padding: 16, display: "flex", alignItems: "center", gap: 10 }}>
          <span className="spinner" /> Starting...
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="card-header"><h3>Escalation Steps</h3></div>
      <div style={{ padding: "12px 16px" }}>
        {steps.map((s, i) => {
          const isEscalation = s.step.toLowerCase().includes("escalat");
          const isFailed = s.step.toLowerCase().includes("fail") || s.step.toLowerCase().includes("error");
          const icon = isFailed ? "\u26A0" : isEscalation ? "\u26A0" : "\u2713";
          const iconColor = isFailed ? "#ef4444" : isEscalation ? "#f59e0b" : "#22c55e";
          return (
            <div key={i} style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 10,
              padding: "6px 0",
              borderBottom: i < steps.length - 1 ? "1px solid var(--color-border)" : undefined,
              fontSize: 13,
            }}>
              <span style={{ color: iconColor, fontWeight: 700, minWidth: 18, textAlign: "center" }}>{icon}</span>
              <span style={{ flex: 1, color: "var(--color-text-secondary)" }}>{s.step}</span>
              <span style={{ color: "var(--color-text-tertiary)", fontSize: 12, whiteSpace: "nowrap" }}>
                {s.duration_ms}ms
              </span>
            </div>
          );
        })}
        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0", fontSize: 13 }}>
            <span className="spinner" style={{ width: 16, height: 16 }} />
            <span style={{ color: "var(--color-text-secondary)" }}>Processing...</span>
          </div>
        )}
      </div>
    </div>
  );
}

/* ============================================================
 * Main page
 * ============================================================ */

export function ScraperPage() {
  /* ── Core state ── */
  const [target, setTarget] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  /* ── Advanced options (collapsed by default) ── */
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [cookieFile, setCookieFile] = useState<any[]>([]);
  const [cookieInfo, setCookieInfo] = useState("");
  const [schema, setSchema] = useState("");
  const [maxPages, setMaxPages] = useState(1);
  const [maxDepth, setMaxDepth] = useState(0);
  const [outputFormat, setOutputFormat] = useState("json");

  const fileRef = useRef<HTMLInputElement>(null);
  const [showRawJson, setShowRawJson] = useState(false);

  /* ── Cookie file handler ── */
  function handleCookieFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target?.result as string);
        const arr = Array.isArray(parsed) ? parsed : [parsed];
        setCookieFile(arr);
        setCookieInfo(`${arr.length} cookie(s) loaded from ${file.name}`);
      } catch {
        setCookieInfo("Invalid JSON cookie file");
        setCookieFile([]);
      }
    };
    reader.readAsText(file);
  }

  /* ── Scrape handler ── */
  async function handleScrape(e?: FormEvent) {
    e?.preventDefault();
    if (!target.trim()) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const payload: any = { target: target.trim() };
      if (cookieFile.length > 0) payload.cookies = cookieFile;
      if (schema.trim()) {
        try {
          payload.schema = JSON.parse(schema);
        } catch {
          setError("Invalid JSON schema");
          setLoading(false);
          return;
        }
      }
      if (maxPages > 1) payload.max_pages = maxPages;
      if (maxDepth > 0) payload.max_depth = maxDepth;
      payload.output_format = outputFormat;

      const res = await smartScrape.run(payload);
      setResult(res);
    } catch (e: any) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  /* ── Build stats from result ── */
  function buildStats() {
    if (!result) return [];
    return [
      { label: "Status", value: result.status?.toUpperCase() ?? "N/A", color: result.status === "completed" || result.status === "success" ? "#22c55e" : "#ef4444" },
      { label: "Items Found", value: result.item_count ?? 0 },
      { label: "Confidence", value: `${Math.round((result.confidence ?? 0) * 100)}%` },
      { label: "Lane Used", value: result.lane_used ?? "N/A" },
      { label: "Duration", value: `${result.duration_ms ?? 0}ms` },
      { label: "Detected As", value: result.detected_as ?? "N/A" },
    ];
  }

  /* ── Render ── */
  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <h2>Scraper</h2>
        <p style={{ color: "var(--color-text-secondary)", marginTop: 4 }}>
          Paste a URL or search query &mdash; we handle the rest
        </p>
      </div>

      <InfoBox>
        Smart Scraper auto-detects what&apos;s needed. Static site &rarr; fast HTTP. JS-heavy &rarr; browser rendering.
        Login required &rarr; uses your cookies. Search query &rarr; finds results across the web.
        Multi-page &rarr; auto-crawls.
      </InfoBox>

      {/* Main input card */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header"><h3>Target</h3></div>
        <form onSubmit={handleScrape} style={{ padding: 16 }}>
          <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
            <input
              type="text"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="https://example.com or search for anything..."
              className="form-input"
              style={{ flex: 1, fontSize: 15 }}
              disabled={loading}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !target.trim()}
              style={{ minWidth: 120, fontSize: 15, padding: "10px 24px" }}
            >
              {loading ? (
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="spinner" style={{ width: 16, height: 16 }} /> Scraping...
                </span>
              ) : "Scrape"}
            </button>
          </div>

          {/* Advanced options toggle */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            style={{
              background: "none",
              border: "none",
              color: "var(--color-primary)",
              cursor: "pointer",
              fontSize: 13,
              padding: 0,
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            Advanced Options {showAdvanced ? "\u25BE" : "\u25B8"}
          </button>

          {/* Advanced options panel */}
          {showAdvanced && (
            <div style={{
              marginTop: 12,
              padding: 16,
              borderRadius: 8,
              border: "1px solid var(--color-border)",
              background: "var(--color-bg-secondary)",
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
            }}>
              {/* Cookie upload */}
              <div style={{ gridColumn: "1 / -1" }}>
                <label className="form-label">Cookie File (JSON)</label>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".json"
                  onChange={handleCookieFile}
                  style={{ display: "block", fontSize: 13 }}
                />
                {cookieInfo && (
                  <span style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 4, display: "block" }}>
                    {cookieInfo}
                  </span>
                )}
              </div>

              {/* Schema */}
              <div style={{ gridColumn: "1 / -1" }}>
                <label className="form-label">Extraction Schema (JSON)</label>
                <textarea
                  value={schema}
                  onChange={(e) => setSchema(e.target.value)}
                  placeholder={'{"title": "string", "price": "number", "description": "string"}'}
                  rows={3}
                  className="form-input"
                  style={{ fontFamily: "monospace", fontSize: 13, width: "100%", resize: "vertical" }}
                />
              </div>

              {/* Max Pages */}
              <div>
                <label className="form-label">Max Pages</label>
                <input
                  type="number"
                  value={maxPages}
                  onChange={(e) => setMaxPages(Math.max(1, Math.min(1000, Number(e.target.value) || 1)))}
                  min={1}
                  max={1000}
                  className="form-input"
                  style={{ width: "100%" }}
                />
              </div>

              {/* Crawl Depth */}
              <div>
                <label className="form-label">Crawl Depth</label>
                <input
                  type="number"
                  value={maxDepth}
                  onChange={(e) => setMaxDepth(Math.max(0, Math.min(10, Number(e.target.value) || 0)))}
                  min={0}
                  max={10}
                  className="form-input"
                  style={{ width: "100%" }}
                />
              </div>

              {/* Output Format */}
              <div>
                <label className="form-label">Output Format</label>
                <select
                  value={outputFormat}
                  onChange={(e) => setOutputFormat(e.target.value)}
                  className="form-input"
                  style={{ width: "100%" }}
                >
                  <option value="json">JSON</option>
                  <option value="markdown">Markdown</option>
                  <option value="html">HTML</option>
                </select>
              </div>
            </div>
          )}
        </form>
      </div>

      {/* Error */}
      <ErrorBanner message={error} />

      {/* Live status / steps */}
      <StepTimeline steps={result?.steps ?? []} loading={loading} />

      {/* Results */}
      {result && !loading && (
        <>
          <StatsGrid stats={buildStats()} />

          {/* Schema matched */}
          {result.schema_matched && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-header"><h3>Schema Match</h3></div>
              <div style={{ padding: 16 }}>
                <pre style={{
                  fontSize: 13,
                  background: "var(--color-bg-secondary)",
                  padding: 12,
                  borderRadius: 6,
                  overflow: "auto",
                  maxHeight: 300,
                }}>
                  {JSON.stringify(result.schema_matched, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Data table */}
          {result.extracted_data && result.extracted_data.length > 0 && (
            <DataTable data={result.extracted_data} />
          )}

          {/* Saved confirmation */}
          {result.saved && (
            <div style={{
              padding: "10px 16px",
              marginBottom: 16,
              borderRadius: 8,
              background: "rgba(34, 197, 94, 0.1)",
              border: "1px solid rgba(34, 197, 94, 0.3)",
              color: "#22c55e",
              fontSize: 13,
            }}>
              Saved to Results (Task ID: {result.saved_task_id})
            </div>
          )}

          {/* Raw JSON collapsible */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header" style={{ cursor: "pointer" }} onClick={() => setShowRawJson(!showRawJson)}>
              <h3>Raw JSON {showRawJson ? "\u25BE" : "\u25B8"}</h3>
            </div>
            {showRawJson && (
              <div style={{ padding: 16 }}>
                <pre style={{
                  fontSize: 12,
                  background: "var(--color-bg-secondary)",
                  padding: 12,
                  borderRadius: 6,
                  overflow: "auto",
                  maxHeight: 400,
                }}>
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </>
      )}

      {/* Empty state */}
      {!result && !loading && !error && (
        <div style={{
          textAlign: "center",
          padding: "60px 20px",
          color: "var(--color-text-tertiary)",
        }}>
          <div style={{ fontSize: 48, marginBottom: 12, opacity: 0.4 }}>&#x1F50D;</div>
          <h3 style={{ color: "var(--color-text-secondary)", marginBottom: 8 }}>Ready to scrape</h3>
          <p>Enter any URL or search query above</p>
        </div>
      )}
    </div>
  );
}
