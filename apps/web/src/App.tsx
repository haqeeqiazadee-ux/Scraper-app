import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { TasksPage } from "./pages/TasksPage";
import { TaskDetailPage } from "./pages/TaskDetailPage";
import { Policies } from "./pages/Policies";
import { ResultsPage } from "./pages/ResultsPage";
import { ResultDetailPage } from "./pages/ResultDetailPage";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
        <Route path="/policies" element={<Policies />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/results/:id" element={<ResultDetailPage />} />
      </Route>
    </Routes>
  );
}
