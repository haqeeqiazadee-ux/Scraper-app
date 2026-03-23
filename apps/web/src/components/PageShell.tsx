import type { ReactNode } from "react";

interface PageShellProps {
  /** Page heading text */
  title: string;
  /** Optional sub-heading text beneath the title */
  subtitle?: string;
  /** Optional ReactNode rendered in the top-right header slot */
  actions?: ReactNode;
  children: ReactNode;
}

/**
 * Reusable page wrapper that renders a consistent header (title + subtitle +
 * actions slot) followed by a scrollable page body.
 */
export default function PageShell({
  title,
  subtitle,
  actions,
  children,
}: PageShellProps) {
  return (
    <div className="page-shell">
      <div className="page-header">
        <div className="page-header-left">
          <h1>{title}</h1>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {actions && (
          <div className="page-header-actions">{actions}</div>
        )}
      </div>
      <div className="page-body">{children}</div>
    </div>
  );
}
