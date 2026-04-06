/**
 * FacebookGroupPage — Extract posts from Facebook group feeds with cookie authentication.
 */

import { useState, useEffect, useRef, type FormEvent, type ChangeEvent } from "react";
import { facebookGroups } from "../api/client";

type JobStatus = "running" | "completed" | "failed";

interface JobData {
  job_id: string;
  status: JobStatus;
  posts_found?: number;
  scrolls?: number;
}

export function FacebookGroupPage() {
  const [cookies, setCookies] = useState<any[]>([]);
  const [cookieStatus, setCookieStatus] = useState("No cookies uploaded");
  const [url, setUrl] = useState("");
  const [maxPosts, setMaxPosts] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | "">("");
  const [posts, setPosts] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState("");
  const [jobData, setJobData] = useState<JobData | null>(null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Poll job status every 3 seconds while running
  useEffect(() => {
    if (!jobId || status === "completed" || status === "failed") {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    intervalRef.current = setInterval(async () => {
      try {
        const data = await facebookGroups.status(jobId);
        setJobData(data);
        setStatus(data.status);
        if (data.status === "completed") {
          // Fetch results
          try {
            const res = await facebookGroups.results(jobId);
            setPosts(res.posts ?? res.items ?? res.results ?? []);
          } catch {
            // will retry on manual action
          }
          setIsLoading(false);
        } else if (data.status === "failed") {
          setIsLoading(false);
          setError("Scrape job failed. Please try again.");
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
  }, [jobId, status]);

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target?.result as string);
        const cookieArray = Array.isArray(parsed) ? parsed : [parsed];
        setCookies(cookieArray);
        setCookieStatus(`${cookieArray.length} cookies loaded from file`);
      } catch {
        setError("Invalid JSON file. Please upload a valid cookies.json.");
        setCookieStatus("No cookies uploaded");
      }
    };
    reader.readAsText(file);
  }

  async function handleUploadCookies() {
    if (cookies.length === 0) return;
    setIsUploading(true);
    setError("");
    try {
      await facebookGroups.uploadCookies(cookies);
      setCookieStatus(`${cookies.length} cookies uploaded successfully`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to upload cookies";
      setError(msg);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleScrape(e: FormEvent) {
    e.preventDefault();
    if (!url.trim() || cookies.length === 0) return;

    setIsLoading(true);
    setError("");
    setPosts([]);
    setJobData(null);

    try {
      const res = await facebookGroups.scrape({
        url: url.trim(),
        max_posts: maxPosts || undefined,
      });
      setJobId(res.job_id);
      setStatus("running");
      setJobData({ job_id: res.job_id, status: "running", posts_found: 0, scrolls: 0 });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start scrape";
      setError(msg);
      setIsLoading(false);
    }
  }

  function handleExport() {
    if (!jobId) return;
    const exportLink = facebookGroups.exportUrl(jobId);
    window.open(exportLink, "_blank");
  }

  function statusColor(s: string): string {
    switch (s) {
      case "running": return "#2563eb";
      case "completed": return "#059669";
      case "failed": return "#dc2626";
      default: return "#6b7280";
    }
  }

  function truncate(text: string, max: number): string {
    if (!text) return "";
    return text.length > max ? text.slice(0, max) + "..." : text;
  }

  const canScrape = cookies.length > 0 && url.trim().length > 0 && !isLoading;

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "32px 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 16,
            background: "linear-gradient(135deg, #1877f2 0%, #42a5f5 100%)",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 2h-3a5 5 0 00-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 011-1h3V2z" />
            </svg>
          </div>
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)", margin: 0 }}>Facebook Groups</h2>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
              Extract posts from Facebook group feeds with cookie authentication
            </p>
          </div>
        </div>
      </div>

      {/* Info */}
      <div style={{
        padding: "14px 18px",
        marginBottom: 24,
        borderRadius: 10,
        border: "1px solid var(--color-border)",
        background: "rgba(24, 119, 242, 0.05)",
        fontSize: 13,
        color: "var(--color-text-secondary)",
        lineHeight: 1.6,
      }}>
        This feature uses <strong style={{ color: "var(--color-text)" }}>Playwright + CDP (Chrome DevTools Protocol)</strong> to scroll through Facebook group feeds, capture posts, and export to Excel. Upload your Facebook cookies, enter a group URL, and it handles the rest — auto-scrolling, data capture, and structured export.
        <br />
        <span style={{ fontSize: 12 }}>
          <strong>Use cases:</strong> Market research, community monitoring, competitor analysis &nbsp;|&nbsp;
          <strong>Requires:</strong> Self-hosted backend with Chrome installed + Facebook cookies
        </span>
      </div>

      {/* Step 1: Cookie Upload */}
      <div style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 12 }}>
          Step 1: Cookie Upload
        </h3>
        <div className="accent-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                Cookies File
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
                Export cookies from your browser using EditThisCookie extension
              </p>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleUploadCookies}
                disabled={cookies.length === 0 || isUploading}
                style={{ height: 44, paddingInline: 28 }}
              >
                {isUploading ? (
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                    <span className="spinner" /> Uploading...
                  </span>
                ) : "Upload Cookies"}
              </button>
              <span style={{
                display: "inline-block",
                padding: "4px 12px",
                borderRadius: 9999,
                fontSize: 12,
                fontWeight: 600,
                color: cookies.length > 0 ? "#059669" : "var(--color-text-secondary)",
                background: cookies.length > 0 ? "rgba(5,150,105,0.1)" : "rgba(107,114,128,0.1)",
              }}>
                {cookieStatus}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Step 2: Group URL + Scrape */}
      <div style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 12 }}>
          Step 2: Group URL &amp; Scrape
        </h3>
        <form onSubmit={handleScrape}>
          <div className="accent-card" style={{ padding: 24 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                  Group URL
                </label>
                <input
                  type="text"
                  placeholder="https://www.facebook.com/groups/..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={isLoading}
                  style={{
                    width: "100%", padding: "10px 14px",
                    border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)",
                    fontSize: 14, boxSizing: "border-box",
                  }}
                />
              </div>
              <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
                <div style={{ flex: 1, minWidth: 180 }}>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                    Max Posts
                  </label>
                  <input
                    type="number"
                    min={0}
                    placeholder="0 = all posts"
                    value={maxPosts}
                    onChange={(e) => setMaxPosts(Number(e.target.value))}
                    disabled={isLoading}
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
                    {isLoading ? (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                        <span className="spinner" /> Scraping...
                      </span>
                    ) : "Scrape Group"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </form>
      </div>

      {/* Error */}
      {error && <div className="form-error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Active Job Progress */}
      {jobData && status === "running" && (
        <div style={{ marginBottom: 24 }}>
          <div className="accent-card" style={{ padding: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
              <span style={{
                display: "inline-block",
                padding: "3px 10px",
                borderRadius: 9999,
                fontSize: 12,
                fontWeight: 600,
                color: "white",
                background: statusColor("running"),
              }}>
                running
              </span>
              <span style={{ fontSize: 14, color: "var(--color-text)" }}>
                Scraping... <strong>{jobData.posts_found ?? 0}</strong> posts found, <strong>{jobData.scrolls ?? 0}</strong> scrolls
              </span>
              <span className="spinner" />
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Results */}
      {posts.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", margin: 0 }}>
              Step 3: Results
              <span style={{ fontSize: 13, fontWeight: 400, color: "var(--color-text-secondary)", marginLeft: 8 }}>
                ({posts.length} posts)
              </span>
            </h3>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleExport}
              style={{ height: 38, paddingInline: 20 }}
            >
              Export to Excel
            </button>
          </div>
          <div className="accent-card" style={{ padding: 0, overflow: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr>
                  {["Author", "Text", "Timestamp", "Likes", "Comments", "Price", "Images"].map((col) => (
                    <th
                      key={col}
                      style={{
                        textAlign: "left",
                        padding: "10px 14px",
                        fontSize: 10,
                        fontWeight: 700,
                        color: "var(--color-text-secondary)",
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        borderBottom: "1px solid var(--color-border)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {posts.map((post, i) => (
                  <tr
                    key={i}
                    style={{
                      background: i % 2 === 0 ? "transparent" : "var(--color-surface)",
                    }}
                  >
                    <td style={{ padding: "10px 14px", whiteSpace: "nowrap" }}>
                      {post.author ?? post.user_name ?? "—"}
                    </td>
                    <td style={{ padding: "10px 14px", maxWidth: 300 }}>
                      {truncate(post.text ?? post.content ?? post.message ?? "", 100)}
                    </td>
                    <td style={{ padding: "10px 14px", whiteSpace: "nowrap", color: "var(--color-text-secondary)" }}>
                      {post.timestamp ?? post.date ?? post.created_at ?? "—"}
                    </td>
                    <td style={{ padding: "10px 14px", textAlign: "center" }}>
                      {post.likes ?? post.reactions ?? "—"}
                    </td>
                    <td style={{ padding: "10px 14px", textAlign: "center" }}>
                      {post.comments ?? post.comment_count ?? "—"}
                    </td>
                    <td style={{ padding: "10px 14px", whiteSpace: "nowrap" }}>
                      {post.price ?? "—"}
                    </td>
                    <td style={{ padding: "10px 14px", textAlign: "center" }}>
                      {Array.isArray(post.images) ? post.images.length : (post.image_count ?? "—")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Completed / Failed badge */}
      {jobData && status !== "running" && status !== "" && posts.length === 0 && (
        <div style={{ marginBottom: 24 }}>
          <div className="accent-card" style={{ padding: 24 }}>
            <span style={{
              display: "inline-block",
              padding: "3px 10px",
              borderRadius: 9999,
              fontSize: 12,
              fontWeight: 600,
              color: "white",
              background: statusColor(status),
            }}>
              {status}
            </span>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!jobData && !isLoading && posts.length === 0 && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{
            width: 64, height: 64, borderRadius: 16,
            background: "linear-gradient(135deg, #1877f2, #42a5f5)",
            display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16,
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 2h-3a5 5 0 00-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 011-1h3V2z" />
            </svg>
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>Ready to scrape</h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            Upload your Facebook cookies, enter a group URL, and start extracting posts.
          </p>
        </div>
      )}
    </div>
  );
}

export default FacebookGroupPage;
