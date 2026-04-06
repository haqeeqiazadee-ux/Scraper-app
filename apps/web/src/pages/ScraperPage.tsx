/**
 * ScraperPage — Unified scraper page with 5 tabs:
 * Scrape, Auth Scrape, Crawl, Search, Extract.
 * Replaces ScrapeTestPage, AuthScrapePage, CrawlPage, SearchPage, ExtractPage.
 */

import { useState, useRef, useEffect, type FormEvent, type ChangeEvent } from "react";
import { scrapeTest, authScrape, crawl, search, extract, type TestScrapeResult } from "../api/client";

type TabId = "scrape" | "auth-scrape" | "crawl" | "search" | "extract";

const TABS: { id: TabId; label: string }[] = [
  { id: "scrape", label: "Scrape" },
  { id: "auth-scrape", label: "Auth Scrape" },
  { id: "crawl", label: "Crawl" },
  { id: "search", label: "Search" },
  { id: "extract", label: "Extract" },
];

const TAB_SUBTITLES: Record<TabId, string> = {
  scrape: "Extract data from any single URL instantly",
  "auth-scrape": "Scrape login-required pages using your browser cookies",
  crawl: "Recursively crawl websites and extract structured data",
  search: "Search the web and extract structured data from results",
  extract: "Extract specific fields from any webpage using a schema",
};

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
      {children}
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
          <div className="stat-value" style={{ fontSize: s.fontSize ?? 20, color: s.color, textTransform: s.label === "Method" ? "capitalize" as const : undefined }}>
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

function RawJson({ data }: { data: unknown }) {
  return (
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
          {JSON.stringify(data, null, 2)}
        </pre>
      </details>
    </div>
  );
}

/* ============================================================
 * Tab 1: Scrape
 * ============================================================ */

function ScrapeTab() {
  const [url, setUrl] = useState("https://yousell.online");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestScrapeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<boolean | null>(null);

  const handleTest = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setSaved(null);
    try {
      const res = await scrapeTest.run(url.trim(), 20000, "everything", true);
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
      <InfoBox>
        <span style={{ fontSize: 16, lineHeight: 1 }}>&#9889;</span>
        <div>
          <strong style={{ color: "var(--color-text)" }}>Scrape</strong> extracts data from any single URL instantly using full "everything" mode. Products, content, headings, links, and metadata are all captured. Results are auto-saved.
          <br />
          <span style={{ fontSize: 12 }}>
            <strong>Use cases:</strong> Product research, content monitoring, competitive analysis &nbsp;|&nbsp;
            <strong>Limitation:</strong> Single page only -- use Crawl for multi-page sites
          </span>
        </div>
      </InfoBox>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8 }}>
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
            ) : "Scrape"}
          </button>
        </div>
      </div>

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

      {result && (
        <>
          <StatsGrid stats={[
            { label: "Status", value: result.status?.toUpperCase() ?? "N/A", color: result.status === "success" ? "var(--color-success)" : "var(--color-error)" },
            { label: "HTTP Code", value: result.status_code ?? "N/A" },
            { label: "Items Found", value: result.item_count },
            { label: "Confidence", value: `${(result.confidence * 100).toFixed(0)}%` },
            { label: "Duration", value: `${result.duration_ms}ms` },
            { label: "Method", value: result.extraction_method ?? "N/A", fontSize: 14 },
          ]} />

          {result.error && (
            <div className="form-error-banner" style={{ marginBottom: 16 }}>
              <strong>Extraction Error:</strong> {result.error}
            </div>
          )}

          <DataTable data={result.extracted_data} />
          <RawJson data={result} />
        </>
      )}

      {!result && !error && !loading && (
        <div className="empty-state">
          <div className="empty-state-icon">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <h3>Ready to Scrape</h3>
          <p>Enter a URL above and click "Scrape" to extract all data from the page.</p>
        </div>
      )}
    </>
  );
}

/* ============================================================
 * Tab 2: Auth Scrape
 * ============================================================ */

type AuthSubTab = "cookie-upload" | "browser-login" | "google-session";
type AuthExtractionMode = "everything" | "table" | "fields" | "links";

interface AuthSessionInfo {
  session_id: string;
  domain: string;
  cookie_count: number;
  status: string;
  created_at: string;
}

interface AuthScrapeResult {
  status: string;
  item_count: number;
  confidence: number;
  extraction_method: string | null;
  extraction_mode: string;
  duration_ms: number;
  error: string | null;
  extracted_data: Record<string, unknown>[];
  saved: boolean;
}

interface Preset {
  id: string;
  name: string;
  icon: string;
  login_url: string;
  description: string;
  default_schema: Record<string, string>;
}

const AUTH_MODE_OPTIONS: { value: AuthExtractionMode; label: string; description: string }[] = [
  { value: "everything", label: "Everything", description: "Full page: products + content + headings + links + metadata" },
  { value: "table", label: "Table Data", description: "Extract HTML tables as structured rows" },
  { value: "fields", label: "Specific Fields", description: "Define your own extraction schema" },
  { value: "links", label: "Links", description: "Extract all links from the page" },
];

const PRESET_ICONS: Record<string, JSX.Element> = {
  briefcase: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
      <path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2" />
    </svg>
  ),
  camera: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z" />
      <circle cx="12" cy="13" r="4" />
    </svg>
  ),
  bird: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M23 3a10.9 10.9 0 01-3.14 1.53A4.48 4.48 0 0012 7.5v1A10.66 10.66 0 013 4s-4 9 5 13a11.64 11.64 0 01-7 2c9 5 20 0 20-11.5a4.5 4.5 0 00-.08-.83A7.72 7.72 0 0023 3z" />
    </svg>
  ),
  alien: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <circle cx="9" cy="10" r="1.5" fill="currentColor" />
      <circle cx="15" cy="10" r="1.5" fill="currentColor" />
      <path d="M9 15c1.5 1 4.5 1 6 0" />
    </svg>
  ),
  store: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  ),
  chart: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  ),
  table: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="3" y1="9" x2="21" y2="9" />
      <line x1="3" y1="15" x2="21" y2="15" />
      <line x1="9" y1="3" x2="9" y2="21" />
      <line x1="15" y1="3" x2="15" y2="21" />
    </svg>
  ),
  folder: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
    </svg>
  ),
  search: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
  mail: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
      <polyline points="22,6 12,13 2,6" />
    </svg>
  ),
  video: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="23 7 16 12 23 17 23 7" />
      <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
    </svg>
  ),
};

function AuthScrapeTab() {
  const [activeSubTab, setActiveSubTab] = useState<AuthSubTab>("cookie-upload");

  // Cookie upload
  const [cookies, setCookies] = useState<any[]>([]);
  const [cookieDomain, setCookieDomain] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Session
  const [sessionInfo, setSessionInfo] = useState<AuthSessionInfo | null>(null);

  // Scrape form
  const [targetUrl, setTargetUrl] = useState("");
  const [extractionMode, setExtractionMode] = useState<AuthExtractionMode>("everything");
  const [customSchema, setCustomSchema] = useState('{\n  "title": "string",\n  "price": "number",\n  "description": "string"\n}');
  const [maxPages, setMaxPages] = useState(1);

  // Scrape result
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AuthScrapeResult | null>(null);
  const [error, setError] = useState("");

  // Presets
  const presets: Preset[] = [
    { id: "linkedin", name: "LinkedIn", icon: "briefcase", login_url: "https://www.linkedin.com/login", description: "Professional profiles, connections, job listings", default_schema: { name: "string", title: "string", company: "string", connections: "string" } },
    { id: "instagram", name: "Instagram", icon: "camera", login_url: "https://www.instagram.com/accounts/login", description: "User profiles, posts, followers, engagement metrics", default_schema: { username: "string", posts: "number", followers: "number", following: "number" } },
    { id: "twitter", name: "Twitter / X", icon: "bird", login_url: "https://twitter.com/login", description: "Tweets, followers, following, engagement data", default_schema: { tweets: "number", followers: "number", following: "number" } },
    { id: "reddit", name: "Reddit", icon: "alien", login_url: "https://www.reddit.com/login", description: "Posts, karma, saved content, subreddit data", default_schema: { posts: "number", karma: "number", saved: "number" } },
    { id: "shopify", name: "Shopify Admin", icon: "store", login_url: "https://myshopify.com/admin", description: "Orders, products, revenue from your Shopify store", default_schema: { orders: "number", products: "number", revenue: "number" } },
    { id: "google-analytics", name: "Google Analytics", icon: "chart", login_url: "https://analytics.google.com", description: "Sessions, users, pageviews, traffic analytics", default_schema: { sessions: "number", users: "number", pageviews: "number" } },
  ];

  const googlePresets: Preset[] = [
    { id: "google-sheets", name: "Google Sheets", icon: "table", login_url: "https://docs.google.com/spreadsheets", description: "Scrape spreadsheet data as a logged-in user", default_schema: { spreadsheet_title: "string", sheet_name: "string", rows: "number", columns: "number" } },
    { id: "google-drive", name: "Google Drive", icon: "folder", login_url: "https://drive.google.com", description: "Scrape file listings from your Drive", default_schema: { file_name: "string", type: "string", size: "string", modified: "string" } },
    { id: "google-analytics2", name: "Google Analytics", icon: "chart", login_url: "https://analytics.google.com", description: "Scrape traffic reports and dashboard data", default_schema: { sessions: "number", users: "number", pageviews: "number", bounce_rate: "number" } },
    { id: "google-search-console", name: "Search Console", icon: "search", login_url: "https://search.google.com/search-console", description: "Scrape search performance and indexing data", default_schema: { query: "string", clicks: "number", impressions: "number", ctr: "number", position: "number" } },
    { id: "gmail", name: "Gmail", icon: "mail", login_url: "https://mail.google.com", description: "Scrape email subjects, senders, dates from inbox", default_schema: { subject: "string", from: "string", date: "string", snippet: "string" } },
    { id: "youtube-studio", name: "YouTube Studio", icon: "video", login_url: "https://studio.youtube.com", description: "Scrape channel analytics, video performance", default_schema: { video_title: "string", views: "number", likes: "number", comments: "number" } },
  ];

  // Google cookie upload
  const googleFileRef = useRef<HTMLInputElement | null>(null);
  const [googleCookies, setGoogleCookies] = useState<any[]>([]);
  const [googleCookieInfo, setGoogleCookieInfo] = useState("");
  const [googleUploading, setGoogleUploading] = useState(false);

  function handleGoogleCookieFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target?.result as string);
        const arr = Array.isArray(parsed) ? parsed : [parsed];
        const googleOnly = arr.filter((c: any) => {
          const domain = (c.domain || c.Domain || "").toLowerCase();
          return domain.includes("google.") || domain.includes(".google.") || domain.includes("youtube.") || domain.includes("gmail.");
        });
        if (googleOnly.length === 0) {
          setError("No Google cookies found. Make sure you export cookies while logged into a Google service.");
          setGoogleCookies([]);
          setGoogleCookieInfo("");
          return;
        }
        setGoogleCookies(googleOnly);
        const domains = [...new Set(googleOnly.map((c: any) => c.domain || c.Domain))].slice(0, 5).join(", ");
        setGoogleCookieInfo(`${googleOnly.length} Google cookies found (${domains})`);
        setError("");
      } catch {
        setError("Invalid JSON file. Export cookies using Cookie-Editor extension.");
        setGoogleCookies([]);
        setGoogleCookieInfo("");
      }
    };
    reader.readAsText(file);
  }

  async function handleGoogleSessionCreate() {
    if (googleCookies.length === 0) return;
    setGoogleUploading(true);
    setError("");
    try {
      const res = await authScrape.uploadSession(googleCookies, "google.com");
      setSessionInfo(res);
      setGoogleCookieInfo("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create Google session");
    } finally {
      setGoogleUploading(false);
    }
  }

  function handleGoogleDisconnect() {
    if (!sessionInfo?.session_id) return;
    authScrape.deleteSession(sessionInfo.session_id).catch(() => {});
    setSessionInfo(null);
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target?.result as string);
        const cookieArray = Array.isArray(parsed) ? parsed : [parsed];
        setCookies(cookieArray);
        for (const c of cookieArray) {
          if (c.domain) {
            setCookieDomain(String(c.domain).replace(/^\./, ""));
            break;
          }
        }
        setError("");
      } catch {
        setError("Invalid JSON file. Please upload a valid cookies.json.");
        setCookies([]);
        setCookieDomain("");
      }
    };
    reader.readAsText(file);
  }

  async function handleCreateSession() {
    if (cookies.length === 0) return;
    setIsUploading(true);
    setError("");
    try {
      const res = await authScrape.uploadSession(cookies, cookieDomain || undefined);
      setSessionInfo({
        session_id: res.session_id,
        domain: res.domain,
        cookie_count: res.cookie_count,
        status: res.status,
        created_at: res.created_at,
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create session");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleScrape(e: FormEvent) {
    e.preventDefault();
    if (!sessionInfo || !targetUrl.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      let schema: Record<string, any> | undefined;
      if (extractionMode === "fields") {
        try {
          schema = JSON.parse(customSchema);
        } catch {
          setError("Invalid JSON schema. Please check your extraction schema.");
          setLoading(false);
          return;
        }
      }
      const res = await authScrape.scrape({
        session_id: sessionInfo.session_id,
        target_url: targetUrl.trim(),
        extraction_mode: extractionMode,
        schema,
        max_pages: maxPages,
      });
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Scrape failed");
    } finally {
      setLoading(false);
    }
  }

  function handlePresetClick(preset: Preset) {
    setTargetUrl(preset.login_url);
    setExtractionMode("fields");
    setCustomSchema(JSON.stringify(preset.default_schema, null, 2));
  }

  const canScrape = sessionInfo !== null && targetUrl.trim().length > 0 && !loading;

  return (
    <>
      <InfoBox>
        <span style={{ fontSize: 16, lineHeight: 1 }}>&#128274;</span>
        <div>
          <strong style={{ color: "var(--color-text)" }}>Authenticated Scrape</strong> lets you extract data from websites that require login. Export cookies from your browser session, upload them here, and scrape pages as if you were logged in.
          <br />
          <span style={{ fontSize: 12 }}>
            <strong>Use cases:</strong> LinkedIn profiles, Instagram analytics, Reddit saved posts, Shopify admin &nbsp;|&nbsp;
            <strong>Requires:</strong> Browser cookies exported as JSON (Cookie-Editor extension recommended)
          </span>
        </div>
      </InfoBox>

      {/* Sub-tabs */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", gap: 0, marginBottom: 0 }}>
          {([
            { id: "cookie-upload" as AuthSubTab, label: "Cookie Upload" },
            { id: "browser-login" as AuthSubTab, label: "Browser Login" },
            { id: "google-session" as AuthSubTab, label: "Google Session" },
          ]).map((tab, idx, arr) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveSubTab(tab.id)}
              style={{
                padding: "10px 24px",
                fontSize: 14,
                fontWeight: activeSubTab === tab.id ? 700 : 500,
                border: "1px solid var(--color-border)",
                borderBottom: activeSubTab === tab.id ? "2px solid var(--color-primary)" : "1px solid var(--color-border)",
                background: activeSubTab === tab.id ? "var(--color-surface)" : "transparent",
                color: activeSubTab === tab.id ? "var(--color-primary)" : "var(--color-text-secondary)",
                cursor: "pointer",
                borderRadius: idx === 0 ? "8px 0 0 0" : idx === arr.length - 1 ? "0 8px 0 0" : "0",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="accent-card" style={{ padding: 24, borderTopLeftRadius: 0 }}>
          {activeSubTab === "cookie-upload" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                  Cookies File (JSON)
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json"
                  onChange={handleFileChange}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, boxSizing: "border-box" }}
                />
                <p style={{ fontSize: 11, color: "var(--color-text-secondary)", margin: "6px 0 0" }}>
                  Export cookies from your browser using the Cookie-Editor extension
                </p>
              </div>
              {cookies.length > 0 && (
                <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 14px", borderRadius: 8, background: "rgba(5, 150, 105, 0.08)", border: "1px solid rgba(5, 150, 105, 0.2)" }}>
                  <span style={{ fontSize: 14 }}>&#9989;</span>
                  <span style={{ fontSize: 13, color: "var(--color-text)" }}>
                    <strong>{cookies.length}</strong> cookies loaded
                    {cookieDomain && (<> &mdash; detected domain: <strong>{cookieDomain}</strong></>)}
                  </span>
                </div>
              )}
              <div>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleCreateSession}
                  disabled={cookies.length === 0 || isUploading}
                  style={{ height: 44, paddingInline: 28 }}
                >
                  {isUploading ? (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                      <span className="spinner" /> Creating Session...
                    </span>
                  ) : "Upload & Create Session"}
                </button>
              </div>
            </div>
          )}

          {activeSubTab === "browser-login" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <p style={{ fontSize: 14, color: "var(--color-text)", lineHeight: 1.7, margin: 0 }}>
                Since most websites block embedding via iframes, use this guided flow to export your session cookies:
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: "0 8px" }}>
                {[
                  "Log into the target website in your browser normally.",
                  "Install the Cookie-Editor browser extension.",
                  "Click the Cookie-Editor icon and click \"Export\" (JSON format).",
                  "Save the exported file as cookies.json.",
                  "Switch to the \"Cookie Upload\" tab above and upload the file.",
                ].map((step, i) => (
                  <div key={i} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                    <span style={{
                      width: 24, height: 24, borderRadius: "50%",
                      background: "var(--color-primary)", color: "white",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 12, fontWeight: 700, flexShrink: 0,
                    }}>
                      {i + 1}
                    </span>
                    <span style={{ fontSize: 14, color: "var(--color-text)", lineHeight: 1.6 }}>{step}</span>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 8 }}>
                <a
                  href="https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: "inline-flex", alignItems: "center", gap: 8,
                    padding: "8px 18px", borderRadius: 8,
                    background: "rgba(99, 102, 241, 0.1)",
                    border: "1px solid var(--color-primary)",
                    color: "var(--color-primary)",
                    fontSize: 13, fontWeight: 600,
                    textDecoration: "none",
                  }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
                    <polyline points="15 3 21 3 21 9" />
                    <line x1="10" y1="14" x2="21" y2="3" />
                  </svg>
                  Get Cookie-Editor for Chrome
                </a>
              </div>
            </div>
          )}

          {activeSubTab === "google-session" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                <svg width="32" height="32" viewBox="0 0 48 48">
                  <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                  <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                  <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                  <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                </svg>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)" }}>Google Session</div>
                  <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                    Use your active Google login to scrape Sheets, Drive, Analytics, Gmail, YouTube Studio, and any Google SSO site
                  </div>
                </div>
              </div>

              <div style={{ padding: "12px 16px", borderRadius: 8, background: "rgba(66, 133, 244, 0.06)", border: "1px solid rgba(66, 133, 244, 0.15)", fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.6 }}>
                <strong style={{ color: "var(--color-text)" }}>How it works:</strong> Export your Google cookies from your browser while logged into Gmail/Google. The scraper uses your active session to access Google services exactly as you see them -- no API keys needed.
                <ol style={{ margin: "8px 0 0", paddingLeft: 20, fontSize: 12 }}>
                  <li>Log into <strong>Gmail</strong> or any Google service in your browser</li>
                  <li>Install <a href="https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm" target="_blank" rel="noopener" style={{ color: "var(--color-primary)" }}>Cookie-Editor</a> extension</li>
                  <li>Click the extension icon, then <strong>Export</strong>, then <strong>Export as JSON</strong></li>
                  <li>Upload the JSON file below</li>
                </ol>
              </div>

              <div>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                  Google Cookies File
                </label>
                <input
                  ref={googleFileRef}
                  type="file"
                  accept=".json"
                  onChange={handleGoogleCookieFile}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 13, boxSizing: "border-box" }}
                />
                {googleCookieInfo && (
                  <div style={{ fontSize: 12, color: "#059669", marginTop: 6, fontWeight: 500 }}>{googleCookieInfo}</div>
                )}
              </div>

              {googleCookies.length > 0 && !sessionInfo && (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleGoogleSessionCreate}
                  disabled={googleUploading}
                  style={{ height: 44, paddingInline: 28, alignSelf: "flex-start" }}
                >
                  {googleUploading ? "Creating Session..." : `Create Google Session (${googleCookies.length} cookies)`}
                </button>
              )}

              {sessionInfo && sessionInfo.domain?.includes("google") && (
                <div style={{ padding: "10px 16px", borderRadius: 8, border: "1px solid rgba(5, 150, 105, 0.3)", background: "rgba(5, 150, 105, 0.06)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: 13, color: "#059669", fontWeight: 600 }}>
                    Google session active -- ready to scrape
                  </span>
                  <button type="button" onClick={handleGoogleDisconnect} style={{
                    padding: "4px 12px", borderRadius: 6, border: "1px solid var(--color-border)",
                    background: "transparent", color: "var(--color-text-secondary)", fontSize: 11,
                    fontWeight: 600, cursor: "pointer",
                  }}>
                    Disconnect
                  </button>
                </div>
              )}

              <div>
                <h4 style={{ fontSize: 14, fontWeight: 600, color: "var(--color-text)", marginBottom: 10 }}>
                  Google Services -- click to pre-fill
                </h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 10 }}>
                  {googlePresets.map((preset) => (
                    <button
                      key={preset.id}
                      type="button"
                      onClick={() => handlePresetClick(preset)}
                      style={{
                        display: "flex", alignItems: "flex-start", gap: 10,
                        padding: 12, borderRadius: 8,
                        border: "1px solid var(--color-border)",
                        background: "var(--color-surface)",
                        cursor: "pointer", textAlign: "left",
                        transition: "all 0.15s",
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--color-primary)"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--color-border)"; }}
                    >
                      <div style={{
                        width: 32, height: 32, borderRadius: 6,
                        background: "linear-gradient(135deg, #4285F4, #34A853)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        flexShrink: 0, color: "white",
                      }}>
                        {PRESET_ICONS[preset.icon] ?? (
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /></svg>
                        )}
                      </div>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text)" }}>{preset.name}</div>
                        <div style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>{preset.description}</div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Session Confirmation */}
      {sessionInfo && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ padding: "14px 18px", borderRadius: 10, border: "1px solid rgba(5, 150, 105, 0.3)", background: "rgba(5, 150, 105, 0.06)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              <span style={{ display: "inline-block", padding: "3px 10px", borderRadius: 9999, fontSize: 12, fontWeight: 600, color: "#059669", background: "rgba(5, 150, 105, 0.15)" }}>
                Active
              </span>
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--color-text)" }}>
                Session created for {sessionInfo.domain} ({sessionInfo.cookie_count} cookies)
              </span>
            </div>
            <div style={{ display: "flex", gap: 24, flexWrap: "wrap", fontSize: 12, color: "var(--color-text-secondary)" }}>
              <span>ID: <code style={{ fontFamily: "var(--font-mono)" }}>{sessionInfo.session_id.slice(0, 12)}...</code></span>
              <span>Domain: <strong>{sessionInfo.domain}</strong></span>
              <span>Status: <strong style={{ color: "#059669" }}>{sessionInfo.status}</strong></span>
            </div>
          </div>
        </div>
      )}

      {/* Scrape Form */}
      {sessionInfo && (
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 12 }}>
            Scrape Requirements
          </h3>
          <form onSubmit={handleScrape}>
            <div className="accent-card" style={{ padding: 24 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Target URL</label>
                  <input
                    type="text"
                    placeholder="https://www.linkedin.com/in/username"
                    value={targetUrl}
                    onChange={(e) => setTargetUrl(e.target.value)}
                    disabled={loading}
                    style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, boxSizing: "border-box" }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Extraction Mode</label>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {AUTH_MODE_OPTIONS.map((opt) => (
                      <button key={opt.value} type="button" onClick={() => setExtractionMode(opt.value)} title={opt.description} style={{
                        padding: "6px 14px", fontSize: 13, fontWeight: extractionMode === opt.value ? 700 : 500, borderRadius: 6,
                        border: extractionMode === opt.value ? "2px solid var(--color-primary)" : "1px solid var(--color-border)",
                        background: extractionMode === opt.value ? "rgba(99, 102, 241, 0.1)" : "transparent",
                        color: extractionMode === opt.value ? "var(--color-primary)" : "var(--color-text-secondary)",
                        cursor: "pointer", transition: "all 0.15s",
                      }}>
                        {opt.label}
                      </button>
                    ))}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 4 }}>
                    {AUTH_MODE_OPTIONS.find((o) => o.value === extractionMode)?.description}
                  </div>
                </div>

                {extractionMode === "fields" && (
                  <div>
                    <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Extraction Schema (JSON)</label>
                    <textarea
                      value={customSchema}
                      onChange={(e) => setCustomSchema(e.target.value)}
                      placeholder='{"title": "string", "price": "number"}'
                      rows={6}
                      style={{ width: "100%", fontFamily: "var(--font-mono)", fontSize: 13, padding: 12, borderRadius: 8, border: "1px solid var(--color-border)", background: "var(--color-bg)", color: "var(--color-text)", resize: "vertical", boxSizing: "border-box" }}
                    />
                  </div>
                )}

                <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
                  <div style={{ flex: 1, minWidth: 140, maxWidth: 200 }}>
                    <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Max Pages</label>
                    <input type="number" min={1} max={100} value={maxPages} onChange={(e) => setMaxPages(Number(e.target.value))} disabled={loading}
                      style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, boxSizing: "border-box" }} />
                  </div>
                  <div>
                    <button type="submit" className="btn btn-primary" disabled={!canScrape} style={{ height: 44, paddingInline: 28 }}>
                      {loading ? (<span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}><span className="spinner" /> Scraping...</span>) : "Scrape"}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </form>
        </div>
      )}

      <ErrorBanner message={error} />

      {/* Results */}
      {result && (
        <>
          <StatsGrid stats={[
            { label: "Status", value: result.status?.toUpperCase() ?? "N/A", color: result.status === "success" ? "var(--color-success)" : "var(--color-error)" },
            { label: "Items Found", value: result.item_count },
            { label: "Confidence", value: `${(result.confidence * 100).toFixed(0)}%` },
            { label: "Duration", value: `${result.duration_ms}ms` },
            { label: "Method", value: result.extraction_method ?? "N/A", fontSize: 14 },
            { label: "Saved", value: result.saved ? "Yes" : "No", color: result.saved ? "var(--color-success)" : "var(--color-text-secondary)" },
          ]} />
          {result.error && <div className="form-error-banner" style={{ marginBottom: 16 }}><strong>Extraction Error:</strong> {result.error}</div>}
          <DataTable data={result.extracted_data} />
          <RawJson data={result} />
        </>
      )}

      {/* Preset Cards */}
      <div style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 12 }}>Popular Site Presets</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
          {presets.map((preset) => (
            <button key={preset.id} type="button" onClick={() => handlePresetClick(preset)} style={{
              display: "flex", alignItems: "flex-start", gap: 14, padding: 16, borderRadius: 10,
              border: "1px solid var(--color-border)", background: "var(--color-surface)",
              cursor: "pointer", textAlign: "left", transition: "all 0.15s",
            }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--color-primary)"; e.currentTarget.style.background = "rgba(99, 102, 241, 0.04)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--color-border)"; e.currentTarget.style.background = "var(--color-surface)"; }}
            >
              <div style={{ width: 40, height: 40, borderRadius: 10, background: "linear-gradient(135deg, #f59e0b, #ef4444)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, color: "white" }}>
                {PRESET_ICONS[preset.icon] ?? (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /></svg>)}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: "var(--color-text)", marginBottom: 2 }}>{preset.name}</div>
                <div style={{ fontSize: 12, color: "var(--color-text-secondary)", lineHeight: 1.4 }}>{preset.description}</div>
                <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 4 }}>Fields: {Object.keys(preset.default_schema).join(", ")}</div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {!sessionInfo && !result && !loading && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{ width: 64, height: 64, borderRadius: 16, background: "linear-gradient(135deg, #f59e0b, #ef4444)", display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0110 0v4" />
            </svg>
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>Ready to scrape authenticated pages</h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 450, margin: "0 auto" }}>
            Upload your browser cookies to create a session, then enter a URL to scrape pages that require login.
          </p>
        </div>
      )}
    </>
  );
}

/* ============================================================
 * Tab 3: Crawl
 * ============================================================ */

type CrawlStatus = "running" | "completed" | "stopped" | "failed";

interface CrawlData {
  crawl_id: string;
  status: CrawlStatus;
  pages_crawled?: number;
  items_extracted?: number;
  started_at?: string;
  elapsed_ms?: number;
}

function CrawlTab() {
  const [url, setUrl] = useState("");
  const [maxDepth, setMaxDepth] = useState(3);
  const [maxPages, setMaxPages] = useState(100);
  const [outputFormat, setOutputFormat] = useState("json");
  const [crawlFocus, setCrawlFocus] = useState("everything");
  const [includePatterns, setIncludePatterns] = useState("");
  const [excludePatterns, setExcludePatterns] = useState("");
  const [crawlDelay, setCrawlDelay] = useState(0.5);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState("");

  const [crawlId, setCrawlId] = useState<string | null>(null);
  const [crawlData, setCrawlData] = useState<CrawlData | null>(null);
  const [results, setResults] = useState<unknown[] | null>(null);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!crawlId || crawlData?.status === "completed" || crawlData?.status === "stopped" || crawlData?.status === "failed") {
      if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
      return;
    }
    intervalRef.current = setInterval(async () => {
      try {
        const data = await crawl.get(crawlId);
        setCrawlData(data);
        if (startTime) setElapsed(Math.floor((Date.now() - startTime) / 1000));
      } catch { /* keep polling */ }
    }, 3000);
    return () => { if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; } };
  }, [crawlId, crawlData?.status, startTime]);

  useEffect(() => {
    if (!startTime || crawlData?.status !== "running") return;
    const timer = setInterval(() => { setElapsed(Math.floor((Date.now() - startTime) / 1000)); }, 1000);
    return () => clearInterval(timer);
  }, [startTime, crawlData?.status]);

  async function handleStart(e: FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setIsStarting(true);
    setError("");
    setResults(null);
    try {
      const incPatterns = includePatterns.split(",").map((s) => s.trim()).filter(Boolean);
      const excPatterns = excludePatterns.split(",").map((s) => s.trim()).filter(Boolean);
      const res = await crawl.start({
        seed_urls: [url.trim()],
        max_depth: maxDepth,
        max_pages: maxPages,
        output_format: outputFormat,
        crawl_delay: crawlDelay,
        ...(incPatterns.length > 0 ? { url_patterns: incPatterns } : {}),
        ...(excPatterns.length > 0 ? { deny_patterns: excPatterns } : {}),
      });
      setCrawlId(res.crawl_id);
      setCrawlData({ crawl_id: res.crawl_id, status: res.status as CrawlStatus });
      setStartTime(Date.now());
      setElapsed(0);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start crawl");
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
      setError(err instanceof Error ? err.message : "Failed to stop crawl");
    }
  }

  async function handleViewResults() {
    if (!crawlId) return;
    try {
      const res = await crawl.results(crawlId);
      setResults(res.items ?? res.results ?? [res]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to fetch results");
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
    <>
      <InfoBox>
        <span style={{ fontSize: 16, lineHeight: 1 }}>&#128269;</span>
        <div>
          <strong style={{ color: "var(--color-text)" }}>Web Crawl</strong> follows links within a website, extracting data from every page it discovers. Control depth and page limits.
          <br />
          <span style={{ fontSize: 12 }}>
            <strong>Different from Search:</strong> Search takes a keyword query and finds URLs via search engines. Crawl starts from a specific URL and explores the site itself.
          </span>
        </div>
      </InfoBox>

      <form onSubmit={handleStart} style={{ marginBottom: 24 }}>
        <div className="accent-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>URL</label>
              <input type="text" placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)} disabled={isStarting}
                style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, boxSizing: "border-box" }} />
            </div>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 140 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Max Depth</label>
                <input type="number" min={1} max={10} value={maxDepth} onChange={(e) => setMaxDepth(Number(e.target.value))} disabled={isStarting}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, boxSizing: "border-box" }} />
              </div>
              <div style={{ flex: 1, minWidth: 140 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Max Pages</label>
                <input type="number" min={1} max={10000} value={maxPages} onChange={(e) => setMaxPages(Number(e.target.value))} disabled={isStarting}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, boxSizing: "border-box" }} />
              </div>
              <div style={{ flex: 1, minWidth: 140 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Crawl Delay (s)</label>
                <input type="number" min={0} max={10} step={0.5} value={crawlDelay} onChange={(e) => setCrawlDelay(Number(e.target.value))} disabled={isStarting}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, boxSizing: "border-box" }} />
              </div>
              <div style={{ flex: 1, minWidth: 140 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Output Format</label>
                <select value={outputFormat} onChange={(e) => setOutputFormat(e.target.value)} disabled={isStarting}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, cursor: "pointer", boxSizing: "border-box" }}>
                  <option value="json">JSON</option>
                  <option value="markdown">Markdown</option>
                  <option value="html">HTML</option>
                </select>
              </div>
              <div style={{ flex: 1, minWidth: 140 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Extract</label>
                <select value={crawlFocus} onChange={(e) => setCrawlFocus(e.target.value)} disabled={isStarting}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, cursor: "pointer", boxSizing: "border-box" }}>
                  <option value="everything">Everything</option>
                  <option value="products">Products</option>
                  <option value="articles">Articles</option>
                  <option value="links">Links Only</option>
                </select>
              </div>
            </div>

            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 200 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                  Include URL Patterns <span style={{ fontWeight: 400, fontSize: 11 }}>(optional)</span>
                </label>
                <input type="text" placeholder="/products/*, /category/*" value={includePatterns} onChange={(e) => setIncludePatterns(e.target.value)} disabled={isStarting}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 13, boxSizing: "border-box" }} />
                <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 3 }}>Only crawl URLs matching these patterns (comma-separated)</div>
              </div>
              <div style={{ flex: 1, minWidth: 200 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                  Exclude URL Patterns <span style={{ fontWeight: 400, fontSize: 11 }}>(optional)</span>
                </label>
                <input type="text" placeholder="/login, /admin/*, /api/*" value={excludePatterns} onChange={(e) => setExcludePatterns(e.target.value)} disabled={isStarting}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 13, boxSizing: "border-box" }} />
                <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 3 }}>Skip URLs matching these patterns (comma-separated)</div>
              </div>
            </div>

            <div>
              <button type="submit" className="btn btn-primary" disabled={isStarting || !url.trim()} style={{ height: 44, paddingInline: 28 }}>
                {isStarting ? (<span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}><span className="spinner" /> Starting...</span>) : "Start Crawl"}
              </button>
            </div>
          </div>
        </div>
      </form>

      <ErrorBanner message={error} />

      {crawlData && (
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 12 }}>Active Crawl</h3>
          <div className="accent-card" style={{ padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ display: "inline-block", padding: "3px 10px", borderRadius: 9999, fontSize: 12, fontWeight: 600, color: "white", background: statusColor(crawlData.status) }}>
                    {crawlData.status}
                  </span>
                  <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>ID: {crawlData.crawl_id}</span>
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
                  <button className="btn btn-danger" onClick={handleStop} style={{ height: 38, paddingInline: 20 }}>Stop</button>
                )}
                {crawlData.status === "completed" && (
                  <button className="btn btn-primary" onClick={handleViewResults} style={{ height: 38, paddingInline: 20 }}>View Results</button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {results && (
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 12 }}>
            Crawl Results <span style={{ fontSize: 13, fontWeight: 400, color: "var(--color-text-secondary)", marginLeft: 8 }}>({Array.isArray(results) ? results.length : 0} items)</span>
          </h3>
          <div className="accent-card" style={{ padding: 24 }}>
            <pre style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: 16, overflow: "auto", maxHeight: 500, fontSize: 13, lineHeight: 1.5, color: "var(--color-text)", margin: 0 }}>
              {JSON.stringify(results, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {!crawlData && !isStarting && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{ width: 64, height: 64, borderRadius: 16, background: "linear-gradient(135deg, #4f46e5, #818cf8)", display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2a1 1 0 011 1v1a1 1 0 01-2 0V3a1 1 0 011-1z" />
              <path d="M12 19a1 1 0 011 1v1a1 1 0 01-2 0v-1a1 1 0 011-1z" />
            </svg>
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>Ready to crawl</h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            Enter a URL above and configure crawl settings to start extracting data from websites.
          </p>
        </div>
      )}
    </>
  );
}

/* ============================================================
 * Tab 4: Search
 * ============================================================ */

interface SearchResultItem {
  title?: string;
  url?: string;
  status?: string;
  extracted_data?: Record<string, unknown>;
  [key: string]: unknown;
}

function SearchTab() {
  const [query, setQuery] = useState("");
  const [maxResults, setMaxResults] = useState(10);
  const [outputFormat, setOutputFormat] = useState("json");
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setIsSearching(true);
    setError("");
    setHasSearched(true);
    try {
      const res = await search.run({ query: query.trim(), max_results: maxResults, output_format: outputFormat });
      setResults(res.results ?? res.items ?? []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }

  return (
    <>
      <InfoBox>
        <span style={{ fontSize: 16, lineHeight: 1 }}>&#127760;</span>
        <div>
          <strong style={{ color: "var(--color-text)" }}>Web Search</strong> takes a keyword query, finds top results from search engines (Google/Serper), then scrapes each result page to extract structured data.
          <br />
          <span style={{ fontSize: 12 }}>
            <strong>Different from Crawl:</strong> Crawl takes a specific URL and follows internal links. Search takes a keyword and finds relevant pages across the entire web.
          </span>
        </div>
      </InfoBox>

      <form onSubmit={handleSearch} style={{ marginBottom: 24 }}>
        <div className="accent-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Query</label>
              <input type="text" placeholder="Search for anything..." value={query} onChange={(e) => setQuery(e.target.value)} disabled={isSearching}
                style={{ width: "100%", padding: "12px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 16, boxSizing: "border-box" }} />
            </div>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
              <div style={{ minWidth: 140 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Max Results</label>
                <select value={maxResults} onChange={(e) => setMaxResults(Number(e.target.value))} disabled={isSearching}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, cursor: "pointer", boxSizing: "border-box" }}>
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                </select>
              </div>
              <div style={{ minWidth: 140 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Output Format</label>
                <select value={outputFormat} onChange={(e) => setOutputFormat(e.target.value)} disabled={isSearching}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, cursor: "pointer", boxSizing: "border-box" }}>
                  <option value="json">JSON</option>
                  <option value="markdown">Markdown</option>
                </select>
              </div>
              <button type="submit" className="btn btn-primary" disabled={isSearching || !query.trim()} style={{ height: 44, paddingInline: 28 }}>
                {isSearching ? (<span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}><span className="spinner" /> Searching...</span>) : "Search"}
              </button>
            </div>
          </div>
        </div>
      </form>

      <ErrorBanner message={error} />

      {isSearching && (
        <div style={{ textAlign: "center", padding: 60 }}>
          <div className="spinner" style={{ width: 32, height: 32, margin: "0 auto 16px" }} />
          <p style={{ color: "var(--color-text-secondary)" }}>Searching the web...</p>
        </div>
      )}

      {!isSearching && results.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 14, color: "var(--color-text-secondary)", marginBottom: 12 }}>
            <strong style={{ color: "var(--color-text)" }}>{results.length}</strong> result{results.length !== 1 ? "s" : ""} found
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {results.map((r, idx) => (
              <div key={idx} className="accent-card" style={{ padding: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 8 }}>
                  <div style={{ flex: 1 }}>
                    <a href={r.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 16, fontWeight: 600, color: "var(--color-primary)", textDecoration: "none" }}>
                      {r.title || "Untitled"}
                    </a>
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 4, wordBreak: "break-all" }}>{r.url}</div>
                  </div>
                  {r.status && (
                    <span style={{ display: "inline-block", padding: "3px 10px", borderRadius: 9999, fontSize: 12, fontWeight: 600, color: "white", background: r.status === "success" ? "#059669" : "#6b7280", flexShrink: 0 }}>
                      {r.status}
                    </span>
                  )}
                </div>
                {r.extracted_data && Object.keys(r.extracted_data).length > 0 && (
                  <details style={{ marginTop: 8 }}>
                    <summary style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", cursor: "pointer", userSelect: "none" }}>Extracted Data</summary>
                    <pre style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: 12, overflow: "auto", maxHeight: 300, fontSize: 12, lineHeight: 1.5, color: "var(--color-text)", marginTop: 8 }}>
                      {JSON.stringify(r.extracted_data, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!isSearching && !hasSearched && results.length === 0 && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{ width: 64, height: 64, borderRadius: 16, background: "linear-gradient(135deg, #059669, #34d399)", display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
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

      {!isSearching && hasSearched && results.length === 0 && !error && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>No results found</h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>Try a different search query.</p>
        </div>
      )}
    </>
  );
}

/* ============================================================
 * Tab 5: Extract
 * ============================================================ */

interface ExtractResult {
  confidence?: number;
  extraction_method?: string;
  data?: Record<string, unknown>;
  extracted_data?: Record<string, unknown>;
  raw?: unknown;
  [key: string]: unknown;
}

const SCHEMA_PLACEHOLDER = `{
  "name": "string",
  "price": "number",
  "description": "string"
}`;

function ExtractTab() {
  const [url, setUrl] = useState("");
  const [schema, setSchema] = useState("");
  const [outputFormat, setOutputFormat] = useState("json");
  const [isExtracting, setIsExtracting] = useState(false);
  const [result, setResult] = useState<ExtractResult | null>(null);
  const [error, setError] = useState("");

  async function handleExtract(e: FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setIsExtracting(true);
    setError("");
    setResult(null);

    let parsedSchema: Record<string, unknown> | undefined;
    if (schema.trim()) {
      try {
        parsedSchema = JSON.parse(schema.trim());
      } catch {
        setError("Invalid JSON schema. Please check the syntax.");
        setIsExtracting(false);
        return;
      }
    }

    try {
      const res = await extract.run({ url: url.trim(), schema: parsedSchema, output_format: outputFormat });
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Extraction failed");
    } finally {
      setIsExtracting(false);
    }
  }

  const extractedData = result?.data ?? result?.extracted_data ?? null;
  const confidence = result?.confidence;
  const method = result?.extraction_method;

  return (
    <>
      <InfoBox>
        <span style={{ fontSize: 16, lineHeight: 1 }}>&#128196;</span>
        <div>
          <strong style={{ color: "var(--color-text)" }}>Structured Extract</strong> lets you define exactly which fields to extract using a JSON schema. The system scrapes the page and maps data to your schema fields.
          <br />
          <span style={{ fontSize: 12 }}>
            <strong>Use cases:</strong> Extract title+price+availability from product pages, pull author+date+content from articles &nbsp;|&nbsp;
            <strong>Limitation:</strong> Works best on pages with clear HTML structure
          </span>
        </div>
      </InfoBox>

      <form onSubmit={handleExtract} style={{ marginBottom: 24 }}>
        <div className="accent-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>URL</label>
              <input type="text" placeholder="https://example.com/product" value={url} onChange={(e) => setUrl(e.target.value)} disabled={isExtracting}
                style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, boxSizing: "border-box" }} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Schema (JSON)</label>
              <textarea
                placeholder={SCHEMA_PLACEHOLDER}
                value={schema}
                onChange={(e) => setSchema(e.target.value)}
                disabled={isExtracting}
                rows={6}
                style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 13, fontFamily: "monospace", resize: "vertical", boxSizing: "border-box", lineHeight: 1.5 }}
              />
            </div>
            <div style={{ display: "flex", gap: 16, alignItems: "flex-end" }}>
              <div style={{ minWidth: 140 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Output Format</label>
                <select value={outputFormat} onChange={(e) => setOutputFormat(e.target.value)} disabled={isExtracting}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, cursor: "pointer", boxSizing: "border-box" }}>
                  <option value="json">JSON</option>
                  <option value="markdown">Markdown</option>
                </select>
              </div>
              <button type="submit" className="btn btn-primary" disabled={isExtracting || !url.trim()} style={{ height: 44, paddingInline: 28 }}>
                {isExtracting ? (<span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}><span className="spinner" /> Extracting...</span>) : "Extract"}
              </button>
            </div>
          </div>
        </div>
      </form>

      <ErrorBanner message={error} />

      {isExtracting && (
        <div style={{ textAlign: "center", padding: 60 }}>
          <div className="spinner" style={{ width: 32, height: 32, margin: "0 auto 16px" }} />
          <p style={{ color: "var(--color-text-secondary)" }}>Extracting data from page...</p>
        </div>
      )}

      {!isExtracting && result && (
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 12 }}>Extraction Results</h3>

          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
            {confidence != null && (
              <span style={{ display: "inline-block", padding: "4px 12px", borderRadius: 9999, fontSize: 13, fontWeight: 600, color: "white", background: confidence >= 0.8 ? "#059669" : confidence >= 0.5 ? "#d97706" : "#dc2626" }}>
                Confidence: {Math.round(confidence * 100)}%
              </span>
            )}
            {method && (
              <span style={{ display: "inline-block", padding: "4px 12px", borderRadius: 9999, fontSize: 13, fontWeight: 600, color: "var(--color-text)", background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                Method: {method}
              </span>
            )}
          </div>

          {extractedData && Object.keys(extractedData).length > 0 && (
            <div className="accent-card" style={{ padding: 0, marginBottom: 16, overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "var(--color-surface)" }}>
                    <th style={{ textAlign: "left", padding: "10px 16px", fontSize: 12, fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: "1px solid var(--color-border)" }}>Field</th>
                    <th style={{ textAlign: "left", padding: "10px 16px", fontSize: 12, fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: "1px solid var(--color-border)" }}>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(extractedData).map(([key, value]) => (
                    <tr key={key}>
                      <td style={{ padding: "10px 16px", fontSize: 13, fontWeight: 600, color: "var(--color-text)", borderBottom: "1px solid var(--color-border)", whiteSpace: "nowrap" }}>{key}</td>
                      <td style={{ padding: "10px 16px", fontSize: 13, color: "var(--color-text)", borderBottom: "1px solid var(--color-border)", wordBreak: "break-word" }}>
                        {typeof value === "object" ? JSON.stringify(value) : String(value ?? "")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="accent-card" style={{ padding: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 8 }}>Raw JSON</div>
            <pre style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: 16, overflow: "auto", maxHeight: 400, fontSize: 12, lineHeight: 1.5, color: "var(--color-text)", margin: 0 }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {!isExtracting && !result && !error && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{ width: 64, height: 64, borderRadius: 16, background: "linear-gradient(135deg, #7c3aed, #a78bfa)", display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6" />
              <polyline points="8 6 2 12 8 18" />
            </svg>
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>Extract structured data from any page</h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            Enter a URL and define a JSON schema to extract specific fields from the webpage.
          </p>
        </div>
      )}
    </>
  );
}

/* ============================================================
 * Main ScraperPage component
 * ============================================================ */

export function ScraperPage() {
  const [activeTab, setActiveTab] = useState<TabId>("scrape");

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "32px 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)", margin: 0 }}>Scraper</h2>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "4px 0 0" }}>
          {TAB_SUBTITLES[activeTab]}
        </p>
      </div>

      {/* Tab bar */}
      <div style={{ display: "flex", gap: 0, marginBottom: 24, borderBottom: "2px solid var(--color-border)" }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "10px 24px",
              fontSize: 14,
              fontWeight: activeTab === tab.id ? 700 : 500,
              border: "none",
              borderBottom: activeTab === tab.id ? "2px solid var(--color-primary)" : "2px solid transparent",
              background: "transparent",
              color: activeTab === tab.id ? "var(--color-primary)" : "var(--color-text-secondary)",
              cursor: "pointer",
              marginBottom: -2,
              transition: "all 0.15s",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "scrape" && <ScrapeTab />}
      {activeTab === "auth-scrape" && <AuthScrapeTab />}
      {activeTab === "crawl" && <CrawlTab />}
      {activeTab === "search" && <SearchTab />}
      {activeTab === "extract" && <ExtractTab />}
    </div>
  );
}

export default ScraperPage;
