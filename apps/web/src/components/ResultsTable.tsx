/**
 * ResultsTable — Table showing scraping results with columns:
 * title/name, url, extracted_data (preview), confidence_score (color-coded), created_at.
 * Supports pagination, sorting, and filtering by confidence threshold.
 */

import { Link } from "react-router-dom";
import type { ResultListItem } from "../api/types";

interface ResultsTableProps {
  results: ResultListItem[];
  total: number;
  page: number;
  pageSize: number;
  sortBy: string;
  sortOrder: "asc" | "desc";
  onPageChange: (page: number) => void;
  onSortChange: (field: string) => void;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function confidenceColor(confidence: number): string {
  if (confidence >= 0.9) return "var(--color-success)";
  if (confidence >= 0.7) return "var(--color-primary)";
  if (confidence >= 0.5) return "var(--color-warning)";
  return "var(--color-error)";
}

function confidenceBg(confidence: number): string {
  if (confidence >= 0.9) return "#dcfce7";
  if (confidence >= 0.7) return "#dbeafe";
  if (confidence >= 0.5) return "#fef3c7";
  return "#fee2e2";
}

function SortIndicator({ field, sortBy, sortOrder }: { field: string; sortBy: string; sortOrder: string }) {
  if (field !== sortBy) {
    return <span style={{ opacity: 0.3, marginLeft: 4 }}>&#8597;</span>;
  }
  return <span style={{ marginLeft: 4 }}>{sortOrder === "asc" ? "\u2191" : "\u2193"}</span>;
}

export function ResultsTable({
  results,
  total,
  page,
  pageSize,
  sortBy,
  sortOrder,
  onPageChange,
  onSortChange,
}: ResultsTableProps) {
  if (results.length === 0) {
    return (
      <div className="empty-state">
        <h3>No results found</h3>
        <p>Run a scraping task to generate results, or adjust your filters.</p>
      </div>
    );
  }

  const totalPages = Math.ceil(total / pageSize);

  const sortableHeader = (label: string, field: string) => (
    <th
      onClick={() => onSortChange(field)}
      style={{ cursor: "pointer", userSelect: "none" }}
    >
      {label}
      <SortIndicator field={field} sortBy={sortBy} sortOrder={sortOrder} />
    </th>
  );

  return (
    <>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              {sortableHeader("URL", "url")}
              <th>Method</th>
              {sortableHeader("Items", "item_count")}
              {sortableHeader("Confidence", "confidence")}
              {sortableHeader("Created", "created_at")}
              <th></th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.id}>
                <td className="url-cell" title={r.url}>
                  {r.url}
                </td>
                <td>{r.extraction_method}</td>
                <td>{r.item_count}</td>
                <td>
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      padding: "2px 10px",
                      borderRadius: 9999,
                      fontSize: 12,
                      fontWeight: 600,
                      lineHeight: "20px",
                      background: confidenceBg(r.confidence),
                      color: confidenceColor(r.confidence),
                    }}
                  >
                    {(r.confidence * 100).toFixed(0)}%
                  </span>
                </td>
                <td>{formatDate(r.created_at)}</td>
                <td>
                  <Link to={`/results/${r.id}`} className="btn btn-secondary btn-sm">
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "12px 0 0",
            borderTop: "1px solid var(--color-border)",
            marginTop: 12,
          }}
        >
          <button
            className="btn btn-secondary btn-sm"
            disabled={page === 0}
            onClick={() => onPageChange(page - 1)}
          >
            Previous
          </button>
          <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
            Page {page + 1} of {totalPages} ({total} result{total !== 1 ? "s" : ""})
          </span>
          <button
            className="btn btn-secondary btn-sm"
            disabled={page >= totalPages - 1}
            onClick={() => onPageChange(page + 1)}
          >
            Next
          </button>
        </div>
      )}
    </>
  );
}
