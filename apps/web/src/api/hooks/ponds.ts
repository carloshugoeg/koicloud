import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { ApiError } from "@/lib/errors";

export type Pond = components["schemas"]["PondOut"];
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

function pondsNeedPolling(ponds: Pond[] | undefined): boolean {
  return Boolean(ponds?.some((pond) => pondIsTransient(pond.observed_state)));
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
    refetchInterval: (query) =>
      pondIsTransient(query.state.data?.observed_state) ? POLL_MS : false,
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
