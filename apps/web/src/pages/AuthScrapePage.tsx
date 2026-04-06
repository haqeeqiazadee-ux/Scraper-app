/**
 * AuthScrapePage — Authenticated scraping with cookie-based sessions.
 * Upload browser cookies, create sessions, and scrape login-required pages.
 */

import { useState, useRef, useEffect, type FormEvent, type ChangeEvent } from "react";
import { authScrape } from "../api/client";

type ExtractionMode = "everything" | "table" | "fields" | "links";
type TabId = "cookie-upload" | "browser-login" | "google-account";

interface SessionInfo {
  session_id: string;
  domain: string;
  cookie_count: number;
  status: string;
  created_at: string;
}

interface ScrapeResult {
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

const MODE_OPTIONS: { value: ExtractionMode; label: string; description: string }[] = [
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
};

export function AuthScrapePage() {
  // Tab state
  const [activeTab, setActiveTab] = useState<TabId>("cookie-upload");

  // Cookie upload state
  const [cookies, setCookies] = useState<any[]>([]);
  const [cookieDomain, setCookieDomain] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Session state
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);

  // Scrape form state
  const [targetUrl, setTargetUrl] = useState("");
  const [extractionMode, setExtractionMode] = useState<ExtractionMode>("everything");
  const [customSchema, setCustomSchema] = useState('{\n  "title": "string",\n  "price": "number",\n  "description": "string"\n}');
  const [maxPages, setMaxPages] = useState(1);

  // Scrape result state
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScrapeResult | null>(null);
  const [error, setError] = useState("");

  // Presets
  const [presets] = useState<Preset[]>([
    { id: "linkedin", name: "LinkedIn", icon: "briefcase", login_url: "https://www.linkedin.com/login", description: "Professional profiles, connections, job listings", default_schema: { name: "string", title: "string", company: "string", connections: "string" } },
    { id: "instagram", name: "Instagram", icon: "camera", login_url: "https://www.instagram.com/accounts/login", description: "User profiles, posts, followers, engagement metrics", default_schema: { username: "string", posts: "number", followers: "number", following: "number" } },
    { id: "twitter", name: "Twitter / X", icon: "bird", login_url: "https://twitter.com/login", description: "Tweets, followers, following, engagement data", default_schema: { tweets: "number", followers: "number", following: "number" } },
    { id: "reddit", name: "Reddit", icon: "alien", login_url: "https://www.reddit.com/login", description: "Posts, karma, saved content, subreddit data", default_schema: { posts: "number", karma: "number", saved: "number" } },
    { id: "shopify", name: "Shopify Admin", icon: "store", login_url: "https://myshopify.com/admin", description: "Orders, products, revenue from your Shopify store", default_schema: { orders: "number", products: "number", revenue: "number" } },
    { id: "google-analytics", name: "Google Analytics", icon: "chart", login_url: "https://analytics.google.com", description: "Sessions, users, pageviews, traffic analytics", default_schema: { sessions: "number", users: "number", pageviews: "number" } },
  ]);

  // Google Account state
  const [googleStatus, setGoogleStatus] = useState<{
    configured: boolean;
    connected: boolean;
    user_email?: string;
    user_name?: string;
    session_id?: string;
  }>({ configured: false, connected: false });
  const [googleConnecting, setGoogleConnecting] = useState(false);

  // Google presets (subset for the Google Account tab)
  const googlePresets: Preset[] = [
    { id: "google-sheets", name: "Google Sheets", icon: "table", login_url: "https://docs.google.com/spreadsheets", description: "Extract data from Google Spreadsheets", default_schema: { spreadsheet_title: "string", sheet_name: "string", rows: "number", columns: "number" } },
    { id: "google-drive", name: "Google Drive", icon: "folder", login_url: "https://drive.google.com", description: "List files and folders from Google Drive", default_schema: { file_name: "string", type: "string", size: "string", modified: "string" } },
    { id: "google-analytics", name: "Google Analytics", icon: "chart", login_url: "https://analytics.google.com", description: "Extract traffic reports and metrics", default_schema: { sessions: "number", users: "number", pageviews: "number", bounce_rate: "number" } },
    { id: "google-search-console", name: "Search Console", icon: "search", login_url: "https://search.google.com/search-console", description: "Search performance data and indexing", default_schema: { query: "string", clicks: "number", impressions: "number", ctr: "number", position: "number" } },
  ];

  async function refreshGoogleStatus() {
    try {
      const status = await authScrape.getGoogleStatus();
      // Also check if we have an active Google session
      const sessionsRes = await authScrape.listSessions();
      const googleSession = sessionsRes.sessions?.find(
        (s: any) => s.domain === "google.com" && s.status === "active"
      );
      setGoogleStatus({
        configured: status.configured,
        connected: !!googleSession,
        user_email: googleSession?.user_email,
        user_name: googleSession?.user_name,
        session_id: googleSession?.id,
      });
      // If we have a Google session, also set it as the active session for scraping
      if (googleSession && !sessionInfo) {
        setSessionInfo({
          session_id: googleSession.id,
          domain: "google.com",
          cookie_count: 0,
          status: "active",
          created_at: googleSession.created_at || "",
        });
      }
    } catch {
      // Google auth not available
      setGoogleStatus({ configured: false, connected: false });
    }
  }

  // On mount: check Google status and handle OAuth callback
  useEffect(() => {
    refreshGoogleStatus();

    // Check if we're returning from Google OAuth (URL has ?code=...&state=...)
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");
    if (code && state) {
      // Clean URL
      window.history.replaceState({}, "", window.location.pathname);
      // Exchange code for session
      setGoogleConnecting(true);
      authScrape.handleGoogleCallback(code, state)
        .then((res) => {
          setGoogleStatus({
            configured: true,
            connected: true,
            user_email: res.user_email,
            user_name: res.user_name,
            session_id: res.session_id,
          });
          setSessionInfo({
            session_id: res.session_id,
            domain: "google.com",
            cookie_count: 0,
            status: "active",
            created_at: res.created_at,
          });
          setActiveTab("google-account");
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : "Google OAuth callback failed");
        })
        .finally(() => setGoogleConnecting(false));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleGoogleConnect() {
    setGoogleConnecting(true);
    setError("");
    try {
      const { auth_url } = await authScrape.getGoogleAuthUrl();
      const popup = window.open(auth_url, "google-auth", "width=500,height=600");
      // Poll for popup close, then refresh status
      const interval = setInterval(async () => {
        if (popup?.closed) {
          clearInterval(interval);
          await refreshGoogleStatus();
          setGoogleConnecting(false);
        }
      }, 1000);
      // Safety timeout to stop polling after 5 minutes
      setTimeout(() => {
        clearInterval(interval);
        setGoogleConnecting(false);
      }, 300000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start Google OAuth");
      setGoogleConnecting(false);
    }
  }

  async function handleGoogleDisconnect() {
    if (!googleStatus.session_id) return;
    try {
      await authScrape.deleteSession(googleStatus.session_id);
      setGoogleStatus({ configured: googleStatus.configured, connected: false });
      if (sessionInfo?.session_id === googleStatus.session_id) {
        setSessionInfo(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disconnect Google account");
    }
  }

  // ----- Cookie file handler -----
  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target?.result as string);
        const cookieArray = Array.isArray(parsed) ? parsed : [parsed];
        setCookies(cookieArray);

        // Detect domain from cookies
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

  // ----- Upload cookies & create session -----
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
      const msg = err instanceof Error ? err.message : "Failed to create session";
      setError(msg);
    } finally {
      setIsUploading(false);
    }
  }

  // ----- Scrape handler -----
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
      const msg = err instanceof Error ? err.message : "Scrape failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  // ----- Preset click handler -----
  function handlePresetClick(preset: Preset) {
    setTargetUrl(preset.login_url);
    setExtractionMode("fields");
    setCustomSchema(JSON.stringify(preset.default_schema, null, 2));
  }

  const canScrape = sessionInfo !== null && targetUrl.trim().length > 0 && !loading;

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "32px 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 16,
            background: "linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0110 0v4" />
            </svg>
          </div>
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)", margin: 0 }}>Authenticated Scrape</h2>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
              Scrape login-required pages using your browser cookies
            </p>
          </div>
        </div>
      </div>

      {/* Info box */}
      <div style={{
        padding: "14px 18px",
        marginBottom: 24,
        borderRadius: 10,
        border: "1px solid var(--color-border)",
        background: "rgba(245, 158, 11, 0.05)",
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        fontSize: 13,
        color: "var(--color-text-secondary)",
        lineHeight: 1.6,
      }}>
        <span style={{ fontSize: 16, lineHeight: 1 }}>&#128274;</span>
        <div>
          <strong style={{ color: "var(--color-text)" }}>Authenticated Scrape</strong> lets you extract data from websites that require login. Export cookies from your browser session, upload them here, and scrape pages as if you were logged in.
          <br />
          <span style={{ fontSize: 12 }}>
            <strong>Use cases:</strong> LinkedIn profiles, Instagram analytics, Reddit saved posts, Shopify admin &nbsp;|&nbsp;
            <strong>Requires:</strong> Browser cookies exported as JSON (Cookie-Editor extension recommended)
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", gap: 0, marginBottom: 0 }}>
          {([
            { id: "cookie-upload" as TabId, label: "Cookie Upload" },
            { id: "browser-login" as TabId, label: "Browser Login" },
            { id: "google-account" as TabId, label: "Google Account" },
          ]).map((tab, idx, arr) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: "10px 24px",
                fontSize: 14,
                fontWeight: activeTab === tab.id ? 700 : 500,
                border: "1px solid var(--color-border)",
                borderBottom: activeTab === tab.id ? "2px solid var(--color-primary)" : "1px solid var(--color-border)",
                background: activeTab === tab.id ? "var(--color-surface)" : "transparent",
                color: activeTab === tab.id ? "var(--color-primary)" : "var(--color-text-secondary)",
                cursor: "pointer",
                borderRadius: idx === 0 ? "8px 0 0 0" : idx === arr.length - 1 ? "0 8px 0 0" : "0",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="accent-card" style={{ padding: 24, borderTopLeftRadius: 0 }}>
          {activeTab === "cookie-upload" && (
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
                  style={{
                    width: "100%", padding: "10px 14px",
                    border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)",
                    fontSize: 14, boxSizing: "border-box",
                  }}
                />
                <p style={{ fontSize: 11, color: "var(--color-text-secondary)", margin: "6px 0 0" }}>
                  Export cookies from your browser using the Cookie-Editor extension
                </p>
              </div>
              {cookies.length > 0 && (
                <div style={{
                  display: "flex", alignItems: "center", gap: 12,
                  padding: "8px 14px", borderRadius: 8,
                  background: "rgba(5, 150, 105, 0.08)",
                  border: "1px solid rgba(5, 150, 105, 0.2)",
                }}>
                  <span style={{ fontSize: 14 }}>&#9989;</span>
                  <span style={{ fontSize: 13, color: "var(--color-text)" }}>
                    <strong>{cookies.length}</strong> cookies loaded
                    {cookieDomain && (
                      <> &mdash; detected domain: <strong>{cookieDomain}</strong></>
                    )}
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

          {activeTab === "browser-login" && (
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

          {activeTab === "google-account" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {/* Google Logo + Connect */}
              <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                <svg width="32" height="32" viewBox="0 0 48 48">
                  <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                  <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                  <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                  <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                </svg>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)" }}>Google Account</div>
                  <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                    Connect via OAuth2 for Sheets, Drive, Analytics, and Search Console
                  </div>
                </div>
              </div>

              {/* Connected state */}
              {googleStatus.connected ? (
                <div style={{
                  padding: "14px 18px",
                  borderRadius: 10,
                  border: "1px solid rgba(5, 150, 105, 0.3)",
                  background: "rgba(5, 150, 105, 0.06)",
                }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{
                        display: "inline-block", padding: "3px 10px",
                        borderRadius: 9999, fontSize: 12, fontWeight: 600,
                        color: "#059669", background: "rgba(5, 150, 105, 0.15)",
                      }}>
                        Connected
                      </span>
                      <span style={{ fontSize: 14, fontWeight: 600, color: "var(--color-text)" }}>
                        {googleStatus.user_email || "Google Account"}
                      </span>
                      {googleStatus.user_name && (
                        <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                          ({googleStatus.user_name})
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={handleGoogleDisconnect}
                      style={{
                        padding: "6px 14px", borderRadius: 6,
                        border: "1px solid var(--color-border)",
                        background: "transparent",
                        color: "var(--color-text-secondary)",
                        fontSize: 12, fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      Disconnect
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleGoogleConnect}
                    disabled={googleConnecting}
                    style={{ height: 48, paddingInline: 32, fontSize: 15 }}
                  >
                    {googleConnecting ? (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                        <span className="spinner" /> Connecting...
                      </span>
                    ) : "Connect Google Account"}
                  </button>
                  {!googleStatus.configured && (
                    <p style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 8 }}>
                      Google OAuth is not configured on the server. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.
                    </p>
                  )}
                </div>
              )}

              {/* Google-specific presets */}
              <div>
                <h4 style={{ fontSize: 14, fontWeight: 600, color: "var(--color-text)", marginBottom: 10 }}>
                  Google Services
                </h4>
                <div style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
                  gap: 10,
                }}>
                  {googlePresets.map((preset) => (
                    <button
                      key={preset.id}
                      type="button"
                      onClick={() => handlePresetClick(preset)}
                      disabled={!googleStatus.connected}
                      style={{
                        display: "flex", alignItems: "flex-start", gap: 12,
                        padding: 14, borderRadius: 10,
                        border: "1px solid var(--color-border)",
                        background: googleStatus.connected ? "var(--color-surface)" : "rgba(0,0,0,0.02)",
                        cursor: googleStatus.connected ? "pointer" : "not-allowed",
                        textAlign: "left",
                        opacity: googleStatus.connected ? 1 : 0.5,
                        transition: "all 0.15s",
                      }}
                      onMouseEnter={(e) => {
                        if (googleStatus.connected) {
                          e.currentTarget.style.borderColor = "var(--color-primary)";
                          e.currentTarget.style.background = "rgba(99, 102, 241, 0.04)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = "var(--color-border)";
                        e.currentTarget.style.background = googleStatus.connected ? "var(--color-surface)" : "rgba(0,0,0,0.02)";
                      }}
                    >
                      <div style={{
                        width: 36, height: 36, borderRadius: 8,
                        background: "linear-gradient(135deg, #4285F4, #34A853)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        flexShrink: 0, color: "white",
                      }}>
                        {PRESET_ICONS[preset.icon] ?? (
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10" />
                          </svg>
                        )}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text)", marginBottom: 2 }}>
                          {preset.name}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--color-text-secondary)", lineHeight: 1.4 }}>
                          {preset.description}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              <p style={{ fontSize: 11, color: "var(--color-text-secondary)", margin: 0 }}>
                Or export Google cookies manually using the Cookie Upload tab.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Session Confirmation */}
      {sessionInfo && (
        <div style={{ marginBottom: 24 }}>
          <div style={{
            padding: "14px 18px",
            borderRadius: 10,
            border: "1px solid rgba(5, 150, 105, 0.3)",
            background: "rgba(5, 150, 105, 0.06)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              <span style={{
                display: "inline-block", padding: "3px 10px",
                borderRadius: 9999, fontSize: 12, fontWeight: 600,
                color: "#059669", background: "rgba(5, 150, 105, 0.15)",
              }}>
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

      {/* Scrape Form (shown after session exists) */}
      {sessionInfo && (
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 12 }}>
            Scrape Requirements
          </h3>
          <form onSubmit={handleScrape}>
            <div className="accent-card" style={{ padding: 24 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {/* Target URL */}
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                    Target URL
                  </label>
                  <input
                    type="text"
                    placeholder="https://www.linkedin.com/in/username"
                    value={targetUrl}
                    onChange={(e) => setTargetUrl(e.target.value)}
                    disabled={loading}
                    style={{
                      width: "100%", padding: "10px 14px",
                      border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)",
                      fontSize: 14, boxSizing: "border-box",
                    }}
                  />
                </div>

                {/* Extraction Mode */}
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                    Extraction Mode
                  </label>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {MODE_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setExtractionMode(opt.value)}
                        title={opt.description}
                        style={{
                          padding: "6px 14px",
                          fontSize: 13,
                          fontWeight: extractionMode === opt.value ? 700 : 500,
                          borderRadius: 6,
                          border: extractionMode === opt.value ? "2px solid var(--color-primary)" : "1px solid var(--color-border)",
                          background: extractionMode === opt.value ? "rgba(99, 102, 241, 0.1)" : "transparent",
                          color: extractionMode === opt.value ? "var(--color-primary)" : "var(--color-text-secondary)",
                          cursor: "pointer",
                          transition: "all 0.15s",
                        }}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 4 }}>
                    {MODE_OPTIONS.find((o) => o.value === extractionMode)?.description}
                  </div>
                </div>

                {/* Custom Schema (for "fields" mode) */}
                {extractionMode === "fields" && (
                  <div>
                    <label style={{
                      display: "block", fontSize: 12, fontWeight: 600,
                      color: "var(--color-text-secondary)", marginBottom: 6,
                    }}>
                      Extraction Schema (JSON)
                    </label>
                    <textarea
                      value={customSchema}
                      onChange={(e) => setCustomSchema(e.target.value)}
                      placeholder='{"title": "string", "price": "number"}'
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

                {/* Max Pages */}
                <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
                  <div style={{ flex: 1, minWidth: 140, maxWidth: 200 }}>
                    <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                      Max Pages
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={maxPages}
                      onChange={(e) => setMaxPages(Number(e.target.value))}
                      disabled={loading}
                      style={{
                        width: "100%", padding: "10px 14px",
                        border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)",
                        fontSize: 14, boxSizing: "border-box",
                      }}
                    />
                  </div>
                  <div>
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={!canScrape}
                      style={{ height: 44, paddingInline: 28 }}
                    >
                      {loading ? (
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                          <span className="spinner" /> Scraping...
                        </span>
                      ) : "Scrape"}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </form>
        </div>
      )}

      {/* Error */}
      {error && <div className="form-error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Results */}
      {result && (
        <>
          {/* Stats Grid */}
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
            <div className="stat-card">
              <div className="stat-label">Saved</div>
              <div className="stat-value" style={{ fontSize: 20, color: result.saved ? "var(--color-success)" : "var(--color-text-secondary)" }}>
                {result.saved ? "Yes" : "No"}
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
          <div className="card" style={{ marginBottom: 16 }}>
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

      {/* Popular Site Presets */}
      <div style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 12 }}>
          Popular Site Presets
        </h3>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: 12,
        }}>
          {presets.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => handlePresetClick(preset)}
              style={{
                display: "flex", alignItems: "flex-start", gap: 14,
                padding: 16, borderRadius: 10,
                border: "1px solid var(--color-border)",
                background: "var(--color-surface)",
                cursor: "pointer",
                textAlign: "left",
                transition: "all 0.15s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--color-primary)";
                e.currentTarget.style.background = "rgba(99, 102, 241, 0.04)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--color-border)";
                e.currentTarget.style.background = "var(--color-surface)";
              }}
            >
              <div style={{
                width: 40, height: 40, borderRadius: 10,
                background: "linear-gradient(135deg, #f59e0b, #ef4444)",
                display: "flex", alignItems: "center", justifyContent: "center",
                flexShrink: 0, color: "white",
              }}>
                {PRESET_ICONS[preset.icon] ?? (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                  </svg>
                )}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: "var(--color-text)", marginBottom: 2 }}>
                  {preset.name}
                </div>
                <div style={{ fontSize: 12, color: "var(--color-text-secondary)", lineHeight: 1.4 }}>
                  {preset.description}
                </div>
                <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 4 }}>
                  Fields: {Object.keys(preset.default_schema).join(", ")}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Empty state when no session and no result */}
      {!sessionInfo && !result && !loading && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{
            width: 64, height: 64, borderRadius: 16,
            background: "linear-gradient(135deg, #f59e0b, #ef4444)",
            display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16,
          }}>
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
    </div>
  );
}

export default AuthScrapePage;
