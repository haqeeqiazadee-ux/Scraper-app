import { useState } from "react";
import { useTauri } from "./hooks/useTauri";
import { ServerStatus } from "./components/ServerStatus";
import { Settings } from "./components/Settings";
import { LogViewer } from "./components/LogViewer";

type Tab = "dashboard" | "logs" | "settings";

/**
 * Desktop App — wraps the shared web dashboard with Tauri-specific
 * functionality: local server management, status indicators, settings,
 * and log viewing.
 */
function App() {
  const { invoke } = useTauri();
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");
  const [version, setVersion] = useState<string | null>(null);

  // Load version once
  if (version === null) {
    invoke<string>("get_version")
      .then(setVersion)
      .catch(() => setVersion("0.1.0"));
  }

  return (
    <div style={styles.app}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.appTitle}>AI Scraper Desktop</h1>
          <span style={styles.versionBadge}>v{version ?? "..."}</span>
        </div>
        <nav style={styles.nav}>
          {(["dashboard", "logs", "settings"] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                ...styles.navButton,
                ...(activeTab === tab ? styles.navButtonActive : {}),
              }}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>
      </header>

      {/* Content */}
      <main style={styles.main}>
        {activeTab === "dashboard" && <DashboardTab />}
        {activeTab === "logs" && <LogsTab />}
        {activeTab === "settings" && <SettingsTab />}
      </main>

      {/* Footer */}
      <footer style={styles.footer}>
        AI Scraper Desktop v{version ?? "0.1.0"} — Local scraping platform with embedded control plane
      </footer>
    </div>
  );
}

/** Dashboard tab: server status + placeholder for future dashboard integration. */
function DashboardTab() {
  return (
    <div style={styles.tabContent}>
      <div style={{ maxWidth: "700px" }}>
        <ServerStatus />
      </div>

      <section style={styles.dashboardSection}>
        <h2 style={styles.sectionTitle}>Dashboard</h2>
        <p style={styles.sectionDescription}>
          The full scraping dashboard will be available here once the local server is running.
          Dashboard components are shared with the web application.
        </p>
      </section>
    </div>
  );
}

/** Logs tab: real-time server log viewer. */
function LogsTab() {
  return (
    <div style={{ ...styles.tabContent, height: "calc(100vh - 140px)" }}>
      <LogViewer />
    </div>
  );
}

/** Settings tab: application configuration. */
function SettingsTab() {
  return (
    <div style={styles.tabContent}>
      <Settings />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    fontFamily: "system-ui, -apple-system, sans-serif",
    display: "flex",
    flexDirection: "column",
    minHeight: "100vh",
    background: "#fff",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "0.75rem 1.5rem",
    borderBottom: "1px solid #e5e7eb",
    background: "#fafafa",
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: "0.75rem",
  },
  appTitle: {
    fontSize: "1.125rem",
    fontWeight: 600,
    margin: 0,
  },
  versionBadge: {
    fontSize: "0.7rem",
    padding: "0.15rem 0.4rem",
    borderRadius: "4px",
    background: "#e5e7eb",
    color: "#6b7280",
    fontFamily: "monospace",
  },
  nav: {
    display: "flex",
    gap: "0.25rem",
  },
  navButton: {
    padding: "0.4rem 0.9rem",
    borderRadius: "6px",
    border: "1px solid transparent",
    background: "transparent",
    color: "#6b7280",
    fontSize: "0.85rem",
    fontWeight: 500,
    cursor: "pointer",
    transition: "all 0.15s",
  },
  navButtonActive: {
    background: "#2563eb",
    color: "#fff",
    border: "1px solid #2563eb",
  },
  main: {
    flex: 1,
    overflow: "auto",
  },
  tabContent: {
    padding: "1.5rem",
    display: "flex",
    flexDirection: "column",
    gap: "1.5rem",
  },
  dashboardSection: {
    background: "#f8f9fa",
    borderRadius: "8px",
    padding: "1.5rem",
  },
  sectionTitle: {
    fontSize: "1.125rem",
    fontWeight: 600,
    marginBottom: "0.75rem",
  },
  sectionDescription: {
    color: "#6b7280",
    fontSize: "0.875rem",
    lineHeight: 1.6,
    margin: 0,
  },
  footer: {
    padding: "0.5rem 1.5rem",
    borderTop: "1px solid #e5e7eb",
    fontSize: "0.7rem",
    color: "#9ca3af",
    textAlign: "center",
  },
};

export default App;
