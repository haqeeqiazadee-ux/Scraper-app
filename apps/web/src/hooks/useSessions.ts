import { useQuery } from "@tanstack/react-query";
import { sessions } from "../api/client";

const KEYS = {
  all: ["sessions"] as const,
  list: () => [...KEYS.all, "list"] as const,
};

export function useSessionList() {
  return useQuery({
    queryKey: KEYS.list(),
    queryFn: () => sessions.list({ limit: 100 }),
    refetchInterval: 10_000,
  });
}
