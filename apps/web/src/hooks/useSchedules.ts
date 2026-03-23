import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { schedules } from "../api/client";
import type { ScheduleCreateRequest } from "../api/types";

const KEYS = {
  all: ["schedules"] as const,
  list: () => [...KEYS.all, "list"] as const,
};

export function useScheduleList() {
  return useQuery({
    queryKey: KEYS.list(),
    queryFn: () => schedules.listV2(),
    refetchInterval: 30_000,
  });
}

export function useCreateSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ScheduleCreateRequest) => schedules.createV2(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => schedules.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}
