import { useMutation } from "@tanstack/react-query";
import { routing } from "../api/client";

export function useDryRunRoute() {
  return useMutation({
    mutationFn: ({ url, policyId }: { url: string; policyId?: string }) =>
      routing.dryRun(url, policyId),
  });
}
