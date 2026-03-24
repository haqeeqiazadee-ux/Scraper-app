/**
 * SidebarNav — Grouped navigation sidebar with section labels.
 * Groups: CORE, TOOLS, MONITORING, ACCOUNT.
 * Active item has left border accent + background highlight.
 */

import { NavLink, useLocation } from "react-router-dom";
import { GlobalSearch } from "./GlobalSearch";

/* ── SVG Icon components ── */

function IconGrid() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="1" width="6" height="6" rx="1" />
      <rect x="9" y="1" width="6" height="6" rx="1" />
      <rect x="1" y="9" width="6" height="6" rx="1" />
      <rect x="9" y="9" width="6" height="6" rx="1" />
    </svg>
  );
}

function IconList() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
      <line x1="2" y1="4" x2="14" y2="4" />
      <line x1="2" y1="8" x2="14" y2="8" />
      <line x1="2" y1="12" x2="14" y2="12" />
    </svg>
  );
}

function IconShield() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 1.5L2 4v4c0 3.3 2.5 5.7 6 6.5 3.5-.8 6-3.2 6-6.5V4L8 1.5z" />
    </svg>
  );
}

function IconDatabase() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="8" cy="4" rx="6" ry="2" />
      <path d="M2 4v3c0 1.1 2.7 2 6 2s6-.9 6-2V4" />
      <path d="M2 7v3c0 1.1 2.7 2 6 2s6-.9 6-2V7" />
    </svg>
  );
}

function IconCompass() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="6.5" />
      <polygon points="10.5,5.5 6.5,8 5.5,10.5 9.5,8" fill="currentColor" stroke="none" />
    </svg>
  );
}

function IconClock() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="6.5" />
      <polyline points="8,4.5 8,8 10.5,10" />
    </svg>
  );
}

function IconActivity() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="1,8 4,4 6,11 9,5 11,9 15,8" />
    </svg>
  );
}

function IconGlobe() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="6.5" />
      <line x1="1.5" y1="8" x2="14.5" y2="8" />
      <path d="M8 1.5a9.5 9.5 0 0 1 0 13" />
      <path d="M8 1.5a9.5 9.5 0 0 0 0 13" />
    </svg>
  );
}

function IconWebhook() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="4.5" cy="12.5" r="2" />
      <circle cx="11.5" cy="12.5" r="2" />
      <circle cx="8" cy="3.5" r="2" />
      <path d="M8 5.5L4.5 10.5" />
      <path d="M8 5.5L11.5 10.5" />
    </svg>
  );
}

function IconCreditCard() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="3.5" width="14" height="9" rx="1.5" />
      <line x1="1" y1="7" x2="15" y2="7" />
      <line x1="4" y1="10.5" x2="7" y2="10.5" />
    </svg>
  );
}

/* ── Nav groups ── */

interface NavItem {
  to: string;
  label: string;
  Icon: React.FC;
}

interface NavGroup {
  section: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    section: "CORE",
    items: [
      { to: "/dashboard", label: "Dashboard", Icon: IconGrid },
      { to: "/tasks",     label: "Tasks",     Icon: IconList },
      { to: "/policies",  label: "Policies",  Icon: IconShield },
      { to: "/results",   label: "Results",   Icon: IconDatabase },
    ],
  },
  {
    section: "TOOLS",
    items: [
      { to: "/route-tester",  label: "Route Tester",  Icon: IconCompass },
      { to: "/scrape-test",   label: "Scrape Tester", Icon: IconDatabase },
      { to: "/schedules",     label: "Schedules",     Icon: IconClock },
    ],
  },
  {
    section: "MONITORING",
    items: [
      { to: "/sessions", label: "Sessions", Icon: IconActivity },
      { to: "/proxies",  label: "Proxies",  Icon: IconGlobe },
      { to: "/webhooks", label: "Webhooks", Icon: IconWebhook },
    ],
  },
  {
    section: "ACCOUNT",
    items: [
      { to: "/billing", label: "Billing", Icon: IconCreditCard },
    ],
  },
];

/* ── Component ── */

export function SidebarNav() {
  // useLocation consumed only for re-render on route change; NavLink handles
  // the active class itself.
  useLocation();

  return (
    <nav
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        overflowY: "auto",
        paddingBottom: 12,
      }}
    >
      {/* Search box */}
      <GlobalSearch />

      {/* Nav groups */}
      {NAV_GROUPS.map((group, gi) => (
        <div
          key={group.section}
          style={{ marginTop: gi === 0 ? 4 : 12, paddingInline: 8 }}
        >
          {/* Section label */}
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: "rgba(255,255,255,0.3)",
              letterSpacing: "0.08em",
              padding: "4px 8px 6px",
              textTransform: "uppercase",
            }}
          >
            {group.section}
          </div>

          {/* Items */}
          <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {group.items.map(({ to, label, Icon }) => (
              <NavLink
                key={to}
                to={to}
                style={({ isActive }) => ({
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "8px 10px 8px 10px",
                  borderRadius: "var(--radius-md)",
                  color: isActive ? "#ffffff" : "rgba(255,255,255,0.65)",
                  fontSize: 13,
                  fontWeight: isActive ? 600 : 500,
                  textDecoration: "none",
                  background: isActive
                    ? "rgba(37,99,235,0.5)"
                    : "transparent",
                  borderLeft: isActive
                    ? "2px solid var(--color-primary)"
                    : "2px solid transparent",
                  transition:
                    "background 0.15s, color 0.15s, border-color 0.15s",
                  marginLeft: isActive ? 0 : 0,
                })}
                className={({ isActive }) => (isActive ? "active" : "")}
                onMouseEnter={(e) => {
                  const el = e.currentTarget;
                  if (!el.classList.contains("active")) {
                    el.style.background = "rgba(255,255,255,0.06)";
                    el.style.color = "#ffffff";
                  }
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget;
                  if (!el.classList.contains("active")) {
                    el.style.background = "transparent";
                    el.style.color = "rgba(255,255,255,0.65)";
                  }
                }}
              >
                <span
                  style={{
                    width: 18,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    opacity: 0.85,
                  }}
                >
                  <Icon />
                </span>
                <span>{label}</span>
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </nav>
  );
}
