import { NavLink, Outlet } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "\u25A3" },
  { to: "/tasks", label: "Tasks", icon: "\u25B6" },
  { to: "/policies", label: "Policies", icon: "\u2630" },
  { to: "/results", label: "Results", icon: "\u25C9" },
];

export function Layout() {
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
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
