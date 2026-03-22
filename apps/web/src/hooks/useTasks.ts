/**
 * Custom hooks for task management operations.
 * Uses @tanstack/react-query for caching, background refetching, and optimistic updates.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tasks } from "../api/client";
import type { TaskCreate, TaskUpdate, TaskStatus } from "../api/types";

/* ── Query Keys ── */

const TASK_KEYS = {
  all: ["tasks"] as const,
  lists: () => [...TASK_KEYS.all, "list"] as const,
  list: (params: { status?: string; limit?: number; offset?: number }) =>
    [...TASK_KEYS.lists(), params] as const,
  details: () => [...TASK_KEYS.all, "detail"] as const,
  detail: (id: string) => [...TASK_KEYS.details(), id] as const,
  runs: (id: string) => [...TASK_KEYS.all, "runs", id] as const,
  results: (id: string) => [...TASK_KEYS.all, "results", id] as const,
};

/* ── useTaskList ── */

export function useTaskList(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: TASK_KEYS.list(params ?? {}),
    queryFn: () =>
      tasks.list({
        status: params?.status,
        limit: params?.limit ?? 20,
        offset: params?.offset ?? 0,
      }),
  });
}

/* ── useTask ── */

export function useTask(taskId: string | undefined) {
  return useQuery({
    queryKey: TASK_KEYS.detail(taskId ?? ""),
    queryFn: () => tasks.get(taskId!),
    enabled: !!taskId,
  });
}

/* ── useTaskRuns ── */

export function useTaskRuns(taskId: string | undefined) {
  return useQuery({
    queryKey: TASK_KEYS.runs(taskId ?? ""),
    queryFn: () => tasks.runs(taskId!),
    enabled: !!taskId,
  });
}

/* ── useTaskResults ── */

export function useTaskResults(taskId: string | undefined) {
  return useQuery({
    queryKey: TASK_KEYS.results(taskId ?? ""),
    queryFn: () => tasks.results(taskId!),
    enabled: !!taskId,
  });
}

/* ── useCreateTask ── */

export function useCreateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TaskCreate) => tasks.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TASK_KEYS.lists() });
    },
  });
}

/* ── useUpdateTask ── */

export function useUpdateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ taskId, data }: { taskId: string; data: TaskUpdate }) =>
      tasks.update(taskId, data),
    onSuccess: (_result, variables) => {
      queryClient.invalidateQueries({
        queryKey: TASK_KEYS.detail(variables.taskId),
      });
      queryClient.invalidateQueries({ queryKey: TASK_KEYS.lists() });
    },
  });
}

/* ── useDeleteTask ── */

export function useDeleteTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (taskId: string) => tasks.delete(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TASK_KEYS.lists() });
    },
  });
}

/* ── useExecuteTask ── */

export function useExecuteTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (taskId: string) => tasks.execute(taskId),
    onSuccess: (_result, taskId) => {
      queryClient.invalidateQueries({
        queryKey: TASK_KEYS.detail(taskId),
      });
      queryClient.invalidateQueries({ queryKey: TASK_KEYS.lists() });
      queryClient.invalidateQueries({ queryKey: TASK_KEYS.runs(taskId) });
    },
  });
}

/* ── useCancelTask ── */

export function useCancelTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (taskId: string) => tasks.cancel(taskId),
    onSuccess: (_result, taskId) => {
      queryClient.invalidateQueries({
        queryKey: TASK_KEYS.detail(taskId),
      });
      queryClient.invalidateQueries({ queryKey: TASK_KEYS.lists() });
    },
  });
}
