/**
 * Hooks for fetching and managing scraping results.
 */

import { useQuery, useMutation } from "@tanstack/react-query";
import { results } from "../api/client";

export function useResultList(params: {
  limit?: number;
  offset?: number;
  min_confidence?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}) {
  return useQuery({
    queryKey: ["results", params],
    queryFn: () => results.list(params),
  });
}

export function useResult(resultId: string | undefined) {
  return useQuery({
    queryKey: ["result", resultId],
    queryFn: () => results.get(resultId!),
    enabled: !!resultId,
  });
}

export function useExportResults() {
  return useMutation({
    mutationFn: (params: {
      format: "json" | "csv" | "xlsx";
      min_confidence?: number;
      date_from?: string;
      date_to?: string;
      destination: "download" | "s3" | "webhook";
      webhook_url?: string;
      s3_path?: string;
    }) => results.export(params),
  });
}

export function useExportCount(params: {
  min_confidence?: number;
  date_from?: string;
  date_to?: string;
}) {
  return useQuery({
    queryKey: ["results-export-count", params],
    queryFn: () => results.exportCount(params),
  });
}
