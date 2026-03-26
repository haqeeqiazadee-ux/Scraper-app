/**
 * Login page with split layout: colorful branding panel + login form.
 * Supports toggling to a registration view.
 */

import { useState, type FormEvent } from "react";
import { useLogin, useRegister } from "../hooks/useAuth";

export function Login() {
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const {
    handleLogin,
    isLoading: loginLoading,
    error: loginError,
    clearError: clearLoginError,
  } = useLogin();

  const {
    handleRegister,
    isLoading: registerLoading,
    error: registerError,
    clearError: clearRegisterError,
  } = useRegister();

  const isLoading = loginLoading || registerLoading;
  const error = isRegisterMode ? registerError : loginError;

  function toggleMode() {
    setIsRegisterMode((prev) => !prev);
    clearLoginError();
    clearRegisterError();
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;

    try {
      if (isRegisterMode) {
        await handleRegister(username.trim(), password.trim());
      } else {
        await handleLogin(username.trim(), password.trim());
      }
    } catch {
      // Error state is already handled by the hooks
    }
  }

  return (
    <div className="login-split">
      {/* Left branding panel */}
      <div className="login-brand">
        <div style={{ maxWidth: 480 }}>
          {/* Logo */}
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: 16,
              background: "rgba(255,255,255,0.2)",
              backdropFilter: "blur(10px)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 28,
              fontWeight: 800,
              color: "#fff",
              marginBottom: 32,
              boxShadow: "0 8px 32px rgba(0,0,0,0.15)",
            }}
          >
            S
          </div>

          <h1
            style={{
              fontSize: 42,
              fontWeight: 800,
              lineHeight: 1.1,
              marginBottom: 12,
              letterSpacing: "-0.03em",
            }}
          >
            Scraper AI
          </h1>
          <p
            style={{
              fontSize: 20,
              fontWeight: 500,
              opacity: 0.9,
              marginBottom: 48,
              lineHeight: 1.4,
            }}
          >
            Intelligent Web Data Extraction
          </p>

          {/* Feature bullets */}
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            <FeatureBullet
              icon={
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <path d="M16 10a4 4 0 01-8 0" />
                </svg>
              }
              title="Amazon & Keepa Integration"
              description="Real-time product data, price tracking, and sales analytics"
            />
            <FeatureBullet
              icon={
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" />
                  <circle cx="12" cy="10" r="3" />
                </svg>
              }
              title="Google Maps Scraping"
              description="Extract business data, reviews, and contact information"
            />
            <FeatureBullet
              icon={
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="2" y1="12" x2="22" y2="12" />
                  <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
                </svg>
              }
              title="Universal Extraction"
              description="6-tier cascade with AI-powered fallback chains"
            />
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="login-form-side">
        <div
          className="card"
          style={{
            width: "100%",
            maxWidth: 400,
            boxShadow: "var(--shadow-lg)",
          }}
        >
          {/* Branded header */}
          <div style={{ textAlign: "center", marginBottom: 28 }}>
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 12,
                background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 22,
                color: "#fff",
                fontWeight: 700,
                marginBottom: 16,
                boxShadow: "0 4px 12px rgba(99, 102, 241, 0.3)",
              }}
            >
              S
            </div>
            <h1
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: "var(--color-text)",
                marginBottom: 4,
                letterSpacing: "-0.025em",
              }}
            >
              {isRegisterMode ? "Create Account" : "Welcome Back"}
            </h1>
            <p
              style={{
                fontSize: 14,
                color: "var(--color-text-secondary)",
                margin: 0,
              }}
            >
              {isRegisterMode
                ? "Create a new account to get started"
                : "Sign in to your account"}
            </p>
          </div>

          {error && (
            <div className="form-error-banner" style={{ marginBottom: 16 }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="login-username">Username</label>
              <input
                id="login-username"
                type="text"
                className="form-input"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={isLoading}
                autoComplete="username"
                autoFocus
              />
            </div>

            <div className="form-group">
              <label htmlFor="login-password">Password</label>
              <input
                id="login-password"
                type="password"
                className="form-input"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                autoComplete={
                  isRegisterMode ? "new-password" : "current-password"
                }
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-lg"
              style={{ width: "100%", marginTop: 8 }}
              disabled={isLoading || !username.trim() || !password.trim()}
            >
              {isLoading ? (
                <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                  <span className="spinner" />
                  Please wait...
                </span>
              ) : isRegisterMode ? (
                "Create Account"
              ) : (
                "Sign In"
              )}
            </button>
          </form>

          <div
            style={{
              textAlign: "center",
              marginTop: 20,
              fontSize: 13,
              color: "var(--color-text-secondary)",
            }}
          >
            {isRegisterMode ? "Already have an account?" : "Don't have an account?"}{" "}
            <button
              type="button"
              onClick={toggleMode}
              style={{
                background: "none",
                border: "none",
                color: "var(--color-primary)",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: 600,
                padding: 0,
              }}
            >
              {isRegisterMode ? "Sign in" : "Create one"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Feature bullet sub-component ── */

function FeatureBullet({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: 12,
          background: "rgba(255,255,255,0.15)",
          backdropFilter: "blur(8px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        {icon}
      </div>
      <div>
        <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>
          {title}
        </div>
        <div style={{ fontSize: 14, opacity: 0.8, lineHeight: 1.4 }}>
          {description}
        </div>
      </div>
    </div>
  );
}
