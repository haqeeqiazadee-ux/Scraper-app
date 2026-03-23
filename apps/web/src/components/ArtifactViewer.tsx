/**
 * ArtifactViewer — Card list of result artifacts.
 * Shows type icon, filename, formatted size, timestamp, and download button.
 */

interface ArtifactItem {
  key: string;
  content_type: string;
  size_bytes: number;
  page?: number;
  url?: string;
  captured_at?: string;
}

interface ArtifactViewerProps {
  artifacts: ArtifactItem[];
}

function formatSize(bytes: number): string {
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  if (bytes >= 1_024) return `${(bytes / 1_024).toFixed(1)} KB`;
  return `${bytes} B`;
}

function formatDate(iso?: string): string {
  if (!iso) return "--";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function filenameFromKey(key: string): string {
  return key.split("/").pop() ?? key;
}

function TypeIcon({ contentType }: { contentType: string }) {
  const ct = contentType.toLowerCase();
  if (ct.includes("html")) {
    return (
      <span
        style={{
          fontSize: 18,
          color: "#f59e0b",
          fontFamily: "var(--font-mono)",
          lineHeight: 1,
        }}
        title="HTML snapshot"
      >
        {"</>"}
      </span>
    );
  }
  if (ct.includes("png") || ct.includes("image")) {
    return (
      <span style={{ fontSize: 18, lineHeight: 1 }} title="Screenshot">
        🖼
      </span>
    );
  }
  if (ct.includes("json")) {
    return (
      <span
        style={{ fontSize: 18, color: "#2563eb", lineHeight: 1 }}
        title="JSON export"
      >
        &#123;&#125;
      </span>
    );
  }
  if (ct.includes("csv")) {
    return (
      <span
        style={{ fontSize: 15, color: "#059669", fontWeight: 700, lineHeight: 1 }}
        title="CSV export"
      >
        CSV
      </span>
    );
  }
  if (ct.includes("xlsx") || ct.includes("spreadsheet")) {
    return (
      <span
        style={{ fontSize: 15, color: "#16a34a", fontWeight: 700, lineHeight: 1 }}
        title="Excel export"
      >
        XLS
      </span>
    );
  }
  return <span style={{ fontSize: 16, lineHeight: 1 }}>📄</span>;
}

export function ArtifactViewer({ artifacts }: ArtifactViewerProps) {
  if (artifacts.length === 0) {
    return (
      <div className="empty-state" style={{ padding: "24px" }}>
        <p>No artifacts for this result.</p>
      </div>
    );
  }

  function handleDownload(artifact: ArtifactItem) {
    if (artifact.url) {
      const a = document.createElement("a");
      a.href = artifact.url;
      a.download = filenameFromKey(artifact.key);
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {artifacts.map((artifact) => {
        const filename = filenameFromKey(artifact.key);
        return (
          <div
            key={artifact.key}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "10px 14px",
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              boxShadow: "var(--shadow-sm)",
              transition: "border-color 0.15s",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.borderColor = "var(--color-primary)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.borderColor = "var(--color-border)")
            }
          >
            {/* Icon */}
            <div
              style={{
                width: 36,
                height: 36,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "var(--color-bg)",
                borderRadius: "var(--radius-sm)",
                flexShrink: 0,
                border: "1px solid var(--color-border)",
              }}
            >
              <TypeIcon contentType={artifact.content_type} />
            </div>

            {/* Details */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: "var(--color-text)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  fontFamily: "var(--font-mono)",
                }}
                title={artifact.key}
              >
                {filename}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: "var(--color-text-secondary)",
                  marginTop: 2,
                  display: "flex",
                  gap: 10,
                  flexWrap: "wrap",
                }}
              >
                <span>{formatSize(artifact.size_bytes)}</span>
                {artifact.page != null && <span>Page {artifact.page}</span>}
                <span>{formatDate(artifact.captured_at)}</span>
              </div>
            </div>

            {/* Download button */}
            {artifact.url && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handleDownload(artifact)}
                title="Download artifact"
                style={{ flexShrink: 0 }}
              >
                ↓ Download
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
