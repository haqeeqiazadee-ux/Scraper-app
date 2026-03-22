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
          boxShadow: "var(--shadow-md)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <h1
            style={{
              fontSize: 20,
              fontWeight: 700,
              color: "var(--color-text)",
              marginBottom: 4,
            }}
          >
            Scraping Platform
          </h1>
          <p
            style={{
              fontSize: 14,
              color: "var(--color-text-secondary)",
              margin: 0,
            }}
          >
            {isRegisterMode
              ? "Create a new account"
              : "Sign in to your account"}
          </p>
        </div>

        {error && (
          <div
            style={{
              padding: "10px 12px",
              background: "#fee2e2",
              borderRadius: "var(--radius-md)",
              fontSize: 13,
              color: "var(--color-error)",
              fontWeight: 500,
              marginBottom: 16,
            }}
          >
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
            className="btn btn-primary"
            style={{ width: "100%", marginTop: 8 }}
            disabled={isLoading || !username.trim() || !password.trim()}
          >
            {isLoading
              ? "Please wait..."
              : isRegisterMode
                ? "Create Account"
                : "Sign In"}
          </button>
        </form>

        <div
          style={{
            textAlign: "center",
            marginTop: 16,
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
              fontWeight: 500,
              padding: 0,
              textDecoration: "underline",
            }}
          >
            {isRegisterMode ? "Sign in" : "Create one"}
          </button>
        </div>
      </div>
    </div>
  );
}
