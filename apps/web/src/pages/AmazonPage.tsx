/**
 * AmazonPage — Amazon product lookup via live Keepa API.
 * Searches by ASIN, Amazon URL, or keyword. Displays real product data.
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

const SEARCH_EXAMPLES = [
  { label: "ASIN Lookup", example: "B0088PUEPK", desc: "Single product by ASIN" },
  { label: "Multiple ASINs", example: "B0088PUEPK, B09V3KXJPB", desc: "Comma-separated ASINs" },
  { label: "Amazon URL", example: "https://www.amazon.com/dp/B0088PUEPK", desc: "Any Amazon product URL" },
  { label: "Keyword Search", example: "wireless mouse", desc: "Search by product title" },
  { label: "Brand Search", example: "Apple MacBook", desc: "Brand + keyword" },
];

function StarRating({ rating }: { rating: number }) {
  const stars = [];
  for (let i = 1; i <= 5; i++) {
    stars.push(
      <span key={i} className={i <= Math.round(rating) ? "star" : "star-empty"}>
        &#9733;
      </span>
    );
  }
  return <span className="stars">{stars}</span>;
}

export function AmazonPage() {
  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState("US");
  const [isSearching, setIsSearching] = useState(false);
  const [products, setProducts] = useState<KeepaProduct[]>([]);
  const [response, setResponse] = useState<KeepaQueryResponse | null>(null);
  const [error, setError] = useState("");
  const [hasSearched, setHasSearched] = useState(false);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setError("");
    setHasSearched(true);

    try {
      const result = await keepa.query(query.trim(), domain);
      setResponse(result);
      setProducts(result.products || []);
      if (result.count === 0) {
        setError("No products found. Try a different ASIN or keyword.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to query Keepa API";
      setError(msg);
      setProducts([]);
    } finally {
      setIsSearching(false);
    }
  }

  function handleExampleClick(example: string) {
    setQuery(example);
  }

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div
            style={{
              width: 40, height: 40, borderRadius: 10,
              background: "linear-gradient(135deg, #ff9900 0%, #ffb347 100%)",
              display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}
          >
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

      {/* Search bar */}
      <form onSubmit={handleSearch} style={{ marginBottom: 24 }}>
        <div className="accent-card" style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 280 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
              ASIN, Amazon URL, or Keyword
            </label>
            <input
              type="text"
              className="search-input-lg"
              placeholder="e.g. B0088PUEPK or wireless mouse"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isSearching}
            />
          </div>
          <div style={{ minWidth: 200 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
              Marketplace
            </label>
            <select
              className="search-input-lg"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              disabled={isSearching}
              style={{ cursor: "pointer" }}
            >
              {DOMAIN_OPTIONS.map((d) => (
                <option key={d.code} value={d.code}>{d.label}</option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            disabled={isSearching || !query.trim()}
            style={{ height: 50, paddingInline: 32 }}
          >
            {isSearching ? (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                <span className="spinner" /> Searching...
              </span>
            ) : "Search"}
          </button>
        </div>
      </form>

      {/* Quick examples */}
      {!hasSearched && (
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 10 }}>
            Search Examples — click to try:
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {SEARCH_EXAMPLES.map((ex) => (
              <button
                key={ex.example}
                type="button"
                onClick={() => handleExampleClick(ex.example)}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--color-border)",
                  background: "var(--color-surface)",
                  cursor: "pointer",
                  fontSize: 13,
                  color: "var(--color-text)",
                  transition: "all 0.15s",
                }}
                title={ex.desc}
              >
                <span style={{ fontWeight: 600, color: "var(--color-primary)" }}>{ex.label}:</span>{" "}
                <code style={{ fontSize: 12 }}>{ex.example}</code>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="form-error-banner" style={{ marginBottom: 16 }}>{error}</div>
      )}

      {/* Loading */}
      {isSearching && (
        <div style={{ textAlign: "center", padding: 60 }}>
          <div className="spinner" style={{ width: 32, height: 32, margin: "0 auto 16px" }} />
          <p style={{ color: "var(--color-text-secondary)" }}>Fetching live data from Keepa API...</p>
        </div>
      )}

      {/* Empty state */}
      {!isSearching && !hasSearched && (
        <div className="accent-card" style={{ textAlign: "center", padding: 60 }}>
          <div style={{
            width: 64, height: 64, borderRadius: 16,
            background: "linear-gradient(135deg, #ff9900, #ffb347)",
            display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16,
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>Search for a Product</h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            Enter an ASIN, Amazon URL, or keyword to fetch live pricing, sales rank, and offer data.
          </p>
        </div>
      )}

      {/* Results */}
      {!isSearching && products.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Meta info */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
            <div style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>
              <strong style={{ color: "var(--color-text)" }}>{products.length}</strong> product{products.length !== 1 ? "s" : ""} found
              {response?.query_type && (
                <span className="badge-blue" style={{ marginLeft: 8 }}>{response.query_type}</span>
              )}
              {response?.tokens_left !== undefined && (
                <span style={{ marginLeft: 12 }}>Tokens: {response.tokens_left}</span>
              )}
            </div>
          </div>

          {/* Product cards */}
          {products.map((product) => (
            <div key={product.asin} className="product-card-lg">
              {/* Image */}
              <div style={{
                width: 200, height: 200, background: "#f8f9fa",
                borderRadius: "var(--radius-md)", display: "flex",
                alignItems: "center", justifyContent: "center", overflow: "hidden",
              }}>
                {product.image_url ? (
                  <img src={product.image_url} alt={product.name} style={{ width: 200, height: 200, objectFit: "contain" }} />
                ) : (
                  <div style={{ textAlign: "center", color: "#aaa", fontSize: 13 }}>
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ opacity: 0.4 }}>
                      <rect x="3" y="3" width="18" height="18" rx="2" />
                      <circle cx="8.5" cy="8.5" r="1.5" />
                      <polyline points="21 15 16 10 5 21" />
                    </svg>
                    <div style={{ marginTop: 8 }}>No Image</div>
                  </div>
                )}
              </div>

              {/* Details */}
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div>
                  <span className="badge-blue" style={{ marginBottom: 6, display: "inline-block" }}>
                    ASIN: {product.asin}
                  </span>
                  <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)", lineHeight: 1.3, marginTop: 4 }}>
                    {product.name || "Untitled Product"}
                  </h2>
                  <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 4 }}>
                    {product.brand && <>by <strong>{product.brand}</strong></>}
                    {product.category && <> in {product.category}</>}
                  </p>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
                  {product.price && (
                    <span style={{
                      fontSize: 26, fontWeight: 800,
                      background: "linear-gradient(135deg, #ff9900, #e67e00)",
                      WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                    }}>
                      ${product.price}
                    </span>
                  )}
                  {product.amazon_price && product.amazon_price !== product.price && (
                    <span style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>
                      Amazon: ${product.amazon_price}
                    </span>
                  )}
                  {product.original_price && (
                    <span style={{ fontSize: 14, color: "var(--color-text-secondary)", textDecoration: "line-through" }}>
                      ${product.original_price}
                    </span>
                  )}
                  {product.stock_status && (
                    <span className={product.stock_status === "InStock" ? "badge-green" : "badge-red"}>
                      {product.stock_status}
                    </span>
                  )}
                </div>

                {product.rating && (
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <StarRating rating={parseFloat(product.rating)} />
                    <span style={{ fontSize: 14, fontWeight: 600 }}>{product.rating}</span>
                    {product.reviews_count && (
                      <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                        ({parseInt(product.reviews_count).toLocaleString()} reviews)
                      </span>
                    )}
                  </div>
                )}

                {product.sales_rank > 0 && (
                  <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                    Sales Rank: <strong style={{ color: "var(--color-text)" }}>#{product.sales_rank.toLocaleString()}</strong>
                  </div>
                )}

                {product.product_url && (
                  <a href={product.product_url} target="_blank" rel="noopener noreferrer"
                    style={{ fontSize: 13, color: "var(--color-primary)" }}>
                    View on Amazon →
                  </a>
                )}
              </div>
            </div>
          ))}

          {/* Stats row for first product */}
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
