/**
 * GoogleMapsPage — Google Maps business scraping interface.
 * Search for businesses by type and location, view results in a card grid.
 */

import { useState, type FormEvent } from "react";

interface BusinessResult {
  id: string;
  name: string;
  address: string;
  phone: string;
  website: string;
  rating: number;
  reviewCount: number;
  isOpen: boolean;
  category: string;
  placeId: string;
}

const DEMO_BUSINESSES: BusinessResult[] = [
  {
    id: "1",
    name: "The Italian Kitchen",
    address: "142 Main Street, San Francisco, CA 94105",
    phone: "(415) 555-0142",
    website: "https://italiankitchensf.com",
    rating: 4.6,
    reviewCount: 847,
    isOpen: true,
    category: "Italian Restaurant",
    placeId: "ChIJabc123",
  },
  {
    id: "2",
    name: "Bay Sushi House",
    address: "298 Market Street, San Francisco, CA 94102",
    phone: "(415) 555-0298",
    website: "https://baysushihouse.com",
    rating: 4.3,
    reviewCount: 562,
    isOpen: true,
    category: "Japanese Restaurant",
    placeId: "ChIJdef456",
  },
  {
    id: "3",
    name: "Golden Gate Tacos",
    address: "78 Mission Street, San Francisco, CA 94105",
    phone: "(415) 555-0078",
    website: "https://goldengatetacos.com",
    rating: 4.8,
    reviewCount: 1203,
    isOpen: false,
    category: "Mexican Restaurant",
    placeId: "ChIJghi789",
  },
  {
    id: "4",
    name: "Pacific Brew Coffee",
    address: "455 Howard Street, San Francisco, CA 94105",
    phone: "(415) 555-0455",
    website: "https://pacificbrew.coffee",
    rating: 4.5,
    reviewCount: 389,
    isOpen: true,
    category: "Coffee Shop",
    placeId: "ChIJjkl012",
  },
  {
    id: "5",
    name: "Marina Seafood Grill",
    address: "1020 Chestnut Street, San Francisco, CA 94109",
    phone: "(415) 555-1020",
    website: "https://marinaseafoodgrill.com",
    rating: 4.1,
    reviewCount: 276,
    isOpen: true,
    category: "Seafood Restaurant",
    placeId: "ChIJmno345",
  },
  {
    id: "6",
    name: "Nob Hill Bakery",
    address: "832 Powell Street, San Francisco, CA 94108",
    phone: "(415) 555-0832",
    website: "https://nobhillbakery.com",
    rating: 4.9,
    reviewCount: 1547,
    isOpen: true,
    category: "Bakery",
    placeId: "ChIJpqr678",
  },
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

export function GoogleMapsPage() {
  const [businessType, setBusinessType] = useState("");
  const [location, setLocation] = useState("");
  const [maxResults, setMaxResults] = useState(20);
  const [isSearching, setIsSearching] = useState(false);
  const [businesses, setBusinesses] = useState<BusinessResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!businessType.trim() || !location.trim()) return;

    setIsSearching(true);
    setHasSearched(true);

    // Simulate API call
    setTimeout(() => {
      setBusinesses(DEMO_BUSINESSES);
      setIsSearching(false);
    }, 1500);
  }

  function handleExportToSheet() {
    alert("Export to Google Sheet functionality will connect to the Google Sheets connector.");
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
              background: "linear-gradient(135deg, #4285F4 0%, #34A853 50%, #FBBC05 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" />
              <circle cx="12" cy="10" r="3" />
            </svg>
          </div>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)" }}>
              Google Maps
            </h1>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
              Extract business data, reviews, and contact information
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
          <div style={{ flex: 1, minWidth: 200 }}>
            <label
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "var(--color-text-secondary)",
                marginBottom: 6,
              }}
            >
              What type of businesses?
            </label>
            <input
              type="text"
              className="search-input-lg"
              placeholder="e.g., restaurants, dentists, hotels"
              value={businessType}
              onChange={(e) => setBusinessType(e.target.value)}
              disabled={isSearching}
            />
          </div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <label
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "var(--color-text-secondary)",
                marginBottom: 6,
              }}
            >
              Location
            </label>
            <input
              type="text"
              className="search-input-lg"
              placeholder="e.g., San Francisco, CA"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              disabled={isSearching}
            />
          </div>
          <div style={{ minWidth: 120 }}>
            <label
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "var(--color-text-secondary)",
                marginBottom: 6,
              }}
            >
              Max Results
            </label>
            <select
              className="search-input-lg"
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value))}
              disabled={isSearching}
              style={{ cursor: "pointer" }}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            disabled={isSearching || !businessType.trim() || !location.trim()}
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
          <p style={{ color: "var(--color-text-secondary)" }}>Searching Google Maps...</p>
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
              background: "linear-gradient(135deg, #4285F4 0%, #34A853 50%, #FBBC05 100%)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 16,
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" />
              <circle cx="12" cy="10" r="3" />
            </svg>
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>
            Search Google Maps
          </h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            Enter a business type and location to scrape business listings including ratings, contact info, and reviews.
          </p>
        </div>
      )}

      {!isSearching && businesses.length > 0 && (
        <>
          {/* Results header */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 20,
            }}
          >
            <div>
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--color-text)" }}>
                {businesses.length} businesses found
              </span>
              <span style={{ fontSize: 13, color: "var(--color-text-secondary)", marginLeft: 8 }}>
                in {location || "selected area"}
              </span>
            </div>
            <button className="btn btn-primary" onClick={handleExportToSheet}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}>
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Export to Sheet
            </button>
          </div>

          {/* Business cards grid */}
          <div className="grid-cards">
            {businesses.map((biz) => (
              <div key={biz.id} className="business-card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--color-text)", marginBottom: 4 }}>
                      {biz.name}
                    </h3>
                    <span className="badge-purple" style={{ fontSize: 11 }}>{biz.category}</span>
                  </div>
                  <span className={biz.isOpen ? "badge-green" : "badge-red"}>
                    {biz.isOpen ? "Open" : "Closed"}
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <StarRating rating={biz.rating} />
                  <span style={{ fontSize: 14, fontWeight: 600, color: "var(--color-text)" }}>
                    {biz.rating}
                  </span>
                  <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                    ({biz.reviewCount.toLocaleString()})
                  </span>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13 }}>
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 8, color: "var(--color-text-secondary)" }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: 2 }}>
                      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" />
                      <circle cx="12" cy="10" r="3" />
                    </svg>
                    <span>{biz.address}</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--color-text-secondary)" }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                      <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z" />
                    </svg>
                    <span>{biz.phone}</span>
                  </div>
                  {biz.website && (
                    <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--color-text-secondary)" }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                        <circle cx="12" cy="12" r="10" />
                        <line x1="2" y1="12" x2="22" y2="12" />
                        <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
                      </svg>
                      <a
                        href={biz.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: "var(--color-primary)", textDecoration: "none" }}
                      >
                        {biz.website.replace(/^https?:\/\//, "")}
                      </a>
                    </div>
                  )}
                </div>

                <div style={{ marginTop: "auto", paddingTop: 8, borderTop: "1px solid var(--color-border)" }}>
                  <a
                    href={`https://www.google.com/maps/place/?q=place_id:${biz.placeId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: "var(--color-primary)",
                      textDecoration: "none",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                  >
                    View on Maps
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
                      <polyline points="15 3 21 3 21 9" />
                      <line x1="10" y1="14" x2="21" y2="3" />
                    </svg>
                  </a>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default GoogleMapsPage;
