import { useQuery } from "@tanstack/react-query";
import { metrics } from "../api/client";

const KEYS = {
  all: ["metrics"] as const,
};

export function useMetrics() {
  return useQuery({
    queryKey: KEYS.all,
    queryFn: () => metrics.get(),
    refetchInterval: 30_000,
  });
}
