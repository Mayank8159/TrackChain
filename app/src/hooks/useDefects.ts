// Hook to fetch defect events with filters, gated by DEMO vs REAL mode (tc.v1).

import { api } from "../lib/api";
import type { DefectEvent } from "../lib/types";
import { MOCK_DEFECTS } from "../lib/mock-provider";
import { useRoutedData } from "../lib/data-router";

export interface DefectFilters {
  sessionId?: string;
  severity?: string;
  defectClass?: string;
}

export function useDefects(filters?: DefectFilters, pollIntervalMs = 0) {
  const filterMockDefects = (): DefectEvent[] => {
    return MOCK_DEFECTS.filter((d) => {
      if (filters?.sessionId && d.sessionId !== filters.sessionId) return false;
      if (filters?.severity && filters.severity !== "all" && d.severity !== filters.severity) return false;
      if (filters?.defectClass && filters.defectClass !== "all" && d.defectClass !== filters.defectClass) return false;
      return true;
    });
  };

  const routed = useRoutedData<DefectEvent[]>({
    queryKey: ["defects", filters?.sessionId, filters?.severity, filters?.defectClass],
    demoData: filterMockDefects,
    fetchReal: () => api.getDefects(filters),
    refetchInterval: pollIntervalMs || undefined,
  });

  return {
    defects: routed.data || [],
    loading: routed.isLoading,
    isLoading: routed.isLoading,
    isError: routed.isError,
    error: routed.error ? routed.error.message : null,
    isDemoData: routed.isDemo,
    refetch: routed.refetch,
  };
}
