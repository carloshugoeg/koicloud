import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { ApiError } from "@/lib/errors";

export type Pond = components["schemas"]["PondOut"];
export type PondObservedState = components["schemas"]["PondObservedState"];

const TRANSIENT_STATES = new Set<PondObservedState>([
  "provisioning",
  "restoring",
  "deleting",
]);

async function listPonds(): Promise<Pond[]> {
  const { data, error } = await apiClient.GET("/api/v1/ponds", {});
  if (error) {
    throw new ApiError(error);
  }
  return data?.ponds ?? [];
}

function pondsNeedPolling(ponds: Pond[] | undefined): boolean {
  return Boolean(ponds?.some((pond) => TRANSIENT_STATES.has(pond.observed_state)));
}

export function usePondsQuery() {
  return useQuery({
    queryKey: ["ponds"],
    queryFn: listPonds,
    refetchInterval: (query) => (pondsNeedPolling(query.state.data) ? 4_000 : false),
  });
}
