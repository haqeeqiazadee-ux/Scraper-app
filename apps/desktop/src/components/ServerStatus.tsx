import { useEffect, useState } from "react";
import { useTauri } from "../hooks/useTauri";

type ServerStatusData = {
  running: boolean;
  pid: number | null;
  port: number;
  mode: string;
  uptime_secs: number | null;
  restart_count: number;
  health_ok: boolean;
};

/**
 * Server status widget showing running/stopped indicator, uptime,
 * health status, and restart count. Auto-refreshes every 5 seconds.
 */
export function ServerStatus() {
  const { invoke } = useTauri();
  const [status, setStatus] = useState<ServerStatusData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState(false);

  const refreshStatus = async () => {
    try {
      const s = await invoke<ServerStatusData>("get_server_status");
      setStatus(s);
      setError(null);
    } catch (err) {
      setError(String(err));
    }
  };

  useEffect(() => {
    refreshStatus();
    const interval = setInterval(refreshStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    setActionInProgress(true);
    setError(null);
    try {
      const s = await invoke<ServerStatusData>("start_local_server");
      setStatus(s);
    } catch (err) {
      setError(String(err));
    } finally {
      setActionInProgress(false);
    }
  };

  const handleStop = async () => {
    setActionInProgress(true);
    setError(null);
    try {
      const s = await invoke<ServerStatusData>("stop_local_server");
      setStatus(s);
    } catch (err) {
      setError(String(err));
    } finally {
      setActionInProgress(false);
    }
  };

  const handleRestart = async () => {
    setActionInProgress(true);
    setError(null);
    try {
      const s = await invoke<ServerStatusData>("restart_server");
      setStatus(s);
    } catch (err) {
      setError(String(err));
    } finally {
      setActionInProgress(false);
    }
  };

  const formatUptime = (secs: number): string => {
    if (secs < 60) return `${secs}s`;
    if (secs < 3600) return `${Math.floor(secs / 60)}m ${secs % 60}s`;
    const hours = Math.floor(secs / 3600);
    const mins = Math.floor((secs % 3600) / 60);
    return `${hours}h ${mins}m`;
  };

  const isRunning = status?.running ?? false;
  const isHealthy = status?.health_ok ?? false;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>Server Status</h3>
        <div style={styles.statusBadge}>
          <span
            style={{
              ...styles.statusDot,
              background: isRunning ? (isHealthy ? "#22c55e" : "#f59e0b") : "#ef4444",
            }}
          />
          <span style={styles.statusText}>
            {isRunning ? (isHealthy ? "Running" : "Starting...") : "Stopped"}
          </span>
        </div>
      </div>

      {/* Status details */}
      {status && (
        <div style={styles.details}>
          <div style={styles.detailRow}>
            <span style={styles.detailLabel}>Port</span>
            <span style={styles.detailValue}>{status.port}</span>
          </div>
          {status.pid && (
            <div style={styles.detailRow}>
              <span style={styles.detailLabel}>PID</span>
              <span style={styles.detailValue}>{status.pid}</span>
            </div>
          )}
          {status.uptime_secs !== null && status.uptime_secs > 0 && (
            <div style={styles.detailRow}>
              <span style={styles.detailLabel}>Uptime</span>
              <span style={styles.detailValue}>{formatUptime(status.uptime_secs)}</span>
            </div>
          )}
          {status.restart_count > 0 && (
            <div style={styles.detailRow}>
              <span style={styles.detailLabel}>Restarts</span>
              <span style={{ ...styles.detailValue, color: "#f59e0b" }}>
                {status.restart_count}
              </span>
            </div>
          )}
          <div style={styles.detailRow}>
            <span style={styles.detailLabel}>Health</span>
            <span
              style={{
                ...styles.detailValue,
                color: isHealthy ? "#22c55e" : "#999",
              }}
            >
              {isRunning ? (isHealthy ? "OK" : "Checking...") : "--"}
            </span>
          </div>
          <div style={styles.detailRow}>
            <span style={styles.detailLabel}>Mode</span>
            <span style={styles.detailValue}>{status.mode}</span>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div style={styles.actions}>
        {!isRunning ? (
          <button
            onClick={handleStart}
            disabled={actionInProgress}
            style={{
              ...styles.startButton,
              opacity: actionInProgress ? 0.6 : 1,
            }}
          >
            {actionInProgress ? "Starting..." : "Start Server"}
          </button>
        ) : (
          <>
            <button
              onClick={handleRestart}
              disabled={actionInProgress}
              style={{
                ...styles.restartButton,
                opacity: actionInProgress ? 0.6 : 1,
              }}
            >
              {actionInProgress ? "Restarting..." : "Restart"}
            </button>
            <button
              onClick={handleStop}
              disabled={actionInProgress}
              style={{
                ...styles.stopButton,
                opacity: actionInProgress ? 0.6 : 1,
              }}
            >
              Stop
            </button>
          </>
        )}
      </div>

      {isRunning && isHealthy && (
        <div style={styles.apiLink}>
          API:{" "}
          <a
            href={`http://localhost:${status?.port}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "#2563eb" }}
          >
            http://localhost:{status?.port}/docs
          </a>
        </div>
      )}

      {error && <div style={styles.errorBanner}>{error}</div>}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: "#f8f9fa",
    borderRadius: "8px",
    padding: "1.25rem",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "1rem",
  },
  title: {
    fontSize: "1rem",
    fontWeight: 600,
    margin: 0,
  },
  statusBadge: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    padding: "0.25rem 0.75rem",
    borderRadius: "999px",
    background: "#fff",
    border: "1px solid #e5e7eb",
    fontSize: "0.8rem",
  },
  statusDot: {
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    display: "inline-block",
  },
  statusText: {
    fontWeight: 500,
  },
  details: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "0.5rem",
    marginBottom: "1rem",
    fontSize: "0.8rem",
  },
  detailRow: {
    display: "flex",
    justifyContent: "space-between",
    padding: "0.25rem 0.5rem",
    background: "#fff",
    borderRadius: "4px",
  },
  detailLabel: {
    color: "#6b7280",
  },
  detailValue: {
    fontWeight: 500,
    fontFamily: "monospace",
  },
  actions: {
    display: "flex",
    gap: "0.5rem",
  },
  startButton: {
    flex: 1,
    padding: "0.5rem 1rem",
    borderRadius: "6px",
    border: "none",
    background: "#2563eb",
    color: "#fff",
    fontWeight: 500,
    fontSize: "0.85rem",
    cursor: "pointer",
  },
  stopButton: {
    padding: "0.5rem 1rem",
    borderRadius: "6px",
    border: "none",
    background: "#dc2626",
    color: "#fff",
    fontWeight: 500,
    fontSize: "0.85rem",
    cursor: "pointer",
  },
  restartButton: {
    flex: 1,
    padding: "0.5rem 1rem",
    borderRadius: "6px",
    border: "1px solid #d1d5db",
    background: "#fff",
    color: "#374151",
    fontWeight: 500,
    fontSize: "0.85rem",
    cursor: "pointer",
  },
  apiLink: {
    marginTop: "0.75rem",
    fontSize: "0.8rem",
    color: "#6b7280",
  },
  errorBanner: {
    marginTop: "0.75rem",
    padding: "0.5rem 0.75rem",
    background: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: "6px",
    color: "#dc2626",
    fontSize: "0.8rem",
  },
};

export default ServerStatus;
