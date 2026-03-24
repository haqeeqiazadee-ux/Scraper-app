/**
 * ScrapeTestPage — Real-time scrape testing environment.
 * Runs a scrape inline (synchronously) and shows results immediately.
 */

import { useState } from "react";
import { scrapeTest, type TestScrapeResult } from "../api/client";

export default function ScrapeTestPage() {
  const [url, setUrl] = useState("https://httpbin.org/html");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestScrapeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleTest = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await scrapeTest.run(url.trim());
      setResult(res);
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
          <h2>Scrape Tester</h2>
          <p>Real-time scrape testing environment. Enter a URL and see extraction results instantly.</p>
        </div>
      </div>
      <div className="page-body">
        {/* Input bar */}
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              type="url"
              className="form-input"
              placeholder="https://example.com/products"
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
                "Test Scrape"
              )}
            </button>
          </div>
        </div>

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
                <div className="stat-value" style={{ fontSize: 20, textTransform: "capitalize" }}>
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
                        {Object.keys(result.extracted_data[0]).map((key) => (
                          <th key={key}>{key}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.extracted_data.map((item, i) => (
                        <tr key={i}>
                          {Object.values(item).map((val, j) => (
                            <td key={j} className="url-cell">
                              {String(val ?? "")}
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
            <h3>Ready to Test</h3>
            <p>Enter a URL above and click "Test Scrape" to see extraction results in real-time.</p>
          </div>
        )}
      </div>
    </>
  );
}
