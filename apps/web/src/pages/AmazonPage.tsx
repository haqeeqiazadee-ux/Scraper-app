/**
 * AmazonPage — Amazon product lookup via live Keepa API.
 * Shows query type buttons for all available search types.
 */

import { useState, type FormEvent } from "react";
import { keepa, type KeepaProduct, type KeepaQueryResponse } from "../api/client";

const DOMAIN_OPTIONS = [
  { code: "US", label: "Amazon.com (US)" },
  { code: "GB", label: "Amazon.co.uk (UK)" },
  { code: "DE", label: "Amazon.de (DE)" },
  { code: "FR", label: "Amazon.fr (FR)" },
  { code: "JP", label: "Amazon.co.jp (JP)" },
  { code: "CA", label: "Amazon.ca (CA)" },
  { code: "IT", label: "Amazon.it (IT)" },
  { code: "ES", label: "Amazon.es (ES)" },
  { code: "IN", label: "Amazon.in (IN)" },
  { code: "MX", label: "Amazon.com.mx (MX)" },
  { code: "BR", label: "Amazon.com.br (BR)" },
];

type QueryType = "asin" | "url" | "keyword" | "multi" | "brand" | "deals";

const QUERY_TYPES: { type: QueryType; label: string; icon: string; example: string; desc: string; color: string }[] = [
  { type: "asin", label: "ASIN Lookup", icon: "🔍", example: "B0088PUEPK", desc: "Single product by ASIN", color: "#2563eb" },
  { type: "multi", label: "Batch ASINs", icon: "📦", example: "B0088PUEPK, B09V3KXJPB, B07FZ8S74R", desc: "Multiple ASINs (comma separated)", color: "#7c3aed" },
  { type: "url", label: "Amazon URL", icon: "🔗", example: "https://www.amazon.com/dp/B0088PUEPK", desc: "Paste any Amazon product URL", color: "#059669" },
  { type: "keyword", label: "Keyword Search", icon: "🔎", example: "wireless mouse", desc: "Search by product name/keywords", color: "#d97706" },
  { type: "brand", label: "Brand Search", icon: "🏷️", example: "Apple MacBook", desc: "Search by brand + product type", color: "#dc2626" },
  { type: "deals", label: "Find Deals", icon: "🔥", example: "20", desc: "Find products with price drops (%)", color: "#ea580c" },
];

function StarRating({ rating }: { rating: number }) {
  const stars = [];
  for (let i = 1; i <= 5; i++) {
    stars.push(
      <span key={i} className={i <= Math.round(rating) ? "star" : "star-empty"}>★</span>
    );
  }
  return <span className="stars">{stars}</span>;
}

export function AmazonPage() {
  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState("US");
  const [selectedType, setSelectedType] = useState<QueryType>("asin");
  const [isSearching, setIsSearching] = useState(false);
  const [products, setProducts] = useState<KeepaProduct[]>([]);
  const [response, setResponse] = useState<KeepaQueryResponse | null>(null);
  const [error, setError] = useState("");
  const [hasSearched, setHasSearched] = useState(false);

  function handleTypeSelect(type: QueryType) {
    setSelectedType(type);
    const qt = QUERY_TYPES.find(q => q.type === type);
    if (qt) setQuery(qt.example);
  }

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setError("");
    setHasSearched(true);

    try {
      let result: KeepaQueryResponse;

      if (selectedType === "deals") {
        const dealsResult = await keepa.deals({
          min_discount_percent: parseInt(query) || 20,
          domain,
        });
        result = {
          query: `Deals ≥${query}% off`,
          query_type: "deals",
          domain,
          asins: [],
          products: (dealsResult.deals || []).slice(0, 20) as KeepaProduct[],
          count: dealsResult.count,
          tokens_left: dealsResult.tokens_left,
        };
      } else {
        result = await keepa.query(query.trim(), domain);
      }

      setResponse(result);
      setProducts(result.products || []);
      if (result.count === 0) {
        setError("No products found. Try a different query.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to query Keepa API";
      setError(msg);
      setProducts([]);
    } finally {
      setIsSearching(false);
    }
  }

  const activeType = QUERY_TYPES.find(q => q.type === selectedType);

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: "linear-gradient(135deg, #ff9900 0%, #ffb347 100%)",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <path d="M16 10a4 4 0 01-8 0" />
            </svg>
          </div>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)" }}>Amazon / Keepa</h1>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
              Live product data, price history, and sales analytics via Keepa API
            </p>
          </div>
        </div>
      </div>

      {/* Query Type Buttons */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 10 }}>
          Select Query Type:
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: 10 }}>
          {QUERY_TYPES.map((qt) => (
            <button
              key={qt.type}
              type="button"
              onClick={() => handleTypeSelect(qt.type)}
              style={{
                padding: "14px 16px",
                borderRadius: 12,
                border: selectedType === qt.type ? `2px solid ${qt.color}` : "2px solid var(--color-border)",
                background: selectedType === qt.type ? `${qt.color}10` : "var(--color-surface)",
                cursor: "pointer",
                textAlign: "left",
                transition: "all 0.15s",
                boxShadow: selectedType === qt.type ? `0 0 0 3px ${qt.color}20` : "none",
              }}
            >
              <div style={{ fontSize: 20, marginBottom: 6 }}>{qt.icon}</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: selectedType === qt.type ? qt.color : "var(--color-text)", marginBottom: 2 }}>
                {qt.label}
              </div>
              <div style={{ fontSize: 11, color: "var(--color-text-secondary)", lineHeight: 1.3 }}>
                {qt.desc}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Search bar */}
      <form onSubmit={handleSearch} style={{ marginBottom: 24 }}>
        <div className="accent-card" style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 280 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
              {activeType?.label || "Search"} — <span style={{ fontWeight: 400 }}>{activeType?.desc}</span>
            </label>
            <input
              type="text"
              className="search-input-lg"
              placeholder={`e.g. ${activeType?.example || "B0088PUEPK"}`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isSearching}
            />
          </div>
          <div style={{ minWidth: 200 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Marketplace</label>
            <select className="search-input-lg" value={domain} onChange={(e) => setDomain(e.target.value)} disabled={isSearching} style={{ cursor: "pointer" }}>
              {DOMAIN_OPTIONS.map((d) => (<option key={d.code} value={d.code}>{d.label}</option>))}
            </select>
          </div>
          <button type="submit" className="btn btn-primary btn-lg" disabled={isSearching || !query.trim()} style={{ height: 50, paddingInline: 32 }}>
            {isSearching ? (<span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}><span className="spinner" /> Searching...</span>) : "Search"}
          </button>
        </div>
      </form>

      {/* Error */}
      {error && <div className="form-error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Loading */}
      {isSearching && (
        <div style={{ textAlign: "center", padding: 60 }}>
          <div className="spinner" style={{ width: 32, height: 32, margin: "0 auto 16px" }} />
          <p style={{ color: "var(--color-text-secondary)" }}>Fetching live data from Keepa API...</p>
        </div>
      )}

      {/* Results */}
      {!isSearching && products.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
            <div style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>
              <strong style={{ color: "var(--color-text)" }}>{products.length}</strong> product{products.length !== 1 ? "s" : ""} found
              {response?.query_type && <span className="badge-blue" style={{ marginLeft: 8 }}>{response.query_type}</span>}
              {response?.tokens_left !== undefined && <span style={{ marginLeft: 12, fontSize: 12 }}>Tokens remaining: {response.tokens_left}</span>}
            </div>
          </div>

          {products.map((product) => (
            <div key={product.asin || Math.random()} className="product-card-lg">
              <div style={{ width: 200, height: 200, background: "#f8f9fa", borderRadius: "var(--radius-md)", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
                {product.image_url ? (
                  <img src={product.image_url} alt={product.name} style={{ width: 200, height: 200, objectFit: "contain" }} />
                ) : (
                  <div style={{ textAlign: "center", color: "#aaa", fontSize: 12 }}>No Image</div>
                )}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div>
                  {product.asin && <span className="badge-blue" style={{ marginBottom: 6, display: "inline-block" }}>ASIN: {product.asin}</span>}
                  <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)", lineHeight: 1.3, marginTop: 4 }}>{product.name || "Untitled"}</h2>
                  <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 4 }}>
                    {product.brand && <>by <strong>{product.brand}</strong></>}
                    {product.category && <> in {product.category}</>}
                  </p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
                  {product.price && (
                    <span style={{ fontSize: 26, fontWeight: 800, background: "linear-gradient(135deg, #ff9900, #e67e00)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                      ${product.price}
                    </span>
                  )}
                  {product.original_price && <span style={{ fontSize: 14, color: "var(--color-text-secondary)", textDecoration: "line-through" }}>${product.original_price}</span>}
                  {product.stock_status && <span className={product.stock_status === "InStock" ? "badge-green" : "badge-red"}>{product.stock_status}</span>}
                </div>
                {product.rating && (
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <StarRating rating={parseFloat(product.rating)} />
                    <span style={{ fontSize: 14, fontWeight: 600 }}>{product.rating}</span>
                    {product.reviews_count && <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>({parseInt(product.reviews_count).toLocaleString()} reviews)</span>}
                  </div>
                )}
                {product.sales_rank > 0 && (
                  <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                    Sales Rank: <strong style={{ color: "var(--color-text)" }}>#{product.sales_rank.toLocaleString()}</strong>
                  </div>
                )}
                {product.product_url && (
                  <a href={product.product_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: "var(--color-primary)" }}>View on Amazon →</a>
                )}
              </div>
            </div>
          ))}

          {products[0] && (
            <div className="grid-stats">
              <StatCard label="New Offers" value={products[0].offer_count_new?.toString() || "—"} color="#2563eb" />
              <StatCard label="Used Offers" value={products[0].offer_count_used?.toString() || "—"} color="#7c3aed" />
              <StatCard label="FBA Price" value={products[0].fba_price ? `$${products[0].fba_price}` : "—"} color="#059669" />
              <StatCard label="Sales Rank" value={products[0].sales_rank > 0 ? `#${products[0].sales_rank}` : "—"} color="#d97706" />
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!isSearching && !hasSearched && products.length === 0 && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{ width: 64, height: 64, borderRadius: 16, background: "linear-gradient(135deg, #ff9900, #ffb347)", display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>Select a query type and search</h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            Choose a query type above, then enter your search to fetch live data from Keepa.
          </p>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="accent-card" style={{ textAlign: "center" }}>
      <div style={{ fontSize: 24, fontWeight: 800, color, marginBottom: 4 }}>{value}</div>
      <div style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
    </div>
  );
}

export default AmazonPage;
