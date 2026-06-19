import { useState, useCallback } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useAuthContext } from "../contexts/AuthContext";
import { SidebarNav } from "./SidebarNav";
import { TopBar } from "./TopBar";

export function Layout() {
  const { user, logout } = useAuthContext();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleMenuToggle = useCallback(() => {
    setSidebarOpen((prev) => !prev);
  }, []);

  const handleNavClick = useCallback(() => {
    setSidebarOpen(false);
  }, []);

  return (
    <div className="app-layout">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside className={`sidebar ${sidebarOpen ? "sidebar--open" : ""}`}>
        <div className="sidebar-header">
          <div
            style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}
            onClick={() => { navigate("/dashboard"); handleNavClick(); }}
            title="Dashboard"
          >
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: "linear-gradient(135deg, #2563eb, #3b82f6)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 14, color: "#fff", fontWeight: 700,
            }}>S</div>
            <div className="sidebar-brand-text">
              <h1 style={{ fontSize: 14, fontWeight: 700, margin: 0, lineHeight: 1.2 }}>Scraper</h1>
              <span style={{ fontSize: 9, color: "rgba(255,255,255,0.35)", letterSpacing: "0.1em", textTransform: "uppercase" }}>Platform</span>
            </div>
          </div>
        </div>
        <div onClick={handleNavClick}>
          <SidebarNav />
        </div>
        {user && (
          <div style={{
            marginTop: "auto", padding: "10px 14px",
            borderTop: "1px solid rgba(255,255,255,0.06)", fontSize: 12,
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "rgba(255,255,255,0.7)" }} title={user.sub}>{user.sub}</div>
                <div style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>{user.tenant_id}</div>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={logout} title="Sign out" style={{ flexShrink: 0, color: "rgba(255,255,255,0.5)", fontSize: 11 }}>Sign out</button>
            </div>
          </div>
        )}
      </aside>
      <div className="main-wrapper">
        <TopBar onMenuToggle={handleMenuToggle} />
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
