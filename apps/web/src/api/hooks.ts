import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { ApiError } from "@/lib/errors";

async function listPlans() {
  const { data, error } = await apiClient.GET("/api/v1/plans", {});
  if (error) {
    throw new ApiError(error);
  }

  return data?.plans ?? [];
}

async function getUsage(month?: string) {
  const { data, error } = await apiClient.GET("/api/v1/usage", {
    params: month ? { query: { month } } : undefined,
  });

  if (error) {
    throw new ApiError(error);
  }

  return data;
}

export function usePlansQuery() {
  return useQuery({
    queryKey: ["plans"],
    queryFn: listPlans,
  });
}

export function useUsageQuery(month?: string) {
  return useQuery({
    queryKey: ["usage", month ?? "current"],
    queryFn: () => getUsage(month),
  });
}

export {
  useGetConnection,
  useGetPond,
  useListBackups,
  usePondsQuery,
  useRestoreBackupMutation,
  type Backup,
  type Connection,
  type Pond,
  type PondObservedState,
} from "@/api/hooks/ponds";

export {
  useForgotPasswordMutation,
  useLoginMutation,
  useRegisterMutation,
  useResetPasswordMutation,
  useVerifyEmailMutation,
  type ForgotPasswordPayload,
  type LoginPayload,
  type RegisterPayload,
  type ResetPasswordPayload,
  type VerifyEmailPayload,
} from "@/api/hooks/auth";

export {
  downloadInvoicePdf,
  useInvoiceQuery,
  useInvoicesQuery,
} from "@/api/hooks/invoices";

