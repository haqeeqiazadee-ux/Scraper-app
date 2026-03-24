/**
 * Login page with username/password form.
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
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--color-bg)",
        padding: 16,
      }}
    >
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
          <div style={{
            width: 48, height: 48, borderRadius: 12,
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            display: "inline-flex", alignItems: "center", justifyContent: "center",
            fontSize: 22, color: "#fff", fontWeight: 700,
            marginBottom: 16, boxShadow: "0 4px 12px rgba(99, 102, 241, 0.3)",
          }}>S</div>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: "var(--color-text)",
              marginBottom: 4,
              letterSpacing: "-0.025em",
            }}
          >
            Scraper AI Platform
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
  );
}
