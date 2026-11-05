import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { ApiError } from "@/lib/errors";

export type Pond = components["schemas"]["PondOut"];
export type PondJob = components["schemas"]["JobOut"];
export type PondObservedState = components["schemas"]["PondObservedState"];
export type Backup = components["schemas"]["BackupOut"];
export type Connection = components["schemas"]["ConnectionOut"];

const TRANSIENT_STATES = new Set<PondObservedState>([
  "pending",
  "provisioning",
  "restoring",
  "deleting",
]);

const POLL_MS = 4_000;
const JOB_POLL_MS = 1_000;
const ACTIVE_JOB_STATUS = new Set(["queued", "running"]);

async function listPonds(): Promise<Pond[]> {
  const { data, error } = await apiClient.GET("/api/v1/ponds", {});
  if (error) {
    throw new ApiError(error);
  }
  return data?.ponds ?? [];
}

export function pondIsTransient(state: PondObservedState | undefined): boolean {
  return Boolean(state && TRANSIENT_STATES.has(state));
}

export function pondNeedsPolling(pond: Pond | undefined): boolean {
  if (!pond) return false;
  if (pondIsTransient(pond.observed_state)) return true;
  if (pond.desired_state === "stopped" && pond.observed_state === "running") return true;
  if (pond.desired_state === "running" && pond.observed_state === "stopped") return true;
  return false;
}

function pondsNeedPolling(ponds: Pond[] | undefined): boolean {
  return Boolean(ponds?.some((pond) => pondNeedsPolling(pond)));
}

export function usePondsQuery() {
  return useQuery({
    queryKey: ["ponds"],
    queryFn: listPonds,
    refetchInterval: (query) => (pondsNeedPolling(query.state.data) ? POLL_MS : false),
  });
}

export function useGetPond(pondId: string | undefined) {
  return useQuery({
    queryKey: ["ponds", pondId],
    enabled: Boolean(pondId),
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/ponds/{pond_id}", {
        params: { path: { pond_id: pondId as string } },
      });
      if (error || !data) throw new ApiError(error);
      return data.pond;
    },
    refetchInterval: (query) => (pondNeedsPolling(query.state.data) ? POLL_MS : false),
  });
}

export function useGetConnection(pondId: string | undefined) {
  return useQuery({
    queryKey: ["ponds", pondId, "connection"],
    enabled: Boolean(pondId),
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/ponds/{pond_id}/connection", {
        params: { path: { pond_id: pondId as string } },
      });
      if (error || !data) throw new ApiError(error);
      return data.connection;
    },
  });
}

export type PondSchema = components["schemas"]["PondSchemaResponse"];
export type PondTable = components["schemas"]["PondTableOut"];
export type PondColumn = components["schemas"]["PondColumnOut"];

/** Manual schema snapshot. Never auto-fetches; Recargar calls refetch(). */
export function usePondSchema(pondId: string | undefined) {
  const query = useQuery({
    queryKey: ["ponds", pondId, "schema"],
    enabled: false,
    refetchOnWindowFocus: false,
    refetchInterval: false,
    retry: false,
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/ponds/{pond_id}/schema", {
        params: { path: { pond_id: pondId as string } },
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
  });

  return {
    ...query,
    reload: () => query.refetch(),
  };
}

export function useListBackups(pondId: string | undefined) {
  return useQuery({
    queryKey: ["ponds", pondId, "backups"],
    enabled: Boolean(pondId),
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/ponds/{pond_id}/backups", {
        params: { path: { pond_id: pondId as string } },
      });
      if (error) throw new ApiError(error);
      return data?.backups ?? [];
    },
  });
}

const ENGINE_VERSION = "16";

export function useCreatePondMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const { data, error } = await apiClient.POST("/api/v1/ponds", {
        body: { name, engine_version: ENGINE_VERSION },
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["ponds"] });
      void queryClient.setQueryData(["ponds", data.pond.id], data.pond);
    },
  });
}

export function pondJobReadFailed(query: { error: unknown; isFetching: boolean }) {
  return Boolean(query.error) && !query.isFetching;
}

export function usePondJob(pondId: string, jobId: string | null) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["ponds", pondId, "jobs", jobId],
    enabled: Boolean(pondId && jobId),
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/ponds/{pond_id}/jobs/{job_id}", {
        params: { path: { pond_id: pondId, job_id: jobId as string } },
      });
      if (error || !data) throw new ApiError(error);
      return data.job;
    },
    refetchInterval: (current) => {
      if (current.state.error) return false;
      const status = current.state.data?.status;
      return status && ACTIVE_JOB_STATUS.has(status) ? JOB_POLL_MS : false;
    },
  });

  const status = query.data?.status;
  useEffect(() => {
    if (!status || ACTIVE_JOB_STATUS.has(status)) return;
    void queryClient.invalidateQueries({ queryKey: ["ponds", pondId], exact: true });
    void queryClient.invalidateQueries({ queryKey: ["ponds", pondId, "backups"], exact: true });
  }, [queryClient, pondId, status]);

  return query;
}

export function useRestoreBackupMutation(pondId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (backupId: string) => {
      const { data, error } = await apiClient.POST("/api/v1/ponds/{pond_id}/restore", {
        params: { path: { pond_id: pondId } },
        body: { backup_id: backupId },
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ponds", pondId] });
      void queryClient.invalidateQueries({ queryKey: ["ponds", pondId, "backups"] });
      void queryClient.invalidateQueries({ queryKey: ["ponds"] });
    },
  });
}

export function useTriggerBackupMutation(pondId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST("/api/v1/ponds/{pond_id}/backups", {
        params: { path: { pond_id: pondId } },
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ponds", pondId, "backups"] });
      void queryClient.invalidateQueries({ queryKey: ["ponds", pondId] });
    },
  });
}

export function useDeletePondMutation(pondId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.DELETE("/api/v1/ponds/{pond_id}", {
        params: { path: { pond_id: pondId } },
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: (data) => {
      void queryClient.setQueryData(["ponds", pondId], data.pond);
      void queryClient.invalidateQueries({ queryKey: ["ponds"] });
      void queryClient.invalidateQueries({ queryKey: ["ponds", pondId, "backups"] });
    },
  });
}

export function useStopPondMutation(pondId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST("/api/v1/ponds/{pond_id}/stop", {
        params: { path: { pond_id: pondId } },
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: (data) => {
      void queryClient.setQueryData(["ponds", pondId], data.pond);
      void queryClient.invalidateQueries({ queryKey: ["ponds"] });
      void queryClient.invalidateQueries({ queryKey: ["ponds", pondId] });
    },
  });
}

export function useStartPondMutation(pondId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST("/api/v1/ponds/{pond_id}/start", {
        params: { path: { pond_id: pondId } },
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: (data) => {
      void queryClient.setQueryData(["ponds", pondId], data.pond);
      void queryClient.invalidateQueries({ queryKey: ["ponds"] });
      void queryClient.invalidateQueries({ queryKey: ["ponds", pondId] });
    },
  });
}

export function useRetryFailedJobMutation(pondId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST("/api/v1/ponds/{pond_id}/retry", {
        params: { path: { pond_id: pondId } },
      });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ponds", pondId] });
      void queryClient.invalidateQueries({ queryKey: ["ponds"] });
    },
  });
}
