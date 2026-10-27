import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { ApiError } from "@/lib/errors";
import { useAuthStore } from "@/lib/auth-store";

export type MeResponse = components["schemas"]["MeResponse"];
export type UpdateProfileRequest = components["schemas"]["UpdateProfileRequest"];
export type ChangePasswordRequest = components["schemas"]["ChangePasswordRequest"];
export type DeleteMeRequest = components["schemas"]["DeleteMeRequest"];

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

export function useUpdateProfileMutation() {
  const queryClient = useQueryClient();
  const session = useAuthStore((state) => state.session);
  const setSession = useAuthStore((state) => state.setSession);

  return useMutation({
    mutationFn: async (body: UpdateProfileRequest) => {
      const { data, error } = await apiClient.PATCH("/api/v1/me", { body });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["me"] });
      if (session) {
        setSession({ ...session, user: data.user });
      }
    },
  });
}

export function useChangePasswordMutation() {
  return useMutation({
    mutationFn: async (body: ChangePasswordRequest) => {
      const { error, response } = await apiClient.POST("/api/v1/me/change-password", {
        body,
      });
      if (error || !response.ok) throw new ApiError(error);
    },
  });
}

export function useDeleteMeMutation() {
  const clearSession = useAuthStore((state) => state.clearSession);

  return useMutation({
    mutationFn: async (body: DeleteMeRequest) => {
      const { data, error } = await apiClient.DELETE("/api/v1/me", { body });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: () => {
      clearSession();
    },
  });
}
