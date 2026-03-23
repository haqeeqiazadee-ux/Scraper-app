import { Outlet } from "react-router-dom";
import { useAuthContext } from "../contexts/AuthContext";
import { SidebarNav } from "./SidebarNav";

export function Layout() {
  const { user, logout } = useAuthContext();

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, color: "#fff", fontWeight: 700,
            }}>S</div>
            <div>
              <h1 style={{ fontSize: 15, fontWeight: 700, margin: 0, lineHeight: 1.2 }}>Scraper</h1>
              <span style={{ fontSize: 10, color: "var(--color-text-secondary)", letterSpacing: "0.05em", textTransform: "uppercase" }}>AI Platform</span>
            </div>
          </div>
        </div>
        <SidebarNav />
        {user && (
          <div style={{
            marginTop: "auto", padding: "12px 16px",
            borderTop: "1px solid var(--color-border)", fontSize: 13,
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={user.sub}>{user.sub}</div>
                <div style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>{user.tenant_id}</div>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={logout} title="Sign out" style={{ flexShrink: 0 }}>Logout</button>
            </div>
          </div>
        )}
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
