/**
 * ResultsPage — Page combining ResultsTable with filters sidebar.
 * Route: /results
 */

import { useState } from "react";
import { useResultList } from "../hooks/useResults";
import { ResultsTable } from "../components/ResultsTable";
import { ExportDialog } from "../components/ExportDialog";

const PAGE_SIZE = 20;

const CONFIDENCE_FILTERS: { label: string; value: number }[] = [
  { label: "All", value: 0 },
  { label: ">50%", value: 0.5 },
  { label: ">70%", value: 0.7 },
  { label: ">90%", value: 0.9 },
];

export function ResultsPage() {
  const [page, setPage] = useState(0);
  const [minConfidence, setMinConfidence] = useState(0);
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [exportOpen, setExportOpen] = useState(false);

  const { data, isLoading, error } = useResultList({
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    min_confidence: minConfidence > 0 ? minConfidence : undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  function handleSortChange(field: string) {
    if (field === sortBy) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
    setPage(0);
  }

  return (
    <>
      <div className="page-header">
        <h2>Results</h2>
        <p>Browse and export extraction results.</p>
      </div>
      <div className="page-body">
        {/* Toolbar: filters + export */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 8,
            marginBottom: 16,
          }}
        >
          {/* Confidence filter pills */}
          <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: "var(--color-text-secondary)",
                marginRight: 4,
              }}
            >
              Confidence:
            </span>
            {CONFIDENCE_FILTERS.map((f) => (
              <button
                key={f.label}
                className={`btn btn-sm ${minConfidence === f.value ? "btn-primary" : "btn-secondary"}`}
                onClick={() => {
                  setMinConfidence(f.value);
                  setPage(0);
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Export button */}
          <button
            className="btn btn-primary btn-sm"
            onClick={() => setExportOpen(true)}
          >
            Export Results
          </button>
        </div>

        {/* Results card */}
        <div className="card">
          <div className="card-header">
            <h3>
              {total} result{total !== 1 ? "s" : ""}
              {minConfidence > 0 ? ` (confidence > ${(minConfidence * 100).toFixed(0)}%)` : ""}
            </h3>
          </div>

          {isLoading && <div className="loading">Loading results...</div>}

          {error && (
            <div className="empty-state">
              <h3>Failed to load results</h3>
              <p>An error occurred while fetching results. Please try again.</p>
            </div>
          )}

          {!isLoading && !error && (
            <ResultsTable
              results={items}
              total={total}
              page={page}
              pageSize={PAGE_SIZE}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onPageChange={setPage}
              onSortChange={handleSortChange}
            />
          )}
        </div>
      </div>

      <ExportDialog open={exportOpen} onClose={() => setExportOpen(false)} />
    </>
  );
}
