/**
 * DataPreview — JSON/table toggle view for previewing extracted data.
 * Shows structured data in a readable format with toggle between views.
 */

import { useState } from "react";

interface DataPreviewProps {
  data: Record<string, unknown>[];
}

type ViewMode = "table" | "json";

export function DataPreview({ data }: DataPreviewProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("table");

  if (data.length === 0) {
    return (
      <div className="empty-state">
        <p>No data to display.</p>
      </div>
    );
  }

  // Collect all unique keys across all records
  const allKeys = Array.from(
    data.reduce((keys, record) => {
      Object.keys(record).forEach((k) => keys.add(k));
      return keys;
    }, new Set<string>()),
  );

  return (
    <div>
      {/* Toggle buttons */}
      <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
        <button
          className={`btn btn-sm ${viewMode === "table" ? "btn-primary" : "btn-secondary"}`}
          onClick={() => setViewMode("table")}
        >
          Table
        </button>
        <button
          className={`btn btn-sm ${viewMode === "json" ? "btn-primary" : "btn-secondary"}`}
          onClick={() => setViewMode("json")}
        >
          JSON
        </button>
        <span
          style={{
            marginLeft: "auto",
            fontSize: 12,
            color: "var(--color-text-secondary)",
            alignSelf: "center",
          }}
        >
          {data.length} record{data.length !== 1 ? "s" : ""}
        </span>
      </div>

      {viewMode === "json" ? (
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
          {JSON.stringify(data, null, 2)}
        </pre>
      ) : (
        <div className="table-container" style={{ maxHeight: 480, overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ width: 40 }}>#</th>
                {allKeys.map((key) => (
                  <th key={key}>{key}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((record, idx) => (
                <tr key={idx}>
                  <td style={{ color: "var(--color-text-secondary)", fontSize: 12 }}>
                    {idx + 1}
                  </td>
                  {allKeys.map((key) => (
                    <td key={key} style={{ maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis" }}>
                      {formatCellValue(record[key])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) return "--";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
