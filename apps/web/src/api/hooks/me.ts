import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { ApiError } from "@/lib/errors";

export type MeResponse = components["schemas"]["MeResponse"];

export function useMeQuery() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async (): Promise<MeResponse> => {
      const { data, error } = await apiClient.GET("/api/v1/me", {});
      if (error || !data) {
        throw new ApiError(error);
      }
      return data;
    },
  });
}
