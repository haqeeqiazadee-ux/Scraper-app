import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Tasks } from "./pages/Tasks";
import { TaskDetail } from "./pages/TaskDetail";
import { Policies } from "./pages/Policies";
import { Results } from "./pages/Results";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/tasks/:taskId" element={<TaskDetail />} />
        <Route path="/policies" element={<Policies />} />
        <Route path="/results" element={<Results />} />
      </Route>
    </Routes>
  );
}
