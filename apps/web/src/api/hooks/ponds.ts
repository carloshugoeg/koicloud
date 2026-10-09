import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { ApiError } from "@/lib/errors";

export type Pond = components["schemas"]["PondOut"];
export type PondObservedState = components["schemas"]["PondObservedState"];
export type Backup = components["schemas"]["BackupOut"];
export type Connection = components["schemas"]["ConnectionOut"];

const TRANSIENT_STATES = new Set<PondObservedState>([
  "provisioning",
  "restoring",
  "deleting",
]);

async function listPonds(): Promise<Pond[]> {
  const { data, error } = await apiClient.GET("/api/v1/ponds", {});
  if (error) {
    throw new ApiError(error);
  }
  return data?.ponds ?? [];
}

function pondsNeedPolling(ponds: Pond[] | undefined): boolean {
  return Boolean(ponds?.some((pond) => TRANSIENT_STATES.has(pond.observed_state)));
}

export function usePondsQuery() {
  return useQuery({
    queryKey: ["ponds"],
    queryFn: listPonds,
    refetchInterval: (query) => (pondsNeedPolling(query.state.data) ? 4_000 : false),
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
