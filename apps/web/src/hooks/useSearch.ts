import { useQuery } from "@tanstack/react-query";
import { tasks, policies } from "../api/client";

const KEYS = {
  search: (q: string) => ["search", q] as const,
};

export interface SearchResult {
  type: "task" | "policy";
  id: string;
  title: string;
  subtitle: string;
  url: string;
}

export function useGlobalSearch(query: string) {
  return useQuery({
    queryKey: KEYS.search(query),
    queryFn: async (): Promise<SearchResult[]> => {
      if (!query || query.length < 2) return [];
      const [taskRes, policyRes] = await Promise.all([
        tasks.list({ limit: 5 }),
        policies.list({ limit: 5 }),
      ]);
      const results: SearchResult[] = [];
      for (const t of taskRes.items) {
        if (
          t.name.toLowerCase().includes(query.toLowerCase()) ||
          t.url.toLowerCase().includes(query.toLowerCase())
        ) {
          results.push({
            type: "task",
            id: t.id,
            title: t.name,
            subtitle: t.url,
            url: `/tasks/${t.id}`,
          });
        }
      }
      for (const p of policyRes.items) {
        if (p.name.toLowerCase().includes(query.toLowerCase())) {
          results.push({
            type: "policy",
            id: p.id,
            title: p.name,
            subtitle: p.target_domains.join(", "),
            url: `/policies`,
          });
        }
      }
      return results;
    },
    enabled: query.length >= 2,
    staleTime: 10_000,
  });
}
