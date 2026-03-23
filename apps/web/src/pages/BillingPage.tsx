/**
 * BillingPage — Subscription plan management and usage tracking.
 *
 * Features:
 * - Current plan card with tier badge, price, billing cycle dates
 * - Available plans grid (Free / Starter / Pro / Enterprise) with upgrade CTAs
 * - Usage section with 5 UsageMeter components reading from useQuota
 */

import { usePlans, useQuota } from "../hooks/useBilling";
import { UsageMeter } from "../components/UsageMeter";
import type { PlanTier } from "../api/types";

/* ── Plan metadata ── */

interface PlanMeta {
  tier: PlanTier;
  name: string;
  price: string;
  priceNote: string;
  features: string[];
  badgeColor: string;
  badgeBg: string;
  accentColor: string;
}

const PLAN_META: Record<PlanTier, PlanMeta> = {
  free: {
    tier: "free",
    name: "Free",
    price: "$0",
    priceNote: "Forever free",
    badgeColor: "#4b5563",
    badgeBg: "#f3f4f6",
    accentColor: "#6b7280",
    features: [
      "100 tasks / day",
      "No browser lane",
      "10 MB storage",
      "Community support",
    ],
  },
  starter: {
    tier: "starter",
    name: "Starter",
    price: "$29",
    priceNote: "per month",
    badgeColor: "#1e40af",
    badgeBg: "#dbeafe",
    accentColor: "#2563eb",
    features: [
      "1,000 tasks / day",
      "60 browser minutes / day",
      "100K AI tokens / day",
      "5 GB storage",
      "Email support",
    ],
  },
  pro: {
    tier: "pro",
    name: "Pro",
    price: "$99",
    priceNote: "per month",
    badgeColor: "#5b21b6",
    badgeBg: "#ede9fe",
    accentColor: "#7c3aed",
    features: [
      "10,000 tasks / day",
      "600 browser minutes / day",
      "1M AI tokens / day",
      "50 GB storage",
      "Priority support",
      "Webhook callbacks",
    ],
  },
  enterprise: {
    tier: "enterprise",
    name: "Enterprise",
    price: "Custom",
    priceNote: "contact sales",
    badgeColor: "#92400e",
    badgeBg: "#fef3c7",
    accentColor: "#d97706",
    features: [
      "Unlimited tasks",
      "Unlimited browser minutes",
      "Custom AI token limits",
      "Unlimited storage",
      "Dedicated support",
      "SLA guarantee",
      "On-premise option",
    ],
  },
};

const PLAN_ORDER: PlanTier[] = ["free", "starter", "pro", "enterprise"];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

/* ── Component ── */

export function BillingPage() {
  const { data: quotaData, isLoading: quotaLoading, error: quotaError } = useQuota();
  const { isLoading: plansLoading } = usePlans();

  const currentTier: PlanTier = quotaData?.plan ?? "free";
  const currentMeta = PLAN_META[currentTier];

  return (
    <>
      <div className="page-header">
        <h2>Billing</h2>
        <p>Manage your subscription plan and monitor resource usage.</p>
      </div>

      <div className="page-body">
        {/* ── Current Plan ── */}
        <section style={{ marginBottom: 32 }}>
          <h3
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--color-text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: 12,
            }}
          >
            Current Plan
          </h3>

          {quotaLoading && <div className="loading">Loading billing info…</div>}

          {!quotaLoading && quotaData && (
            <div
              className="card"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: 16,
                borderLeft: `4px solid ${currentMeta.accentColor}`,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                {/* Tier badge */}
                <span
                  className="badge"
                  style={{
                    background: currentMeta.badgeBg,
                    color: currentMeta.badgeColor,
                    fontSize: 13,
                    padding: "4px 14px",
                  }}
                >
                  {currentMeta.name}
                </span>

                <div>
                  <div
                    style={{
                      fontSize: 26,
                      fontWeight: 700,
                      letterSpacing: "-0.02em",
                      color: "var(--color-text)",
                      lineHeight: 1.2,
                    }}
                  >
                    {currentMeta.price}
                    {currentMeta.priceNote !== "Forever free" &&
                      currentMeta.priceNote !== "contact sales" && (
                        <span
                          style={{
                            fontSize: 13,
                            fontWeight: 400,
                            color: "var(--color-text-secondary)",
                            marginLeft: 4,
                          }}
                        >
                          / mo
                        </span>
                      )}
                  </div>
                  <div
                    style={{ fontSize: 13, color: "var(--color-text-secondary)" }}
                  >
                    {currentMeta.priceNote}
                  </div>
                </div>
              </div>

              {/* Billing cycle */}
              {quotaData.billing_cycle_start && quotaData.billing_cycle_end && (
                <div
                  style={{
                    fontSize: 13,
                    color: "var(--color-text-secondary)",
                    textAlign: "right",
                  }}
                >
                  <div>
                    Billing period:{" "}
                    <span style={{ color: "var(--color-text)", fontWeight: 500 }}>
                      {formatDate(quotaData.billing_cycle_start)}
                    </span>
                  </div>
                  <div>
                    Renews:{" "}
                    <span style={{ color: "var(--color-text)", fontWeight: 500 }}>
                      {formatDate(quotaData.billing_cycle_end)}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        {/* ── Available Plans ── */}
        <section style={{ marginBottom: 32 }}>
          <h3
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--color-text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: 12,
            }}
          >
            Available Plans
          </h3>

          {plansLoading && <div className="loading">Loading plans…</div>}

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 16,
            }}
          >
            {PLAN_ORDER.map((tier) => {
              const meta = PLAN_META[tier];
              const isCurrent = tier === currentTier;

              return (
                <div
                  key={tier}
                  className="card"
                  style={{
                    position: "relative",
                    border: isCurrent
                      ? `2px solid ${meta.accentColor}`
                      : "1px solid var(--color-border)",
                    padding: "20px",
                  }}
                >
                  {/* Current plan label */}
                  {isCurrent && (
                    <div
                      style={{
                        position: "absolute",
                        top: -1,
                        right: 16,
                        background: meta.accentColor,
                        color: "#fff",
                        fontSize: 11,
                        fontWeight: 700,
                        padding: "3px 10px",
                        borderRadius: "0 0 6px 6px",
                        letterSpacing: "0.04em",
                        textTransform: "uppercase",
                      }}
                    >
                      Current
                    </div>
                  )}

                  {/* Tier name + price */}
                  <div style={{ marginBottom: 16 }}>
                    <span
                      className="badge"
                      style={{
                        background: meta.badgeBg,
                        color: meta.badgeColor,
                        marginBottom: 10,
                      }}
                    >
                      {meta.name}
                    </span>
                    <div
                      style={{
                        fontSize: 28,
                        fontWeight: 700,
                        letterSpacing: "-0.02em",
                        color: "var(--color-text)",
                        marginTop: 6,
                      }}
                    >
                      {meta.price}
                    </div>
                    <div
                      style={{ fontSize: 12, color: "var(--color-text-secondary)" }}
                    >
                      {meta.priceNote}
                    </div>
                  </div>

                  {/* Features list */}
                  <ul
                    style={{
                      listStyle: "none",
                      margin: "0 0 20px",
                      padding: 0,
                      display: "flex",
                      flexDirection: "column",
                      gap: 6,
                    }}
                  >
                    {meta.features.map((f) => (
                      <li
                        key={f}
                        style={{
                          fontSize: 13,
                          color: "var(--color-text-secondary)",
                          display: "flex",
                          alignItems: "flex-start",
                          gap: 6,
                        }}
                      >
                        <span
                          style={{ color: meta.accentColor, fontWeight: 700 }}
                        >
                          ✓
                        </span>
                        {f}
                      </li>
                    ))}
                  </ul>

                  {/* CTA */}
                  {isCurrent ? (
                    <button className="btn btn-secondary" disabled style={{ width: "100%" }}>
                      Current Plan
                    </button>
                  ) : tier === "enterprise" ? (
                    <button className="btn btn-secondary" style={{ width: "100%" }}>
                      Contact Sales
                    </button>
                  ) : (
                    <button
                      className="btn btn-primary"
                      style={{ width: "100%", background: meta.accentColor }}
                    >
                      Upgrade to {meta.name}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* ── Usage ── */}
        <section>
          <h3
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--color-text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: 12,
            }}
          >
            Usage — Today
          </h3>

          {quotaLoading && <div className="loading">Loading usage…</div>}

          {quotaError && !quotaLoading && (
            <div className="empty-state">
              <h3>Failed to load usage data</h3>
              <p>Check your connection and try again.</p>
            </div>
          )}

          {!quotaLoading && !quotaError && quotaData && (
            <div className="card">
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                  gap: 24,
                }}
              >
                {/* Tasks / Day */}
                <UsageMeter
                  label="Tasks / Day"
                  current={quotaData.current_usage.tasks_today}
                  max={quotaData.max_tasks_per_day}
                  unit="tasks"
                />

                {/* Browser Minutes */}
                <UsageMeter
                  label="Browser Minutes"
                  current={quotaData.current_usage.browser_minutes_today}
                  max={quotaData.max_browser_minutes_per_day}
                  unit="min"
                />

                {/* AI Tokens */}
                <UsageMeter
                  label="AI Tokens"
                  current={quotaData.current_usage.ai_tokens_today}
                  max={quotaData.max_ai_tokens_per_day}
                  unit="tokens"
                />

                {/* Storage */}
                <UsageMeter
                  label="Storage"
                  current={quotaData.current_usage.storage_bytes_used}
                  max={quotaData.max_storage_bytes}
                  unit="bytes"
                />

                {/* Proxy Requests */}
                <UsageMeter
                  label="Proxy Requests"
                  current={quotaData.current_usage.proxy_requests_today}
                  max={quotaData.max_proxy_requests_per_day}
                  unit="req"
                />
              </div>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
