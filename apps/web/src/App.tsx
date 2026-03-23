import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthContext } from "./contexts/AuthContext";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { TasksPage } from "./pages/TasksPage";
import { TaskDetailPage } from "./pages/TaskDetailPage";
import { Policies } from "./pages/Policies";
import { ResultsPage } from "./pages/ResultsPage";
import { ResultDetailPage } from "./pages/ResultDetailPage";
import { Login } from "./pages/Login";
import { SchedulesPage } from "./pages/SchedulesPage";
import { BillingPage } from "./pages/BillingPage";
import { SessionsPage } from "./pages/SessionsPage";
import { ProxyPage } from "./pages/ProxyPage";
import { RouteTesterPage } from "./pages/RouteTesterPage";
import { WebhookHistoryPage } from "./pages/WebhookHistoryPage";

/** Wrapper that redirects unauthenticated users to /login. */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthContext();

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div className="loading">Initializing...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

/** Wrapper that redirects authenticated users away from login. */
function GuestRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthContext();

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div className="loading">Initializing...</div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      {/* Public route */}
      <Route
        path="/login"
        element={
          <GuestRoute>
            <Login />
          </GuestRoute>
        }
      />

      {/* Protected routes */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
        <Route path="/policies" element={<Policies />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/results/:id" element={<ResultDetailPage />} />
        <Route path="/schedules" element={<SchedulesPage />} />
        <Route path="/route-tester" element={<RouteTesterPage />} />
        <Route path="/sessions" element={<SessionsPage />} />
        <Route path="/proxies" element={<ProxyPage />} />
        <Route path="/webhooks" element={<WebhookHistoryPage />} />
        <Route path="/billing" element={<BillingPage />} />
      </Route>

      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
