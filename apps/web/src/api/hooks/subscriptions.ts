import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { ApiError } from "@/lib/errors";

export type SubscriptionOut = components["schemas"]["SubscriptionOut"];

export function useSubscriptionsQuery() {
  return useQuery({
    queryKey: ["subscriptions"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/subscriptions");
      if (error || !data) {
        throw new ApiError(error);
      }
      return data.subscriptions;
    },
  });
}

export function useCancelSubscriptionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (subscriptionId: string) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/subscriptions/{subscription_id}/cancel",
        {
          params: { path: { subscription_id: subscriptionId } },
        },
      );
      if (error || !data) {
        throw new ApiError(error);
      }
      return data.subscription;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
    },
  });
}
