/**
 * GoogleMapsPage — Google Maps business scraping interface.
 * Search for businesses by type and location with query type buttons.
 * Calls backend API which uses Places API → SerpAPI → browser fallback.
 */

import { useState, type FormEvent } from "react";

interface BusinessResult {
  name: string;
  address: string;
  phone: string;
  website: string;
  rating: number | null;
  review_count: number | null;
  open_now: boolean | null;
  primary_type: string;
  place_id: string;
  google_maps_url: string;
  source: string;
  latitude: number | null;
  longitude: number | null;
  price_level: string;
  business_status: string;
}

type SearchType = "business" | "restaurant" | "hotel" | "medical" | "service" | "retail";

const SEARCH_TYPES: { type: SearchType; label: string; icon: string; example: string; location: string; desc: string; color: string }[] = [
  { type: "business", label: "Any Business", icon: "🏢", example: "business consultants", location: "Dubai", desc: "Search any type of business", color: "#2563eb" },
  { type: "restaurant", label: "Restaurants", icon: "🍽️", example: "italian restaurants", location: "New York", desc: "Restaurants, cafes, food places", color: "#dc2626" },
  { type: "hotel", label: "Hotels", icon: "🏨", example: "luxury hotels", location: "London", desc: "Hotels, resorts, accommodation", color: "#7c3aed" },
  { type: "medical", label: "Medical", icon: "🏥", example: "dentists", location: "Los Angeles", desc: "Doctors, clinics, hospitals", color: "#059669" },
  { type: "service", label: "Services", icon: "🔧", example: "plumbers", location: "Chicago", desc: "Plumbers, electricians, contractors", color: "#d97706" },
  { type: "retail", label: "Retail & Shopping", icon: "🛍️", example: "electronics stores", location: "San Francisco", desc: "Shops, malls, retail stores", color: "#ea580c" },
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

export function GoogleMapsPage() {
  const [businessType, setBusinessType] = useState("");
  const [location, setLocation] = useState("");
  const [maxResults, setMaxResults] = useState(20);
  const [selectedType, setSelectedType] = useState<SearchType>("business");
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<BusinessResult[]>([]);
  const [error, setError] = useState("");
  const [hasSearched, setHasSearched] = useState(false);

  function handleTypeSelect(type: SearchType) {
    setSelectedType(type);
    const st = SEARCH_TYPES.find(s => s.type === type);
    if (st) {
      setBusinessType(st.example);
      setLocation(st.location);
    }
  }

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!businessType.trim()) return;

    setIsSearching(true);
    setError("");
    setHasSearched(true);

    try {
      const query = location.trim()
        ? `${businessType.trim()} in ${location.trim()}`
        : businessType.trim();

      const BASE = (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? "/api/v1";
      const token = localStorage.getItem("auth_token");
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };

      const resp = await fetch(`${BASE}/maps/search`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          query,
          max_results: maxResults,
        }),
      });

      if (!resp.ok) {
        throw new Error(`API error: ${resp.status}`);
      }

      const data = await resp.json();
      setResults(data.results || []);
      if ((data.results || []).length === 0) {
        setError("No businesses found. Try a different search.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Search failed";
      setError(msg);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }

  const activeType = SEARCH_TYPES.find(s => s.type === selectedType);

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: "linear-gradient(135deg, #4285F4 0%, #34A853 50%, #EA4335 100%)",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" />
              <circle cx="12" cy="10" r="3" />
            </svg>
          </div>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)" }}>Google Maps</h1>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
              Scrape business data — 3 tiers: Places API → SerpAPI → Browser
            </p>
          </div>
        </div>
      </div>

      {/* Search Type Buttons */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 10 }}>
          Select Business Category:
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: 10 }}>
          {SEARCH_TYPES.map((st) => (
            <button
              key={st.type}
              type="button"
              onClick={() => handleTypeSelect(st.type)}
              style={{
                padding: "14px 16px",
                borderRadius: 12,
                border: selectedType === st.type ? `2px solid ${st.color}` : "2px solid var(--color-border)",
                background: selectedType === st.type ? `${st.color}10` : "var(--color-surface)",
                cursor: "pointer",
                textAlign: "left",
                transition: "all 0.15s",
                boxShadow: selectedType === st.type ? `0 0 0 3px ${st.color}20` : "none",
              }}
            >
              <div style={{ fontSize: 20, marginBottom: 6 }}>{st.icon}</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: selectedType === st.type ? st.color : "var(--color-text)", marginBottom: 2 }}>
                {st.label}
              </div>
              <div style={{ fontSize: 11, color: "var(--color-text-secondary)", lineHeight: 1.3 }}>{st.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} style={{ marginBottom: 24 }}>
        <div className="accent-card" style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 220 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
              Business Type
            </label>
            <input
              type="text"
              className="search-input-lg"
              placeholder={`e.g. ${activeType?.example || "restaurants"}`}
              value={businessType}
              onChange={(e) => setBusinessType(e.target.value)}
              disabled={isSearching}
            />
          </div>
          <div style={{ flex: 1, minWidth: 180 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
              Location
            </label>
            <input
              type="text"
              className="search-input-lg"
              placeholder={`e.g. ${activeType?.location || "Dubai"}`}
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              disabled={isSearching}
            />
          </div>
          <div style={{ minWidth: 100 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>Results</label>
            <select className="search-input-lg" value={maxResults} onChange={(e) => setMaxResults(Number(e.target.value))} disabled={isSearching} style={{ cursor: "pointer" }}>
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
          <button type="submit" className="btn btn-primary btn-lg" disabled={isSearching || !businessType.trim()} style={{ height: 50, paddingInline: 32 }}>
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
          <p style={{ color: "var(--color-text-secondary)" }}>Searching Google Maps...</p>
        </div>
      )}

      {/* Results Grid */}
      {!isSearching && results.length > 0 && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>
              <strong style={{ color: "var(--color-text)" }}>{results.length}</strong> businesses found
            </div>
          </div>
          <div className="grid-cards">
            {results.map((biz, idx) => (
              <div key={biz.place_id || idx} className="business-card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--color-text)", marginBottom: 4 }}>{biz.name}</h3>
                    {biz.primary_type && <span className="badge-blue">{biz.primary_type}</span>}
                  </div>
                  {biz.open_now !== null && (
                    <span className={biz.open_now ? "badge-green" : "badge-red"}>
                      {biz.open_now ? "Open" : "Closed"}
                    </span>
                  )}
                </div>
                {biz.address && <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>📍 {biz.address}</div>}
                {biz.phone && <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>📞 {biz.phone}</div>}
                {biz.website && (
                  <a href={biz.website} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: "var(--color-primary)" }}>
                    🌐 {biz.website.replace(/^https?:\/\//, "").slice(0, 40)}
                  </a>
                )}
                {biz.rating !== null && (
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <StarRating rating={biz.rating} />
                    <span style={{ fontSize: 14, fontWeight: 600 }}>{biz.rating}</span>
                    {biz.review_count !== null && (
                      <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>({biz.review_count.toLocaleString()})</span>
                    )}
                  </div>
                )}
                {biz.google_maps_url && (
                  <a href={biz.google_maps_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12, color: "var(--color-primary)" }}>
                    View on Google Maps →
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isSearching && !hasSearched && results.length === 0 && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{ width: 64, height: 64, borderRadius: 16, background: "linear-gradient(135deg, #4285F4, #34A853)", display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" /><circle cx="12" cy="10" r="3" /></svg>
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>Search for businesses</h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            Select a category above, then enter a business type and location to search Google Maps.
          </p>
        </div>
      )}
    </div>
  );
}

export default GoogleMapsPage;
