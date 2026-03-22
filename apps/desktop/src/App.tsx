import { useEffect, useState } from "react";
import { useTauri } from "./hooks/useTauri";

type ServerStatus = {
  running: boolean;
  pid: number | null;
  port: number;
  mode: string;
};

/**
 * Desktop App — wraps the shared web dashboard with Tauri-specific
 * functionality: local server management, status indicators, and
 * desktop-only controls.
 *
 * In future phases (EXE-002, EXE-003), this will import and render
 * the shared dashboard routes from @scraper-platform/web.
 */
function App() {
  const { invoke } = useTauri();
  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const refreshStatus = async () => {
    try {
      const s = await invoke<ServerStatus>("get_status");
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
    setStarting(true);
    setError(null);
    try {
      const s = await invoke<ServerStatus>("start_local_server");
      setStatus(s);
    } catch (err) {
      setError(String(err));
    } finally {
      setStarting(false);
    }
  };

  const handleStop = async () => {
    setError(null);
    try {
      const s = await invoke<ServerStatus>("stop_local_server");
      setStatus(s);
    } catch (err) {
      setError(String(err));
    }
  };

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: "2rem", maxWidth: "800px", margin: "0 auto" }}>
      <header style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 600 }}>AI Scraper Desktop</h1>
        <p style={{ color: "#666", fontSize: "0.875rem" }}>
          Local scraping platform — embedded control plane with SQLite storage
        </p>
      </header>

      <section style={{ background: "#f8f9fa", borderRadius: "8px", padding: "1.5rem", marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.125rem", marginBottom: "1rem" }}>Local Server</h2>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
          <span
            style={{
              width: "12px",
              height: "12px",
              borderRadius: "50%",
              background: status?.running ? "#22c55e" : "#ef4444",
              display: "inline-block",
            }}
          />
          <span>{status?.running ? `Running on port ${status.port}` : "Stopped"}</span>
          {status?.pid && <span style={{ color: "#999", fontSize: "0.75rem" }}>PID: {status.pid}</span>}
        </div>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            onClick={handleStart}
            disabled={status?.running || starting}
            style={{
              padding: "0.5rem 1rem",
              borderRadius: "6px",
              border: "1px solid #ccc",
              background: status?.running ? "#e5e7eb" : "#2563eb",
              color: status?.running ? "#999" : "#fff",
              cursor: status?.running ? "not-allowed" : "pointer",
            }}
          >
            {starting ? "Starting..." : "Start Server"}
          </button>

          <button
            onClick={handleStop}
            disabled={!status?.running}
            style={{
              padding: "0.5rem 1rem",
              borderRadius: "6px",
              border: "1px solid #ccc",
              background: !status?.running ? "#e5e7eb" : "#dc2626",
              color: !status?.running ? "#999" : "#fff",
              cursor: !status?.running ? "not-allowed" : "pointer",
            }}
          >
            Stop Server
          </button>
        </div>

        {error && (
          <div style={{ marginTop: "1rem", padding: "0.75rem", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "6px", color: "#dc2626", fontSize: "0.875rem" }}>
            {error}
          </div>
        )}
      </section>

      <section style={{ background: "#f8f9fa", borderRadius: "8px", padding: "1.5rem" }}>
        <h2 style={{ fontSize: "1.125rem", marginBottom: "1rem" }}>Dashboard</h2>
        <p style={{ color: "#666", fontSize: "0.875rem" }}>
          The full scraping dashboard will be available here once the local server is running.
          Dashboard components are shared with the web application.
        </p>
        {status?.running && (
          <p style={{ marginTop: "0.75rem", fontSize: "0.875rem" }}>
            API available at{" "}
            <a
              href={`http://localhost:${status.port}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "#2563eb" }}
            >
              http://localhost:{status.port}/docs
            </a>
          </p>
        )}
      </section>

      <footer style={{ marginTop: "2rem", fontSize: "0.75rem", color: "#999", textAlign: "center" }}>
        AI Scraper Desktop v0.1.0 — Mode: {status?.mode ?? "desktop"}
      </footer>
    </div>
  );
}

export default App;
