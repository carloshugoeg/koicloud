import { useMutation, useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { ApiError } from "@/lib/errors";

export type PlanOut = components["schemas"]["PlanOut"];
export type SubscribeRequest = components["schemas"]["SubscribeRequest"];
export type SubscribeResponse = components["schemas"]["SubscribeResponse"];

export function usePlansQuery() {
  return useQuery({
    queryKey: ["plans"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/plans", {});
      if (error || !data) {
        throw new ApiError(error);
      }
      return data.plans;
    },
  });
}

export function useSubscribeMutation() {
  return useMutation({
    mutationFn: async (body: SubscribeRequest) => {
      const { data, error } = await apiClient.POST("/api/v1/subscriptions", {
        body,
      });
      if (error || !data) {
        throw new ApiError(error);
      }
      return data;
    },
  });
}
