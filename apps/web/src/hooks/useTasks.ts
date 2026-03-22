/**
 * Custom hooks for task management operations.
 * Uses @tanstack/react-query for caching, background refetching, and optimistic updates.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tasks } from "../api/client";
import type {
  TaskCreate,
  TaskUpdate,
  TaskListItem,
  PaginatedResponse,
} from "../api/types";

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
  /** Auto-refresh interval in milliseconds. Set to 0 or false to disable. */
  refetchInterval?: number | false;
}) {
  return useQuery({
    queryKey: TASK_KEYS.list(params ?? {}),
    queryFn: () =>
      tasks.list({
        status: params?.status,
        limit: params?.limit ?? 20,
        offset: params?.offset ?? 0,
      }),
    refetchInterval: params?.refetchInterval,
  });
}

/* ── useTask ── */

export function useTask(
  taskId: string | undefined,
  options?: { refetchInterval?: number | false },
) {
  return useQuery({
    queryKey: TASK_KEYS.detail(taskId ?? ""),
    queryFn: () => tasks.get(taskId!),
    enabled: !!taskId,
    refetchInterval: options?.refetchInterval,
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
    onSuccess: (_result, taskId) => {
      // Optimistically remove the task from cached lists
      queryClient.setQueriesData<PaginatedResponse<TaskListItem>>(
        { queryKey: TASK_KEYS.lists() },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            items: old.items.filter((t) => t.id !== taskId),
            total: old.total - 1,
          };
        },
      );
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
      // Optimistically update the task status to "queued" in cached lists
      queryClient.setQueriesData<PaginatedResponse<TaskListItem>>(
        { queryKey: TASK_KEYS.lists() },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            items: old.items.map((t) =>
              t.id === taskId ? { ...t, status: "queued" as const } : t,
            ),
          };
        },
      );
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
      // Optimistically update the task status to "cancelled" in cached lists
      queryClient.setQueriesData<PaginatedResponse<TaskListItem>>(
        { queryKey: TASK_KEYS.lists() },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            items: old.items.map((t) =>
              t.id === taskId ? { ...t, status: "cancelled" as const } : t,
            ),
          };
        },
      );
      queryClient.invalidateQueries({
        queryKey: TASK_KEYS.detail(taskId),
      });
      queryClient.invalidateQueries({ queryKey: TASK_KEYS.lists() });
    },
  });
}
