import { useEffect, useRef, useState } from "react";
import { useTauri } from "../hooks/useTauri";

type LogLevel = "all" | "debug" | "info" | "warning" | "error";

const LOG_LEVEL_COLORS: Record<string, string> = {
  DEBUG: "#9ca3af",
  INFO: "#3b82f6",
  WARNING: "#f59e0b",
  WARN: "#f59e0b",
  ERROR: "#ef4444",
  CRITICAL: "#dc2626",
};

/**
 * Real-time log viewer showing server logs.
 * Features: auto-scroll, level filtering, line count configuration.
 */
export function LogViewer() {
  const { invoke } = useTauri();
  const [logs, setLogs] = useState<string[]>([]);
  const [filter, setFilter] = useState<LogLevel>("all");
  const [autoScroll, setAutoScroll] = useState(true);
  const [lineCount, setLineCount] = useState(200);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchLogs = async () => {
    try {
      const lines = await invoke<string[]>("get_server_logs", { lines: lineCount });
      setLogs(lines);
      setError(null);
    } catch (err) {
      setError(String(err));
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 3000);
    return () => clearInterval(interval);
  }, [lineCount]);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter((line) => {
    if (filter === "all") return true;
    const upper = filter.toUpperCase();
    // Match lines containing the log level keyword
    return line.toUpperCase().includes(upper);
  });

  const getLineColor = (line: string): string => {
    const upper = line.toUpperCase();
    for (const [level, color] of Object.entries(LOG_LEVEL_COLORS)) {
      if (upper.includes(level)) return color;
    }
    return "#d1d5db"; // default gray
  };

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    // Disable auto-scroll if user scrolled up
    const atBottom = scrollHeight - scrollTop - clientHeight < 50;
    setAutoScroll(atBottom);
  };

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        <h3 style={styles.title}>Server Logs</h3>

        <div style={styles.controls}>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as LogLevel)}
            style={styles.select}
          >
            <option value="all">All levels</option>
            <option value="debug">Debug</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
          </select>

          <select
            value={lineCount}
            onChange={(e) => setLineCount(Number(e.target.value))}
            style={styles.select}
          >
            <option value={50}>50 lines</option>
            <option value={100}>100 lines</option>
            <option value={200}>200 lines</option>
            <option value={500}>500 lines</option>
          </select>

          <label style={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            <span>Auto-scroll</span>
          </label>

          <button onClick={fetchLogs} style={styles.refreshButton}>
            Refresh
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        onScroll={handleScroll}
        style={styles.logContainer}
      >
        {filteredLogs.length === 0 ? (
          <div style={styles.emptyState}>
            {logs.length === 0
              ? "No logs available. Start the server to see logs."
              : "No logs matching the selected filter."}
          </div>
        ) : (
          filteredLogs.map((line, idx) => (
            <div key={idx} style={{ ...styles.logLine, color: getLineColor(line) }}>
              <span style={styles.lineNumber}>{idx + 1}</span>
              <span style={styles.lineText}>{line}</span>
            </div>
          ))
        )}
      </div>

      <div style={styles.footer}>
        <span>
          {filteredLogs.length} / {logs.length} lines
        </span>
        {error && <span style={{ color: "#ef4444" }}>{error}</span>}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    minHeight: "300px",
  },
  toolbar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "0.75rem 1rem",
    borderBottom: "1px solid #e5e7eb",
    flexWrap: "wrap",
    gap: "0.5rem",
  },
  title: {
    fontSize: "1rem",
    fontWeight: 600,
    margin: 0,
  },
  controls: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    flexWrap: "wrap",
  },
  select: {
    padding: "0.3rem 0.5rem",
    borderRadius: "4px",
    border: "1px solid #d1d5db",
    fontSize: "0.8rem",
    background: "#fff",
  },
  checkboxLabel: {
    display: "flex",
    alignItems: "center",
    gap: "0.25rem",
    fontSize: "0.8rem",
    color: "#6b7280",
  },
  refreshButton: {
    padding: "0.3rem 0.6rem",
    borderRadius: "4px",
    border: "1px solid #d1d5db",
    background: "#f9fafb",
    fontSize: "0.8rem",
    cursor: "pointer",
  },
  logContainer: {
    flex: 1,
    overflowY: "auto",
    background: "#1e1e1e",
    padding: "0.5rem",
    fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
    fontSize: "0.75rem",
    lineHeight: 1.5,
  },
  emptyState: {
    color: "#6b7280",
    padding: "2rem",
    textAlign: "center" as const,
    fontFamily: "system-ui, sans-serif",
    fontSize: "0.875rem",
  },
  logLine: {
    display: "flex",
    gap: "0.75rem",
    padding: "1px 0.25rem",
    borderRadius: "2px",
    whiteSpace: "pre-wrap" as const,
    wordBreak: "break-all" as const,
  },
  lineNumber: {
    color: "#4b5563",
    minWidth: "2.5rem",
    textAlign: "right" as const,
    userSelect: "none" as const,
    flexShrink: 0,
  },
  lineText: {
    flex: 1,
  },
  footer: {
    display: "flex",
    justifyContent: "space-between",
    padding: "0.5rem 1rem",
    borderTop: "1px solid #e5e7eb",
    fontSize: "0.75rem",
    color: "#9ca3af",
  },
};

export default LogViewer;
