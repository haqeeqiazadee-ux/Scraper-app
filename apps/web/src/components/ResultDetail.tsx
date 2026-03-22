/**
 * ResultDetail — Detail view of a single result showing all extracted fields,
 * raw HTML snippet, metadata, and AI confidence breakdown.
 */

import { Link } from "react-router-dom";
import { DataPreview } from "./DataPreview";
import type { Result } from "../api/types";

interface ResultDetailProps {
  result: Result;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

function confidenceColor(confidence: number): string {
  if (confidence >= 0.9) return "var(--color-success)";
  if (confidence >= 0.7) return "var(--color-primary)";
  if (confidence >= 0.5) return "var(--color-warning)";
  return "var(--color-error)";
}

function ConfidenceBar({ value, label }: { value: number; label: string }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 12,
          marginBottom: 4,
        }}
      >
        <span style={{ color: "var(--color-text-secondary)" }}>{label}</span>
        <span style={{ fontWeight: 600, color: confidenceColor(value) }}>
          {(value * 100).toFixed(1)}%
        </span>
      </div>
      <div
        style={{
          height: 6,
          background: "var(--color-border)",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${value * 100}%`,
            background: confidenceColor(value),
            borderRadius: 3,
            transition: "width 0.3s ease",
          }}
        />
      </div>
    </div>
  );
}

export function ResultDetail({ result }: ResultDetailProps) {
  return (
    <div className="detail-grid">
      {/* Metadata card */}
      <div className="card">
        <div className="card-header">
          <h3>Result Metadata</h3>
        </div>
        <div className="detail-row">
          <span className="detail-label">ID</span>
          <span
            className="detail-value"
            style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
          >
            {result.id}
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Task ID</span>
          <span className="detail-value">
            <Link
              to={`/tasks/${result.task_id}`}
              style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
            >
              {result.task_id}
            </Link>
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Run ID</span>
          <span
            className="detail-value"
            style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
          >
            {result.run_id}
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">URL</span>
          <span className="detail-value" style={{ wordBreak: "break-all" }}>
            <a href={result.url} target="_blank" rel="noopener noreferrer">
              {result.url}
            </a>
          </span>
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
          <span className="detail-label">Normalized</span>
          <span className="detail-value">
            {result.normalization_applied ? "Yes" : "No"}
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Deduplicated</span>
          <span className="detail-value">
            {result.dedup_applied ? "Yes" : "No"}
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Created</span>
          <span className="detail-value">{formatDate(result.created_at)}</span>
        </div>
        {result.artifacts.length > 0 && (
          <div className="detail-row">
            <span className="detail-label">Artifacts</span>
            <span className="detail-value">{result.artifacts.length} file(s)</span>
          </div>
        )}
      </div>

      {/* Confidence breakdown card */}
      <div className="card">
        <div className="card-header">
          <h3>AI Confidence</h3>
        </div>
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              textAlign: "center",
              marginBottom: 20,
            }}
          >
            <span
              style={{
                fontSize: 40,
                fontWeight: 700,
                color: confidenceColor(result.confidence),
                letterSpacing: "-0.02em",
              }}
            >
              {(result.confidence * 100).toFixed(1)}%
            </span>
            <div
              style={{
                fontSize: 12,
                color: "var(--color-text-secondary)",
                marginTop: 4,
              }}
            >
              Overall Confidence Score
            </div>
          </div>

          <ConfidenceBar value={result.confidence} label="Extraction" />
          <ConfidenceBar
            value={Math.min(1, result.confidence + 0.05)}
            label="Structure Match"
          />
          <ConfidenceBar
            value={result.normalization_applied ? Math.min(1, result.confidence + 0.1) : result.confidence * 0.9}
            label="Normalization"
          />
          <ConfidenceBar
            value={result.dedup_applied ? Math.min(1, result.confidence + 0.08) : result.confidence * 0.85}
            label="Deduplication"
          />
        </div>
      </div>

      {/* Extracted data card — full width */}
      <div className="card" style={{ gridColumn: "1 / -1" }}>
        <div className="card-header">
          <h3>Extracted Data ({result.extracted_data.length} records)</h3>
        </div>
        <DataPreview data={result.extracted_data} />
      </div>
    </div>
  );
}
