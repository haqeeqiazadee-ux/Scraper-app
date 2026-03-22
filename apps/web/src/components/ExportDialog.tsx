/**
 * ExportDialog — Modal dialog for exporting results.
 * Options: format (JSON, CSV, Excel), filters (date range, min confidence),
 * destination (download, S3, webhook). Has a preview count and download button.
 */

import { useState, useEffect, useCallback } from "react";
import { useExportResults, useExportCount } from "../hooks/useResults";

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
}

type ExportFormat = "json" | "csv" | "xlsx";
type Destination = "download" | "s3" | "webhook";

const FORMAT_OPTIONS: { value: ExportFormat; label: string }[] = [
  { value: "json", label: "JSON" },
  { value: "csv", label: "CSV" },
  { value: "xlsx", label: "Excel (.xlsx)" },
];

const DESTINATION_OPTIONS: { value: Destination; label: string; description: string }[] = [
  { value: "download", label: "Download", description: "Download file to your browser" },
  { value: "s3", label: "S3 Bucket", description: "Export to S3-compatible storage" },
  { value: "webhook", label: "Webhook", description: "Send data to a webhook URL" },
];

export function ExportDialog({ open, onClose }: ExportDialogProps) {
  const [format, setFormat] = useState<ExportFormat>("json");
  const [destination, setDestination] = useState<Destination>("download");
  const [minConfidence, setMinConfidence] = useState<number>(0);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [s3Path, setS3Path] = useState("");
  const [exportError, setExportError] = useState<string | null>(null);

  const { data: countData } = useExportCount({
    min_confidence: minConfidence > 0 ? minConfidence : undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  });

  const exportMutation = useExportResults();

  const previewCount = countData?.count ?? 0;

  // Close on escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleKeyDown);
      return () => document.removeEventListener("keydown", handleKeyDown);
    }
  }, [open, handleKeyDown]);

  if (!open) return null;

  function handleExport() {
    setExportError(null);
    exportMutation.mutate(
      {
        format,
        destination,
        min_confidence: minConfidence > 0 ? minConfidence : undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        webhook_url: destination === "webhook" ? webhookUrl : undefined,
        s3_path: destination === "s3" ? s3Path : undefined,
      },
      {
        onSuccess: (data) => {
          if (data instanceof Blob) {
            // Trigger browser download
            const url = URL.createObjectURL(data);
            const a = document.createElement("a");
            a.href = url;
            a.download = `results-export.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            onClose();
          } else {
            onClose();
          }
        },
        onError: (err) => {
          setExportError(err instanceof Error ? err.message : "Export failed");
        },
      },
    );
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "absolute",
          inset: 0,
          background: "rgba(0, 0, 0, 0.4)",
        }}
      />

      {/* Dialog */}
      <div
        className="card"
        style={{
          position: "relative",
          width: "100%",
          maxWidth: 520,
          maxHeight: "90vh",
          overflow: "auto",
          margin: 16,
          boxShadow: "var(--shadow-md)",
        }}
      >
        <div className="card-header">
          <h3>Export Results</h3>
          <button
            className="btn btn-secondary btn-sm"
            onClick={onClose}
            style={{ padding: "4px 8px" }}
          >
            X
          </button>
        </div>

        {/* Format selection */}
        <div style={{ marginBottom: 16 }}>
          <label
            style={{
              display: "block",
              fontSize: 12,
              fontWeight: 600,
              color: "var(--color-text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: 6,
            }}
          >
            Format
          </label>
          <div style={{ display: "flex", gap: 4 }}>
            {FORMAT_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                className={`btn btn-sm ${format === opt.value ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setFormat(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Destination selection */}
        <div style={{ marginBottom: 16 }}>
          <label
            style={{
              display: "block",
              fontSize: 12,
              fontWeight: 600,
              color: "var(--color-text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: 6,
            }}
          >
            Destination
          </label>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {DESTINATION_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "8px 12px",
                  border: `1px solid ${destination === opt.value ? "var(--color-primary)" : "var(--color-border)"}`,
                  borderRadius: "var(--radius-md)",
                  cursor: "pointer",
                  background:
                    destination === opt.value ? "rgba(37, 99, 235, 0.04)" : "transparent",
                }}
              >
                <input
                  type="radio"
                  name="destination"
                  value={opt.value}
                  checked={destination === opt.value}
                  onChange={() => setDestination(opt.value)}
                />
                <div>
                  <div style={{ fontSize: 14, fontWeight: 500 }}>{opt.label}</div>
                  <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                    {opt.description}
                  </div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Conditional destination fields */}
        {destination === "s3" && (
          <div style={{ marginBottom: 16 }}>
            <label
              style={{
                display: "block",
                fontSize: 12,
                fontWeight: 600,
                color: "var(--color-text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: 6,
              }}
            >
              S3 Path
            </label>
            <input
              type="text"
              value={s3Path}
              onChange={(e) => setS3Path(e.target.value)}
              placeholder="s3://bucket/path/results"
              style={{
                width: "100%",
                padding: "8px 12px",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                fontSize: 14,
                fontFamily: "var(--font-mono)",
              }}
            />
          </div>
        )}

        {destination === "webhook" && (
          <div style={{ marginBottom: 16 }}>
            <label
              style={{
                display: "block",
                fontSize: 12,
                fontWeight: 600,
                color: "var(--color-text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: 6,
              }}
            >
              Webhook URL
            </label>
            <input
              type="url"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://example.com/webhook"
              style={{
                width: "100%",
                padding: "8px 12px",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                fontSize: 14,
                fontFamily: "var(--font-mono)",
              }}
            />
          </div>
        )}

        {/* Filters */}
        <div
          style={{
            marginBottom: 16,
            padding: 12,
            background: "var(--color-bg)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <label
            style={{
              display: "block",
              fontSize: 12,
              fontWeight: 600,
              color: "var(--color-text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: 10,
            }}
          >
            Filters
          </label>

          {/* Confidence threshold */}
          <div style={{ marginBottom: 10 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 13,
                marginBottom: 4,
              }}
            >
              <span>Min confidence</span>
              <span style={{ fontWeight: 600 }}>{(minConfidence * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
              style={{ width: "100%" }}
            />
          </div>

          {/* Date range */}
          <div style={{ display: "flex", gap: 8 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, marginBottom: 4 }}>From</div>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                style={{
                  width: "100%",
                  padding: "6px 8px",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: 13,
                }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, marginBottom: 4 }}>To</div>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                style={{
                  width: "100%",
                  padding: "6px 8px",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: 13,
                }}
              />
            </div>
          </div>
        </div>

        {/* Preview count */}
        <div
          style={{
            padding: "10px 12px",
            background: "#f0f9ff",
            borderRadius: "var(--radius-md)",
            fontSize: 13,
            color: "var(--color-primary)",
            fontWeight: 500,
            marginBottom: 16,
            textAlign: "center",
          }}
        >
          {previewCount} result{previewCount !== 1 ? "s" : ""} match your filters
        </div>

        {/* Error message */}
        {exportError && (
          <div
            style={{
              padding: "10px 12px",
              background: "#fee2e2",
              borderRadius: "var(--radius-md)",
              fontSize: 13,
              color: "var(--color-error)",
              fontWeight: 500,
              marginBottom: 16,
            }}
          >
            {exportError}
          </div>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleExport}
            disabled={exportMutation.isPending || previewCount === 0}
          >
            {exportMutation.isPending
              ? "Exporting..."
              : destination === "download"
                ? "Download"
                : "Export"}
          </button>
        </div>
      </div>
    </div>
  );
}
