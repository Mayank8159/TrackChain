// Hook to fetch telemetry series for a session, gated by DEMO vs REAL mode (tc.v1).

import { api } from "../lib/api";
import type { TelemetryPoint } from "../lib/types";
import { MOCK_TELEMETRY_SERIES } from "../lib/mock-provider";
import { useRoutedData } from "../lib/data-router";

export function useTelemetry(sessionId?: string, pollIntervalMs = 0) {
  const routed = useRoutedData<TelemetryPoint[]>({
    queryKey: ["telemetry", sessionId],
    demoData: MOCK_TELEMETRY_SERIES,
    fetchReal: async () => {
      if (!sessionId) return MOCK_TELEMETRY_SERIES;
      return api.getTelemetrySeries(sessionId);
    },
    enabled: !!sessionId,
    refetchInterval: pollIntervalMs || undefined,
  });

  return {
    data: routed.data || [],
    loading: routed.isLoading,
    isLoading: routed.isLoading,
    isError: routed.isError,
    error: routed.error ? routed.error.message : null,
    isDemoData: routed.isDemo,
    refetch: routed.refetch,
  };
}
