import { Routes, Route, Navigate } from "react-router-dom";

import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { TasksPage } from "./pages/TasksPage";
import { TaskDetailPage } from "./pages/TaskDetailPage";
import { Policies } from "./pages/Policies";
import { ResultsPage } from "./pages/ResultsPage";
import { ResultDetailPage } from "./pages/ResultDetailPage";

import { SchedulesPage } from "./pages/SchedulesPage";
import { BillingPage } from "./pages/BillingPage";
import { SessionsPage } from "./pages/SessionsPage";
import { ProxyPage } from "./pages/ProxyPage";
import { RouteTesterPage } from "./pages/RouteTesterPage";
import { WebhookHistoryPage } from "./pages/WebhookHistoryPage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { AmazonPage } from "./pages/AmazonPage";
import { GoogleMapsPage } from "./pages/GoogleMapsPage";
import { FacebookGroupPage } from "./pages/FacebookGroupPage";
import { ScraperPage } from "./pages/ScraperPage";
import { ChangesPage } from "./pages/ChangesPage";
import { McpPage } from "./pages/McpPage";
import { ApiKeysPage } from "./pages/ApiKeysPage";
import { FmsPage } from "./pages/FmsPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      {/* Public route */}
      <Route path="/login" element={<Navigate to="/dashboard" replace />} />

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
        <Route path="/scraper" element={<ScraperPage />} />
        <Route path="/scrape-test" element={<Navigate to="/scraper" replace />} />
        <Route path="/auth-scrape" element={<Navigate to="/scraper" replace />} />
        <Route path="/crawl" element={<Navigate to="/scraper" replace />} />
        <Route path="/search" element={<Navigate to="/scraper" replace />} />
        <Route path="/extract" element={<Navigate to="/scraper" replace />} />
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/amazon" element={<AmazonPage />} />
        <Route path="/google-maps" element={<GoogleMapsPage />} />
        <Route path="/facebook-groups" element={<FacebookGroupPage />} />
        <Route path="/sessions" element={<SessionsPage />} />
        <Route path="/proxies" element={<ProxyPage />} />
        <Route path="/webhooks" element={<WebhookHistoryPage />} />
        <Route path="/billing" element={<BillingPage />} />
        <Route path="/changes" element={<ChangesPage />} />
        <Route path="/mcp" element={<McpPage />} />
        <Route path="/api-keys" element={<ApiKeysPage />} />
        <Route path="/fms" element={<FmsPage />} />
      </Route>

      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
