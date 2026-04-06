/**
 * ScrapeTestPage — Real-time scrape testing environment.
 * Runs a scrape inline (synchronously) and shows results immediately.
 * Supports extraction modes: Everything, Products, Content, Custom.
 * Can save results to the Results & Export page.
 */

import { useState } from "react";
import { scrapeTest, type TestScrapeResult } from "../api/client";

type ExtractionMode = "everything" | "products" | "content" | "custom";

const MODE_OPTIONS: { value: ExtractionMode; label: string; description: string }[] = [
  { value: "everything", label: "Everything", description: "Full page: products + content + headings + links + metadata" },
  { value: "products", label: "Products", description: "Pricing, product cards, and e-commerce data" },
  { value: "content", label: "Text Content", description: "Article text, blog content via trafilatura" },
  { value: "custom", label: "Custom Fields", description: "Define your own extraction schema" },
];

export default function ScrapeTestPage() {
  const [url, setUrl] = useState("https://yousell.online");
  const [mode, setMode] = useState<ExtractionMode>("everything");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestScrapeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<boolean | null>(null);
  const [customSchema, setCustomSchema] = useState('{\n  "title": "string",\n  "price": "number",\n  "description": "string"\n}');

  const handleTest = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setSaved(null);
    try {
      const res = await scrapeTest.run(url.trim(), 20000, mode, true);
      setResult(res);
      setSaved(res.saved ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h2>Quick Scrape</h2>
          <p>Enter any URL, choose what to extract, and see results instantly. Results are auto-saved.</p>
        </div>
      </div>
      {/* Info box */}
      <div style={{
        padding: "14px 18px",
        margin: "0 24px 20px",
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
        <span style={{ fontSize: 16, lineHeight: 1 }}>&#9889;</span>
        <div>
          <strong style={{ color: "var(--color-text)" }}>Quick Scrape</strong> extracts data from any single URL instantly. Choose Everything mode for full page content, Products for pricing data, Text Content for articles, or Custom Fields to define your own schema.
          <br />
          <span style={{ fontSize: 12 }}>
            <strong>Use cases:</strong> Product research, content monitoring, competitive analysis
          </span>
          <br />
          <span style={{ fontSize: 12 }}>
            <strong>Limitation:</strong> Single page only — use Web Crawl for multi-page sites
          </span>
        </div>
      </div>

      <div className="page-body">
        {/* Input bar */}
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <input
              type="url"
              className="form-input"
              placeholder="https://example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleTest()}
              style={{ flex: 1 }}
            />
            <button
              className="btn btn-primary"
              onClick={handleTest}
              disabled={loading || !url.trim()}
            >
              {loading ? (
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <span className="spinner" />
                  Scraping...
                </span>
              ) : (
                "Scrape"
              )}
            </button>
          </div>

          {/* Extraction Mode Selector */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {MODE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setMode(opt.value)}
                title={opt.description}
                style={{
                  padding: "6px 14px",
                  fontSize: 13,
                  fontWeight: mode === opt.value ? 700 : 500,
                  borderRadius: 6,
                  border: mode === opt.value ? "2px solid var(--color-primary)" : "1px solid var(--color-border)",
                  background: mode === opt.value ? "rgba(99, 102, 241, 0.1)" : "var(--color-surface)",
                  color: mode === opt.value ? "var(--color-primary)" : "var(--color-text-secondary)",
                  cursor: "pointer",
                  transition: "all 0.15s",
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 6 }}>
            {MODE_OPTIONS.find((o) => o.value === mode)?.description}
          </div>

          {/* Custom Fields Schema Input */}
          {mode === "custom" && (
            <div style={{ marginTop: 12 }}>
              <label style={{
                display: "block",
                fontSize: 12,
                fontWeight: 600,
                color: "var(--color-text-secondary)",
                marginBottom: 6,
              }}>
                Extraction Schema (JSON)
              </label>
              <textarea
                value={customSchema}
                onChange={(e) => setCustomSchema(e.target.value)}
                placeholder='{"title": "string", "price": "number", "description": "string"}'
                rows={6}
                style={{
                  width: "100%",
                  fontFamily: "var(--font-mono)",
                  fontSize: 13,
                  padding: 12,
                  borderRadius: 8,
                  border: "1px solid var(--color-border)",
                  background: "var(--color-bg)",
                  color: "var(--color-text)",
                  resize: "vertical",
                  boxSizing: "border-box",
                }}
              />
              <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 4 }}>
                Define fields to extract as key-value pairs. Keys are field names, values are types (string, number, boolean).
              </div>
            </div>
          )}
        </div>

        {/* Saved confirmation */}
        {saved === true && (
          <div className="card" style={{ borderColor: "var(--color-success)", marginBottom: 16, background: "rgba(34, 197, 94, 0.05)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--color-success)" }}>
              <span style={{ fontSize: 18 }}>&#10003;</span>
              <div>
                <div style={{ fontWeight: 600 }}>Saved to Results</div>
                <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                  View in <a href="/results" style={{ color: "var(--color-primary)" }}>Results &amp; Export</a> page
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="card" style={{ borderColor: "var(--color-error)", marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 10, color: "var(--color-error)" }}>
              <span style={{ fontSize: 18, lineHeight: 1 }}>!</span>
              <div>
                <div style={{ fontWeight: 600, marginBottom: 2 }}>Request Error</div>
                <div style={{ fontSize: 13, fontFamily: "var(--font-mono)", wordBreak: "break-all" }}>{error}</div>
              </div>
            </div>
          </div>
        )}

        {/* Results */}
        {result && (
          <>
            {/* Status Overview */}
            <div className="stats-grid" style={{ marginBottom: 16 }}>
              <div className="stat-card">
                <div className="stat-label">Status</div>
                <div className="stat-value" style={{
                  fontSize: 20,
                  color: result.status === "success" ? "var(--color-success)" : "var(--color-error)",
                }}>
                  {result.status?.toUpperCase()}
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-label">HTTP Code</div>
                <div className="stat-value" style={{ fontSize: 20 }}>{result.status_code ?? "N/A"}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Items Found</div>
                <div className="stat-value" style={{ fontSize: 20 }}>{result.item_count}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Confidence</div>
                <div className="stat-value" style={{ fontSize: 20 }}>{(result.confidence * 100).toFixed(0)}%</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Duration</div>
                <div className="stat-value" style={{ fontSize: 20 }}>{result.duration_ms}ms</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Method</div>
                <div className="stat-value" style={{ fontSize: 14, textTransform: "capitalize" }}>
                  {result.extraction_method ?? "N/A"}
                </div>
              </div>
            </div>

            {result.error && (
              <div className="form-error-banner" style={{ marginBottom: 16 }}>
                <strong>Extraction Error:</strong> {result.error}
              </div>
            )}

            {/* Extracted Data Table */}
            {result.extracted_data && result.extracted_data.length > 0 && (
              <div className="card" style={{ marginBottom: 16 }}>
                <div className="card-header">
                  <h3>Extracted Data ({result.extracted_data.length} items)</h3>
                </div>
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        {Object.keys(result.extracted_data[0])
                          .filter((k) => !k.startsWith("_") && k !== "full_content")
                          .map((key) => (
                            <th key={key}>{key}</th>
                          ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.extracted_data.map((item, i) => (
                        <tr key={i}>
                          {Object.entries(item)
                            .filter(([k]) => !k.startsWith("_") && k !== "full_content")
                            .map(([, val], j) => (
                              <td key={j} className="url-cell">
                                {typeof val === "boolean" ? (val ? "Yes" : "No") : String(val ?? "").substring(0, 200)}
                              </td>
                            ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Raw JSON */}
            <div className="card">
              <details>
                <summary style={{
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: 13.5,
                  color: "var(--color-text-secondary)",
                  padding: "4px 0",
                }}>
                  Raw JSON Response
                </summary>
                <pre style={{
                  background: "var(--color-bg)",
                  padding: 16,
                  borderRadius: "var(--radius-md)",
                  overflow: "auto",
                  fontSize: 12,
                  maxHeight: 400,
                  fontFamily: "var(--font-mono)",
                  marginTop: 12,
                  border: "1px solid var(--color-border-subtle)",
                }}>
                  {JSON.stringify(result, null, 2)}
                </pre>
              </details>
            </div>
          </>
        )}

        {/* Empty state when no result */}
        {!result && !error && !loading && (
          <div className="empty-state">
            <div className="empty-state-icon">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </div>
            <h3>Ready to Scrape</h3>
            <p>Enter a URL above, choose an extraction mode, and click "Scrape" to see results.</p>
          </div>
        )}
      </div>
    </>
  );
}
