import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { ApiError } from "@/lib/errors";

export type Subscription = components["schemas"]["SubscriptionOut"];

async function listSubscriptions(): Promise<Subscription[]> {
  const { data, error } = await apiClient.GET("/api/v1/subscriptions", {});
  if (error || !data) {
    throw new ApiError(error);
  }
  return data.subscriptions;
}

export function useSubscriptionsQuery() {
  return useQuery({
    queryKey: ["subscriptions"],
    queryFn: listSubscriptions,
  });
}

export function useCancelSubscriptionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (subscriptionId: string) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/subscriptions/{subscription_id}/cancel",
        { params: { path: { subscription_id: subscriptionId } } },
      );
      if (error || !data) {
        throw new ApiError(error);
      }
      return data.subscription;
    },
    onSuccess: (subscription) => {
      queryClient.setQueryData<Subscription[]>(["subscriptions"], (current) =>
        (current ?? []).map((item) => (item.id === subscription.id ? subscription : item)),
      );
    },
  });
}
