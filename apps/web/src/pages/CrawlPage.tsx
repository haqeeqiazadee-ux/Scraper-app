/**
 * CrawlPage — Recursively crawl websites and extract structured data.
 */

import { useState, useEffect, useRef, type FormEvent } from "react";
import { crawl } from "../api/client";

type CrawlStatus = "running" | "completed" | "stopped" | "failed";

interface CrawlData {
  crawl_id: string;
  status: CrawlStatus;
  pages_crawled?: number;
  items_extracted?: number;
  started_at?: string;
  elapsed_ms?: number;
}

export function CrawlPage() {
  const [url, setUrl] = useState("");
  const [maxDepth, setMaxDepth] = useState(3);
  const [maxPages, setMaxPages] = useState(100);
  const [outputFormat, setOutputFormat] = useState("json");
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState("");

  const [crawlId, setCrawlId] = useState<string | null>(null);
  const [crawlData, setCrawlData] = useState<CrawlData | null>(null);
  const [results, setResults] = useState<unknown[] | null>(null);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Poll crawl status every 3 seconds when running
  useEffect(() => {
    if (!crawlId || crawlData?.status === "completed" || crawlData?.status === "stopped" || crawlData?.status === "failed") {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    intervalRef.current = setInterval(async () => {
      try {
        const data = await crawl.get(crawlId);
        setCrawlData(data);
        if (startTime) {
          setElapsed(Math.floor((Date.now() - startTime) / 1000));
        }
      } catch {
        // keep polling
      }
    }, 3000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [crawlId, crawlData?.status, startTime]);

  // Elapsed timer
  useEffect(() => {
    if (!startTime || crawlData?.status !== "running") return;
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [startTime, crawlData?.status]);

  async function handleStart(e: FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;

    setIsStarting(true);
    setError("");
    setResults(null);

    try {
      const res = await crawl.start({
        seed_urls: [url.trim()],
        max_depth: maxDepth,
        max_pages: maxPages,
        output_format: outputFormat,
      });
      setCrawlId(res.crawl_id);
      setCrawlData({ crawl_id: res.crawl_id, status: res.status as CrawlStatus });
      setStartTime(Date.now());
      setElapsed(0);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start crawl";
      setError(msg);
    } finally {
      setIsStarting(false);
    }
  }

  async function handleStop() {
    if (!crawlId) return;
    try {
      await crawl.stop(crawlId);
      setCrawlData((prev) => prev ? { ...prev, status: "stopped" } : prev);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to stop crawl";
      setError(msg);
    }
  }

  async function handleViewResults() {
    if (!crawlId) return;
    try {
      const res = await crawl.results(crawlId);
      setResults(res.items ?? res.results ?? [res]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to fetch results";
      setError(msg);
    }
  }

  function formatElapsed(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  }

  function statusColor(status: CrawlStatus): string {
    switch (status) {
      case "running": return "#2563eb";
      case "completed": return "#059669";
      case "stopped": return "#d97706";
      case "failed": return "#dc2626";
      default: return "#6b7280";
    }
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "32px 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 16,
            background: "linear-gradient(135deg, #4f46e5 0%, #818cf8 100%)",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a1 1 0 011 1v1a1 1 0 01-2 0V3a1 1 0 011-1z" />
              <path d="M12 19a1 1 0 011 1v1a1 1 0 01-2 0v-1a1 1 0 011-1z" />
              <path d="M4.93 4.93a1 1 0 011.41 0l.71.71a1 1 0 01-1.41 1.41l-.71-.71a1 1 0 010-1.41z" />
              <path d="M16.95 16.95a1 1 0 011.41 0l.71.71a1 1 0 01-1.41 1.41l-.71-.71a1 1 0 010-1.41z" />
              <path d="M2 12a1 1 0 011-1h1a1 1 0 010 2H3a1 1 0 01-1-1z" />
              <path d="M19 12a1 1 0 011-1h1a1 1 0 010 2h-1a1 1 0 01-1-1z" />
              <path d="M6.34 17.66a1 1 0 010-1.41l.71-.71a1 1 0 011.41 1.41l-.71.71a1 1 0 01-1.41 0z" />
              <path d="M15.54 8.46a1 1 0 010-1.41l.71-.71a1 1 0 011.41 1.41l-.71.71a1 1 0 01-1.41 0z" />
              <circle cx="12" cy="12" r="4" />
            </svg>
          </div>
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)", margin: 0 }}>Web Crawl</h2>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
              Recursively crawl websites, extract structured data from every page
            </p>
          </div>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleStart} style={{ marginBottom: 24 }}>
        <div className="accent-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                URL
              </label>
              <input
                type="text"
                placeholder="https://example.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={isStarting}
                style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, boxSizing: "border-box" }}
              />
            </div>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 140 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                  Max Depth
                </label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={maxDepth}
                  onChange={(e) => setMaxDepth(Number(e.target.value))}
                  disabled={isStarting}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, boxSizing: "border-box" }}
                />
              </div>
              <div style={{ flex: 1, minWidth: 140 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                  Max Pages
                </label>
                <input
                  type="number"
                  min={1}
                  max={10000}
                  value={maxPages}
                  onChange={(e) => setMaxPages(Number(e.target.value))}
                  disabled={isStarting}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, boxSizing: "border-box" }}
                />
              </div>
              <div style={{ flex: 1, minWidth: 140 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                  Output Format
                </label>
                <select
                  value={outputFormat}
                  onChange={(e) => setOutputFormat(e.target.value)}
                  disabled={isStarting}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, cursor: "pointer", boxSizing: "border-box" }}
                >
                  <option value="json">JSON</option>
                  <option value="markdown">Markdown</option>
                  <option value="html">HTML</option>
                </select>
              </div>
            </div>
            <div>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isStarting || !url.trim()}
                style={{ height: 44, paddingInline: 28 }}
              >
                {isStarting ? (
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                    <span className="spinner" /> Starting...
                  </span>
                ) : "Start Crawl"}
              </button>
            </div>
          </div>
        </div>
      </form>

      {/* Error */}
      {error && <div className="form-error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Active Crawl */}
      {crawlData && (
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 12 }}>Active Crawl</h3>
          <div className="accent-card" style={{ padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{
                    display: "inline-block",
                    padding: "3px 10px",
                    borderRadius: 9999,
                    fontSize: 12,
                    fontWeight: 600,
                    color: "white",
                    background: statusColor(crawlData.status),
                  }}>
                    {crawlData.status}
                  </span>
                  <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                    ID: {crawlData.crawl_id}
                  </span>
                </div>
                <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Pages Crawled</div>
                    <div style={{ fontSize: 20, fontWeight: 700, color: "var(--color-text)" }}>{crawlData.pages_crawled ?? 0}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Items Extracted</div>
                    <div style={{ fontSize: 20, fontWeight: 700, color: "var(--color-text)" }}>{crawlData.items_extracted ?? 0}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Elapsed</div>
                    <div style={{ fontSize: 20, fontWeight: 700, color: "var(--color-text)" }}>{formatElapsed(elapsed)}</div>
                  </div>
                </div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                {crawlData.status === "running" && (
                  <button className="btn btn-danger" onClick={handleStop} style={{ height: 38, paddingInline: 20 }}>
                    Stop
                  </button>
                )}
                {crawlData.status === "completed" && (
                  <button className="btn btn-primary" onClick={handleViewResults} style={{ height: 38, paddingInline: 20 }}>
                    View Results
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {results && (
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 12 }}>
            Crawl Results
            <span style={{ fontSize: 13, fontWeight: 400, color: "var(--color-text-secondary)", marginLeft: 8 }}>
              ({Array.isArray(results) ? results.length : 0} items)
            </span>
          </h3>
          <div className="accent-card" style={{ padding: 24 }}>
            <pre style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              padding: 16,
              overflow: "auto",
              maxHeight: 500,
              fontSize: 13,
              lineHeight: 1.5,
              color: "var(--color-text)",
              margin: 0,
            }}>
              {JSON.stringify(results, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!crawlData && !isStarting && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{
            width: 64, height: 64, borderRadius: 16,
            background: "linear-gradient(135deg, #4f46e5, #818cf8)",
            display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16,
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a1 1 0 011 1v1a1 1 0 01-2 0V3a1 1 0 011-1z" />
              <path d="M12 19a1 1 0 011 1v1a1 1 0 01-2 0v-1a1 1 0 011-1z" />
              <circle cx="12" cy="12" r="4" />
            </svg>
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>Ready to crawl</h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            Enter a URL above and configure crawl settings to start extracting data from websites.
          </p>
        </div>
      )}
    </div>
  );
}

export default CrawlPage;
