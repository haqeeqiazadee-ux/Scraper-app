import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./contexts/AuthContext";
import { App } from "./App";
import "./styles/globals.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 0,              // Always fetch fresh from server
      gcTime: 5 * 60 * 1000,     // Garbage collect after 5 min
      retry: 1,
      refetchOnWindowFocus: true, // Re-fetch when tab regains focus
      refetchOnMount: true,       // Always fetch on component mount
      refetchOnReconnect: true,   // Re-fetch on network reconnect
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
