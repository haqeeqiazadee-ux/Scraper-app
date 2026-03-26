/**
 * AmazonPage — Amazon product lookup via Keepa API.
 * Search by ASIN or Amazon URL, view product details, price history, and offers.
 */

import { useState, type FormEvent } from "react";

const AMAZON_DOMAINS = [
  { code: "us", label: "Amazon.com (US)", domain: "amazon.com" },
  { code: "uk", label: "Amazon.co.uk (UK)", domain: "amazon.co.uk" },
  { code: "de", label: "Amazon.de (DE)", domain: "amazon.de" },
  { code: "fr", label: "Amazon.fr (FR)", domain: "amazon.fr" },
  { code: "jp", label: "Amazon.co.jp (JP)", domain: "amazon.co.jp" },
  { code: "ca", label: "Amazon.ca (CA)", domain: "amazon.ca" },
  { code: "it", label: "Amazon.it (IT)", domain: "amazon.it" },
  { code: "es", label: "Amazon.es (ES)", domain: "amazon.es" },
  { code: "in", label: "Amazon.in (IN)", domain: "amazon.in" },
  { code: "mx", label: "Amazon.com.mx (MX)", domain: "amazon.com.mx" },
  { code: "br", label: "Amazon.com.br (BR)", domain: "amazon.com.br" },
];

interface ProductResult {
  asin: string;
  title: string;
  brand: string;
  price: string;
  currency: string;
  rating: number;
  reviewCount: number;
  salesRank: number;
  category: string;
  imageUrl: string;
  offersNew: number;
  offersUsed: number;
  fbaPrice: string;
  availability: string;
}

const DEMO_PRODUCT: ProductResult = {
  asin: "B0BSHF7WHW",
  title: 'Apple 2023 MacBook Pro Laptop M2 Pro chip with 12-core CPU and 19-core GPU: 16.2-inch Liquid Retina XDR Display, 16GB Unified Memory, 512GB SSD Storage',
  brand: "Apple",
  price: "$2,499.00",
  currency: "USD",
  rating: 4.7,
  reviewCount: 3842,
  salesRank: 12,
  category: "Laptops",
  imageUrl: "",
  offersNew: 24,
  offersUsed: 18,
  fbaPrice: "$2,449.00",
  availability: "In Stock",
};

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
  const [domain, setDomain] = useState("us");
  const [isSearching, setIsSearching] = useState(false);
  const [product, setProduct] = useState<ProductResult | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setHasSearched(true);

    // Simulate API call
    setTimeout(() => {
      setProduct(DEMO_PRODUCT);
      setIsSearching(false);
    }, 1200);
  }

  function handleSaveToSheet() {
    alert("Save to Google Sheet functionality will connect to the Google Sheets connector.");
  }

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 10,
              background: "linear-gradient(135deg, #ff9900 0%, #ffb347 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <path d="M16 10a4 4 0 01-8 0" />
            </svg>
          </div>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)" }}>
              Amazon / Keepa
            </h1>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
              Product data, price history, and sales analytics via Keepa API
            </p>
          </div>
        </div>
      </div>

      {/* Search bar */}
      <form onSubmit={handleSearch} style={{ marginBottom: 32 }}>
        <div
          className="accent-card"
          style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}
        >
          <div style={{ flex: 1, minWidth: 280 }}>
            <label
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "var(--color-text-secondary)",
                marginBottom: 6,
              }}
            >
              ASIN or Amazon URL
            </label>
            <input
              type="text"
              className="search-input-lg"
              placeholder="Enter ASIN (e.g., B0BSHF7WHW) or Amazon product URL"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isSearching}
            />
          </div>
          <div style={{ minWidth: 200 }}>
            <label
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "var(--color-text-secondary)",
                marginBottom: 6,
              }}
            >
              Marketplace
            </label>
            <select
              className="search-input-lg"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              disabled={isSearching}
              style={{ cursor: "pointer" }}
            >
              {AMAZON_DOMAINS.map((d) => (
                <option key={d.code} value={d.code}>
                  {d.label}
                </option>
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
                <span className="spinner" />
                Searching...
              </span>
            ) : (
              "Search"
            )}
          </button>
        </div>
      </form>

      {/* Results */}
      {isSearching && (
        <div style={{ textAlign: "center", padding: 60 }}>
          <div className="spinner" style={{ width: 32, height: 32, margin: "0 auto 16px" }} />
          <p style={{ color: "var(--color-text-secondary)" }}>Fetching product data from Keepa...</p>
        </div>
      )}

      {!isSearching && !hasSearched && (
        <div
          className="accent-card"
          style={{ textAlign: "center", padding: 60 }}
        >
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: 16,
              background: "linear-gradient(135deg, #ff9900 0%, #ffb347 100%)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 16,
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>
            Search for a Product
          </h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            Enter an ASIN or Amazon product URL to fetch real-time pricing, sales rank, and offer data via Keepa.
          </p>
        </div>
      )}

      {!isSearching && product && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Action bar */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
            <button className="btn btn-primary" onClick={handleSaveToSheet}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}>
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
              Save to Google Sheet
            </button>
          </div>

          {/* Product card */}
          <div className="product-card-lg">
            <div
              style={{
                width: 200,
                height: 200,
                background: "linear-gradient(135deg, #f8f9fa, #e9ecef)",
                borderRadius: "var(--radius-md)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-text-tertiary)",
                fontSize: 13,
              }}
            >
              <div style={{ textAlign: "center" }}>
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.4 }}>
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
                <div style={{ marginTop: 8 }}>Product Image</div>
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <span className="badge-blue" style={{ marginBottom: 8, display: "inline-block" }}>
                  ASIN: {product.asin}
                </span>
                <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--color-text)", lineHeight: 1.3, marginTop: 4 }}>
                  {product.title}
                </h2>
                <p style={{ fontSize: 14, color: "var(--color-text-secondary)", marginTop: 4 }}>
                  by <strong>{product.brand}</strong> in {product.category}
                </p>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
                <span
                  style={{
                    fontSize: 28,
                    fontWeight: 800,
                    background: "linear-gradient(135deg, #ff9900, #e67e00)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                  }}
                >
                  {product.price}
                </span>
                <span className="badge-green">{product.availability}</span>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <StarRating rating={product.rating} />
                <span style={{ fontSize: 14, fontWeight: 600, color: "var(--color-text)" }}>
                  {product.rating}
                </span>
                <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                  ({product.reviewCount.toLocaleString()} reviews)
                </span>
              </div>

              <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                Sales Rank: <strong style={{ color: "var(--color-text)" }}>#{product.salesRank.toLocaleString()}</strong> in {product.category}
              </div>
            </div>
          </div>

          {/* Stats row */}
          <div className="grid-stats">
            <StatCard label="New Offers" value={product.offersNew.toString()} color="#2563eb" />
            <StatCard label="Used Offers" value={product.offersUsed.toString()} color="#7c3aed" />
            <StatCard label="FBA Price" value={product.fbaPrice} color="#059669" />
            <StatCard label="Sales Rank" value={`#${product.salesRank}`} color="#d97706" />
          </div>

          {/* Price history placeholder */}
          <div className="accent-card">
            <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 12 }}>
              Price History
            </h3>
            <div
              style={{
                height: 200,
                background: "linear-gradient(135deg, #f8f9fa, #eff6ff)",
                borderRadius: "var(--radius-md)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: "1px dashed var(--color-border)",
              }}
            >
              <div style={{ textAlign: "center", color: "var(--color-text-secondary)" }}>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.4, margin: "0 auto 8px", display: "block" }}>
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                </svg>
                <p style={{ fontWeight: 600, marginBottom: 4 }}>Price history available via Keepa API</p>
                <p style={{ fontSize: 12 }}>Historical pricing, Buy Box tracking, and deal alerts</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="accent-card" style={{ textAlign: "center" }}>
      <div
        style={{
          fontSize: 24,
          fontWeight: 800,
          color,
          marginBottom: 4,
        }}
      >
        {value}
      </div>
      <div style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
        {label}
      </div>
    </div>
  );
}

export default AmazonPage;
