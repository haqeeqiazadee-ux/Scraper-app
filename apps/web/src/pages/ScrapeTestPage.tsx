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
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>Scrape Tester</h2>
        <span style={{ color: "var(--color-muted)" }}>Real-time scrape testing environment</span>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8, padding: 16 }}>
          <input
            type="url"
            className="input"
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
            {loading ? "Scraping..." : "Test Scrape"}
          </button>
        </div>
      </div>

      {error && (
        <div className="card" style={{ borderColor: "var(--color-danger, #dc3545)", marginBottom: 16 }}>
          <div style={{ padding: 16, color: "var(--color-danger, #dc3545)" }}>
            <strong>Request Error:</strong> {error}
          </div>
        </div>
      )}

      {result && (
        <>
          {/* Status Overview */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header">
              <h3>Result</h3>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, padding: 16 }}>
              <div>
                <div style={{ fontSize: 12, color: "var(--color-muted)" }}>Status</div>
                <div style={{
                  fontWeight: 600,
                  color: result.status === "success" ? "var(--color-success, #28a745)" : "var(--color-danger, #dc3545)"
                }}>
                  {result.status?.toUpperCase()}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: "var(--color-muted)" }}>HTTP Code</div>
                <div style={{ fontWeight: 600 }}>{result.status_code ?? "N/A"}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: "var(--color-muted)" }}>Items Found</div>
                <div style={{ fontWeight: 600 }}>{result.item_count}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: "var(--color-muted)" }}>Confidence</div>
                <div style={{ fontWeight: 600 }}>{(result.confidence * 100).toFixed(0)}%</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: "var(--color-muted)" }}>Duration</div>
                <div style={{ fontWeight: 600 }}>{result.duration_ms}ms</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: "var(--color-muted)" }}>Method</div>
                <div style={{ fontWeight: 600 }}>{result.extraction_method ?? "N/A"}</div>
              </div>
            </div>

            {result.error && (
              <div style={{ padding: "0 16px 16px", color: "var(--color-danger, #dc3545)", fontFamily: "var(--font-mono)", fontSize: 12, wordBreak: "break-all" }}>
                <strong>Error:</strong> {result.error}
              </div>
            )}
          </div>

          {/* Extracted Data */}
          {result.extracted_data && result.extracted_data.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h3>Extracted Data (first {result.extracted_data.length} items)</h3>
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
                          <td key={j} style={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
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
          <details style={{ marginTop: 16 }}>
            <summary style={{ cursor: "pointer", fontWeight: 600 }}>Raw JSON Response</summary>
            <pre style={{ background: "var(--color-bg-secondary, #f5f5f5)", padding: 16, borderRadius: 8, overflow: "auto", fontSize: 12, maxHeight: 400 }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        </>
      )}
    </div>
  );
}
