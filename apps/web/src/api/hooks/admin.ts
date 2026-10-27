import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { ApiError } from "@/lib/errors";

export type AdminUser = components["schemas"]["AdminUserOut"];
export type AdminPond = components["schemas"]["AdminPondOut"];
export type AdminSubscription = components["schemas"]["AdminSubscriptionOut"];
export type AuditEvent = components["schemas"]["AuditEventOut"];

export const SUSPEND_CONFIRM_TEXT = "SUSPENDER";

export function useAdminUsersQuery() {
  return useQuery({
    queryKey: ["admin", "users"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/admin/users");
      if (error || !data) {
        throw new ApiError(error);
      }
      return data;
    },
  });
}

export function useSuspendUserMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string) => {
      const { data, error } = await apiClient.POST("/api/v1/admin/users/{user_id}/suspend", {
        params: { path: { user_id: userId } },
        body: { confirm_text: SUSPEND_CONFIRM_TEXT },
      });
      if (error || !data) {
        throw new ApiError(error);
      }
      return data.user;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });
}

export function useReactivateUserMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string) => {
      const { data, error } = await apiClient.POST("/api/v1/admin/users/{user_id}/reactivate", {
        params: { path: { user_id: userId } },
      });
      if (error || !data) {
        throw new ApiError(error);
      }
      return data.user;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });
}

export function useAdminPondsQuery() {
  return useQuery({
    queryKey: ["admin", "ponds"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/admin/ponds");
      if (error || !data) {
        throw new ApiError(error);
      }
      return data;
    },
  });
}

export function useAdminSubscriptionsQuery() {
  return useQuery({
    queryKey: ["admin", "subscriptions"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/admin/subscriptions");
      if (error || !data) {
        throw new ApiError(error);
      }
      return data;
    },
  });
}

export function useAdminAuditQuery() {
  return useQuery({
    queryKey: ["admin", "audit"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/admin/audit");
      if (error || !data) {
        throw new ApiError(error);
      }
      return data;
    },
  });
}
