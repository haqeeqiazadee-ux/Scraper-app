/**
 * TopBar — Compact header bar for the main content area.
 * Contains search trigger, environment badge, and account actions.
 */

import { useAuthContext } from "../contexts/AuthContext";
import { useQuery } from "@tanstack/react-query";
import { health } from "../api/client";

interface TopBarProps {
  onMenuToggle: () => void;
}

export function TopBar({ onMenuToggle }: TopBarProps) {
  const { user } = useAuthContext();

  const { data: healthData } = useQuery({
    queryKey: ["health"],
    queryFn: () => health.check(),
    refetchInterval: 30_000,
  });

  const isHealthy = healthData?.status === "healthy";

  return (
    <header className="topbar">
      {/* Mobile hamburger */}
      <button
        className="topbar-menu-btn"
        onClick={onMenuToggle}
        aria-label="Toggle navigation"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
          <line x1="3" y1="5" x2="17" y2="5" />
          <line x1="3" y1="10" x2="17" y2="10" />
          <line x1="3" y1="15" x2="17" y2="15" />
        </svg>
      </button>

      {/* Search trigger */}
      <button
        className="topbar-search"
        onClick={() => {
          document.dispatchEvent(
            new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true })
          );
        }}
        aria-label="Search"
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="6.5" cy="6.5" r="4.5" />
          <line x1="10.5" y1="10.5" x2="14" y2="14" />
        </svg>
        <span className="topbar-search-text">Search tasks, results...</span>
        <kbd className="topbar-kbd">Ctrl+K</kbd>
      </button>

      <div className="topbar-right">
        {/* Environment badge */}
        <div className={`topbar-env ${isHealthy ? "topbar-env--ok" : "topbar-env--warn"}`}>
          <span className={`topbar-env-dot ${isHealthy ? "topbar-env-dot--ok" : "topbar-env-dot--warn"}`} />
          <span className="topbar-env-label">
            {isHealthy ? "Production" : "Connecting..."}
          </span>
        </div>

        {/* Account */}
        {user && (
          <div className="topbar-account">
            <div className="topbar-avatar">
              {(user.sub ?? "U").charAt(0).toUpperCase()}
            </div>
            <span className="topbar-account-name">{user.sub}</span>
          </div>
        )}
      </div>
    </header>
  );
}
