/**
 * FmsPage — Feed Management System admin page.
 * Three tabs: Products (search/browse catalog), Feed Sources (manage connections),
 * Suppliers (list vendors).
 */

import { useState, useEffect, type FormEvent } from "react";
import { fms } from "../api/client";

type Tab = "products" | "feeds" | "suppliers";

/* ── Products Tab ── */

interface FmsProduct {
  id: number;
  mpn: string;
  brand: string;
  title: string;
  category: string;
  ean: string;
  asin: string;
}

interface FmsOffer {
  id: number;
  product_id: number;
  vendor_name: string;
  region: string;
  price_gbp: number | null;
  price_eur: number | null;
  price_usd: number | null;
  stock_level: number | null;
  last_updated: string | null;
}

function ProductsTab() {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<FmsProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState("");
  const [selectedProduct, setSelectedProduct] = useState<(FmsProduct & { offers?: FmsOffer[] }) | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const LIMIT = 25;

  async function doSearch(newOffset = 0) {
    setLoading(true);
    setError("");
    try {
      const res = await fms.products({ q: query || undefined, offset: newOffset, limit: LIMIT });
      setItems(res.items);
      setOffset(newOffset);
      setHasMore(res.has_more);
    } catch (e: any) {
      setError(e.message || "Failed to load products");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    doSearch(0);
  }, []);

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    setSelectedProduct(null);
    doSearch(0);
  }

  async function handleRowClick(product: FmsProduct) {
    setDetailLoading(true);
    try {
      const detail = await fms.product(product.id);
      setSelectedProduct(detail);
    } catch {
      setSelectedProduct({ ...product, offers: [] });
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <div>
      {/* Search bar */}
      <form onSubmit={handleSearch} style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input
          className="form-input"
          type="text"
          placeholder="Search by title, MPN, or brand..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ flex: 1 }}
        />
        <button className="btn" type="submit" disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {error && <div style={{ color: "#f87171", marginBottom: 12 }}>{error}</div>}

      {/* Product detail panel */}
      {selectedProduct && (
        <div className="accent-card" style={{ marginBottom: 16, padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <h3 style={{ margin: "0 0 8px", fontSize: 16 }}>{selectedProduct.title}</h3>
              <div style={{ display: "flex", gap: 16, fontSize: 13, color: "rgba(255,255,255,0.6)" }}>
                <span>MPN: <strong style={{ color: "#fff" }}>{selectedProduct.mpn || "N/A"}</strong></span>
                <span>Brand: <strong style={{ color: "#fff" }}>{selectedProduct.brand || "N/A"}</strong></span>
                <span>EAN: <strong style={{ color: "#fff" }}>{selectedProduct.ean || "N/A"}</strong></span>
                <span>Category: <strong style={{ color: "#fff" }}>{selectedProduct.category || "N/A"}</strong></span>
              </div>
            </div>
            <button
              className="btn"
              style={{ fontSize: 12, padding: "4px 10px" }}
              onClick={() => setSelectedProduct(null)}
            >
              Close
            </button>
          </div>

          {/* Offers table */}
          <h4 style={{ margin: "16px 0 8px", fontSize: 14, color: "rgba(255,255,255,0.8)" }}>
            Vendor Offers ({selectedProduct.offers?.length || 0})
          </h4>
          {detailLoading ? (
            <div style={{ color: "rgba(255,255,255,0.5)" }}>Loading offers...</div>
          ) : selectedProduct.offers && selectedProduct.offers.length > 0 ? (
            <div style={{ overflowX: "auto" }}>
              <table className="table" style={{ width: "100%", fontSize: 13 }}>
                <thead>
                  <tr>
                    <th>Vendor</th>
                    <th>Region</th>
                    <th>GBP</th>
                    <th>EUR</th>
                    <th>USD</th>
                    <th>Stock</th>
                    <th>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedProduct.offers.map((o) => (
                    <tr key={o.id}>
                      <td style={{ fontWeight: 600 }}>{o.vendor_name}</td>
                      <td>{o.region}</td>
                      <td>{o.price_gbp != null ? `£${o.price_gbp.toFixed(2)}` : "-"}</td>
                      <td>{o.price_eur != null ? `€${o.price_eur.toFixed(2)}` : "-"}</td>
                      <td>{o.price_usd != null ? `$${o.price_usd.toFixed(2)}` : "-"}</td>
                      <td>{o.stock_level ?? "-"}</td>
                      <td style={{ fontSize: 12, color: "rgba(255,255,255,0.5)" }}>
                        {o.last_updated ? new Date(o.last_updated).toLocaleDateString() : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 13 }}>No offers found for this product.</div>
          )}
        </div>
      )}

      {/* Products table */}
      <div style={{ overflowX: "auto" }}>
        <table className="table" style={{ width: "100%", fontSize: 13 }}>
          <thead>
            <tr>
              <th>MPN</th>
              <th>Brand</th>
              <th>Title</th>
              <th>Category</th>
              <th>EAN</th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr
                key={p.id}
                onClick={() => handleRowClick(p)}
                style={{ cursor: "pointer" }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLTableRowElement).style.background = "rgba(255,255,255,0.04)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLTableRowElement).style.background = "";
                }}
              >
                <td style={{ fontFamily: "monospace", fontSize: 12 }}>{p.mpn || "-"}</td>
                <td>{p.brand || "-"}</td>
                <td style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {p.title || "-"}
                </td>
                <td style={{ fontSize: 12, color: "rgba(255,255,255,0.6)" }}>{p.category || "-"}</td>
                <td style={{ fontFamily: "monospace", fontSize: 12 }}>{p.ean || "-"}</td>
              </tr>
            ))}
            {items.length === 0 && !loading && (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", color: "rgba(255,255,255,0.4)", padding: 24 }}>
                  No products found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12, fontSize: 13 }}>
        <span style={{ color: "rgba(255,255,255,0.5)" }}>
          Showing {offset + 1}–{offset + items.length}
        </span>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className="btn"
            style={{ fontSize: 12, padding: "4px 12px" }}
            disabled={offset === 0}
            onClick={() => doSearch(Math.max(0, offset - LIMIT))}
          >
            Previous
          </button>
          <button
            className="btn"
            style={{ fontSize: 12, padding: "4px 12px" }}
            disabled={!hasMore}
            onClick={() => doSearch(offset + LIMIT)}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Feed Sources Tab ── */

interface FeedSource {
  id: number;
  vendor_name: string;
  protocol: string;
  host: string;
  enabled: boolean;
  last_fetched_at: string | null;
  last_ingested_at: string | null;
}

function FeedSourcesTab() {
  const [sources, setSources] = useState<FeedSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState<Record<number, string>>({});

  async function loadSources() {
    setLoading(true);
    setError("");
    try {
      const res = await fms.feedSources();
      setSources(res.sources);
    } catch (e: any) {
      setError(e.message || "Failed to load feed sources");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSources();
  }, []);

  async function handleToggle(source: FeedSource) {
    setActionLoading((prev) => ({ ...prev, [source.id]: "toggle" }));
    try {
      await fms.toggleSource(source.id, !source.enabled);
      setSources((prev) =>
        prev.map((s) => (s.id === source.id ? { ...s, enabled: !s.enabled } : s))
      );
    } catch (e: any) {
      setError(e.message || "Toggle failed");
    } finally {
      setActionLoading((prev) => {
        const next = { ...prev };
        delete next[source.id];
        return next;
      });
    }
  }

  async function handleFetch(source: FeedSource) {
    setActionLoading((prev) => ({ ...prev, [source.id]: "fetch" }));
    try {
      await fms.triggerFetch(source.id);
      setSources((prev) =>
        prev.map((s) =>
          s.id === source.id ? { ...s, last_fetched_at: new Date().toISOString() } : s
        )
      );
    } catch (e: any) {
      setError(e.message || "Fetch trigger failed");
    } finally {
      setActionLoading((prev) => {
        const next = { ...prev };
        delete next[source.id];
        return next;
      });
    }
  }

  if (loading) {
    return <div style={{ color: "rgba(255,255,255,0.5)", padding: 24 }}>Loading feed sources...</div>;
  }

  return (
    <div>
      {error && <div style={{ color: "#f87171", marginBottom: 12 }}>{error}</div>}

      <div style={{ overflowX: "auto" }}>
        <table className="table" style={{ width: "100%", fontSize: 13 }}>
          <thead>
            <tr>
              <th>Vendor</th>
              <th>Protocol</th>
              <th>Host</th>
              <th>Status</th>
              <th>Last Fetched</th>
              <th style={{ textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.id}>
                <td style={{ fontWeight: 600 }}>{s.vendor_name}</td>
                <td>
                  <span
                    style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: 4,
                      fontSize: 11,
                      fontWeight: 600,
                      textTransform: "uppercase",
                      background:
                        s.protocol === "sftp"
                          ? "rgba(99,102,241,0.2)"
                          : s.protocol === "ftp"
                          ? "rgba(34,197,94,0.2)"
                          : s.protocol === "email"
                          ? "rgba(249,115,22,0.2)"
                          : "rgba(255,255,255,0.1)",
                      color:
                        s.protocol === "sftp"
                          ? "#a5b4fc"
                          : s.protocol === "ftp"
                          ? "#86efac"
                          : s.protocol === "email"
                          ? "#fdba74"
                          : "rgba(255,255,255,0.7)",
                    }}
                  >
                    {s.protocol}
                  </span>
                </td>
                <td style={{ fontFamily: "monospace", fontSize: 12, color: "rgba(255,255,255,0.6)" }}>
                  {s.host || "-"}
                </td>
                <td>
                  <span
                    style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: 4,
                      fontSize: 11,
                      fontWeight: 600,
                      background: s.enabled ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)",
                      color: s.enabled ? "#86efac" : "#fca5a5",
                    }}
                  >
                    {s.enabled ? "Enabled" : "Disabled"}
                  </span>
                </td>
                <td style={{ fontSize: 12, color: "rgba(255,255,255,0.5)" }}>
                  {s.last_fetched_at ? new Date(s.last_fetched_at).toLocaleString() : "Never"}
                </td>
                <td style={{ textAlign: "right" }}>
                  <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                    <button
                      className="btn"
                      style={{
                        fontSize: 11,
                        padding: "3px 10px",
                        background: s.enabled ? "rgba(239,68,68,0.15)" : "rgba(34,197,94,0.15)",
                        color: s.enabled ? "#fca5a5" : "#86efac",
                        border: `1px solid ${s.enabled ? "rgba(239,68,68,0.3)" : "rgba(34,197,94,0.3)"}`,
                      }}
                      disabled={!!actionLoading[s.id]}
                      onClick={() => handleToggle(s)}
                    >
                      {actionLoading[s.id] === "toggle" ? "..." : s.enabled ? "Disable" : "Enable"}
                    </button>
                    <button
                      className="btn"
                      style={{ fontSize: 11, padding: "3px 10px" }}
                      disabled={!s.enabled || !!actionLoading[s.id]}
                      onClick={() => handleFetch(s)}
                    >
                      {actionLoading[s.id] === "fetch" ? "Running..." : "Run Fetch"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {sources.length === 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", color: "rgba(255,255,255,0.4)", padding: 24 }}>
                  No feed sources configured.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Suppliers Tab ── */

function SuppliersTab({ onSelectVendor }: { onSelectVendor: (vendor: string) => void }) {
  const [vendors, setVendors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await fms.suppliers();
        setVendors(res.vendors);
      } catch (e: any) {
        setError(e.message || "Failed to load suppliers");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return <div style={{ color: "rgba(255,255,255,0.5)", padding: 24 }}>Loading suppliers...</div>;
  }

  return (
    <div>
      {error && <div style={{ color: "#f87171", marginBottom: 12 }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 10 }}>
        {vendors.map((v) => (
          <div
            key={v}
            className="accent-card"
            style={{
              padding: "12px 16px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              transition: "all 0.15s ease",
            }}
            onClick={() => onSelectVendor(v)}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(99,102,241,0.5)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLDivElement).style.borderColor = "";
            }}
          >
            <span style={{ fontWeight: 600, fontSize: 14 }}>{v}</span>
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.4)" }}>View offers</span>
          </div>
        ))}
        {vendors.length === 0 && (
          <div style={{ color: "rgba(255,255,255,0.4)", padding: 24 }}>No suppliers found.</div>
        )}
      </div>
    </div>
  );
}

/* ── Main Page ── */

const TABS: { key: Tab; label: string; desc: string }[] = [
  { key: "products", label: "Products", desc: "Search and browse the FMS product catalog" },
  { key: "feeds", label: "Feed Sources", desc: "Manage supplier feed connections" },
  { key: "suppliers", label: "Suppliers", desc: "View all vendors" },
];

export function FmsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("products");

  function handleSelectVendor(_vendor: string) {
    // Switch to products tab — user can then search by vendor name
    setActiveTab("products");
  }

  return (
    <div style={{ padding: 24, maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 4px" }}>Feed Management</h1>
        <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 14, margin: 0 }}>
          Manage B2B supplier feeds, browse the product catalog, and compare vendor pricing.
        </p>
      </div>

      {/* Tab bar */}
      <div
        style={{
          display: "flex",
          gap: 4,
          marginBottom: 20,
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          paddingBottom: 0,
        }}
      >
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: "8px 18px",
              fontSize: 13,
              fontWeight: activeTab === tab.key ? 600 : 400,
              color: activeTab === tab.key ? "#fff" : "rgba(255,255,255,0.5)",
              background: "transparent",
              border: "none",
              borderBottom: activeTab === tab.key ? "2px solid #6366f1" : "2px solid transparent",
              cursor: "pointer",
              transition: "all 0.15s ease",
              marginBottom: -1,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab description */}
      <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 13, margin: "0 0 16px" }}>
        {TABS.find((t) => t.key === activeTab)?.desc}
      </p>

      {/* Tab content */}
      {activeTab === "products" && <ProductsTab />}
      {activeTab === "feeds" && <FeedSourcesTab />}
      {activeTab === "suppliers" && <SuppliersTab onSelectVendor={handleSelectVendor} />}
    </div>
  );
}
