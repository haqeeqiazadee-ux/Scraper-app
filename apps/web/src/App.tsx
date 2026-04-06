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
import ScrapeTestPage from "./pages/ScrapeTestPage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { AmazonPage } from "./pages/AmazonPage";
import { GoogleMapsPage } from "./pages/GoogleMapsPage";
import { FacebookGroupPage } from "./pages/FacebookGroupPage";
import { CrawlPage } from "./pages/CrawlPage";
import { SearchPage } from "./pages/SearchPage";
import { ExtractPage } from "./pages/ExtractPage";
import { ChangesPage } from "./pages/ChangesPage";
import { McpPage } from "./pages/McpPage";
import { ApiKeysPage } from "./pages/ApiKeysPage";

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
        <Route path="/scrape-test" element={<ScrapeTestPage />} />
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/amazon" element={<AmazonPage />} />
        <Route path="/google-maps" element={<GoogleMapsPage />} />
        <Route path="/facebook-groups" element={<FacebookGroupPage />} />
        <Route path="/sessions" element={<SessionsPage />} />
        <Route path="/proxies" element={<ProxyPage />} />
        <Route path="/webhooks" element={<WebhookHistoryPage />} />
        <Route path="/billing" element={<BillingPage />} />
        <Route path="/crawl" element={<CrawlPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/extract" element={<ExtractPage />} />
        <Route path="/changes" element={<ChangesPage />} />
        <Route path="/mcp" element={<McpPage />} />
        <Route path="/api-keys" element={<ApiKeysPage />} />
      </Route>

      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
