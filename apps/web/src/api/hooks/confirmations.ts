import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { ConfirmationToken } from "@/features/confirm/proposal";
import { ApiError } from "@/lib/errors";

export function useConfirmActionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (token: ConfirmationToken): Promise<void> => {
      const { error } = await apiClient.POST("/api/v1/confirm/{token}", {
        params: { path: { token } },
      });
      if (error) {
        throw new ApiError(error);
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries();
    },
  });
}

export function useDiscardConfirmationMutation() {
  return useMutation({
    mutationFn: async (token: ConfirmationToken): Promise<void> => {
      const { error } = await apiClient.DELETE("/api/v1/confirm/{token}", {
        params: { path: { token } },
      });
      if (error) {
        throw new ApiError(error);
      }
    },
  });
}
