/**
 * Custom hooks for policy management operations.
 * Uses @tanstack/react-query for caching, background refetching, and optimistic updates.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { policies } from "../api/client";
import type { PolicyCreate, PolicyUpdate } from "../api/types";

/* ── Query Keys ── */

const POLICY_KEYS = {
  all: ["policies"] as const,
  lists: () => [...POLICY_KEYS.all, "list"] as const,
  list: (params: { limit?: number; offset?: number }) =>
    [...POLICY_KEYS.lists(), params] as const,
  details: () => [...POLICY_KEYS.all, "detail"] as const,
  detail: (id: string) => [...POLICY_KEYS.details(), id] as const,
};

/* ── usePolicyList ── */

export function usePolicyList(params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: POLICY_KEYS.list(params ?? {}),
    queryFn: () =>
      policies.list({
        limit: params?.limit ?? 50,
        offset: params?.offset ?? 0,
      }),
  });
}

/* ── usePolicy ── */

export function usePolicy(policyId: string | undefined) {
  return useQuery({
    queryKey: POLICY_KEYS.detail(policyId ?? ""),
    queryFn: () => policies.get(policyId!),
    enabled: !!policyId,
  });
}

/* ── useCreatePolicy ── */

export function useCreatePolicy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PolicyCreate) => policies.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: POLICY_KEYS.lists() });
    },
  });
}

/* ── useUpdatePolicy ── */

export function useUpdatePolicy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      policyId,
      data,
    }: {
      policyId: string;
      data: PolicyUpdate;
    }) => policies.update(policyId, data),
    onSuccess: (_result, variables) => {
      queryClient.invalidateQueries({
        queryKey: POLICY_KEYS.detail(variables.policyId),
      });
      queryClient.invalidateQueries({ queryKey: POLICY_KEYS.lists() });
    },
  });
}

/* ── useDeletePolicy ── */

export function useDeletePolicy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (policyId: string) => policies.delete(policyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: POLICY_KEYS.lists() });
    },
  });
}
