// Hook to fetch and compute real-time pipeline performance observatory metrics (tc.v1).

import { useQuery } from "@tanstack/react-query";
import { usePerformanceStore } from "../stores/performance-store";
import { useModeStore } from "../stores/mode-store";
import { api } from "../lib/api";
import type { PerformanceMetrics } from "../lib/types";

export function usePerformance(windowSeconds = 300) {
  const { mode } = useModeStore();
  const { traces, getMetrics, addTrace } = usePerformanceStore();

  const isDemo = mode === "DEMO";

  const { data: realMetrics, isLoading, isError, refetch } = useQuery<PerformanceMetrics>({
    queryKey: ["performance-metrics", windowSeconds],
    queryFn: async () => {
      return api.request<PerformanceMetrics>(`/api/dashboard/performance?window=${windowSeconds}`);
    },
    enabled: !isDemo,
    refetchInterval: 5000, // Poll every 5s in REAL mode
  });

  const metrics = isDemo || !realMetrics ? getMetrics() : realMetrics;

  return {
    metrics,
    traces,
    isLoading: !isDemo && isLoading,
    isError: !isDemo && isError,
    refetch,
    addTrace,
    isDemo,
  };
}
