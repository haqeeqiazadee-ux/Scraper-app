import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { results } from "../api/client";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

export function Results() {
  const [searchParams] = useSearchParams();
  const resultId = searchParams.get("id");

  const {
    data: result,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["result", resultId],
    queryFn: () => results.get(resultId!),
    enabled: !!resultId,
  });

  return (
    <>
      <div className="page-header">
        <h2>Results</h2>
        <p>Browse and inspect extraction results.</p>
      </div>
      <div className="page-body">
        {!resultId && (
          <div className="card">
            <div className="empty-state">
              <h3>Select a result to inspect</h3>
              <p>
                Navigate to a task detail page and click "View" on a result,
                or provide a result ID in the URL (?id=...).
              </p>
            </div>
          </div>
        )}

        {resultId && isLoading && <div className="loading">Loading result...</div>}

        {resultId && error && (
          <div className="card">
            <div className="empty-state">
              <h3>Result not found</h3>
              <p>The requested result does not exist.</p>
            </div>
          </div>
        )}

        {result && (
          <div className="detail-grid">
            {/* Metadata card */}
            <div className="card">
              <div className="card-header">
                <h3>Result Metadata</h3>
              </div>
              <div className="detail-row">
                <span className="detail-label">ID</span>
                <span className="detail-value" style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
                  {result.id}
                </span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Task ID</span>
                <span className="detail-value" style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
                  {result.task_id}
                </span>
              </div>
              <div className="detail-row">
                <span className="detail-label">URL</span>
                <span className="detail-value">{result.url}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Method</span>
                <span className="detail-value">{result.extraction_method}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Items</span>
                <span className="detail-value">{result.item_count}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Confidence</span>
                <span className="detail-value">{(result.confidence * 100).toFixed(1)}%</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Normalized</span>
                <span className="detail-value">{result.normalization_applied ? "Yes" : "No"}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Deduplicated</span>
                <span className="detail-value">{result.dedup_applied ? "Yes" : "No"}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Created</span>
                <span className="detail-value">{formatDate(result.created_at)}</span>
              </div>
            </div>

            {/* Data preview card */}
            <div className="card">
              <div className="card-header">
                <h3>Extracted Data ({result.extracted_data.length} records)</h3>
              </div>
              {result.extracted_data.length === 0 ? (
                <div className="empty-state">
                  <p>No extracted data in this result.</p>
                </div>
              ) : (
                <pre
                  style={{
                    background: "var(--color-bg)",
                    borderRadius: "var(--radius-md)",
                    padding: 16,
                    fontSize: 13,
                    fontFamily: "var(--font-mono)",
                    overflow: "auto",
                    maxHeight: 480,
                    lineHeight: 1.5,
                  }}
                >
                  {JSON.stringify(result.extracted_data, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
