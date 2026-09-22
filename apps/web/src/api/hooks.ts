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

async function listPonds() {
  const { data, error } = await apiClient.GET("/api/v1/ponds", {});
  if (error) {
    throw new ApiError(error);
  }

  return data?.ponds ?? [];
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

export function usePondsQuery() {
  return useQuery({
    queryKey: ["ponds"],
    queryFn: listPonds,
  });
}

export function useUsageQuery(month?: string) {
  return useQuery({
    queryKey: ["usage", month ?? "current"],
    queryFn: () => getUsage(month),
  });
}
