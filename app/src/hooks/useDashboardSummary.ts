// Fetch dashboard summary KPIs with deterministic fallback (tc.v1).

import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { DashboardSummary } from "../lib/types";
import { MOCK_DASHBOARD_SUMMARY } from "../lib/mock-provider";

export function useDashboardSummary() {
  return useQuery<DashboardSummary>({
    queryKey: ["dashboard-summary"],
    queryFn: async (): Promise<DashboardSummary> => {
      try {
        const data = await api.getDashboardSummary();
        return data || MOCK_DASHBOARD_SUMMARY;
      } catch {
        return MOCK_DASHBOARD_SUMMARY;
      }
    },
    initialData: MOCK_DASHBOARD_SUMMARY,
  });
}
