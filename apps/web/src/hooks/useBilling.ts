import { useQuery } from "@tanstack/react-query";
import { billing } from "../api/client";

const KEYS = {
  all: ["billing"] as const,
  plans: () => [...KEYS.all, "plans"] as const,
  quota: () => [...KEYS.all, "quota"] as const,
};

export function usePlans() {
  return useQuery({
    queryKey: KEYS.plans(),
    queryFn: () => billing.plans(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useQuota() {
  return useQuery({
    queryKey: KEYS.quota(),
    queryFn: () => billing.quota(),
    refetchInterval: 30_000,
  });
}
