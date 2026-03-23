import { NavLink, Outlet } from "react-router-dom";
import { useAuthContext } from "../contexts/AuthContext";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "\u25A3" },
  { to: "/tasks", label: "Tasks", icon: "\u25B6" },
  { to: "/policies", label: "Policies", icon: "\u2630" },
  { to: "/results", label: "Results", icon: "\u25C9" },
];

export function Layout() {
  const { user, logout } = useAuthContext();

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>Scraping Platform</h1>
          <span>AI-Powered</span>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        {user && (
          <div
            style={{
              marginTop: "auto",
              padding: "12px 16px",
              borderTop: "1px solid var(--color-border)",
              fontSize: 13,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 8,
              }}
            >
              <div style={{ minWidth: 0 }}>
                <div
                  style={{
                    fontWeight: 600,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                  title={user.sub}
                >
                  {user.sub}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: "var(--color-text-secondary)",
                  }}
                >
                  {user.tenant_id}
                </div>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={logout}
                title="Sign out"
                style={{ flexShrink: 0 }}
              >
                Logout
              </button>
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
