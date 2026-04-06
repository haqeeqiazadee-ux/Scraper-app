/**
 * ApiKeysPage — Manage API keys for the Zero Checksum Public API.
 * Create, list, and revoke API keys for external access.
 */

import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_URL ?? "/api/v1";

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

export function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [copied, setCopied] = useState(false);

  async function fetchKeys() {
    try {
      const res = await fetch(`${API_BASE}/api-keys`, { headers: { "X-Tenant-ID": "default" } });
      if (res.ok) {
        const data = await res.json();
        setKeys(data.keys ?? data.items ?? data ?? []);
      }
    } catch {
      setError("Failed to load API keys");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchKeys(); }, []);

  async function handleCreate() {
    if (!newKeyName.trim()) return;
    setCreating(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api-keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Tenant-ID": "default" },
        body: JSON.stringify({ name: newKeyName.trim(), scopes: ["*"] }),
      });
      if (res.ok) {
        const data = await res.json();
        setCreatedKey(data.key);
        setNewKeyName("");
        fetchKeys();
      } else {
        const err = await res.json();
        setError(err.detail || "Failed to create key");
      }
    } catch {
      setError("Failed to create API key");
    } finally {
      setCreating(false);
    }
  }

  async function handleRevoke(keyId: string) {
    try {
      await fetch(`${API_BASE}/api-keys/${keyId}`, {
        method: "DELETE",
        headers: { "X-Tenant-ID": "default" },
      });
      fetchKeys();
    } catch {
      setError("Failed to revoke key");
    }
  }

  function handleCopy() {
    if (createdKey) {
      navigator.clipboard.writeText(createdKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "32px 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 16,
            background: "linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
            </svg>
          </div>
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)", margin: 0 }}>API Keys</h2>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
              Manage API keys for the Zero Checksum Public API at <code>/v1/</code>
            </p>
          </div>
        </div>
      </div>

      {/* Info box */}
      <div style={{
        padding: "14px 18px",
        marginBottom: 20,
        borderRadius: 10,
        border: "1px solid var(--color-border)",
        background: "rgba(245, 158, 11, 0.05)",
        fontSize: 13,
        color: "var(--color-text-secondary)",
        lineHeight: 1.6,
      }}>
        <strong style={{ color: "var(--color-text)" }}>Public API</strong> lets external apps scrape, crawl, search, and extract data via <code>POST /v1/scrape</code>, <code>/v1/crawl</code>, <code>/v1/search</code>, <code>/v1/extract</code>. Authenticate with <code>Authorization: Bearer sk_live_xxx</code>. Every request is tracked with a unique <code>request_id</code> for full audit trail.
        <br />
        <span style={{ fontSize: 12 }}>
          <strong>Features:</strong> Idempotency keys, credit tracking, async jobs with polling, webhook notifications
        </span>
      </div>

      {/* Create Key */}
      <div className="accent-card" style={{ padding: 24, marginBottom: 24 }}>
        {!showCreate && !createdKey && (
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            + Create API Key
          </button>
        )}

        {showCreate && !createdKey && (
          <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                Key Name
              </label>
              <input
                type="text"
                placeholder="e.g. Production API, My App, Testing"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, boxSizing: "border-box" }}
              />
            </div>
            <button className="btn btn-primary" onClick={handleCreate} disabled={creating || !newKeyName.trim()} style={{ height: 42, paddingInline: 24 }}>
              {creating ? "Creating..." : "Create"}
            </button>
            <button className="btn btn-secondary" onClick={() => setShowCreate(false)} style={{ height: 42 }}>
              Cancel
            </button>
          </div>
        )}

        {/* Newly created key - show ONCE */}
        {createdKey && (
          <div style={{
            padding: 16,
            borderRadius: 8,
            border: "1px solid var(--color-success)",
            background: "rgba(34, 197, 94, 0.05)",
          }}>
            <div style={{ fontWeight: 700, color: "var(--color-success)", marginBottom: 8 }}>
              API Key Created — Copy it now! You won't see it again.
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <code style={{
                flex: 1,
                padding: "10px 14px",
                background: "var(--color-bg)",
                borderRadius: 6,
                fontSize: 14,
                fontFamily: "var(--font-mono)",
                color: "var(--color-text)",
                wordBreak: "break-all",
              }}>
                {createdKey}
              </code>
              <button className="btn btn-primary" onClick={handleCopy} style={{ height: 42, paddingInline: 20 }}>
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <button
              className="btn btn-secondary"
              onClick={() => { setCreatedKey(null); setShowCreate(false); }}
              style={{ marginTop: 12 }}
            >
              Done
            </button>
          </div>
        )}
      </div>

      {error && <div className="form-error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Keys List */}
      <div className="accent-card" style={{ padding: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 16 }}>
          Your API Keys ({keys.length})
        </h3>

        {loading && <div style={{ color: "var(--color-text-secondary)" }}>Loading...</div>}

        {!loading && keys.length === 0 && (
          <div style={{ textAlign: "center", padding: "32px 0", color: "var(--color-text-secondary)" }}>
            No API keys yet. Create one to start using the Public API.
          </div>
        )}

        {keys.length > 0 && (
          <div style={{ border: "1px solid var(--color-border)", borderRadius: 8, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "var(--color-bg)", borderBottom: "1px solid var(--color-border)" }}>
                  <th style={{ padding: "10px 14px", textAlign: "left", fontWeight: 600, color: "var(--color-text-secondary)" }}>Name</th>
                  <th style={{ padding: "10px 14px", textAlign: "left", fontWeight: 600, color: "var(--color-text-secondary)" }}>Key</th>
                  <th style={{ padding: "10px 14px", textAlign: "left", fontWeight: 600, color: "var(--color-text-secondary)" }}>Scopes</th>
                  <th style={{ padding: "10px 14px", textAlign: "left", fontWeight: 600, color: "var(--color-text-secondary)" }}>Created</th>
                  <th style={{ padding: "10px 14px", textAlign: "left", fontWeight: 600, color: "var(--color-text-secondary)" }}>Last Used</th>
                  <th style={{ padding: "10px 14px", textAlign: "right", fontWeight: 600, color: "var(--color-text-secondary)" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {keys.map((key) => (
                  <tr key={key.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                    <td style={{ padding: "10px 14px", color: "var(--color-text)", fontWeight: 500 }}>{key.name}</td>
                    <td style={{ padding: "10px 14px", fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)" }}>{key.key_prefix}...</td>
                    <td style={{ padding: "10px 14px", color: "var(--color-text-secondary)" }}>{key.scopes?.join(", ") || "*"}</td>
                    <td style={{ padding: "10px 14px", color: "var(--color-text-secondary)" }}>
                      {key.created_at ? new Date(key.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td style={{ padding: "10px 14px", color: "var(--color-text-secondary)" }}>
                      {key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : "Never"}
                    </td>
                    <td style={{ padding: "10px 14px", textAlign: "right" }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleRevoke(key.id)}
                        style={{ color: "var(--color-error)", fontSize: 12 }}
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Usage Example */}
      <div style={{ marginTop: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 12 }}>Quick Start</h3>
        <div style={{
          position: "relative",
          background: "#1e1e2e",
          borderRadius: 8,
          padding: 16,
          overflow: "auto",
        }}>
          <pre style={{ color: "#cdd6f4", fontSize: 13, fontFamily: "monospace", lineHeight: 1.6, margin: 0 }}>
{`curl -X POST https://scraper-platform-production-17cb.up.railway.app/v1/scrape \\
  -H "Authorization: Bearer sk_live_YOUR_KEY_HERE" \\
  -H "Content-Type: application/json" \\
  -d '{"url": "https://example.com", "formats": ["json"]}'`}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default ApiKeysPage;
