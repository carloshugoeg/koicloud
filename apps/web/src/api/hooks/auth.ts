import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { ApiError } from "@/lib/errors";
import { useAuthStore } from "@/lib/auth-store";

export type RegisterPayload = components["schemas"]["RegisterUserRequest"];
export type VerifyEmailPayload = components["schemas"]["VerifyEmailRequest"];
export type LoginPayload = components["schemas"]["LoginRequest"];
export type ForgotPasswordPayload = components["schemas"]["ForgotPasswordRequest"];
export type ResetPasswordPayload = components["schemas"]["ResetPasswordRequest"];

export function useRegisterMutation() {
  return useMutation({
    mutationFn: async (body: RegisterPayload) => {
      const { data, error } = await apiClient.POST("/api/v1/auth/register", { body });
      if (error || !data) throw new ApiError(error);
      return data;
    },
  });
}

export function useVerifyEmailMutation() {
  return useMutation({
    mutationFn: async (body: VerifyEmailPayload) => {
      const { data, error } = await apiClient.POST("/api/v1/auth/verify", { body });
      if (error || !data) throw new ApiError(error);
      return data;
    },
  });
}

export function useLoginMutation() {
  const setSession = useAuthStore((state) => state.setSession);
  return useMutation({
    mutationFn: async (body: LoginPayload) => {
      const { data, error } = await apiClient.POST("/api/v1/auth/login", { body });
      if (error || !data) throw new ApiError(error);
      return data;
    },
    onSuccess: (data) => {
      setSession({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        user: data.user,
      });
    },
  });
}

export function useForgotPasswordMutation() {
  return useMutation({
    mutationFn: async (body: ForgotPasswordPayload) => {
      const { data, error } = await apiClient.POST("/api/v1/auth/forgot", { body });
      if (error || !data) throw new ApiError(error);
      return data;
    },
  });
}

export function useResetPasswordMutation() {
  return useMutation({
    mutationFn: async (body: ResetPasswordPayload) => {
      const { data, error } = await apiClient.POST("/api/v1/auth/reset", { body });
      if (error || !data) throw new ApiError(error);
      return data;
    },
  });
}
