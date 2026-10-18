import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { ApiError } from "@/lib/errors";

export type SQLMode = components["schemas"]["SQLMode"];
export type RunSQLRequest = components["schemas"]["RunSQLRequest"];
export type SQLResultResponse = components["schemas"]["SQLResultResponse"];
export type SQLHistoryItem = components["schemas"]["SQLHistoryItem"];
export type SQLHistoryResponse = components["schemas"]["SQLHistoryResponse"];

function historyKey(pondId: string) {
  return ["ponds", pondId, "sql-history"] as const;
}

export function useSqlHistoryQuery(pondId: string | undefined) {
  return useQuery({
    queryKey: historyKey(pondId ?? ""),
    enabled: Boolean(pondId),
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/ponds/{pond_id}/sql/history", {
        params: { path: { pond_id: pondId as string } },
      });
      if (error || !data) {
        throw new ApiError(error);
      }
      return data;
    },
  });
}

export function useRunSqlMutation(pondId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: RunSQLRequest) => {
      const { data, error } = await apiClient.POST("/api/v1/ponds/{pond_id}/sql", {
        params: { path: { pond_id: pondId } },
        body,
      });
      if (error || !data) {
        throw new ApiError(error);
      }
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: historyKey(pondId) });
    },
  });
}
