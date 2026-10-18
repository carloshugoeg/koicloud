import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { ApiError } from "@/lib/errors";

export type AgentAccess = components["schemas"]["AgentAccessOut"];
export type AgentAccessSecret = components["schemas"]["AgentAccessSecretOut"];

export function useAgentAccessQuery() {
  return useQuery({
    queryKey: ["agent-access"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/agent-access");
      if (error || !data) {
        throw new ApiError(error);
      }
      return data;
    },
  });
}

export function useRotateAgentPasswordMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST("/api/v1/agent-access/rotate", {});
      if (error || !data) {
        throw new ApiError(error);
      }
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["agent-access"] });
    },
  });
}

export function useToggleAgentAccessMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (enabled: boolean) => {
      const { data, error } = await apiClient.POST("/api/v1/agent-access/toggle", {
        body: { enabled },
      });
      if (error || !data) {
        throw new ApiError(error);
      }
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData<AgentAccess>(["agent-access"], (current) =>
        current ? { ...current, enabled: data.enabled } : current,
      );
    },
  });
}
