import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { ApiError } from "@/lib/errors";

async function getUsage(month?: string) {
  const { data, error } = await apiClient.GET("/api/v1/usage", {
    params: month ? { query: { month } } : undefined,
  });

  if (error) {
    throw new ApiError(error);
  }

  return data;
}

export function useUsageQuery(month?: string) {
  return useQuery({
    queryKey: ["usage", month ?? "current"],
    queryFn: () => getUsage(month),
  });
}

export {
  usePlansQuery,
  useSubscribeMutation,
  type PlanOut,
  type SubscribeRequest,
  type SubscribeResponse,
} from "@/api/hooks/plans";

export {
  useCreatePondMutation,
  useGetConnection,
  useGetPond,
  useListBackups,
  usePondsQuery,
  useRestoreBackupMutation,
  pondIsTransient,
  type Backup,
  type Connection,
  type Pond,
  type PondObservedState,
} from "@/api/hooks/ponds";

export { useMeQuery, type MeResponse } from "@/api/hooks/me";

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

export {
  useAgentAccessQuery,
  useRotateAgentPasswordMutation,
  useToggleAgentAccessMutation,
  type AgentAccess,
  type AgentAccessSecret,
} from "@/api/hooks/agent-access";

export {
  useRunSqlMutation,
  useSqlHistoryQuery,
  type RunSQLRequest,
  type SQLHistoryItem,
  type SQLHistoryResponse,
  type SQLMode,
  type SQLResultResponse,
} from "@/api/hooks/sql-console";

export {
  SUSPEND_CONFIRM_TEXT,
  useAdminAuditQuery,
  useAdminPondsQuery,
  useAdminUsersQuery,
  useReactivateUserMutation,
  useSuspendUserMutation,
  type AdminPond,
  type AdminUser,
  type AuditEvent,
} from "@/api/hooks/admin";
