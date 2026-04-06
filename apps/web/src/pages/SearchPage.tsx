/**
 * SearchPage — Search the web and extract structured data from results.
 */

import { useState, type FormEvent } from "react";
import { search } from "../api/client";

interface SearchResult {
  title?: string;
  url?: string;
  status?: string;
  extracted_data?: Record<string, unknown>;
  [key: string]: unknown;
}

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [maxResults, setMaxResults] = useState(10);
  const [outputFormat, setOutputFormat] = useState("json");
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setError("");
    setHasSearched(true);

    try {
      const res = await search.run({
        query: query.trim(),
        max_results: maxResults,
        output_format: outputFormat,
      });
      setResults(res.results ?? res.items ?? []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Search failed";
      setError(msg);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "32px 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 16,
            background: "linear-gradient(135deg, #059669 0%, #34d399 100%)",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)", margin: 0 }}>Web Search</h2>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
              Enter a keyword query, find top results from search engines, and auto-scrape each page
            </p>
          </div>
        </div>
      </div>

      {/* How it works */}
      <div style={{
        padding: "14px 18px",
        marginBottom: 20,
        borderRadius: 10,
        border: "1px solid var(--color-border)",
        background: "rgba(5, 150, 105, 0.05)",
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        fontSize: 13,
        color: "var(--color-text-secondary)",
        lineHeight: 1.5,
      }}>
        <span style={{ fontSize: 16, lineHeight: 1 }}>&#127760;</span>
        <div>
          <strong style={{ color: "var(--color-text)" }}>How Web Search works:</strong> Enter a keyword (like "best gaming laptops 2026"). The system searches via Serper (Google), gets the top URLs, then scrapes each result page to extract structured data.
          <br />
          <span style={{ fontSize: 12 }}>
            <strong>Different from Web Crawl:</strong> Crawl takes a specific URL and follows internal links to map an entire site. Search takes a keyword and finds relevant pages across the entire web.
          </span>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSearch} style={{ marginBottom: 24 }}>
        <div className="accent-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                Query
              </label>
              <input
                type="text"
                placeholder="Search for anything..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={isSearching}
                style={{ width: "100%", padding: "12px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 16, boxSizing: "border-box" }}
              />
            </div>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
              <div style={{ minWidth: 140 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                  Max Results
                </label>
                <select
                  value={maxResults}
                  onChange={(e) => setMaxResults(Number(e.target.value))}
                  disabled={isSearching}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, cursor: "pointer", boxSizing: "border-box" }}
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                </select>
              </div>
              <div style={{ minWidth: 140 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                  Output Format
                </label>
                <select
                  value={outputFormat}
                  onChange={(e) => setOutputFormat(e.target.value)}
                  disabled={isSearching}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, cursor: "pointer", boxSizing: "border-box" }}
                >
                  <option value="json">JSON</option>
                  <option value="markdown">Markdown</option>
                </select>
              </div>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isSearching || !query.trim()}
                style={{ height: 44, paddingInline: 28 }}
              >
                {isSearching ? (
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                    <span className="spinner" /> Searching...
                  </span>
                ) : "Search"}
              </button>
            </div>
          </div>
        </div>
      </form>

      {/* Error */}
      {error && <div className="form-error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Loading */}
      {isSearching && (
        <div style={{ textAlign: "center", padding: 60 }}>
          <div className="spinner" style={{ width: 32, height: 32, margin: "0 auto 16px" }} />
          <p style={{ color: "var(--color-text-secondary)" }}>Searching the web...</p>
        </div>
      )}

      {/* Results */}
      {!isSearching && results.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 14, color: "var(--color-text-secondary)", marginBottom: 12 }}>
            <strong style={{ color: "var(--color-text)" }}>{results.length}</strong> result{results.length !== 1 ? "s" : ""} found
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {results.map((result, idx) => (
              <div key={idx} className="accent-card" style={{ padding: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 8 }}>
                  <div style={{ flex: 1 }}>
                    <a
                      href={result.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: 16, fontWeight: 600, color: "var(--color-primary)", textDecoration: "none" }}
                    >
                      {result.title || "Untitled"}
                    </a>
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 4, wordBreak: "break-all" }}>
                      {result.url}
                    </div>
                  </div>
                  {result.status && (
                    <span style={{
                      display: "inline-block",
                      padding: "3px 10px",
                      borderRadius: 9999,
                      fontSize: 12,
                      fontWeight: 600,
                      color: "white",
                      background: result.status === "success" ? "#059669" : "#6b7280",
                      flexShrink: 0,
                    }}>
                      {result.status}
                    </span>
                  )}
                </div>
                {result.extracted_data && Object.keys(result.extracted_data).length > 0 && (
                  <details style={{ marginTop: 8 }}>
                    <summary style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", cursor: "pointer", userSelect: "none" }}>
                      Extracted Data
                    </summary>
                    <pre style={{
                      background: "var(--color-surface)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-md)",
                      padding: 12,
                      overflow: "auto",
                      maxHeight: 300,
                      fontSize: 12,
                      lineHeight: 1.5,
                      color: "var(--color-text)",
                      marginTop: 8,
                    }}>
                      {JSON.stringify(result.extracted_data, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state — no search yet */}
      {!isSearching && !hasSearched && results.length === 0 && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{
            width: 64, height: 64, borderRadius: 16,
            background: "linear-gradient(135deg, #059669, #34d399)",
            display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16,
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>Enter a search query above to get started</h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            Search the web and extract structured data from the results automatically.
          </p>
        </div>
      )}

      {/* Empty state — searched but no results */}
      {!isSearching && hasSearched && results.length === 0 && !error && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>No results found</h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            Try a different search query.
          </p>
        </div>
      )}
    </div>
  );
}

export default SearchPage;
